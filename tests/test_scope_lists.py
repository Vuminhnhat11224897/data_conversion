"""Regression for the 06/11/2026 conversion stall on document 299233."""

import json
import subprocess
import sys
import unittest

from vbpl_v3.relations import scope


class ScopeLists(unittest.TestCase):
    def test_long_lists_finish_when_the_article_is_missing(self):
        # The source misses the comma between 9 and 10 and never names an Điều.
        clauses = 'Khoản ' + ', '.join(str(n) for n in range(2, 44) if n != 20)
        clauses = clauses.replace('9, 10', '9 10')
        points = 'điểm ' + ', '.join(['a', 'b', 'c', 'd', 'đ'] * 10)
        cases = [clauses + ' Thông tư số', clauses + ' Điều 5', points + ' Thông tư số']
        script = ('import json; from vbpl_v3.relations import scope; '
                  f'print(json.dumps([scope(text) for text in {cases!r}]))')
        # A subprocess deadline fails the old regex without hanging the test runner.
        result = subprocess.run([sys.executable, '-c', script], capture_output=True,
                                text=True, check=True, timeout=3)
        self.assertEqual(json.loads(result.stdout), [
            [clauses, False], [clauses + ' Điều 5', False], ['chưa xác định', True]])

    def test_valid_list_separators_keep_the_entire_scope(self):
        cases = [
            'điểm a, b và điểm c khoản 2 Điều 3',
            'điểm a, và điểm b khoản 2 Điều 3',
            'Khoản 2, 3 và khoản 4 Điều 5',
            'Khoản 2, và khoản 3 Điều 5',
            'Điều 1, 2 và 3',
            'Khoản 2 3 4',
            'Khoản 2a, 3b Điều 5',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(scope(text), (text, False))
