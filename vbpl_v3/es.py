"""Elasticsearch clients: the source is read-only; the target may write only the configured v3 indices."""

import json
import re
from urllib.parse import quote

import requests

from .text import number_key

READ_POST = re.compile(r'^/[^/_][^/]*/(?:_search|_count|_mget)(?:\?.*)?$|^/_search/scroll$')
TARGET_FIELDS = ['document_number', 'title', 'issuing_authority', 'issuance_date', 'legal_type', 'legal_sectors', 'pdf_minio_path', 'origin']


class WriteRefused(RuntimeError):
    """A request would modify an index outside the allowed set."""


class Cluster:
    def __init__(self, url, writable=()):
        self.url = url.rstrip('/')
        self.writable = frozenset(writable)

    def allowed(self, method, path, raw):
        if method in ('GET', 'HEAD') or (method == 'POST' and READ_POST.match(path)) or (method == 'DELETE' and path == '/_search/scroll'):
            return True
        if method == 'DELETE':
            return False  # never drop an index or delete outside the scroll API
        if path.split('?')[0] == '/_bulk':
            targets = {json.loads(line)['index']['_index'] for line in raw.decode('utf-8').splitlines()[0::2] if line.strip()}
            return bool(targets) and targets <= self.writable
        return path.lstrip('/').split('/')[0].split('?')[0] in self.writable

    def request(self, method, path, body=None, raw=None, missing=False):
        payload = raw if raw is not None else json.dumps(body, ensure_ascii=False) if body is not None else None
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        if not self.allowed(method, path, payload):
            raise WriteRefused(f'Refused {method} {path} on {self.url}')
        response = requests.request(method, self.url + path, data=payload, timeout=(10, 120),
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

    def scan(self, index, query, source=True, size=500):
        result = self.request('POST', f'/{index}/_search?scroll=5m', {'size': size, 'sort': ['_doc'], 'query': query, '_source': source})
        scroll = result.get('_scroll_id')
        try:
            while result['hits']['hits']:
                yield from result['hits']['hits']
                result = self.request('POST', '/_search/scroll', {'scroll': '5m', 'scroll_id': scroll})
                scroll = result.get('_scroll_id', scroll)
        finally:
            if scroll:
                self.request('DELETE', '/_search/scroll', {'scroll_id': [scroll]})

    def by_numbers(self, index, numbers):
        """Documents whose number matches any given number, tolerating legacy case/whitespace/dash variants."""
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
                for hit in self.scan(index, {'regexp': {'document_number': {'value': pattern}}}, TARGET_FIELDS):
                    if number_key(hit['_source'].get('document_number')) == key:
                        results[hit['_id']] = hit
        return list(results.values())

    # Writes: every one passes allowed(), so only indices in self.writable can change.
    def create_index(self, index, body):
        return self.request('PUT', f'/{index}', body)

    def put(self, index, doc_id, source):
        return self.request('PUT', f'/{index}/_doc/{quote(str(doc_id), safe="")}', source)

    def bulk(self, index, records):
        def send(batch):
            lines = []
            for record in batch:
                lines += [json.dumps({'index': {'_index': index, '_id': record['_id']}}), json.dumps(record['_source'], ensure_ascii=False)]
            try:
                result = self.request('POST', '/_bulk', raw='\n'.join(lines) + '\n')
            except requests.HTTPError as error:
                if error.response.status_code != 413 or len(batch) == 1:
                    raise
                send(batch[:len(batch) // 2])
                send(batch[len(batch) // 2:])
                return
            errors = [item for item in result.get('items', []) if next(iter(item.values())).get('error')]
            if result.get('errors') or errors or len(result.get('items', [])) != len(batch):
                raise RuntimeError('ES bulk failed: ' + json.dumps(errors[:3], ensure_ascii=False))
        batch, size = [], 0
        for record in records:
            length = len(json.dumps(record['_source'], ensure_ascii=False).encode('utf-8')) + 100
            if batch and (len(batch) >= 300 or size + length > 8 * 1024 * 1024):
                send(batch)
                batch, size = [], 0
            batch.append(record)
            size += length
        if batch:
            send(batch)

    def remove_group(self, index, field, value):
        result = self.request('POST', f'/{index}/_delete_by_query?refresh=true&conflicts=abort', {'query': {'term': {field: value}}})
        if result.get('version_conflicts'):
            raise RuntimeError('Delete-by-query version conflict')
