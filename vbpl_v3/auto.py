"""Continuous migration: convert the source documents missing from the target, in small batches, until stopped.

Every AUTO_RESCAN_HOURS the queue is rebuilt from one scan of the source: every source _id that is not in the target documents
index and not excluded. Documents new since the previous scan come first, then the rest by issuance_date, newest first; undated
last. Before each batch its ids are looked up in the target again, so a document already there is never converted twice.

Workers follow llm.concurrency(): LLM_CONCURRENCY_DAY by day, LLM_CONCURRENCY_NIGHT in LLM_NIGHT_HOURS. A batch holds
AUTO_BATCH_PER_WORKER documents per worker, so the day/night switch waits at most one batch. A skipped document (English, before
START_YEAR) is excluded for good. A failed one goes to the end of the queue and is excluded after AUTO_MAX_ATTEMPTS failures. When
half a batch of 4 or more fails, a service is down: attempts are not counted, the batch stays first and the loop waits.

State in work/auto/: queue.json, seen.json.gz (source ids of the last scan), scan.json, attempts.json, excluded.json
(id -> reason), history.jsonl (one line per batch), batches/<run>.txt. Each batch is a convert run work/auto-<time>/.
SIGTERM/SIGINT: documents not started yet stay queued; the ones in flight finish (docker stop --time 600).
"""

import fcntl
import gzip
import json
import os
import signal
import threading
import time
from argparse import Namespace
from datetime import datetime

from . import llm
from .convert import run


def setting(name, default):
    return int(os.getenv(name, default))


def load(path, default):
    if not path.exists():
        return default
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, data):
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    part = path.with_name(path.name + '.part')
    part.write_bytes(gzip.compress(raw) if path.suffix == '.gz' else raw)
    part.replace(path)  # atomic: a crash never leaves half a queue


def order(rows, present, excluded, seen):
    """rows: (id, issuance_date). Ids still to convert: new since the previous scan (seen) first, then newest first, undated last."""
    todo = [(i, d or '') for i, d in rows if i not in present and i not in excluded]
    key = lambda row: (row[1] != '', row[1], int(row[0]) if row[0].isdigit() else 0)  # noqa: E731
    new = sorted((r for r in todo if seen is not None and r[0] not in seen), key=key, reverse=True)
    old = sorted((r for r in todo if seen is None or r[0] in seen), key=key, reverse=True)
    return [i for i, _ in new + old]


def scan(config, source, target, state):
    present = {h['_id'] for h in target.scan(config.target['documents'], {'match_all': {}}, False, size=10000)}
    rows = [(h['_id'], (h.get('_source') or {}).get('issuance_date'))
            for h in source.scan(config.source['documents'], {'match_all': {}}, ['issuance_date'], size=10000)]
    seen = load(state / 'seen.json.gz', None)
    seen = set(seen) if seen is not None else None
    queue = order(rows, present, load(state / 'excluded.json', {}), seen)
    info = {'at': time.time(), 'time': datetime.now().astimezone().isoformat(timespec='seconds'), 'source': len(rows), 'target': len(present),
            'queue': len(queue), 'new': 0 if seen is None else sum(1 for i, _ in rows if i not in seen and i not in present)}
    save(state / 'queue.json', queue)
    save(state / 'seen.json.gz', [i for i, _ in rows])
    save(state / 'scan.json', info)
    # Documents new in the source must become resolvable relation targets: refresh the number table once per scan.
    source.use_number_index(config.source['documents'], config.workdir)
    return queue, info


def settle(root, batch, attempts, excluded, max_attempts):
    """Read a finished batch run: (done ids, failed ids, outage). Updates attempts and excluded in place."""
    log, fails = root / 'documents.jsonl', root / 'failures.jsonl'
    records = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()] if log.exists() else []
    done = {r['doc_id'] for r in records}
    failed = {json.loads(line)['doc_id'] for line in fails.read_text(encoding='utf-8').splitlines() if line.strip()} - done if fails.exists() else set()
    # Small batches never count as an outage: else the last few always-failing documents would never be excluded.
    outage = len(batch) >= 4 and 2 * len(failed) >= len(batch)
    for record in records:
        if record.get('skipped'):
            excluded[record['doc_id']] = record['skipped']
    if not outage:
        for doc_id in failed:
            attempts[doc_id] = attempts.get(doc_id, 0) + 1
            if attempts[doc_id] >= max_attempts:
                excluded[doc_id] = f'loi_{attempts[doc_id]}_lan'
    return done, failed, outage


