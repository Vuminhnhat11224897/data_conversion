"""Compare two runs on one labeled set: three groups of measures and what changed between them.

Usage: python -m eval.compare <set> <run A> <run B> [--json out.json]

Groups (the old eval.score report stays as it is, for comparison):
1. phat_hien (detection): source document, target document and action are right, whatever the source unit or the position.
2. pham_vi (exact scope): group 1 plus the position or the part named by name; a whole-document act is the position "toàn bộ".
   A relation kept for review (unresolved) is not an edge: it counts in neither group 1 nor group 2.
3. truy_vet (tracing): for the acts found in group 1, the source unit is the labeled one or one up or down its tree, and the
   source unit's effective day (source_ngay_hieu_luc) is the labeled unit's day.

Changes from A to B, at group 1 level: true acts recovered, true acts lost, new wrong acts, wrong acts removed, and moves between
validated and unresolved.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval import score as S  # noqa: E402
from vbpl_v3.legal_status import unit_dates, unit_of_path  # noqa: E402


def load(set_name):
    gold = {g['doc_id']: g for f in sorted((ROOT / 'eval' / 'gold' / set_name).glob('*.json')) for g in json.loads(f.read_text())}
    packets = {p['doc_id']: p for f in sorted((ROOT / 'eval' / 'packets' / set_name).glob('*.json')) for p in json.loads(f.read_text())}
    return gold, packets


def run_items(run, doc_id, expected):
    output = ROOT / 'work' / run / 'dry-run' / f'{doc_id}.json'
    if not output.exists():
        return None
    out = json.loads(output.read_text())
    relations = [r['_source'] for r in out['relations']]
    validated = S.align(S.tool_items(relations, 'validated'), expected)
    unresolved = S.align(S.tool_items(relations, 'unresolved'), expected)
    return {'document': out['document'], 'relations': relations, 'validated': validated, 'unresolved': unresolved}


def measure(gold, packets, run):
    c = Counter()
    states = {}
    for doc_id, labels in gold.items():
        expected = S.gold_items(S.normalize_gold(labels, packets.get(doc_id)))
        got = run_items(run, doc_id, expected)
        if got is None:
            c['missing_outputs'] += 1
            continue
        g1, t1 = {i[1:3] for i in expected}, {i[1:3] for i in got['validated']}
        u1 = {i[1:3] for i in got['unresolved']} - t1
        c['p1_tp'] += len(g1 & t1); c['p1_fp'] += len(t1 - g1 - S.extra_halves(g1, t1)); c['p1_fn'] += len(g1 - t1)
        g2, t2 = {i[1:] for i in expected}, {i[1:] for i in got['validated']}
        c['p2_tp'] += len(g2 & t2); c['p2_fp'] += len(t2 - g2 - S.extra_halves(g2, t2)); c['p2_fn'] += len(g2 - t2)
        for key in g1 & t1:
            units = [i[0] for i in expected if i[1:3] == key]
            tool = [r for r in got['relations'] if r.get('resolution_status') == 'validated' and r['action'] == key[0]
                    and S.document(r.get('target_doc')) == key[1]]
            near = [r for r in tool if any(S.related(S.unit(r['source_path']), u) for u in units)]
            c['p3_total'] += 1
            c['p3_unit'] += bool(near)
            unit = unit_of_path('intro' if units[0] == 'Phần đầu' else units[0])
            day = unit_dates(unit, got['document'], got['document'].get('hieu_luc_rieng') or [])['ngay_hieu_luc'] if unit \
                else got['document'].get('ngay_hieu_luc')
            c['p3_day'] += bool(tool) and (tool[0].get('source_ngay_hieu_luc') == day)
        for key in g1 | t1 | u1:
            states[(doc_id,) + key] = ('validated' if key in t1 else 'unresolved' if key in u1 else 'none', key in g1)
    ratio = lambda a, b: round(a / b, 3) if b else None
    report = {'phat_hien': {'P': ratio(c['p1_tp'], c['p1_tp'] + c['p1_fp']), 'R': ratio(c['p1_tp'], c['p1_tp'] + c['p1_fn']),
                            'tp': c['p1_tp'], 'fp': c['p1_fp'], 'fn': c['p1_fn']},
              'pham_vi': {'P': ratio(c['p2_tp'], c['p2_tp'] + c['p2_fp']), 'R': ratio(c['p2_tp'], c['p2_tp'] + c['p2_fn']),
                          'tp': c['p2_tp'], 'fp': c['p2_fp'], 'fn': c['p2_fn']},
              'truy_vet': {'don_vi_nguon': ratio(c['p3_unit'], c['p3_total']), 'ngay_tac_dong': ratio(c['p3_day'], c['p3_total']),
                           'n': c['p3_total']},
              'missing_outputs': c['missing_outputs']}
    return report, states


def changes(a, b):
    out = Counter()
    for key in set(a) | set(b):
        sa, real_a = a.get(key, ('none', None))
        sb, real_b = b.get(key, ('none', None))
        real = real_a if real_a is not None else real_b
        hit_a, hit_b = sa == 'validated', sb == 'validated'
        if real and not hit_a and hit_b: out['dung_phuc_hoi'] += 1
        if real and hit_a and not hit_b: out['dung_bi_mat'] += 1
        if not real and not hit_a and hit_b: out['sai_moi'] += 1
        if not real and hit_a and not hit_b: out['sai_duoc_loai'] += 1
        if sa != sb:
            out[f'{sa}->{sb}'] += 1
    return dict(out)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('set')
    cli.add_argument('a')
    cli.add_argument('b')
    cli.add_argument('--json')
    args = cli.parse_args()
    gold, packets = load(args.set)
    ra, sa = measure(gold, packets, args.a)
    rb, sb = measure(gold, packets, args.b)
    result = {'set': args.set, 'A': {'run': args.a, **ra}, 'B': {'run': args.b, **rb}, 'thay_doi': changes(sa, sb)}
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
