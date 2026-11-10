"""Own-worker rollout and read-only capacity guard; never controls other containers."""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime
import fcntl
import http.client
import io
import json
import os
from pathlib import Path
import socket
import time
from zoneinfo import ZoneInfo

import requests

ROOT = Path('/data/data_conversion')
CONTROL = ROOT / 'work/daytime-worker-control'
CONTAINER = 'vbpl-auto'
ZONE = ZoneInfo('Asia/Ho_Chi_Minh')


def save(path, value):
    part = path.with_suffix(path.suffix + '.part')
    fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    part.replace(path)


def load(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


class Docker(http.client.HTTPConnection):
    def __init__(self):
        super().__init__('localhost', timeout=15)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def docker(method, path, body=None):
    connection = Docker()
    try:
        connection.request(method, path, body=json.dumps(body) if body is not None else None,
                           headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read()
        if response.status >= 400:
            raise RuntimeError(f'Docker {method} {path}: HTTP {response.status}')
        return json.loads(raw) if raw else None
    finally:
        connection.close()


def container():
    return docker('GET', f'/containers/{CONTAINER}/json')


def environment(item):
    return dict(row.split('=', 1) for row in item['Config']['Env'])


def replacement(item, workers):
    if workers not in (1, 3):
        raise ValueError('Only the authorized daytime settings 1 and 3 are supported')
    result = copy.deepcopy(item['Config'])
    entries = result['Env']
    if sum(row.startswith('LLM_CONCURRENCY_DAY=') for row in entries) != 1:
        raise ValueError('Expected exactly one daytime concurrency setting')
    result['Env'] = [f'LLM_CONCURRENCY_DAY={workers}' if row.startswith('LLM_CONCURRENCY_DAY=') else row
                     for row in entries]
    result['Image'] = item['Image']
    result['HostConfig'] = copy.deepcopy(item['HostConfig'])
    return result


def change_env_file(workers):
    path = ROOT / '.env'
    lines = path.read_text().splitlines(keepends=True)
    if sum(line.startswith('LLM_CONCURRENCY_DAY=') for line in lines) != 1:
        raise ValueError('Expected one daytime setting in .env')
    text = ''.join(f'LLM_CONCURRENCY_DAY={workers}\n' if line.startswith('LLM_CONCURRENCY_DAY=') else line
                   for line in lines)
    part = path.with_name('.env.daytime-guard.part')
    fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, path.stat().st_mode & 0o777)
    with os.fdopen(fd, 'w') as stream:
        stream.write(text)
    part.replace(path)


def switch(workers, reason):
    CONTROL.mkdir(exist_ok=True, mode=0o700)
    with (CONTROL / 'operation.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = container()
        old_day = int(environment(old)['LLM_CONCURRENCY_DAY'])
        if old_day == workers:
            return {'workers': workers, 'changed': False}
        if not old['State']['Running']:
            raise RuntimeError('Live worker was stopped; do not override a manual stop')
        stamp = datetime.now(ZONE).strftime('%Y%m%d-%H%M%S')
        folder = CONTROL / f'switch-{stamp}-day{workers}'
        folder.mkdir(mode=0o700)
        save(folder / 'original-container.json', old)
        env_path = folder / 'original.env'
        env_path.write_bytes((ROOT / '.env').read_bytes())
        env_path.chmod(0o600)
        staged = f'vbpl-auto-stage-day{workers}-{stamp}'
        backup = f'vbpl-auto-backup-day{old_day}-{stamp}'
        docker('POST', '/containers/create?name=' + staged, replacement(old, workers))
        docker('POST', f'/containers/{CONTAINER}/kill?signal=TERM')
        print(f'Draining only {CONTAINER}; target daytime workers={workers}', flush=True)
        while container()['State']['Running']:
            time.sleep(3)
        docker('POST', f'/containers/{CONTAINER}/rename?name={backup}')
        docker('POST', f'/containers/{staged}/rename?name={CONTAINER}')
        try:
            change_env_file(workers)
            docker('POST', f'/containers/{CONTAINER}/start')
            new = container()
            expected = replacement(old, workers)
            assert new['Config']['Env'] == expected['Env']
            assert new['Image'] == old['Image']
            assert new['HostConfig'] == old['HostConfig']
        except Exception:
            # Put the exact original container/config back. No other workload is touched.
            if container()['State']['Running']:
                docker('POST', f'/containers/{CONTAINER}/kill?signal=TERM')
                while container()['State']['Running']:
                    time.sleep(2)
            docker('POST', f'/containers/{CONTAINER}/rename?name=vbpl-auto-failed-day{workers}-{stamp}')
            docker('POST', f'/containers/{backup}/rename?name={CONTAINER}')
            (ROOT / '.env').write_bytes(env_path.read_bytes())
            docker('POST', f'/containers/{CONTAINER}/start')
            raise
        result = {'at': time.time(), 'workers': workers, 'reason': reason, 'backup': backup, 'changed': True}
        save(folder / 'switched.json', result)
        save(CONTROL / 'last-switch.json', result)
        print(json.dumps(result), flush=True)
        return result


def probe():
    session = requests.Session()
    session.trust_env = False
    current = container()
    env = environment(current)
    result = {'at': time.time(), 'running': current['State']['Running'],
              'day_workers': int(env['LLM_CONCURRENCY_DAY']), 'night_workers': int(env['LLM_CONCURRENCY_NIGHT']),
              'services': {}, 'probe_errors': []}
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()}
    result['host_available_memory'] = memory['MemAvailable']
    try:
        response = session.get('http://127.0.0.1:8406/;csv', timeout=(2, 4))
        response.raise_for_status()
        rows = [row for row in csv.DictReader(io.StringIO(response.text.lstrip('# ')))
                if row['svname'] in ('sg1', 'sg2', 'sg3', 'sg4', 'sg5', 'sg6', 'sg7')]
        if len(rows) != 7:
            raise ValueError('Missing expected LLM backends')
        result['services']['llm'] = {'errors_5xx': sum(int(row['hrsp_5xx'] or 0) for row in rows),
                                     'queue': sum(int(row['qcur'] or 0) for row in rows),
                                     'active': sum(int(row['scur'] or 0) for row in rows),
                                     'max_response_ms': max(int(row['rtime'] or 0) for row in rows),
                                     'up': sum(row['status'] == 'UP' for row in rows)}
    except Exception as exc:
        result['probe_errors'].append('llm:' + type(exc).__name__)
    try:
        response = session.get(env['TARGET_ES_URL'] + '/_nodes/stats/jvm,thread_pool,os?filter_path=nodes.*.jvm.mem.heap_used_percent,nodes.*.thread_pool.write,nodes.*.thread_pool.search,nodes.*.os.cpu.percent', timeout=(2, 4))
        response.raise_for_status()
        nodes = list(response.json()['nodes'].values())
        result['services']['es'] = {'heap': max(n['jvm']['mem']['heap_used_percent'] for n in nodes),
                                    'write_queue': sum(n['thread_pool']['write']['queue'] for n in nodes),
                                    'search_queue': sum(n['thread_pool']['search']['queue'] for n in nodes),
                                    'rejected': sum(n['thread_pool'][k]['rejected'] for n in nodes for k in ('write', 'search')),
                                    'cpu': max(n['os']['cpu']['percent'] for n in nodes)}
    except Exception as exc:
        result['probe_errors'].append('es:' + type(exc).__name__)
    try:
        url = env['EMBEDDING_URL'].removesuffix('/v1') + '/metrics'
        response = session.get(url, timeout=(2, 4)); response.raise_for_status()
        rows = response.text.splitlines()
        result['services']['embedding'] = {
            'queue': sum(float(line.rsplit(' ', 1)[1]) for line in rows if line.startswith('vllm:num_requests_waiting{')),
            'active': sum(float(line.rsplit(' ', 1)[1]) for line in rows if line.startswith('vllm:num_requests_running{'))}
    except Exception as exc:
        result['probe_errors'].append('embedding:' + type(exc).__name__)
    if current['State']['Running']:
        try:
            stats = docker('GET', f'/containers/{CONTAINER}/stats?stream=false&one-shot=true')
            mem = stats['memory_stats']
            result['container_memory'] = mem['usage'] - mem.get('stats', {}).get('inactive_file', 0)
        except Exception as exc:
            result['probe_errors'].append('container:' + type(exc).__name__)
    return result


def decision(sample, previous, timers, now, hour, armed=True):
    """Only reduce our daytime worker; never infer who caused shared-service trouble."""
    if not armed or not 6 <= hour < 22 or not sample.get('running') or sample.get('day_workers') != 3:
        timers.clear()
        return None
    services = sample.get('services', {})
    before = (previous or {}).get('services', {})
    llm, old_llm = services.get('llm', {}), before.get('llm', {})
    es, old_es = services.get('es', {}), before.get('es', {})
    if 'errors_5xx' in old_llm and llm.get('errors_5xx', 0) > old_llm['errors_5xx']:
        return 'new_5xx_on_shared_llm_conservative_backoff'
    if 'rejected' in old_es and es.get('rejected', 0) > old_es['rejected']:
        return 'new_es_rejection'
    conditions = {
        'llm_queue': llm.get('queue', 0) > 4,
        'llm_latency': llm.get('max_response_ms', 0) > 15000,
        'llm_backend_down': 'up' in llm and llm['up'] < 7,
        'es_queue': es.get('write_queue', 0) > 16 or es.get('search_queue', 0) > 16,
        'es_heap': es.get('heap', 0) >= 92,
        'embedding_queue': services.get('embedding', {}).get('queue', 0) > 4,
        'own_memory': sample.get('container_memory', 0) > 6 * 1024**3,
        'host_memory': sample.get('host_available_memory', 2**60) < 32 * 1024**3,
        'probe_unavailable': bool(sample.get('probe_errors')),
    }
    for key, active in conditions.items():
        if not active:
            timers.pop(key, None)
        else:
            timers.setdefault(key, now)
            if now - timers[key] >= 90:
                return key + '_sustained_90s'
    return None


def monitor():
    CONTROL.mkdir(exist_ok=True, mode=0o700)
    with (CONTROL / 'monitor.lock').open('w') as singleton:
        fcntl.flock(singleton, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = load(CONTROL / 'status.json', {}).get('sample')
        timers = {}
        while True:
            started = time.monotonic()
            policy = load(CONTROL / 'policy.json', {'armed': False})
            try:
                sample = probe()
                reason = decision(sample, previous, timers, time.time(), datetime.now(ZONE).hour,
                                  armed=policy.get('armed', False))
                pending = load(CONTROL / 'backoff.json', {})
                if (not reason and pending and not pending.get('completed')
                        and policy.get('armed') and sample['running'] and sample['day_workers'] == 3
                        and 6 <= datetime.now(ZONE).hour < 22):
                    reason = pending['reason']
                status = {'checked_at': datetime.now(ZONE).isoformat(), 'sample': sample,
                          'armed': policy.get('armed', False), 'timers': timers,
                          'action': 'backoff_pending' if reason else 'observing', 'reason': reason}
                save(CONTROL / 'status.json', status)
                path = CONTROL / 'metrics.jsonl'
                if path.exists() and path.stat().st_size > 8 * 1024**2:
                    path.replace(CONTROL / 'metrics.previous.jsonl')
                with path.open('a') as stream:
                    stream.write(json.dumps(status) + '\n')
                previous = sample
                if reason:
                    event = {'at': datetime.now(ZONE).isoformat(), 'reason': reason,
                             'note': 'Conservative reduction of our worker; no attribution of shared errors.'}
                    save(CONTROL / 'backoff.json', event)
                    print('BACKOFF ' + json.dumps(event), flush=True)
                    switch(1, reason)
                    event['completed'] = True
                    save(CONTROL / 'backoff.json', event)
                    timers.clear()
            except Exception as exc:
                save(CONTROL / 'monitor-error.json', {'at': datetime.now(ZONE).isoformat(),
                                                     'error': type(exc).__name__})
                print('Guard error: ' + type(exc).__name__, flush=True)
            time.sleep(max(1, 30 - (time.monotonic() - started)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--monitor', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--switch', type=int, choices=[1, 3])
    args = parser.parse_args()
    if args.monitor:
        monitor()
    elif args.check:
        print(json.dumps(probe(), ensure_ascii=False, indent=2))
    else:
        switch(args.switch, 'user_requested_daytime_worker_change')
