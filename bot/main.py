"""Telegram report of the continuous v2 -> v4 migration (python -m vbpl_v3 auto), every BOT_INTERVAL_MINUTES (30).

Reads only: work/auto/ (history, queue, excluded), the batch folders work/auto-*/ and the counts of the three target indices.
Each report covers the batches finished in one window (00/30 by default); windows missed while the bot was down or had no
token are merged into one report. Delivery progress is kept in BOT_STATE_DIR, so a restart never resends a sent part.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import statistics
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger('vbpl-bot')
ZONE = ZoneInfo('Asia/Ho_Chi_Minh')


def settings():
    # The project .env, then the process environment (docker --env-file), then bot/.env: token and chat ID live there.
    return {**dotenv_values(ROOT.parent / '.env'), **os.environ, **dotenv_values(ROOT / '.env')}


def number(n):
    return f'{n:,}'.replace(',', '.')


def pct(n, total):
    return f'{100 * n / total:.0f}%' if total else '0%'


def local(value):
    stamp = datetime.fromisoformat(value) if isinstance(value, str) else value
    return stamp.replace(tzinfo=ZONE) if stamp.tzinfo is None else stamp.astimezone(ZONE)


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def read_jsonl(path):
    try:
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except OSError:
        return []


def workdir(config):
    path = Path(config.get('V3_WORKDIR') or 'work')
    return path if path.is_absolute() else ROOT.parent / path


def category(error):
    low = error.lower()
    match = re.search(r'\b([45]\d\d)\b (?:client|server) error|http (\d{3})|\b(504) gateway', low)
    if match:
        return 'HTTP ' + next(g for g in match.groups() if g)
    if any(k in low for k in ('timed out', 'timeout', 'deadline')):
        return 'Timeout / hết thời gian'
    if any(k in low for k in ('connection', 'max retries', 'refused')):
        return 'Kết nối'
    return error.split(':', 1)[0].strip() or 'Khác'


def window_entries(work, start, end):
    return [e for e in read_jsonl(work / 'auto' / 'history.jsonl') if e.get('at') and start < local(e['at']) <= end]


def details(work, entries):
    """Totals over the documents of the given batches."""
    total = Counter()
    skipped, errors, seconds = Counter(), Counter(), []
    for entry in entries:
        for record in read_jsonl(work / entry['run'] / 'documents.jsonl'):
            if record.get('skipped'):
                skipped[record['skipped']] += 1
                continue
            total['written'] += 1
            total['chunks'] += record.get('chunks', 0)
            total['relations'] += record.get('relations', 0)
            total['resolved'] += record.get('resolved', 0)
            total['metadata'] += bool(record.get('metadata_boc_lai'))
            total['ai_warnings'] += bool(record.get('ai_warnings'))
            if record.get('seconds') is not None:
                seconds.append(record['seconds'])
        for failure in read_jsonl(work / entry['run'] / 'failures.jsonl'):
            errors[category(failure.get('error', ''))] += 1
    return total, skipped, errors, seconds


def target_counts(config):
    url = (config.get('TARGET_ES_URL') or '').rstrip('/')
    names = [config.get(k) for k in ('TARGET_DOCUMENT_INDEX', 'TARGET_CHUNK_INDEX', 'TARGET_CHANGE_INDEX')]
    if not url or not all(names):
        return None
    try:
        return [requests.get(f'{url}/{name}/_count', timeout=(5, 20)).json()['count'] for name in names]
    except (requests.RequestException, ValueError, KeyError):
        return None


def mode(config, now):
    """(night, workers now, next switch time, workers after it), like vbpl_v3.llm.concurrency."""
    start, end = (int(x) for x in config.get('LLM_NIGHT_HOURS', '22-6').split('-'))
    night = (now.hour >= start or now.hour < end) if start > end else start <= now.hour < end
    day, nights = int(config.get('LLM_CONCURRENCY_DAY', '3')), int(config.get('LLM_CONCURRENCY_NIGHT', '10'))
    return night, nights if night else day, f'{end if night else start:02d}:00', day if night else nights


def in_progress(work):
    """(done, total, started) of a batch folder auto has not finished yet, else None."""
    finished = {e.get('run') for e in read_jsonl(work / 'auto' / 'history.jsonl')}
    folders = [f for f in sorted(work.glob('auto-*')) if f.name not in finished and (f / 'ids.json').exists()]
    if not folders:
        return None
    folder = folders[-1]
    done = len(read_jsonl(folder / 'documents.jsonl')) + len(read_jsonl(folder / 'failures.jsonl'))
    return done, len(read_json(folder / 'ids.json', [])), datetime.fromtimestamp((folder / 'ids.json').stat().st_mtime, ZONE)


def timed(call):
    started = time.monotonic()
    result = call()
    return result, (time.monotonic() - started) * 1000


def probes(config):
    """One line per connection auto uses, measured now. Keys go in headers only; never printed."""
    lines = []

    def es(label, url, extra):
        host = urlsplit(url).netloc
        try:
            health, ms = timed(lambda: requests.get(f'{url}/_cluster/health', timeout=(5, 15)).json())
            line = f"• {label} {host}: ✅ {health.get('status', '?')} · {ms:.0f} ms"
            if extra:
                disk = requests.get(f'{url}/_cat/allocation?format=json&bytes=gb', timeout=(5, 15)).json()
                used = max(float(n['disk.percent']) for n in disk if n.get('disk.percent'))
                heap = requests.get(f'{url}/_nodes/stats/jvm?filter_path=nodes.*.jvm.mem.heap_used_percent', timeout=(5, 15)).json()
                line += f" · đĩa {used:.0f}% · heap {max(n['jvm']['mem']['heap_used_percent'] for n in heap['nodes'].values())}%"
            lines.append(line)
        except Exception as exc:
            lines.append(f'• {label} {host}: ❌ {type(exc).__name__}')

    source, target = (config.get(k, '').rstrip('/') for k in ('SOURCE_ES_URL', 'TARGET_ES_URL'))
    if source:
        es('ES nguồn', source, extra=False)
    if target:
        es('ES đích', target, extra=True)
    llm, model = (config.get('LITELLM_BASE_URL') or '').rstrip('/'), config.get('LITELLM_MODEL', '')
    if llm:
        try:
            data, ms = timed(lambda: requests.get(f'{llm}/models', timeout=(5, 15),
                                                  headers={'Authorization': 'Bearer ' + config.get('LITELLM_API_KEY', '')}).json())
            found = model in [m.get('id') for m in data.get('data', [])]
            lines.append(f"• LLM {urlsplit(llm).netloc} ({model}): {'✅' if found else '⚠️ không thấy model'} · {ms:.0f} ms")
        except Exception as exc:
            lines.append(f'• LLM {urlsplit(llm).netloc}: ❌ {type(exc).__name__}')
    embed = (config.get('EMBEDDING_URL') or '').rstrip('/')
    if embed.endswith('/v1'):
        try:
            data, ms = timed(lambda: requests.post(f'{embed}/embeddings', timeout=(5, 30), json={
                'model': config.get('EMBEDDING_MODEL', 'bge-m3'), 'input': ['Điều 1. Phạm vi điều chỉnh']},
                headers={'Authorization': 'Bearer ' + config.get('EMBEDDING_KEY', '')}).json())
            lines.append(f"• Embedding {urlsplit(embed).netloc}: ✅ {len(data['data'][0]['embedding'])} chiều · {ms:.0f} ms")
        except Exception as exc:
            lines.append(f'• Embedding {urlsplit(embed).netloc}: ❌ {type(exc).__name__}')
    return lines


def last_activity(work):
    """Newest write of auto: its history or a file of the newest batch folder (documents finish one by one)."""
    stamps = []
    for path in [work / 'auto' / 'history.jsonl', *sorted(work.glob('auto-*'))[-1:]]:
        files = [path] if path.is_file() else [path / n for n in ('ids.json', 'documents.jsonl', 'failures.jsonl')]
        stamps += [f.stat().st_mtime for f in files if f.exists()]
    return datetime.fromtimestamp(max(stamps), ZONE) if stamps else None


def render(config, start, end, now=None):
    now = now or datetime.now(ZONE)
    work = workdir(config)
    state = work / 'auto'
    entries = window_entries(work, start, end)
    total, skipped, errors, seconds = details(work, entries)
    queue = read_json(state / 'queue.json', None)
    excluded = Counter(read_json(state / 'excluded.json', {}).values())
    scan = read_json(state / 'scan.json', {})
    hours = (end - start).total_seconds() / 3600
    lines = ['🔔 Báo cáo chuyển VBPL v2 → v4', f'Khung: {start:%H:%M}–{end:%H:%M} {end:%d/%m}']
    seen = last_activity(work)
    stale = int(config.get('BOT_STALE_MINUTES', '45'))
    if queue is None:
        lines.append('Trạng thái: chưa có hàng đợi (auto chưa chạy lần nào)')
    elif seen is None:
        lines.append('⚠️ Trạng thái: luồng chuyển đổi chưa chạy. Kiểm tra: docker ps, docker logs vbpl-auto')
    elif not queue:
        lines.append('Trạng thái: hàng đợi trống, chờ lần quét v2 tiếp theo')
    elif (now - seen).total_seconds() > stale * 60:
        lines.append(f'⚠️ Trạng thái: không thấy hoạt động {(now - seen).total_seconds() / 60:.0f} phút. Kiểm tra: docker logs vbpl-auto')
    else:
        lines.append('Trạng thái: đang chạy')
    outages = sum(1 for e in entries if e.get('outage'))
    if outages:
        lines.append(f'⚠️ Lỗi hàng loạt {outages} lần: dịch vụ LLM/embedding/ES có thể trục trặc, luồng tự chờ rồi chạy lại')
    lines += ['', f'Trong {hours * 60:.0f} phút',
              f"• Ghi -v4: {number(total['written'])} văn bản · {number(total['chunks'])} chunk · "
              f"{number(total['relations'])} quan hệ ({pct(total['resolved'], total['relations'])} nối được đích)",
              f"• Bỏ qua: {sum(skipped.values())}" + (' (' + ', '.join(f'{k} {n}' for k, n in skipped.most_common()) + ')' if skipped else ''),
              f"• Lỗi: {sum(errors.values())}",
              f"• Bóc lại metadata: {number(total['metadata'])} văn bản · cảnh báo AI: {total['ai_warnings']}",
              f"• Tốc độ: {number(round(total['written'] / hours)) if hours else 0} văn bản/giờ"]
    night, workers, switch, after = mode(config, now)
    lines += ['', 'Luồng', f"• Hiện tại: {'ban đêm' if night else 'ban ngày'} · {workers} luồng (từ {switch}: {after} luồng)"]
    current = in_progress(work)
    if current:
        lines.append(f'• Đang xử lý: {current[0]}/{current[1]} văn bản, bắt đầu {current[2]:%H:%M}')
    if seconds:
        lines.append(f"• Thời gian mỗi văn bản: trung vị {statistics.median(seconds):.1f} giây".replace('.', ','))
    counts = target_counts(config)
    day = [e for e in read_jsonl(state / 'history.jsonl') if e.get('at') and local(e['at']) > end - timedelta(hours=24)]
    rate = sum(e.get('done', 0) for e in day) / 24 if day else 0
    lines += ['', 'Lũy kế',
              '• -v4: ' + (f'{number(counts[0])} văn bản · {number(counts[1])} chunk · {number(counts[2])} quan hệ'
                           if counts else 'không đọc được ES đích'),
              f"• Hàng đợi còn: {number(len(queue)) if queue is not None else '?'} · đã loại: {sum(excluded.values())}"
              + (' (' + ', '.join(f'{k} {n}' for k, n in excluded.most_common(3)) + ')' if excluded else '')]
    if queue and rate:
        lines.append(f'• Ước tính còn: {len(queue) / rate / 24:.0f} ngày (theo {number(round(rate * 24))} văn bản trong 24 giờ qua)')
    if scan.get('at'):  # epoch seconds: right whatever zone the scan ran in
        lines.append(f"• Quét v2 gần nhất: {datetime.fromtimestamp(scan['at'], ZONE):%H:%M %d/%m} · văn bản mới {number(scan.get('new', 0))}")
    if errors:
        lines += ['', f'Phân loại lỗi ({sum(errors.values())})']
        lines += [f'• {k}: {n} ({pct(n, sum(errors.values()))})' for k, n in errors.most_common(4)]
    lines += ['', f'Kết nối (đo lúc {now:%H:%M})', *probes(config)]
    lines += ['', 'Văn bản lỗi được thử lại ở cuối hàng đợi, lỗi 3 lần thì loại.']
    return '\n'.join(lines)


def chunks(report, limit=3400):
    parts, current = [], ''
    for line in report.splitlines(keepends=True):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ''
            parts.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            parts.append(current)
            current = ''
        current += line
    if current:
        parts.append(current)
    if len(parts) == 1:
        return parts
    return [f'[{i}/{len(parts)}]\n{part}' for i, part in enumerate(parts, 1)]


def send(token, chat_id, message):
    # Never print exception URLs: Telegram URLs contain the bot token.
    try:
        response = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                                 json={'chat_id': chat_id, 'text': message}, timeout=(5, 25))
        data = response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError('Telegram: lỗi kết nối hoặc phản hồi không hợp lệ') from None
    if response.status_code == 429:
        delay = min(300, max(1, int(data.get('parameters', {}).get('retry_after', 30))))
        time.sleep(delay)
        raise RuntimeError('Telegram: đang giới hạn tốc độ, sẽ thử lại')
    if not response.ok or not data.get('ok'):
        raise RuntimeError(f'Telegram: gửi thất bại, HTTP {response.status_code}')


def boundary(now, minutes):
    """The last window boundary at or before now (00/30 for 30 minutes)."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start + timedelta(minutes=(now - start).total_seconds() // 60 // minutes * minutes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true', help='In báo cáo của khung vừa xong, không gửi Telegram')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.preview:
        config = settings()
        end = boundary(datetime.now(ZONE), int(config.get('BOT_INTERVAL_MINUTES', '30')))
        print(render(config, end - timedelta(minutes=int(config.get('BOT_INTERVAL_MINUTES', '30'))), end))
        return
    folder = Path(os.getenv('BOT_STATE_DIR', str(ROOT / 'state')))
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder / 'delivery.sqlite3')
    db.execute('CREATE TABLE IF NOT EXISTS deliveries (id TEXT PRIMARY KEY, parts TEXT, next_part INTEGER DEFAULT 0)')
    db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')
    if not db.execute("SELECT 1 FROM meta WHERE key='last_end'").fetchone():
        first = boundary(datetime.now(ZONE), int(settings().get('BOT_INTERVAL_MINUTES', '30')))
        db.execute("INSERT INTO meta VALUES ('last_end', ?)", (first.isoformat(),))
        db.commit()
    LOG.info('Bot đã chạy; chờ cấu hình Telegram và khung báo cáo tiếp theo.')
    while True:
        try:
            config = settings()
            token, chat = config.get('TELEGRAM_BOT_TOKEN'), config.get('TELEGRAM_CHAT_ID')
            if not token or not chat:
                time.sleep(15)
                continue
            pending = db.execute('SELECT id,parts,next_part FROM deliveries WHERE next_part < json_array_length(parts)').fetchone()
            if pending is None:
                start = datetime.fromisoformat(db.execute("SELECT value FROM meta WHERE key='last_end'").fetchone()[0])
                end = boundary(datetime.now(ZONE), int(config.get('BOT_INTERVAL_MINUTES', '30')))
                if end <= start:
                    time.sleep(15)
                    continue
                # Windows missed while the bot was down or had no token are merged into this one report.
                parts = chunks(render(config, start, end))
                db.execute('INSERT OR REPLACE INTO deliveries(id,parts,next_part) VALUES (?,?,0)', (end.isoformat(), json.dumps(parts)))
                db.execute("UPDATE meta SET value=? WHERE key='last_end'", (end.isoformat(),))
                db.commit()
                pending = (end.isoformat(), json.dumps(parts), 0)
            identity, parts, index = pending[0], json.loads(pending[1]), pending[2]
            while index < len(parts):
                send(token, chat, parts[index])
                index += 1
                db.execute('UPDATE deliveries SET next_part=? WHERE id=?', (index, identity))
                db.commit()
                time.sleep(1)
        except Exception as exc:
            LOG.warning('Báo cáo chưa gửi được (%s); sẽ thử lại.', type(exc).__name__)
            time.sleep(30)


if __name__ == '__main__':
    main()
