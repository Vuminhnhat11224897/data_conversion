"""One measurement round on the 6 labeled sets: replay each set with the current code, then compare with baseline A.

Usage: python -m eval.round <name> [--without b2] [--allow-new] [--from <run>] [--sets dev,h2,...]
Runs `eval.replay <base> <name>-<set> …` for every set and prints, per set, detection and exact-scope P / R with counts
(right, wrong, missed) for A and for the new run, and the changes between them (eval.compare). A strict replay (the default) asks
the model nothing, so all sets run at once; with --allow-new the model may be asked (B2), so the sets run one after another (the
model server takes 3 calls at once by day). --from C replays the answers stored by round C (<C>-<set>), the B2 answers
included, so a later code change is measured with B2 and no model call; the comparison stays with A.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# key: (gold set, baseline run A whose stored answers are replayed, ids file, START_YEAR of that run)
SETS = {'dev': ('dev', 'r7-dev', 'eval/sets/dev.txt', None),
        'h2': ('holdout-20261020-adj', 'r7-holdout2', 'eval/sets/holdout-20261020.txt', None),
        'h3': ('holdout-20261021', 'A-h3', 'eval/sets/holdout-20261021.txt', None),
        'h4': ('holdout-20261022', 'h4-final', 'eval/sets/holdout-20261022.txt', None),
        'blind': ('blind-adj', 'A-blind', 'work/blind-minus-review50-ids.txt', None),
        'r50': ('review50-20261019', 'A-r50', 'eval/sets/review50-20261019.txt', 1000)}


def replay(name, key, options, source=None):
    gold, base, ids, year = SETS[key]
    base = f'{source}-{key}' if source else base
    command = [sys.executable, '-m', 'eval.replay', base, f'{name}-{key}', ids] + options + (['--start-year', str(year)] if year else [])
    return subprocess.Popen(command, cwd=ROOT, stdout=open(ROOT / 'work' / f'{name}-{key}.log', 'w'), stderr=subprocess.STDOUT)


def cell(report, group):
    r = report[group]
    number = lambda x: '–' if x is None else f'{x:.3f}'.replace('.', ',')
    return f"{number(r['P'])} / {number(r['R'])} ({r['tp']}, {r['fp']}, {r['fn']})"


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('name')
    cli.add_argument('--without', choices=['b2'], action='append', default=[])
    cli.add_argument('--allow-new', action='store_true')
    cli.add_argument('--sets', default=','.join(SETS))
    cli.add_argument('--from', dest='source', help='lượt có câu trả lời để chạy lại (mặc định: lượt A)')
    args = cli.parse_args()
    keys = args.sets.split(',')
    options = sum((['--without', w] for w in args.without), []) + (['--allow-new'] if args.allow_new else [])
    if args.allow_new:
        for key in keys:
            replay(args.name, key, options, args.source).wait()
    else:
        for process in [replay(args.name, key, options, args.source) for key in keys]:
            process.wait()
    rows, changes, invalid = [], [], []
    for key in keys:
        state = json.loads((ROOT / 'work' / f'{args.name}-{key}' / 'replay.json').read_text())
        if not state['valid']:
            invalid.append(f"{key}: {state['failures']} lỗi, {state['replay_misses']} câu trả lời thiếu")
        gold, base = SETS[key][:2]
        out = subprocess.run([sys.executable, '-m', 'eval.compare', gold, base, f'{args.name}-{key}'], cwd=ROOT, capture_output=True, text=True)
        d = json.loads(out.stdout)
        rows.append(f"| {key} | {cell(d['A'], 'phat_hien')} | {cell(d['B'], 'phat_hien')} | {cell(d['A'], 'pham_vi')} | {cell(d['B'], 'pham_vi')} |"
                    f" {state['new_model_answers']} |")
        t = d['thay_doi']
        changes.append(f"| {key} | {t.get('dung_phuc_hoi', 0)} | {t.get('dung_bi_mat', 0)} | {t.get('sai_moi', 0)} | {t.get('sai_duoc_loai', 0)} |")
    print(f'| Bộ | A phát hiện P / R (đúng, sai, sót) | {args.name} phát hiện | A phạm vi | {args.name} phạm vi | LLM mới |')
    print('| --- | --- | --- | --- | --- | --- |')
    print('\n'.join(rows))
    print()
    print('| Bộ | Đúng phục hồi | Đúng bị mất | Sai mới | Sai được loại |')
    print('| --- | --- | --- | --- | --- |')
    print('\n'.join(changes))
    if invalid:
        print('\nKHÔNG HỢP LỆ: ' + '; '.join(invalid))
        sys.exit(1)


if __name__ == '__main__':
    main()
