"""Replay a finished run with the current code and the model answers that run stored, without any new model call.

Usage: python -m eval.replay <base run> <new run> <ids file> [--start-year N] [--without b2]
Copies the stored answers of work/<base run> (cache/, extract/, qa/) to work/<new run>, then runs
`convert --dry-run --redo` with LLM_REPLAY=strict: an answer that is not stored stops that document (ReplayMiss) instead of
asking the model. A replay is valid only with 0 such documents; the report lists them. A change measured on a valid replay
comes from the code alone.

--without b2: the units governed by a list lead are not added to what the model reads (extract.units). That is the one change of
21/10/2026 that alters the model's input; without it, the other changes (evidence, scope) are measured by a strict replay.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('base')
    cli.add_argument('new')
    cli.add_argument('ids')
    cli.add_argument('--start-year', type=int, help='START_YEAR của lượt gốc (review50 dùng 1000)')
    cli.add_argument('--workers', type=int, default=6)
    cli.add_argument('--without', choices=['b2'], action='append', default=[])
    cli.add_argument('--allow-new', action='store_true', help='Cho gọi model khi thiếu câu trả lời (đo thay đổi đổi đầu vào của model, như B2)')
    args = cli.parse_args()
    base, new = ROOT / 'work' / args.base, ROOT / 'work' / args.new
    if not (base / 'extract').exists():
        sys.exit(f'{base} không có câu trả lời đã lưu')
    if new.exists():
        shutil.rmtree(new)
    new.mkdir(parents=True)
    for part in ('cache', 'extract', 'qa'):
        if (base / part).exists():
            shutil.copytree(base / part, new / part)
    import time
    started = time.time()
    if not args.allow_new:
        os.environ['LLM_REPLAY'] = 'strict'
    if args.start_year:
        os.environ['START_YEAR'] = str(args.start_year)
    sys.path.insert(0, str(ROOT))
    if 'b2' in args.without:
        import vbpl_v3.extract
        vbpl_v3.extract.opens_list = lambda lead: False  # only extract.units uses this name: validation keeps governance.opens_list
    from vbpl_v3.__main__ import main as cli_main
    try:
        exit_code = cli_main(['convert', '--run', args.new, '--ids', args.ids, '--dry-run', '--redo', '--workers', str(args.workers)]) or 0
    except SystemExit as stop:
        exit_code = stop.code
    failures = [json.loads(line) for line in (new / 'failures.jsonl').read_text().splitlines()] if (new / 'failures.jsonl').exists() else []
    misses = [f for f in failures if 'chạy lại chặt' in json.dumps(f, ensure_ascii=False)]
    records = [json.loads(line) for line in (new / 'documents.jsonl').read_text().splitlines()] if (new / 'documents.jsonl').exists() else []
    structure = sum(1 for r in records if 'chạy lại chặt' in json.dumps(r.get('ai_warnings') or [], ensure_ascii=False))
    report = {'base': args.base, 'new': args.new, 'documents': len(records), 'failures': len(failures),
              'replay_misses': len(misses), 'structure_fallbacks': structure, 'valid': not failures,
              'missed_documents': [f.get('doc_id') for f in misses][:20], 'exit_code': exit_code, 'without': args.without,
              'strict': not args.allow_new,
              'new_model_answers': sum(1 for p in new.rglob('llm_response.json') if p.stat().st_mtime >= started)}
    (new / 'replay.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
