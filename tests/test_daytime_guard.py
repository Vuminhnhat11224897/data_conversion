import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ops import daytime_guard as guard
from ops.daytime_guard import decision, replacement


class DaytimeGuardTests(unittest.TestCase):
    def sample(self, errors=17):
        return {'running': True, 'day_workers': 3,
                'services': {'llm': {'errors_5xx': errors, 'queue': 0, 'up': 7}, 'es': {'rejected': 9}}}

    def test_existing_shared_errors_do_not_trigger_backoff(self):
        self.assertIsNone(decision(self.sample(), self.sample(), {}, 100, 14))

    def test_new_shared_error_reduces_our_load_without_attribution(self):
        self.assertEqual(decision(self.sample(18), self.sample(17), {}, 100, 14),
                         'new_5xx_on_shared_llm_conservative_backoff')

    def test_backend_counter_reset_is_not_a_new_error(self):
        self.assertIsNone(decision(self.sample(0), self.sample(17), {}, 100, 14))

    def test_short_queue_spike_is_not_sustained_pressure(self):
        x = self.sample(); x['services']['llm']['queue'] = 5
        timers = {}
        self.assertIsNone(decision(x, self.sample(), timers, 100, 14))
        self.assertIsNone(decision(x, x, timers, 189, 14))
        self.assertEqual(decision(x, x, timers, 190, 14), 'llm_queue_sustained_90s')
        self.assertIsNone(decision(self.sample(), x, timers, 191, 14))
        self.assertNotIn('llm_queue', timers)

    def test_no_change_to_nighttime_or_stopped_or_one_worker(self):
        for hour, running, workers in [(23, True, 3), (14, False, 3), (14, True, 1)]:
            x = self.sample(18); x['running'] = running; x['day_workers'] = workers
            self.assertIsNone(decision(x, self.sample(), {}, 100, hour))

    def test_disarmed_monitor_never_changes_worker(self):
        self.assertIsNone(decision(self.sample(18), self.sample(), {}, 100, 14, armed=False))

    def test_replacement_preserves_all_other_configuration(self):
        old = {'Config': {'Env': ['LLM_CONCURRENCY_DAY=1', 'LLM_CONCURRENCY_NIGHT=12', 'API_KEY=private'],
                          'Cmd': ['auto'], 'User': '1000:1000'},
               'Image': 'sha256:pinned',
               'HostConfig': {'NanoCpus': 8000000000, 'Memory': 8589934592, 'Binds': ['/work:/app/work']}}
        before = copy.deepcopy(old)
        new = replacement(old, 3)
        self.assertEqual(old, before)
        self.assertEqual(new['Env'], ['LLM_CONCURRENCY_DAY=3', 'LLM_CONCURRENCY_NIGHT=12', 'API_KEY=private'])
        self.assertEqual(new['HostConfig'], old['HostConfig'])
        self.assertEqual(new['Image'], old['Image'])
        self.assertEqual(new['Cmd'], old['Config']['Cmd'])
        self.assertEqual(new['User'], old['Config']['User'])
        with self.assertRaises(ValueError):
            replacement(old, 12)

    def run_switch_with_fake_docker(self, fail_new_start):
        old = {'Config': {'Env': ['LLM_CONCURRENCY_DAY=1', 'LLM_CONCURRENCY_NIGHT=12'],
                          'Cmd': ['auto'], 'User': '1000:1000'},
               'Image': 'sha256:pinned', 'State': {'Running': True},
               'HostConfig': {'NanoCpus': 8000000000, 'Memory': 8589934592}}
        containers = {'vbpl-auto': copy.deepcopy(old)}
        calls = []
        failed_once = False

        def fake(method, path, body=None):
            nonlocal failed_once
            calls.append((method, path))
            if path.startswith('/containers/create?name='):
                name = path.split('=', 1)[1]
                containers[name] = {'Config': {k: copy.deepcopy(v) for k, v in body.items() if k != 'HostConfig'},
                                    'Image': body['Image'], 'HostConfig': copy.deepcopy(body['HostConfig']),
                                    'State': {'Running': False}}
                return {'Id': name}
            name = path.split('/')[2]
            if method == 'GET':
                return copy.deepcopy(containers[name])
            if '/kill?' in path:
                containers[name]['State']['Running'] = False
            elif '/rename?' in path:
                containers[path.split('name=', 1)[1]] = containers.pop(name)
            elif path.endswith('/start'):
                if fail_new_start and not failed_once:
                    failed_once = True
                    raise RuntimeError('injected new-container start failure')
                containers[name]['State']['Running'] = True

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'work').mkdir()
            original_text = 'LLM_CONCURRENCY_DAY=1\nLLM_CONCURRENCY_NIGHT=12\n'
            (root / '.env').write_text(original_text)
            with patch.object(guard, 'ROOT', root), patch.object(guard, 'CONTROL', root / 'work/control'), \
                    patch.object(guard, 'docker', side_effect=fake):
                if fail_new_start:
                    with self.assertRaises(RuntimeError):
                        guard.switch(3, 'test')
                    self.assertEqual((root / '.env').read_text(), original_text)
                    self.assertEqual(containers['vbpl-auto'], old)
                else:
                    guard.switch(3, 'test')
                    self.assertIn('LLM_CONCURRENCY_DAY=3', (root / '.env').read_text())
                    self.assertIn('LLM_CONCURRENCY_NIGHT=12', containers['vbpl-auto']['Config']['Env'])
                    self.assertEqual(containers['vbpl-auto']['HostConfig'], old['HostConfig'])
                    self.assertTrue(containers['vbpl-auto']['State']['Running'])
            for method, path in calls:
                if '/create?' not in path:
                    self.assertTrue(path.split('/')[2].startswith('vbpl-auto'))

    def test_switch_controls_only_own_container_and_preserves_limits(self):
        self.run_switch_with_fake_docker(False)

    def test_start_failure_restores_original_container_and_env(self):
        self.run_switch_with_fake_docker(True)


if __name__ == '__main__':
    unittest.main()
