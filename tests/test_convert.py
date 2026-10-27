"""End-to-end conversion of one document with in-memory clusters and a fake model."""

from argparse import Namespace
import json
from pathlib import Path
import tempfile
import unicodedata
import unittest
from unittest.mock import patch

from vbpl_v3.convert import convert_document, run
from vbpl_v3.text import number_key
from tests.test_guard import config

TEXT = ('QUYẾT ĐỊNH:\nĐiều 1. Ban hành kèm theo Quyết định này Quy định quản lý chi phí.\n'
        'Điều 2. Quyết định này có hiệu lực kể từ ngày ký.\n'
        'Điều 3. Bãi bỏ Quyết định số 12/2010/QĐ-UBND ngày 01/01/2010 của Ủy ban nhân dân tỉnh A.\n'
        'Nơi nhận:\n- Như Điều 3;\n- Lưu: VT.\nKT. CHỦ TỊCH\nPHÓ CHỦ TỊCH\nNguyễn Văn A\n'
        'QUY ĐỊNH\nVỀ QUẢN LÝ CHI PHÍ\n(Ban hành kèm theo Quyết định số 29/2026/QĐ-UBND)\n'
        'Điều 1. Phạm vi điều chỉnh\nNội dung phạm vi.\nĐiều 2. Đối tượng áp dụng\n1. Cơ quan nhà nước.\n2. Tổ chức, cá nhân.\n')
SOURCE_DOC = {'document_number': '29/2026/QĐ-UBND', 'title': 'Quyết định ban hành Quy định quản lý chi phí', 'legal_type': 'Quyết định',
              'legal_sectors': ['Tài chính'], 'issuing_authority': 'Tỉnh A', 'issuance_date': '2026-01-01', 'signers': 'Nguyễn Văn A:1',
              'tom_tat': 'Quy định quản lý chi phí.', 'action': 'other', 'url': 'https://example.org/900', 'pdf_minio_path': 'pdf/900.pdf',
              'embedding': [0.3] * 1024, 'full_content': unicodedata.normalize('NFD', TEXT), 'n_dieu': 40}
OLD_VECTOR = [0.5] * 1024


class Memory:
    """The subset of Cluster used by conversion, kept in memory."""

    def __init__(self, indices):
        self.indices = {name: dict(rows) for name, rows in indices.items()}

    def get(self, index, doc_id):
        row = self.indices.get(index, {}).get(str(doc_id))
        return {'_id': str(doc_id), '_source': row} if row is not None else None

    def scan(self, index, query, source=True, size=500):
        field, value = next(iter(query['term'].items()))
        return [{'_id': k, '_source': v} for k, v in self.indices[index].items() if v.get(field) == value]

    def use_number_index(self, index, folder):
        pass  # by_numbers below already matches by number_key

    def by_numbers(self, index, numbers):
        keys = {number_key(n) for n in numbers}
        return [{'_id': k, '_source': v} for k, v in self.indices[index].items() if number_key(v.get('document_number')) in keys]

    def count(self, index, query):
        return len(self.scan(index, query))

    def remove_group(self, index, field, value):
        self.indices[index] = {k: v for k, v in self.indices[index].items() if v.get(field) != value}

    def bulk(self, index, records):
        self.indices.setdefault(index, {}).update({r['_id']: r['_source'] for r in records})

    def put(self, index, doc_id, source):
        self.indices.setdefault(index, {})[str(doc_id)] = source


def model(prompt, payload, folder, **options):
    data = json.loads(payload)
    if 'dieu_can_xac_dinh' in data:
        return json.dumps({'articles': [{'line': x['line'], 'has_title': False} for x in data['dieu_can_xac_dinh']]}), {}
    if 'khung' in data:
        return json.dumps({'parts': []}), {}
    if 'verdict' in prompt or 'valid:boolean' in prompt:
        return json.dumps({'valid': True, 'reason': 'Đơn vị nguồn tự bãi bỏ văn bản đích.'}), {}
    return json.dumps({'scope': data['scope'], 'correct': True, 'evidence': data['unit'][:200]}), {}


