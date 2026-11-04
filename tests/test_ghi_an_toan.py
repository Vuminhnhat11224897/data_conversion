"""Group A (04/11/2026): a write that fails at any step loses nothing and is found; the source is checked; missing targets are
linked again. es.Cluster runs as in production; only its HTTP session talks to an in-memory Elasticsearch that can fail on purpose."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit, parse_qs

import requests

from vbpl_v3 import es, integrity, source_guard
from vbpl_v3.convert import write_document
from vbpl_v3.es import Cluster, WriteIncomplete
from vbpl_v3.relations import resolve
from vbpl_v3.relink import relink
from vbpl_v3.text import number_key
from tests.test_guard import config

DOCS, CHUNKS, CHANGES = 'legal-docs-v3', 'legal-chunk-section-v3', 'legal-changed-v3'


def matches(query, row, _id):
    if not query or 'match_all' in query:
        return True
    if 'term' in query:
        field, value = next(iter(query['term'].items()))
        return row.get(field) == value
    if 'ids' in query:
        return _id in query['ids']['values']
    if 'exists' in query:
        return row.get(query['exists']['field']) is not None
    if 'bool' in query:
        b = query['bool']
        return all(matches(q, row, _id) for q in b.get('filter', []) + b.get('must', [])) and \
            not any(matches(q, row, _id) for q in b.get('must_not', []))
    raise ValueError(query)


class FakeElastic:
    """Enough of Elasticsearch for es.Cluster: _bulk (index, update with if_seq_no), PUT _doc, _count, _delete_by_query, _mget,
    _search (hits with seq_no, composite aggregation). bulk_fault(call, actions) may raise, return a reply, or return None."""

    def __init__(self):
        self.indices, self.seq, self.bulk_calls, self.bulk_fault, self.after_search = {}, 0, 0, None, None

    def store(self, index, _id, source):
        self.seq += 1
        self.indices.setdefault(index, {})[_id] = {'_source': dict(source), '_seq_no': self.seq, '_primary_term': 1}

    def rows(self, index):
        return self.indices.get(index, {})

    def reply(self, status, body):
        response = Mock(status_code=status, content=json.dumps(body).encode())
        response.json = lambda: body
        if status >= 400:
            response.raise_for_status = Mock(side_effect=requests.HTTPError(f'{status}', response=response))
        else:
            response.raise_for_status = lambda: None
        return response

    def __call__(self, method, url, data=None, timeout=None, headers=None):
        parts = urlsplit(url)
        path, args = parts.path, parse_qs(parts.query)
        text = data.decode('utf-8') if isinstance(data, bytes) else data
        if path == '/_bulk':
            return self.bulk(text)
        if path == '/_search/scroll':
            return self.reply(200, {})
        body = json.loads(text) if text else {}
        index, _, op = path.strip('/').partition('/')
        if method == 'PUT' and op.startswith('_doc/'):
            self.store(index, op[5:], body)
            return self.reply(200, {'result': 'updated'})
        if op == '_count':
            return self.reply(200, {'count': sum(matches(body.get('query'), r['_source'], i) for i, r in self.rows(index).items())})
        if op == '_delete_by_query':
            gone = [i for i, r in self.rows(index).items() if matches(body['query'], r['_source'], i)]
            for i in gone:
                del self.indices[index][i]
            return self.reply(200, {'deleted': len(gone), 'version_conflicts': 0})
        if op == '_mget':
            fields = args.get('_source_includes', [''])[0].split(',')
            docs = [{'_id': i, 'found': i in self.rows(index), **({'_source': {f: self.rows(index)[i]['_source'].get(f) for f in fields}}
                                                                  if i in self.rows(index) else {})} for i in body['ids']]
            return self.reply(200, {'docs': docs})
        if op == '_search':
            if 'aggs' in body:
                comp = body['aggs']['c']['composite']
                field = comp['sources'][0]['k']['terms']['field']
                counts = {}
                for r in self.rows(index).values():
                    key = (r['_source'].get(field), r['_source'].get('ingest_job_id'))
                    counts[key] = counts.get(key, 0) + 1
                keys = sorted(counts, key=lambda k: (str(k[0]), str(k[1])))
                if 'after' in comp:
                    keys = [k for k in keys if (str(k[0]), str(k[1])) > (str(comp['after']['k']), str(comp['after']['j']))]
                page = keys[:comp['size']]
                buckets = [{'key': {'k': k, 'j': j}, 'doc_count': counts[(k, j)]} for k, j in page]
                return self.reply(200, {'aggregations': {'c': {'buckets': buckets, **({'after_key': buckets[-1]['key']} if buckets else {})}}})
            hits = []
            for i, r in self.rows(index).items():
                if matches(body.get('query'), r['_source'], i):
                    source = r['_source'] if body.get('_source', True) is True else (
                        {f: r['_source'].get(f) for f in body['_source']} if body.get('_source') else {})
                    hits.append({'_id': i, '_source': source, **({'_seq_no': r['_seq_no'], '_primary_term': 1} if body.get('seq_no_primary_term') else {})})
            if self.after_search:
                self.after_search(index)
            return self.reply(200, {'hits': {'hits': hits[:body.get('size', 10)]}})
        raise AssertionError(f'{method} {path}')

    def bulk(self, text):
        self.bulk_calls += 1
        lines = [json.loads(x) for x in text.splitlines() if x.strip()]
        actions = list(zip(lines[0::2], lines[1::2]))
        fault = self.bulk_fault(self.bulk_calls, actions) if self.bulk_fault else None
        if isinstance(fault, Exception):
            raise fault
        if fault is not None:
            return fault
        items = []
        for head, body in actions:
            kind, meta = next(iter(head.items()))
            index, _id = meta['_index'], meta['_id']
            if kind == 'update':
                row = self.rows(index).get(_id)
                if row is None:
                    items.append({kind: {'_id': _id, 'status': 404, 'error': {'type': 'document_missing_exception'}}})
                    continue
                if 'if_seq_no' in meta and meta['if_seq_no'] != row['_seq_no']:
                    items.append({kind: {'_id': _id, 'status': 409, 'error': {'type': 'version_conflict_engine_exception'}}})
                    continue
                self.store(index, _id, {**row['_source'], **body['doc']})
            else:
                self.store(index, _id, body)
            items.append({kind: {'_id': _id, 'status': 200}})
        return self.reply(200, {'errors': any('error' in next(iter(i.values())) for i in items), 'items': items})


def records(doc_id, job, n_chunks, n_relations, chunk_ids=None):
    document = {'document_number': f'{doc_id}/QĐ-UBND', 'ingest_job_id': job}
    chunks = [{'_id': cid, '_source': {'doc_id': doc_id, 'noi_dung': f'{job} {cid}', 'ingest_job_id': job}}
              for cid in (chunk_ids or [f'{doc_id}_d{i}' for i in range(1, n_chunks + 1)])]
    relations = [{'_id': f'{doc_id}_{i}', '_source': {'source_id': int(doc_id), 'action': 'bai-bo', 'ingest_job_id': job}}
                 for i in range(n_relations)]
    return document, chunks, relations


class SafeWrite(unittest.TestCase):
    def setUp(self):
        self.es = FakeElastic()
        self.target = Cluster('http://target:9200', writable={DOCS, CHUNKS, CHANGES})
        self.patches = [patch.object(self.target.session, 'request', side_effect=self.es), patch('vbpl_v3.es.BULK_RETRY_WAITS', (0, 0)),
                        patch('vbpl_v3.es.BULK_RECORDS', 100)]
        for p in self.patches:
            p.start()
        self.config = config()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def write(self, doc_id, job, n_chunks, n_relations=0, chunk_ids=None, qa=True):
        document, chunks, relations = records(doc_id, job, n_chunks, n_relations, chunk_ids)
        write_document(self.target, self.config, doc_id, document, chunks, relations if qa else None)

    def jobs(self, index, field, value):
        return sorted({r['_source']['ingest_job_id'] for r in self.es.rows(index).values() if r['_source'].get(field) == value})

    def broken(self):
        return {k: v for k, v in integrity.broken(self.target, self.config).items() if v}

    def test_rewrite_replaces_and_drops_what_the_new_parse_no_longer_has(self):
        self.write('900', 'v3:a', 5, 3)
        self.write('900', 'v3:b', 0, 2, chunk_ids=['900_d1', '900_d2', '900_d9'])
        self.assertEqual(sorted(self.es.rows(CHUNKS)), ['900_d1', '900_d2', '900_d9'])
        self.assertEqual(sorted(self.es.rows(CHANGES)), ['900_0', '900_1'])
        self.assertEqual((self.jobs(CHUNKS, 'doc_id', '900'), self.jobs(CHANGES, 'source_id', 900)), (['v3:b'], ['v3:b']))
        self.assertEqual(self.es.rows(DOCS)['900']['_source']['ingest_job_id'], 'v3:b')
        self.assertEqual(self.broken(), {})

    def test_connection_lost_on_a_batch_keeps_every_unit_and_is_found_then_repaired(self):
        # The 686325 case: 700 chunks, the second batch never gets through. Before: the old chunks deleted, 300 new ones left.
        self.write('686325', 'v3:a', 700, 4)
        self.es.bulk_calls = 0
        self.es.bulk_fault = lambda call, actions: requests.ConnectionError('VPN') if call >= 2 else None
        with self.assertRaises(requests.ConnectionError):
            self.write('686325', 'v3:b', 700, 4)
        self.assertEqual(self.es.bulk_calls, 4)  # the batch was sent 3 times (2 waits), then the write gave up
        self.assertEqual(len(self.es.rows(CHUNKS)), 700)  # no unit lost: 100 new, 600 old
        self.assertEqual(self.es.rows(DOCS)['686325']['_source']['ingest_job_id'], 'v3:a')  # the record is still the old one
        self.assertEqual(self.broken(), {'chunk_khac_luot': ['686325']})
        self.es.bulk_fault = None
        self.write('686325', 'v3:c', 700, 4)
        self.assertEqual((len(self.es.rows(CHUNKS)), self.jobs(CHUNKS, 'doc_id', '686325')), (700, ['v3:c']))
        self.assertEqual(self.broken(), {})

    def test_bulk_200_with_an_item_refused_never_writes_the_record(self):
        def refuse(call, actions):
            items = [{'index': {'_id': h['index']['_id'], 'status': 200}} for h, _ in actions]
            items[1] = {'index': {'_id': items[1]['index']['_id'], 'status': 400, 'error': {'type': 'mapper_parsing_exception'}}}
            return self.es.reply(200, {'errors': True, 'items': items})
        self.es.bulk_fault = refuse
        with self.assertRaises(RuntimeError):
            self.write('901', 'v3:a', 3)
        self.assertNotIn('901', self.es.rows(DOCS))
        self.assertEqual(self.broken(), {})  # the refused batch wrote nothing here (the fake applies nothing on a fault)

    def test_busy_shard_items_are_sent_again_alone(self):
        sent = []

        def busy(call, actions):
            sent.append([h['index']['_id'] for h, _ in actions])
            if call == 1:
                for head, body in actions[2:]:
                    self.es.store(CHUNKS, head['index']['_id'], body)
                items = [{'index': {'_id': h['index']['_id'], 'status': 429, 'error': {'type': 'es_rejected_execution_exception'}}} for h, _ in actions[:2]]
                items += [{'index': {'_id': h['index']['_id'], 'status': 201}} for h, _ in actions[2:]]
                return self.es.reply(200, {'errors': True, 'items': items})
            return None
        self.es.bulk_fault = busy
        self.write('902', 'v3:a', 5)
        self.assertEqual(sent[1], ['902_d1', '902_d2'])  # only the refused items went again
        self.assertEqual(self.broken(), {})

    def test_timeout_after_the_cluster_wrote_sends_again_without_duplicates(self):
        def late(call, actions):
            if call == 1:
                for head, body in actions:
                    self.es.store(CHUNKS, head['index']['_id'], body)
                return requests.Timeout('read timeout')
            return None
        self.es.bulk_fault = late
        self.write('903', 'v3:a', 50)
        self.assertEqual(len(self.es.rows(CHUNKS)), 50)
        self.assertEqual(self.broken(), {})

    def test_stopped_before_the_record_is_found_and_repaired(self):
        self.write('904', 'v3:a', 3, 2)
        with patch.object(Cluster, 'put', side_effect=SystemExit('worker killed')), self.assertRaises(SystemExit):
            self.write('904', 'v3:b', 4, 1)
        self.assertEqual(self.broken(), {'chunk_khac_luot': ['904'], 'quan_he_khac_luot': ['904']})
        self.write('904', 'v3:c', 4, 1)
        self.assertEqual(self.broken(), {})

    def test_old_records_left_when_removal_fails_are_found(self):
        self.write('905', 'v3:a', 5, 3)
        with patch.object(Cluster, 'remove_stale', side_effect=requests.Timeout('delete_by_query')), self.assertRaises(requests.Timeout):
            self.write('905', 'v3:b', 2, 1)
        self.assertEqual(self.es.rows(DOCS)['905']['_source']['ingest_job_id'], 'v3:b')
        self.assertEqual(self.broken(), {'chunk_khac_luot': ['905'], 'quan_he_khac_luot': ['905']})

    def test_a_record_the_cluster_lost_fails_the_check(self):
        def lose(call, actions):
            items = []
            for head, body in actions:
                if head['index']['_id'] != '906_d2':
                    self.es.store(CHUNKS, head['index']['_id'], body)
                items.append({'index': {'_id': head['index']['_id'], 'status': 201}})
            return self.es.reply(200, {'errors': False, 'items': items})
        self.es.bulk_fault = lose
        with self.assertRaises(WriteIncomplete):
            self.write('906', 'v3:a', 3)

    def test_writing_the_same_document_again_leaves_one_copy(self):
        for job in ('v3:a', 'v3:b', 'v3:b', 'v3:c'):
            self.write('907', job, 250, 3)
        self.assertEqual((len(self.es.rows(CHUNKS)), len(self.es.rows(CHANGES))), (250, 3))
        self.assertEqual(self.broken(), {})

    def test_no_qa_leaves_the_relations(self):
        self.write('908', 'v3:a', 2, 2)
        self.write('908', 'v3:b', 2, qa=False)
        self.assertEqual(self.jobs(CHANGES, 'source_id', 908), ['v3:a'])
        self.assertEqual(self.broken(), {'quan_he_khac_luot': ['908']})  # said in integrity: --no-qa keeps older relations

    def test_records_without_a_document_and_a_document_without_chunks(self):
        self.es.store(CHUNKS, '909_d1', {'doc_id': '909', 'ingest_job_id': 'v3:a'})
        self.es.store(DOCS, '910', {'ingest_job_id': 'v3:a'})
        report = integrity.broken(self.target, self.config)
        self.assertEqual((report['chunk_khong_van_ban'], report['van_ban_khong_chunk']), (['909'], ['910']))
        self.assertEqual((integrity.to_rewrite(report), integrity.without_record(report)), ({'910'}, {'909'}))


class Source:
    """A source documents index: by_numbers by number_key, count."""

    def __init__(self, docs):
        self.docs = docs

    def count(self, index):
        return len(self.docs)

    def by_numbers(self, index, numbers):
        keys = {number_key(n) for n in numbers}
        return [{'_id': i, '_source': d} for i, d in self.docs.items() if number_key(d['document_number']) in keys]


class SourceGuard(unittest.TestCase):
    def setUp(self):
        self.config = config(workdir=Path(tempfile.mkdtemp()), source_canaries=(('08/2015/NĐ-CP', '263815'),))
        self.docs = {'263815': {'document_number': '08/2015/NĐ-CP', 'issuance_date': '2015-01-21'},
                     **{str(i): {'document_number': f'{i}/QĐ-UBND', 'issuance_date': '2020-01-01'} for i in range(1, 200)}}

    def test_known_number_missing_stops_the_run(self):
        # The 27/10/2026 runs read legal-docs on 10.1.10.10, which has no 263815.
        del self.docs['263815']
        with self.assertRaises(source_guard.SourceCheckFailed):
            source_guard.check(self.config, Source(self.docs))

    def test_a_shrunken_source_stops_the_run(self):
        self.assertEqual(source_guard.check(self.config, Source(self.docs))['count'], 200)
        for i in range(1, 10):
            del self.docs[str(i)]
        with self.assertRaises(source_guard.SourceCheckFailed):
            source_guard.check(self.config, Source(self.docs))

    def test_no_check_configured(self):
        self.assertIsNone(source_guard.check(config(), Source({})))

    def test_canaries_from_text(self):
        self.assertEqual(source_guard.canaries('08/2015/NĐ-CP=263815; 98/2020/TT-BTC=461197'), (('08/2015/NĐ-CP', '263815'), ('98/2020/TT-BTC', '461197')))
        self.assertEqual(source_guard.canaries('off'), ())
        with self.assertRaises(ValueError):
            source_guard.canaries('08/2015/NĐ-CP')


class Relink(unittest.TestCase):
    def setUp(self):
        self.es = FakeElastic()
        self.target = Cluster('http://target:9200', writable={DOCS, CHUNKS, CHANGES})
        self.patch = patch.object(self.target.session, 'request', side_effect=self.es)
        self.patch.start()
        self.config = config()
        relation = {'source_id': 577436, 'source_issuance_date': '2025-06-30', 'source_issuing_authority': 'Chính phủ', 'action': 'sua-doi',
                    'target_doc': '08/2015/NĐ-CP', 'target_candidates_count': 0, 'target_issuance_date': '2015-01-21',
                    'evidence': 'Sửa đổi, bổ sung khoản 1 như sau:', 'ingest_job_id': 'v3:a'}
        self.es.store(CHANGES, '577436_0', relation)
        self.es.store(CHANGES, '577436_1', {**relation, 'target_doc': 'Luật Đất đai'})  # a law by name is not looked up here
        self.es.store(CHANGES, '577436_2', {**relation, 'target_doc': '72/2023/NĐ-CP', 'target_matched_id': 580611})
        self.source = Source({'263815': {'document_number': '08/2015/NĐ-CP', 'issuance_date': '2015-01-21', 'issuing_authority': 'Chính phủ'},
                              '37690': {'document_number': '21-LCT/HĐNN8', 'issuance_date': '1989-06-30', 'issuing_authority': 'Quốc hội'}})

    def tearDown(self):
        self.patch.stop()

    def test_dry_run_reads_only(self):
        self.assertEqual(relink(self.config, self.source, self.target)['linked'], 1)
        self.assertNotIn('target_matched_id', self.es.rows(CHANGES)['577436_0']['_source'])
        self.assertEqual(self.es.bulk_calls, 0)

    def test_a_dash_number_is_linked(self):
        self.es.store(CHANGES, '443680_27', {'source_id': 443680, 'source_issuance_date': '2008-01-01', 'source_issuing_authority': 'Quốc hội',
                                             'target_doc': '21-LCT/HĐNN8', 'target_candidates_count': 0, 'evidence': 'Bãi bỏ cụm từ', 'ingest_job_id': 'v3:a'})
        relink(self.config, self.source, self.target, write=True)
        self.assertEqual(self.es.rows(CHANGES)['443680_27']['_source']['target_matched_id'], 37690)

    def test_links_the_missing_target(self):
        summary = relink(self.config, self.source, self.target, write=True)
        self.assertEqual((summary['checked'], summary['linked'], summary['written'], summary['conflicts']), (1, 1, 1, 0))
        row = self.es.rows(CHANGES)['577436_0']['_source']
        self.assertEqual((row['target_matched_id'], row['target_candidates_count'], row['action']), (263815, 1, 'sua-doi'))

    def test_a_relation_rewritten_since_it_was_read_is_not_touched(self):
        def rewrite(index):
            # The document is converted again between the read and the update: the relation has new content.
            self.es.store(CHANGES, '577436_0', {**self.es.rows(CHANGES)['577436_0']['_source'], 'action': 'bai-bo'})
            self.es.after_search = None
        self.es.after_search = rewrite
        summary = relink(self.config, self.source, self.target, write=True)
        self.assertEqual((summary['written'], summary['conflicts']), (0, 1))
        self.assertNotIn('target_matched_id', self.es.rows(CHANGES)['577436_0']['_source'])


class DashNumber(unittest.TestCase):
    def test_party_and_old_numbers_are_looked_up(self):
        from vbpl_v3.relations import is_number
        self.assertTrue(all(is_number(n) for n in ('338-QĐ/TW', '36-CP', '19-BYT/TT', '21-LCT/HĐNN8', '08/2015/NĐ-CP')))
        self.assertFalse(any(is_number(n) for n in ('Luật Đất đai', '2-3', '')))

    def test_the_cited_day_after_a_dash_number_picks_the_right_year(self):
        # 674437_0: "thay thế Quy định số 338-QĐ/TW, ngày 26/11/2010" was linked to the 338-QĐ/TW of 2025 (the latest one).
        hits = [{'_id': i, '_source': {'document_number': '338-QĐ/TW', 'issuance_date': d, 'issuing_authority': 'Ban Chấp hành Trung ương'}}
                for i, d in (('665419', '2025-07-09'), ('429311', '2010-11-26'))]
        row = resolve({'target_doc': '338-QĐ/TW', 'source_id': 674437, 'source_issuance_date': '2025-09-01',
                       'source_issuing_authority': 'Ban Chấp hành Trung ương',
                       '_evidence': 'thay thế Quy định số 338-QĐ/TW, ngày 26/11/2010 về chức năng, nhiệm vụ'}, hits)
        self.assertEqual(row['target_matched_id'], 429311)
        hits = [{'_id': i, '_source': {'document_number': '12-HD/BTCTW', 'issuance_date': d, 'issuing_authority': 'Ban Tổ chức Trung ương'}}
                for i, d in (('1', '2022-01-18'), ('2', '2018-07-06'))]
        row = resolve({'target_doc': '12-HD/BTCTW', 'source_id': 679297, 'source_issuance_date': '2025-01-01',
                       'source_issuing_authority': 'Ban Tổ chức Trung ương',
                       '_evidence': 'Hướng dẫn này thay thế Hướng dẫn số 12 -HD/BTCTW, ngày 06/7/2018 của Ban Tổ chức Trung ương.'}, hits)
        self.assertEqual(row['target_matched_id'], 2)
        # No day in the quote: two 12-HD/BTCTW of the same body stay unlinked rather than taking the latest.
        row = resolve({'target_doc': '12-HD/BTCTW', 'source_id': 679297, 'source_issuance_date': '2025-01-01',
                       'source_issuing_authority': 'Ban Tổ chức Trung ương', '_evidence': 'thay thế Hướng dẫn số 12-HD/BTCTW.'}, hits)
        self.assertIsNone(row['target_matched_id'])


class YearlessNumber(unittest.TestCase):
    def candidate(self, number, cited):
        return {'target_doc': number, 'source_id': 1, 'source_issuance_date': '2020-01-01', 'source_issuing_authority': 'Thủ tướng Chính phủ',
                '_evidence': f'thay thế Quyết định số {number} ngày {cited} của Thủ tướng Chính phủ'}

    def hit(self, _id, number, day):
        return {'_id': _id, '_source': {'document_number': number, 'issuance_date': day, 'issuing_authority': 'Thủ tướng Chính phủ'}}

    def test_yearless_registration_of_another_day_is_not_linked(self):
        # 366797_0: "28/2014/QĐ-TTg ngày 07/4/2014" was linked to 28/QĐ-TTg of 06/01/2014, another decision.
        row = resolve(self.candidate('28/2014/QĐ-TTg', '07 tháng 4 năm 2014'), [self.hit('218605', '28/QĐ-TTg', '2014-01-06')])
        self.assertIsNone(row['target_matched_id'])

    def test_yearless_registration_of_the_cited_day_is_linked(self):
        row = resolve(self.candidate('28/2014/QĐ-TTg', '07 tháng 4 năm 2014'), [self.hit('9', '28/QĐ-TTg', '2014-04-07')])
        self.assertEqual(row['target_matched_id'], 9)

    def test_a_mistyped_day_on_a_number_with_its_year_is_still_linked(self):
        row = resolve(self.candidate('45/2012/QĐ-TTg', '30 tháng 11 năm 2012'), [self.hit('7', '45/2012/QĐ-TTg', '2012-12-05')])
        self.assertEqual((row['target_matched_id'], row.get('target_match_note')), (7, 'lech_ngay_trich_dan'))


if __name__ == '__main__':
    unittest.main()
