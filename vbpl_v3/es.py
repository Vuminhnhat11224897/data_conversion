"""Elasticsearch clients: the source is read-only; the target may write only the configured v3 indices."""

import gzip
import json
import os
from pathlib import Path
import random
import re
import time
from urllib.parse import quote

import requests

from .text import number_key

READ_POST = re.compile(r'^/[^/_][^/]*/(?:_search|_count|_mget)(?:\?.*)?$|^/_search/scroll$')
REGEX_LIMIT = 900  # below Elasticsearch's default index.max_regex_length (1000)
TARGET_FIELDS = ['document_number', 'title', 'issuing_authority', 'issuance_date', 'legal_type', 'legal_sectors', 'pdf_minio_path', 'origin']
NUMBER_INDEX_AGE = 7 * 86400  # seconds: the local table of document numbers is rebuilt at least weekly


# Waits before sending a bulk batch again after a dropped connection, a timeout or a busy cluster (seconds). Each wait gets up to
# 30% more at random, so workers that failed together do not all send again at the same moment.
BULK_RETRY_WAITS = (5, 15, 30, 60)
RETRY_STATUS = {429, 502, 503, 504}
# A batch holds at most 300 records and about ES_BULK_BYTES bytes: 300 chunks with their vectors are near 7 MB, too much for one
# request over the lossy VPN in 120 seconds (04/11/2026).
BULK_RECORDS = 300
BULK_BYTES = int(os.getenv('ES_BULK_BYTES', str(4 * 1024 * 1024)))


class WriteIncomplete(RuntimeError):
    """Records read back after a write are missing, from another run, or old records of the document are still there."""


def pause(wait):
    time.sleep(wait * (1 + random.uniform(0, 0.3)))


class WriteRefused(RuntimeError):
    """A request would modify an index outside the allowed set."""