def fake_embed(texts, url, batch, **options):
    return [[0.1] * 1024 for _ in texts]


class ConvertCheck(unittest.TestCase):
    def setUp(self):
        self.source = Memory({'legal-docs': {'900': SOURCE_DOC, '777': {'document_number': '12/2010/QĐ-UBND', 'issuing_authority': 'Tỉnh A',
                                                                         'issuance_date': '2010-01-01', 'title': 'Quyết định cũ'}},
                              'legal-chunk-section-v2': {'900_d2': {'doc_id': '900', 'tieu_de': 'Quyết định này có hiệu lực kể từ ngày ký.',
                                                                    'noi_dung': '', 'embedding': OLD_VECTOR}}})
        self.target = Memory({'legal-docs-v3': {}, 'legal-chunk-section-v3': {}, 'legal-changed-v3': {}})
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def convert(self, **options):
        with patch('vbpl_v3.convert.embed', side_effect=fake_embed):
            return convert_document('900', config(workdir=self.root), self.source, self.target, 'run1', self.root, caller=model, **options)

    def test_document_chunks_vectors_and_relations(self):
        record = self.convert()
        document = self.target.indices['legal-docs-v3']['900']
        self.assertEqual(document['full_content'], unicodedata.normalize('NFC', TEXT).strip())
        self.assertEqual((document['n_dieu'], document['ingest_job_id'], document['uploaded_by'], document['origin']), (3, 'v3:run1', 'migration-v3', 'legacy'))
        self.assertEqual((document['title'], document['signers'], document['embedding']), (SOURCE_DOC['title'], 'Nguyễn Văn A:1', [0.3] * 1024))
        self.assertEqual(len(document['content_sha256']), 64)
        self.assertEqual([(p['tieu_de'][:8], len(p['dieu_luat'])) for p in document['phu_luc']], [('QUY ĐỊNH', 2)])
        chunks = self.target.indices['legal-chunk-section-v3']
        # The untitled closing article now carries its sentence as content, and keeps the unchanged vector.
        self.assertEqual((chunks['900_d2']['tieu_de'], chunks['900_d2']['noi_dung']), ('', 'Quyết định này có hiệu lực kể từ ngày ký.'))
        self.assertEqual(chunks['900_d2']['embedding'], OLD_VECTOR)
        self.assertTrue(all(c['ingest_job_id'] == 'v3:run1' and len(c['embedding']) == 1024 for c in chunks.values()))
        self.assertEqual((record['vectors_reused'], record['vectors_new'], record['empty_dieu']), (1, len(chunks) - 1, 0))
        relations = list(self.target.indices['legal-changed-v3'].values())
        self.assertEqual([(r['target_doc'], r['action'], r['target_matched_id'], r['source_id']) for r in relations],
                         [('12/2010/QĐ-UBND', 'bai-bo', 777, 900)])
        self.assertEqual((record['qa'], record['relations'], record['resolved']), ('done', 1, 1))
        # Converting again replaces the same records instead of adding stale ones.
        self.convert()
        self.assertEqual(len(self.target.indices['legal-chunk-section-v3']), len(chunks))
        self.assertEqual(len(self.target.indices['legal-changed-v3']), 1)

    def test_target_vectors_reused_when_rewriting(self):
        # EMBEDDING_REUSE=target (rewriting -v4, 27/10/2026): an unchanged chunk keeps the target's own vector, not the source's.
        kept = [0.7] * 1024
        self.target.indices['legal-chunk-section-v3']['900_d2'] = {'doc_id': '900', 'tieu_de': '', 'embedding': kept,
                                                                   'noi_dung': 'Quyết định này có hiệu lực kể từ ngày ký.'}
        with patch('vbpl_v3.convert.embed', side_effect=fake_embed):
            record = convert_document('900', config(workdir=self.root, embedding_reuse=False, embedding_reuse_target=True), self.source,
                                      self.target, 'run1', self.root, caller=model)
        self.assertEqual(self.target.indices['legal-chunk-section-v3']['900_d2']['embedding'], kept)
        self.assertEqual(record['vectors_reused'], 1)

    def test_english_full_text_is_skipped(self):
        # 39074: an English translation stored as the full text. Skipped before any model or embedding call, nothing written.
        english = ('THE GOVERNMENT\nDECREE\nISSUING THE REGULATION ON SOCIAL INSURANCE\nDECREES:\n'
                   'Article 1.- To issue together with this Decree the Regulation on Social Insurance applicable to State officials. ' * 8)
        self.source.indices['legal-docs']['900'] = {**SOURCE_DOC, 'full_content': english}
        never = lambda *args, **kwargs: self.fail('model called')
        with patch('vbpl_v3.convert.embed', side_effect=lambda *a: self.fail('embedding called')):
            record = convert_document('900', config(workdir=self.root), self.source, self.target, 'run1', self.root, caller=never)
        self.assertEqual((record['skipped'], record['ngon_ngu']), ('tieng_anh', 'en'))
        self.assertEqual(self.target.indices['legal-docs-v3'], {})

    def test_dry_run_writes_only_local_preview(self):
        record = self.convert(dry_run=True)
        self.assertTrue(record['dry_run'])
        self.assertEqual([len(rows) for rows in self.target.indices.values()], [0, 0, 0])
        preview = json.loads((self.root / 'dry-run' / '900.json').read_text())
        self.assertEqual(preview['document']['n_dieu'], 3)
        self.assertNotIn('embedding', preview['chunks'][0])

    def test_run_resumes_and_records_failures(self):
        args = Namespace(run='r1', ids=None, sample=None, seed=1, all=False, from_date=None, to_date=None, legal_type=None, redo=False,
                         limit=None, workers=2, no_qa=False, dry_run=False)
        (self.root / 'r1').mkdir()
        (self.root / 'r1' / 'ids.json').write_text(json.dumps(['900', '404']))
        with patch('vbpl_v3.convert.embed', side_effect=fake_embed), patch('builtins.print'):
            self.assertEqual(run(config(workdir=self.root), self.source, self.target, args, caller=model), 1)
            done = [json.loads(line)['doc_id'] for line in (self.root / 'r1' / 'documents.jsonl').read_text().splitlines()]
            self.assertEqual(done, ['900'])
            self.assertIn('404', (self.root / 'r1' / 'failures.jsonl').read_text())
            # A second invocation skips finished documents and retries only the failure.
            with patch('vbpl_v3.convert.convert_document', side_effect=LookupError('missing')) as again:
                run(config(workdir=self.root), self.source, self.target, args, caller=model)
            self.assertEqual([c.args[0] for c in again.call_args_list], ['404'])


