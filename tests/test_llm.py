"""LLM server limits (15/10/2026): 3 calls at once by day, 10 from 22:00 to 06:00; 4000 tokens; connect 5 s, read 30 s."""

from datetime import datetime
import os
import threading
import time
import unittest
from unittest.mock import Mock, patch

from vbpl_v3 import llm

LIMITS = {'LLM_CONCURRENCY_DAY': '3', 'LLM_CONCURRENCY_NIGHT': '10', 'LLM_NIGHT_HOURS': '22-6', 'LLM_MAX_TOKENS': '4000',
          'LLM_TIMEOUT_CONNECT': '5', 'LLM_TIMEOUT_READ': '30', 'LLM_MIN_TOKENS_PER_SECOND': '20',
          'LITELLM_BASE_URL': 'http://llm.test/v1', 'LITELLM_API_KEY': 'EMPTY', 'LITELLM_MODEL': 'qwen3.6-35b'}


@patch.dict(os.environ, LIMITS)
class ServerLimits(unittest.TestCase):
    def test_concurrency_follows_the_clock(self):
        at = lambda hour: llm.concurrency(datetime(2026, 10, 15, hour, 30))
        self.assertEqual([at(9), at(21), at(22), at(3), at(5), at(6)], [3, 3, 10, 10, 10, 3])

    def test_tokens_and_timeouts(self):
        self.assertEqual(llm.timeouts(512), (5.0, 30.0))   # QA verdict: the server's 30 s
        self.assertEqual(llm.timeouts(2000), (5.0, 100.0))  # long structure answer: time to write 2000 tokens
        self.assertEqual(llm.timeouts(4000, 120), (5.0, 120))
        reply = Mock(status_code=200, json=Mock(return_value={'choices': [{'finish_reason': 'stop', 'message': {'content': '{"a":1}'}}]}))
        with patch('vbpl_v3.llm.requests.post', return_value=reply) as post, self.subTest('cap'):
            import tempfile
            from pathlib import Path
            with tempfile.TemporaryDirectory() as folder:
                llm.call_llm('p', 't', Path(folder), max_tokens=8192)
            body = post.call_args.kwargs['json']
            self.assertEqual((body['max_tokens'], body['model'], body['chat_template_kwargs']), (4000, 'qwen3.6-35b', {'enable_thinking': False}))
            self.assertEqual(post.call_args.kwargs['timeout'], (5.0, 200.0))

    def test_gate_never_exceeds_the_day_limit(self):
        gate, active, peak, lock = llm.Gate(), [0], [0], threading.Lock()

        def call():
            with gate:
                with lock:
                    active[0] += 1; peak[0] = max(peak[0], active[0])
                time.sleep(0.05)
                with lock:
                    active[0] -= 1
        with patch('vbpl_v3.llm.concurrency', return_value=3):
            threads = [threading.Thread(target=call) for _ in range(12)]
            for t in threads: t.start()
            for t in threads: t.join()
        self.assertEqual(peak[0], 3)


@patch.dict(os.environ, {**LIMITS, 'LLM_CONNECT_RETRY_WAITS': '1,2'})
class RefusedConnection(unittest.TestCase):
    def test_a_refused_connection_is_retried_then_given_up(self):
        import tempfile
        from pathlib import Path
        import requests
        reply = Mock(status_code=200, json=Mock(return_value={'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}))
        with tempfile.TemporaryDirectory() as folder, patch('vbpl_v3.llm.time.sleep') as sleep, \
                patch('vbpl_v3.llm.requests.post', side_effect=[requests.ConnectTimeout('busy'), reply]) as post:
            llm.call_llm('p', 't', Path(folder), max_tokens=10)
            self.assertEqual((post.call_count, sleep.call_args_list[0].args), (2, (1,)))
        with tempfile.TemporaryDirectory() as folder, patch('vbpl_v3.llm.time.sleep'), \
                patch('vbpl_v3.llm.requests.post', side_effect=requests.ConnectionError('down')) as post:
            with self.assertRaises(requests.ConnectionError):
                llm.call_llm('p', 't', Path(folder), max_tokens=10)
            self.assertEqual(post.call_count, 3)