class Cluster:
    def __init__(self, url, writable=()):
        self.url = url.rstrip('/')
        self.writable = frozenset(writable)
        # One pool of kept-alive connections for the worker threads: a new connection per request costs a handshake each time.
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=32)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.numbers = None  # (index, {number_key: [ids]}) once use_number_index() has run

    def allowed(self, method, path, raw):
        if method in ('GET', 'HEAD') or (method == 'POST' and READ_POST.match(path)) or (method == 'DELETE' and path == '/_search/scroll'):
            return True
        if method == 'DELETE':
            return False  # never drop an index or delete outside the scroll API
        if path.split('?')[0] == '/_bulk':
            # Every action line (index, update) names its index; a line without one is refused.
            targets = {next(iter(json.loads(line).values())).get('_index') for line in raw.decode('utf-8').splitlines()[0::2] if line.strip()}
            return bool(targets) and targets <= self.writable
        return path.lstrip('/').split('/')[0].split('?')[0] in self.writable

    def request(self, method, path, body=None, raw=None, missing=False):
        payload = raw if raw is not None else json.dumps(body, ensure_ascii=False) if body is not None else None
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        if not self.allowed(method, path, payload):
            raise WriteRefused(f'Refused {method} {path} on {self.url}')
        response = self.session.request(method, self.url + path, data=payload, timeout=(10, 120),
            headers={'Content-Type': 'application/x-ndjson' if raw is not None else 'application/json'})
        if missing and response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json() if response.content else {}
        if isinstance(data, dict) and (data.get('timed_out') or data.get('_shards', {}).get('failed') or data.get('failures')):
            raise RuntimeError('Elasticsearch query/write was incomplete')
        return data

    def exists(self, index):
        return self.request('GET', f'/{index}/_mapping', missing=True) is not None

    def get(self, index, doc_id):
        return self.request('GET', f'/{index}/_doc/{quote(str(doc_id), safe="")}', missing=True)

    def count(self, index, query=None):
        return self.request('POST', f'/{index}/_count', {'query': query} if query else None)['count']

    def scan(self, index, query, source=True, size=500, seq_no=False):
        """Every hit of the query, in index order. One request when the hits fit in one page; a scroll otherwise (a scroll costs two
        more requests: the empty last page and its release). seq_no: each hit carries _seq_no and _primary_term, for a write that
        must not land on a record changed since it was read."""
        body = {'size': size, 'sort': ['_doc'], 'query': query, '_source': source, **({'seq_no_primary_term': True} if seq_no else {})}
        page = self.request('POST', f'/{index}/_search', body)
        if len(page['hits']['hits']) < size:
            yield from page['hits']['hits']
            return
        result = self.request('POST', f'/{index}/_search?scroll=5m', body)
        scroll = result.get('_scroll_id')
        try:
            while result['hits']['hits']:
                yield from result['hits']['hits']
                result = self.request('POST', '/_search/scroll', {'scroll': '5m', 'scroll_id': scroll})
                scroll = result.get('_scroll_id', scroll)
        finally:
            if scroll:
                self.request('DELETE', '/_search/scroll', {'scroll_id': [scroll]})

    def use_number_index(self, index, folder):
        """Look document numbers up in a local table (number_key -> ids) built from one scan of the index and kept in folder. A
        tolerant regexp query per number takes 1-2 s on the 518,261 source documents (measured 21/10/2026); the table answers at
        once. It is rebuilt when the index's document count changes or after NUMBER_INDEX_AGE."""
        path = Path(folder) / f'number-index-{index}.json.gz'
        count, table = self.count(index), None
        if path.exists():
            try:
                stored = json.loads(gzip.decompress(path.read_bytes()))
                if stored['count'] == count and time.time() - stored['built'] < NUMBER_INDEX_AGE:
                    table = stored['keys']
            except (OSError, ValueError, KeyError):
                table = None
        if table is None:
            table = {}
            for hit in self.scan(index, {'match_all': {}}, ['document_number'], size=10000):
                key = number_key((hit.get('_source') or {}).get('document_number') or '')
                if key:
                    table.setdefault(key, []).append(hit['_id'])
            path.parent.mkdir(parents=True, exist_ok=True)
            part = path.with_name(f'{path.name}.{os.getpid()}.part')
            part.write_bytes(gzip.compress(json.dumps({'count': count, 'built': time.time(), 'keys': table}, ensure_ascii=False).encode(), 6))
            part.replace(path)  # atomic: parallel runs never read a half-written table
        self.numbers = (index, table)

    def by_numbers(self, index, numbers):
        """Documents whose number matches any given number, tolerating legacy case/whitespace/dash variants."""
        if self.numbers and self.numbers[0] == index:
            # number_key is the tolerance the search below filters on; the table holds every document by it.
            ids = list(dict.fromkeys(i for key in dict.fromkeys(number_key(n) for n in numbers) for i in self.numbers[1].get(key, ())))
            return [hit for start in range(0, len(ids), 500) for hit in self.scan(index, {'ids': {'values': ids[start:start + 500]}}, TARGET_FIELDS)]
        results = {}
        for start in range(0, len(numbers), 500):
            batch = numbers[start:start + 500]
            variants = list({v for n in batch for v in (n, n.upper(), n.lower())})
            for hit in self.scan(index, {'terms': {'document_number': variants}}, TARGET_FIELDS):
                results[hit['_id']] = hit
            for key in dict.fromkeys(number_key(number) for number in batch):
                # Only a document number gets the tolerant search. A law named by name ("Bộ luật Dân sự, quy định của …") has no digit
                # and is matched by name elsewhere; a long text would also exceed the server's limit on a regular expression.
                if not key or len(key) > 60 or not re.search(r'\d', key):
                    continue
                gap = '[ \t\r\n\v\f\u001c-\u001f\u0085   -‍    ⁠　﻿]*'
                chars = []
                for char in key:
                    if char == '-':
                        chars.append('[-–—]')
                    elif char.isalpha() and char.lower() != char.upper():
                        chars.append('[' + char.lower() + char.upper() + ']')
                    else:
                        chars.append('\\' + char if char in '.?+*|{}[]()"\\#@&<>~' else char)
                pattern = gap + ('(0' + gap + ')*' if re.match(r'\d+/', key) else '') + gap.join(chars) + gap
                if len(pattern) > REGEX_LIMIT:
                    # A long joint number ("05/2013/TTLT-UBDT-NNPTNT-KHĐT-TC-XD") with the full set of gaps passes the server's
                    # limit on a regular expression (index.max_regex_length): spaces only between its characters.
                    short = '[ ]*'
                    pattern = short + ('(0' + short + ')*' if re.match(r'\d+/', key) else '') + short.join(chars) + short
                if len(pattern) > REGEX_LIMIT:
                    continue
                try:
                    for hit in self.scan(index, {'regexp': {'document_number': {'value': pattern}}}, TARGET_FIELDS):
                        if number_key(hit['_source'].get('document_number')) == key:
                            results[hit['_id']] = hit
                except requests.HTTPError as error:
                    if error.response is None or error.response.status_code != 400:
                        raise
                    # The server refuses this one expression: the exact search above stands for this number.
        return list(results.values())

    # Writes: every one passes allowed(), so only indices in self.writable can change.
    def create_index(self, index, body):
        return self.request('PUT', f'/{index}', body)

    def put(self, index, doc_id, source):
        return self.request('PUT', f'/{index}/_doc/{quote(str(doc_id), safe="")}', source)

    def bulk(self, index, records, action='index', skip_status=()):
        """Write records {'_id', '_source'} in batches. action 'update': _source is the partial document, and a record may carry
        if_seq_no / if_primary_term so the update never lands on a record rewritten since it was read. Returns the _id of the
        records refused with a status in skip_status (409 for such an update); any other refusal raises once retries are spent."""
        skipped = []

        def post(raw):
            # A batch writes by _id, so sending it again changes nothing that was already written. The VPN to the cluster drops
            # 20-33% of packets; one lost batch used to leave a document with its first 300, 600 … chunks only (E1, 03/11/2026).
            for wait in (*BULK_RETRY_WAITS, None):
                try:
                    return self.request('POST', '/_bulk', raw=raw)
                except (requests.ConnectionError, requests.Timeout) as error:
                    failure = error
                except requests.HTTPError as error:
                    if error.response is None or error.response.status_code not in RETRY_STATUS:
                        raise
                    failure = error
                if wait is None:
                    raise failure
                pause(wait)

        def lines(record):
            head = {'_index': index, '_id': record['_id'], **{k: record[k] for k in ('if_seq_no', 'if_primary_term') if k in record}}
            body = {'doc': record['_source']} if action == 'update' else record['_source']
            return [json.dumps({action: head}), json.dumps(body, ensure_ascii=False)]

        def send(batch):
            waits = iter(BULK_RETRY_WAITS)
            while batch:
                try:
                    result = post('\n'.join(line for record in batch for line in lines(record)) + '\n')
                except requests.HTTPError as error:
                    if error.response is None or error.response.status_code != 413 or len(batch) == 1:
                        raise
                    send(batch[:len(batch) // 2])
                    send(batch[len(batch) // 2:])
                    return
                items = result.get('items', [])
                if len(items) != len(batch):
                    raise RuntimeError(f'ES bulk failed: {len(items)} kết quả cho {len(batch)} bản ghi')
                # HTTP 200 with errors=true: each item says whether it was written. A busy shard (429, 503) refuses some items only;
                # those are sent again, the others stand.
                retry, fatal, refused = [], [], 0
                for record, item in zip(batch, items):
                    status = next(iter(item.values()))
                    if not status.get('error'):
                        continue
                    refused += 1
                    if status.get('status') in skip_status:
                        skipped.append(record['_id'])
                    elif status.get('status') in RETRY_STATUS:
                        retry.append(record)
                    else:
                        fatal.append(status)
                if fatal:
                    raise RuntimeError('ES bulk failed: ' + json.dumps(fatal[:3], ensure_ascii=False))
                if result.get('errors') and not refused:
                    raise RuntimeError('ES bulk failed: errors=true nhưng không item nào báo lỗi')
                if retry:
                    wait = next(waits, None)
                    if wait is None:
                        raise RuntimeError(f'ES bulk failed: {len(retry)} bản ghi vẫn bị từ chối sau {len(BULK_RETRY_WAITS)} lần gửi lại')
                    pause(wait)
                batch = retry

        batch, size = [], 0
        for record in records:
            length = len(json.dumps(record['_source'], ensure_ascii=False).encode('utf-8')) + 100
            if batch and (len(batch) >= BULK_RECORDS or size + length > BULK_BYTES):
                send(batch)
                batch, size = [], 0
            batch.append(record)
            size += length
        if batch:
            send(batch)
        return skipped

    def verify_written(self, index, field, value, records, job):
        """Read back the records one document's write produced: each is there with this run's ingest_job_id (a realtime get, no
        refresh needed), and no other record of the document is left (remove_stale runs first). Raises WriteIncomplete."""
        ids = [r['_id'] for r in records]
        bad = []
        for start in range(0, len(ids), 1000):
            docs = self.request('POST', f'/{index}/_mget?_source_includes=ingest_job_id', {'ids': ids[start:start + 1000]})['docs']
            bad += [d['_id'] for d in docs if not d.get('found') or (d.get('_source') or {}).get('ingest_job_id') != job]
        left = self.count(index, {'bool': {'filter': [{'term': {field: value}}], 'must_not': [{'ids': {'values': ids}}] if ids else []}})
        if bad or left:
            raise WriteIncomplete(f'{index} {field}={value}: {len(bad)} bản ghi thiếu hoặc khác lượt (ví dụ {bad[:3]}), '
                                  f'{left} bản ghi cũ còn lại')

    def remove_stale(self, index, field, value, keep):
        """Delete the records of one document (field = value) whose _id is not in keep: what a rewrite no longer produces. Run after
        the new records are written, so a failure part way leaves the old records, never a document with part of its chunks."""
        query = {'bool': {'filter': [{'term': {field: value}}], 'must_not': [{'ids': {'values': sorted(keep)}}] if keep else []}}
        if not self.count(index, query):
            return
        result = self.request('POST', f'/{index}/_delete_by_query?refresh=true&conflicts=abort', {'query': query})
        if result.get('version_conflicts'):
            raise RuntimeError('Delete-by-query version conflict')

    def remove_group(self, index, field, value):
        result = self.request('POST', f'/{index}/_delete_by_query?refresh=true&conflicts=abort', {'query': {'term': {field: value}}})
        if result.get('version_conflicts'):
            raise RuntimeError('Delete-by-query version conflict')
