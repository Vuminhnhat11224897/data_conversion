"""Continuous migration (auto): queue order, dedup against the target, skipped/failed bookkeeping, stop."""

from argparse import Namespace
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from vbpl_v3 import auto
from vbpl_v3.convert import run
from tests.test_guard import config


class Cluster:
    """The subset of es.Cluster used by auto: match_all scans and an ids lookup."""

    def __init__(self, indices):
        self.indices = indices
        self.numbers = None
        self.number_loads = 0

    def scan(self, index, query, source=True, size=500):
        return [{'_id': k, '_source': v} for k, v in self.indices.get(index, {}).items()]

    def request(self, method, path, body=None):
        index = path.strip('/').split('/')[0]
        ids = body['query']['ids']['values']
        return {'hits': {'hits': [{'_id': i} for i in ids if i in self.indices.get(index, {})]}}

    def use_number_index(self, index, folder):
        self.number_loads += 1
        self.numbers = (index, {})


class Order(unittest.TestCase):
    def test_new_first_then_newest_undated_last_without_target_or_excluded(self):
        rows = [('1', '2020-01-01'), ('2', '2026-05-01'), ('3', None), ('4', '2025-01-01'), ('5', '2024-01-01'), ('6', '2026-06-01')]
        queue = auto.order(rows, present={'6'}, excluded={'5': 'tieng_anh'}, seen={'1', '2', '3', '5', '6'})
        self.assertEqual(queue, ['4', '2', '1', '3'])  # 4 is new since the last scan; 6 is in the target; 5 is excluded

    def test_first_scan_has_no_new(self):
        self.assertEqual(auto.order([('1', '2020-01-01'), ('2', '2021-01-01')], set(), {}, None), ['2', '1'])


class Settle(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def write(self, records, failures):
        (self.root / 'documents.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records))
        (self.root / 'failures.jsonl').write_text(''.join(json.dumps({'doc_id': i, 'error': 'x'}) + '\n' for i in failures))

    def test_skipped_excluded_failed_counted_then_excluded(self):
        self.write([{'doc_id': '1'}, {'doc_id': '2', 'skipped': 'tieng_anh'}, {'doc_id': '3'}], ['4'])
        attempts, excluded = {'4': 2}, {}
        done, failed, outage = auto.settle(self.root, ['1', '2', '3', '4'], attempts, excluded, 3)
        self.assertEqual((done, failed, outage), ({'1', '2', '3'}, {'4'}, False))
        self.assertEqual(excluded, {'2': 'tieng_anh', '4': 'loi_3_lan'})

    def test_half_batch_failing_is_an_outage_and_not_counted(self):
        self.write([{'doc_id': '1'}, {'doc_id': '4'}], ['2', '3'])
        attempts, excluded = {}, {}
        self.assertTrue(auto.settle(self.root, ['1', '2', '3', '4'], attempts, excluded, 3)[2])
        self.assertEqual((attempts, excluded), ({}, {}))
        # A batch under 4 documents is never an outage: the last always-failing documents still get excluded.
        self.assertFalse(auto.settle(self.root, ['2', '3'], attempts, excluded, 1)[2])
        self.assertEqual(excluded, {'2': 'loi_1_lan', '3': 'loi_1_lan'})


class Forever(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.config = config(workdir=self.root)
        docs = {str(i): {'issuance_date': f'2026-01-{i:02d}'} for i in range(1, 8)}
        self.source = Cluster({self.config.source['documents']: docs})
        self.target = Cluster({self.config.target['documents']: {'7': {}}})
        self.runs = []

    def fake_run(self, config, source, target, args):
        ids = Path(args.ids).read_text().split()
        self.runs.append((ids, args.workers))
        folder = config.workdir / args.run
        folder.mkdir()
        (folder / 'documents.jsonl').write_text(''.join(json.dumps({'doc_id': i}) + '\n' for i in ids if i != '5'))
        if '5' in ids:
            (folder / 'failures.jsonl').write_text(json.dumps({'doc_id': '5', 'error': 'x'}) + '\n')
        for i in ids:
            if i != '5':
                target.indices[config.target['documents']][i] = {}
        return 0

    def once(self):
        with patch('vbpl_v3.auto.run', side_effect=self.fake_run), patch('vbpl_v3.auto.llm.concurrency', return_value=1), \
                patch.dict('os.environ', {'AUTO_BATCH_PER_WORKER': '3'}), patch('builtins.print'), patch('signal.signal'):
            return auto.forever(self.config, self.source, self.target, once=True)

    def test_batches_skip_target_and_move_failures_to_the_end(self):
        self.once()
        self.assertEqual(self.runs[-1], (['6', '5', '4'], 1))  # 7 is already in the target; newest first; 1 worker by day
        self.assertEqual(json.loads((self.root / 'auto' / 'queue.json').read_text()), ['3', '2', '1', '5'])
        self.assertEqual(self.source.number_loads, 1)  # refreshed by the scan, kept for the batches
        # A document written to the target since the scan (here 3) is dropped at the last moment, never converted again.
        self.target.indices[self.config.target['documents']]['3'] = {}
        self.once()
        self.assertEqual(self.runs[-1][0], ['2', '1'])  # the batch is not refilled; 5 waits at the end of the queue
        self.assertEqual(json.loads((self.root / 'auto' / 'queue.json').read_text()), ['5'])
        self.once()
        self.assertEqual(self.runs[-1][0], ['5'])
        self.assertEqual(json.loads((self.root / 'auto' / 'attempts.json').read_text()), {'5': 2})

    def test_a_second_process_is_refused(self):
        (self.root / 'auto').mkdir()
        holder = open(self.root / 'auto' / 'lock', 'w')
        auto.fcntl.flock(holder, auto.fcntl.LOCK_EX | auto.fcntl.LOCK_NB)
        with self.assertRaises(SystemExit):
            self.once()


class TimeZone(unittest.TestCase):
    def test_tz_from_env_file_decides_day_and_night(self):
        import os, time
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from vbpl_v3 import config as settings
        old = os.environ.get('TZ')
        env = Path(tempfile.mkdtemp()) / '.env'
        env.write_text('TZ=Asia/Ho_Chi_Minh\n')
        try:
            os.environ.pop('TZ', None)
            settings.load(env)
            self.assertEqual(datetime.now().hour, datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).hour)
        finally:
            os.environ.pop('TZ', None) if old is None else os.environ.__setitem__('TZ', old)
            time.tzset()


class Stop(unittest.TestCase):
    def test_documents_not_started_stay_undone(self):
        root = Path(tempfile.mkdtemp())
        (root / 'r').mkdir()
        (root / 'r' / 'ids.json').write_text(json.dumps(['1', '2']))
        stop = threading.Event()
        stop.set()
        args = Namespace(run='r', ids=None, sample=None, seed=1, all=False, from_date=None, to_date=None, legal_type=None, redo=False,
                         limit=None, workers=2, no_qa=False, dry_run=False, stop=stop)
        with patch('vbpl_v3.convert.convert_document') as convert, patch('builtins.print'):
            self.assertEqual(run(config(workdir=root), Cluster({}), Cluster({}), args), 0)
        convert.assert_not_called()
        self.assertFalse((root / 'r' / 'documents.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
