import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from bot.main import ZONE, boundary, category, chunks, render


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.config = {'V3_WORKDIR': str(self.work), 'LLM_CONCURRENCY_DAY': '1', 'LLM_CONCURRENCY_NIGHT': '12', 'BOT_STALE_MINUTES': '45'}
        self.end = datetime(2026, 10, 29, 15, 0, tzinfo=ZONE)
        write_jsonl(self.work / 'auto' / 'history.jsonl', [
            {'at': '2026-10-29T14:10:00', 'run': 'auto-a', 'workers': 1, 'done': 3, 'failed': 1, 'outage': False},
            {'at': '2026-10-29T14:40:00', 'run': 'auto-b', 'workers': 1, 'done': 2, 'failed': 0, 'outage': False},
            {'at': '2026-10-29T13:50:00', 'run': 'auto-old', 'workers': 1, 'done': 9, 'failed': 0, 'outage': False},
        ])
        write_jsonl(self.work / 'auto-a' / 'documents.jsonl', [
            {'doc_id': '1', 'chunks': 10, 'relations': 2, 'resolved': 1, 'metadata_boc_lai': ['signers'], 'ai_warnings': [], 'seconds': 4.0},
            {'doc_id': '2', 'chunks': 5, 'relations': 0, 'resolved': 0, 'metadata_boc_lai': [], 'ai_warnings': ['x'], 'seconds': 6.0},
            {'doc_id': '3', 'skipped': 'tieng_anh'}])
        write_jsonl(self.work / 'auto-a' / 'failures.jsonl', [{'doc_id': '4', 'error': 'ConnectionError: Read timed out. (read timeout=120)'}])
        write_jsonl(self.work / 'auto-b' / 'documents.jsonl', [{'doc_id': '5', 'chunks': 1, 'relations': 2, 'resolved': 2, 'seconds': 3.0}])
        (self.work / 'auto' / 'queue.json').write_text(json.dumps(['6', '7']))
        (self.work / 'auto' / 'excluded.json').write_text(json.dumps({'3': 'tieng_anh'}))
        (self.work / 'auto' / 'scan.json').write_text(json.dumps({'at': 1793257574, 'time': '2026-10-29T07:06:14', 'new': 12}))

    def report(self, now):
        with patch('bot.main.target_counts', return_value=[31028, 1535751, 75546]), \
                patch('bot.main.probes', return_value=['• LLM localhost:8012 (qwen3.6-35b): ✅ · 8 ms']):
            return render(self.config, self.end - timedelta(hours=1), self.end, now=now)

    def test_window_totals(self):
        report = self.report(datetime.now(ZONE))
        self.assertNotIn('9 văn bản', report)  # auto-old finished before the window
        self.assertIn('Ghi -v4: 3 văn bản · 16 chunk · 4 quan hệ (75% nối được đích)', report)
        self.assertIn('Bỏ qua: 1 (tieng_anh 1)', report)
        self.assertIn('Bóc lại metadata: 1 văn bản · cảnh báo AI: 1', report)
        self.assertIn('Timeout / hết thời gian: 1 (100%)', report)
        self.assertIn('-v4: 31.028 văn bản · 1.535.751 chunk · 75.546 quan hệ', report)
        self.assertIn('Hàng đợi còn: 2 · đã loại: 1 (tieng_anh 1)', report)
        self.assertIn('Trạng thái: đang chạy', report)
        self.assertIn('Quét v2 gần nhất: 14:06 29/10 · văn bản mới 12', report)  # epoch, not the UTC text
        self.assertIn('LLM localhost:8012 (qwen3.6-35b): ✅ · 8 ms', report)
        self.assertIn('Thời gian mỗi văn bản: trung vị 4,0 giây', report)
        self.assertLess(len(report), 3400)

    def test_mode_follows_night_hours(self):
        from bot.main import mode
        self.assertEqual(mode(self.config, datetime(2026, 10, 29, 14, 0)), (False, 1, '22:00', 12))
        self.assertEqual(mode(self.config, datetime(2026, 10, 29, 23, 0)), (True, 12, '06:00', 1))
        self.assertEqual(mode(self.config, datetime(2026, 10, 29, 5, 59)), (True, 12, '06:00', 1))

    def test_stale_runner_is_flagged(self):
        report = self.report(datetime.now(ZONE) + timedelta(hours=2))
        self.assertIn('không thấy hoạt động', report)

    def test_categories_and_boundaries(self):
        self.assertEqual(category('HTTPError: 504 Server Error: Gateway Time-out'), 'HTTP 504')
        self.assertEqual(category('ConnectionError: Max retries exceeded'), 'Kết nối')
        self.assertEqual(category('ReplayMiss: thiếu câu trả lời'), 'ReplayMiss')
        self.assertEqual(boundary(datetime(2026, 10, 29, 14, 47, tzinfo=ZONE), 30), datetime(2026, 10, 29, 14, 30, tzinfo=ZONE))
        self.assertEqual(len(chunks('x\n' * 3000, limit=1000)), 6)


if __name__ == '__main__':
    unittest.main()