def forever(config, source, target, once=False, scan_only=False):
    state = config.workdir / 'auto'
    (state / 'batches').mkdir(parents=True, exist_ok=True)
    lock = open(state / 'lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Đã có một tiến trình auto khác đang chạy (work/auto/lock)')
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    rescan, per_worker = setting('AUTO_RESCAN_HOURS', 24) * 3600, setting('AUTO_BATCH_PER_WORKER', 25)
    max_attempts, wait = setting('AUTO_MAX_ATTEMPTS', 3), 60
    while not stop.is_set():
        try:
            info, queue = load(state / 'scan.json', {}), load(state / 'queue.json', None)
            if scan_only or queue is None or time.time() - info.get('at', 0) >= rescan:
                queue, info = scan(config, source, target, state)
                print(f'auto: quét nguồn {info["time"]}: nguồn {info["source"]}, đích {info["target"]}, mới {info["new"]}, '
                      f'hàng đợi {info["queue"]}', flush=True)
                if scan_only:
                    return 0
            attempts, excluded = load(state / 'attempts.json', {}), load(state / 'excluded.json', {})
            workers = llm.concurrency()
            batch = queue[:workers * per_worker]
            if batch:
                # Dedup at the last moment: whatever reached the target since the scan is dropped from the queue.
                hits = target.request('POST', f"/{config.target['documents']}/_search",
                                      {'size': len(batch), '_source': False, 'query': {'ids': {'values': batch}}})['hits']['hits']
                present = {h['_id'] for h in hits}
                if present:
                    queue = [i for i in queue if i not in present]
                    save(state / 'queue.json', queue)
                    batch = [i for i in batch if i not in present]
            if not queue:
                left = max(60, rescan - (time.time() - info.get('at', 0)))
                print(f'auto: hàng đợi trống, quét lại sau {left / 3600:.1f} giờ', flush=True)
                stop.wait(min(left, 3600))
                continue
            if not batch:
                continue
            name = base = 'auto-' + datetime.now().strftime('%Y%m%d-%H%M%S')
            n = 1
            while (config.workdir / name).exists():  # a run folder is never reused: it would keep the old batch's ids.json
                n += 1
                name = f'{base}-{n}'
            ids_file = state / 'batches' / f'{name}.txt'
            ids_file.write_text('\n'.join(batch) + '\n')
            args = Namespace(run=name, ids=str(ids_file), sample=None, seed=0, all=False, from_date=None, to_date=None, legal_type=None,
                             limit=None, workers=workers, no_qa=False, dry_run=False, redo=False, keep_number_index=True, stop=stop)
            started = time.time()
            run(config, source, target, args)
            done, failed, outage = settle(config.workdir / name, batch, attempts, excluded, max_attempts)
            if outage:  # keep the batch where it is: it goes first again once the service is back
                queue = [i for i in queue if i not in done and i not in excluded]
            else:
                retry = [i for i in batch if i in failed and i not in excluded]
                queue = [i for i in queue if i not in done and i not in failed and i not in excluded] + retry
            save(state / 'queue.json', queue)
            save(state / 'attempts.json', attempts)
            save(state / 'excluded.json', excluded)
            entry = {'at': datetime.now().astimezone().isoformat(timespec='seconds'), 'run': name, 'workers': workers, 'batch': len(batch), 'done': len(done), 'failed': len(failed), 'outage': outage,
                     'seconds': round(time.time() - started), 'queue': len(queue), 'excluded': len(excluded)}
            with (state / 'history.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
            print(f'auto: {entry}', flush=True)
            if once:
                return 1 if failed else 0
            wait = min(wait * 2, 1800) if outage else 60
            if outage:
                print(f'auto: {len(failed)}/{len(batch)} văn bản lỗi, coi là dịch vụ trục trặc; chờ {wait} giây', flush=True)
                stop.wait(wait)
        except Exception as exc:
            print(f'auto: lỗi {type(exc).__name__}: {str(exc)[:300]}; thử lại sau {wait} giây', flush=True)
            if once or scan_only:
                raise
            stop.wait(wait)
            wait = min(wait * 2, 1800)
    print('auto: dừng theo yêu cầu', flush=True)
    return 0
