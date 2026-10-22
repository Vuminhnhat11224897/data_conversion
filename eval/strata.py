"""Score a run on a stratified set: each stratum, and the population estimate weighted by stratum size.

Usage: python -m eval.strata <set>[+<set>…] <run> [--boot 2000] [--json out.json]
Reads eval/sets/<set>.strata.json ({strata: {name: {N, n, ids}}}), the labels of eval/gold/<set>/ and work/<run>/dry-run/.
Measures as eval.compare: phat_hien (source document, act and target) and pham_vi (plus the position or the part named by name),
counted per document. A stratum's counts are weighted by N/n (its population size over its sample size); the 95% interval comes
from a bootstrap that redraws documents within each stratum.
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval import compare as C  # noqa: E402
from eval import score as S  # noqa: E402


def per_document(gold, packets, run, ids):
    """{doc_id: (tp1, fp1, fn1, tp2, fp2, fn2)}; a document the run has no output for counts every label as missed."""
    out = {}
    for doc_id in ids:
        expected = S.gold_items(S.normalize_gold(gold[doc_id], packets.get(doc_id)))
        got = C.run_items(run, doc_id, expected)
        tool = got['validated'] if got else set()
        g1, t1 = {i[1:3] for i in expected}, {i[1:3] for i in tool}
        g2, t2 = {i[1:] for i in expected}, {i[1:] for i in tool}
        out[doc_id] = (len(g1 & t1), len(t1 - g1), len(g1 - t1), len(g2 & t2), len(t2 - g2), len(g2 - t2))
    return out


def rates(counts, weights):
    """(P1, R1, P2, R2) of weighted sums of per-document counts."""
    tp1, fp1, fn1, tp2, fp2, fn2 = (sum(w * c[k] for c, w in zip(counts, weights)) for k in range(6))
    ratio = lambda a, b: a / b if b else None
    return ratio(tp1, tp1 + fp1), ratio(tp1, tp1 + fn1), ratio(tp2, tp2 + fp2), ratio(tp2, tp2 + fn2)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('set')
    cli.add_argument('run')
    cli.add_argument('--boot', type=int, default=2000)
    cli.add_argument('--json')
    args = cli.parse_args()
    # Several sets drawn from one population are scored as one sample: "h5-20261022+h6-20261022".
    gold, packets, strata = {}, {}, {}
    for name in args.set.split('+'):
        found, cards = C.load(name)
        gold.update(found)
        packets.update(cards)
        design = json.loads((ROOT / 'eval' / 'sets' / f'{name}.strata.json').read_text())
        for key, s in design['strata'].items():
            entry = strata.setdefault(key, {'N': s['N'], 'ids': []})
            if entry['N'] != s['N']:
                sys.exit(f'Tầng {key}: N khác nhau giữa các bộ, không gộp được')
            entry['ids'] += s['ids']
    docs = {name: per_document(gold, packets, args.run, [i for i in s['ids'] if i in gold]) for name, s in strata.items()}
    weight = {name: strata[name]['N'] / max(1, len(docs[name])) for name in strata}
    report = {'set': args.set, 'run': args.run, 'strata': {}}
    names = ('phat_hien_P', 'phat_hien_R', 'pham_vi_P', 'pham_vi_R')
    for name, per in docs.items():
        counts = list(per.values())
        totals = [sum(c[k] for c in counts) for k in range(6)]
        report['strata'][name] = {'N': strata[name]['N'], 'n': len(counts), 'phat_hien': totals[:3], 'pham_vi': totals[3:],
                                  **{k: v for k, v in zip(names, rates(counts, [1] * len(counts)))}}
    counts = [c for name in docs for c in docs[name].values()]
    weights = [weight[name] for name in docs for _ in docs[name]]
    report['tong_the'] = dict(zip(names, rates(counts, weights)))
    rng = random.Random(20261022)
    draws = []
    for _ in range(args.boot):
        sample, w = [], []
        for name, per in docs.items():
            values = list(per.values())
            pick = [rng.choice(values) for _ in values]
            sample += pick
            w += [weight[name]] * len(pick)
        draws.append(rates(sample, w))
    for k, key in enumerate(names):
        values = sorted(d[k] for d in draws if d[k] is not None)
        report['tong_the'][key + '_95'] = (values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]) if values else None
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
