"""Score the document metadata of a run against metadata gold (eval/rubric-metadata.md).

Usage: python -m eval.score_meta <set> <run> [--json out.json]
Reads eval/gold-meta/<set>/*.json and work/<run>/dry-run/<id>.json (run convert with --dry-run).

Six fields per document, each right or wrong:
- la_vbqppl, cap_hieu_luc, ngay_hieu_luc, ngay_het_hieu_luc, ngay_hoi_to: equal values (null equals null);
- hieu_luc_rieng: the same set of (position, date) pairs.
Reports accuracy per field, over all fields (micro), the share of documents with every field right, and the same without the fields
the labeler marked unsure (chua_chac).
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vbpl_v3.temporal import positions  # noqa: E402

FIELDS = ['la_vbqppl', 'cap_hieu_luc', 'ngay_hieu_luc', 'ngay_het_hieu_luc', 'ngay_hoi_to', 'hieu_luc_rieng']


def pairs(rows):
    out = set()
    for row in rows or []:
        for place in row.get('vi_tri') or []:
            for p in positions(place) or [place]:
                out.add((p, row.get('ngay_hieu_luc')))
    return out


def value(document, field):
    if field == 'hieu_luc_rieng':
        return pairs(document.get(field))
    if field == 'ngay_hoi_to' and not document.get('hoi_to', True):
        return None
    return document.get(field)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('set')
    cli.add_argument('run')
    cli.add_argument('--json')
    args = cli.parse_args()
    gold = {g['doc_id']: g for f in sorted((ROOT / 'eval' / 'gold-meta' / args.set).glob('*.json')) for g in json.loads(f.read_text())}
    right, total, sure_right, sure_total = Counter(), Counter(), Counter(), Counter()
    docs = all_right = 0
    misses = []
    for doc_id, labels in gold.items():
        output = ROOT / 'work' / args.run / 'dry-run' / f'{doc_id}.json'
        if not output.exists():
            continue
        document = json.loads(output.read_text())['document']
        docs += 1
        unsure = set(labels.get('chua_chac') or [])
        ok_all = True
        for field in FIELDS:
            expected = pairs(labels.get(field)) if field == 'hieu_luc_rieng' else labels.get(field)
            got = value(document, field)
            ok = expected == got
            total[field] += 1
            right[field] += ok
            if field not in unsure:
                sure_total[field] += 1
                sure_right[field] += ok
            if not ok:
                ok_all = False
                misses.append({'doc_id': doc_id, 'field': field, 'gold': sorted(expected) if isinstance(expected, set) else expected,
                               'tool': sorted(got) if isinstance(got, set) else got, 'unsure': field in unsure})
        all_right += ok_all

    def ratio(a, b):
        return round(a / b, 3) if b else None
    report = {'set': args.set, 'run': args.run, 'documents': docs,
              'field_accuracy': {f: ratio(right[f], total[f]) for f in FIELDS},
              'micro_accuracy': ratio(sum(right.values()), sum(total.values())),
              'documents_all_right': ratio(all_right, docs),
              'sure_field_accuracy': {f: ratio(sure_right[f], sure_total[f]) for f in FIELDS},
              'sure_micro_accuracy': ratio(sum(sure_right.values()), sum(sure_total.values())),
              'misses_by_field': dict(Counter(m['field'] for m in misses))}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps({**report, 'misses': misses}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