if __name__ == '__main__':
    unittest.main()


class NumberIndex(unittest.TestCase):
    """The local table of document numbers answers what the tolerant search answers, by number_key."""

    def test_table_matches_by_number_key(self):
        import tempfile
        from vbpl_v3.es import Cluster
        numbers = {'1': '32/2012/QĐ-UBND', '2': '32/2012/QĐ- U BND', '3': '132/2012/QĐ-UBND', '4': '05/2013/TT-BYT', '5': ''}
        cluster = Cluster('http://127.0.0.1:9')
        def scan(index, query, source=True, size=500):
            if 'match_all' in query:
                return [{'_id': k, '_source': {'document_number': v}} for k, v in numbers.items()]
            return [{'_id': k, '_source': {'document_number': numbers[k]}} for k in query['ids']['values']]
        cluster.scan, cluster.count = scan, lambda index, query=None: len(numbers)
        with tempfile.TemporaryDirectory() as folder:
            cluster.use_number_index('legal-docs', folder)
            self.assertEqual(sorted(h['_id'] for h in cluster.by_numbers('legal-docs', ['32/2012/QĐ-UBND'])), ['1', '2'])
            self.assertEqual([h['_id'] for h in cluster.by_numbers('legal-docs', ['5/2013/TT-BYT'])], ['4'])
            again = Cluster('http://127.0.0.1:9')
            again.scan, again.count = scan, lambda index, query=None: len(numbers)
            again.use_number_index('legal-docs', folder)  # read from the file, not scanned again
            self.assertEqual(again.numbers[1], cluster.numbers[1])
