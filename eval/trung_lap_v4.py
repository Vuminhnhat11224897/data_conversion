"""Copies of one document held twice in legal-docs-v4 (E10, 03/11/2026). Read-only on ES.

Usage: python -m eval.trung_lap_v4 [--es http://10.1.10.23:9200] [--out pairs.json]
Groups by the test of convert.duplicate_of: same number (number_key, a number with a digit), issuance date and issuer, and texts
alike (convert.same_text); or the same content_sha256. Groups with the same catalogue data but other text are listed apart
(khac_chu): they are kept. Each group lists its ids, oldest id first (a crawler copy has an id 101…).
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vbpl_v3.convert import clean_number, same_text  # noqa: E402
from vbpl_v3.text import number_key  # noqa: E402


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--es', default='http://10.1.10.23:9200')
    cli.add_argument('--out')
    args = cli.parse_args()
    fields = ['document_number', 'issuance_date', 'issuing_authority', 'content_sha256', 'origin']
    by_key, by_sha, docs = defaultdict(list), defaultdict(list), {}
    r = requests.post(f'{args.es}/legal-docs-v4/_search?scroll=5m', json={'size': 10000, '_source': fields}, timeout=600).json()
    sid = r['_scroll_id']
    try:
        while r['hits']['hits']:
            for h in r['hits']['hits']:
                s = h['_source']
                docs[h['_id']] = s
                number = number_key(clean_number(s.get('document_number') or ''))
                authority = ' '.join((s.get('issuing_authority') or '').casefold().split())
                if s.get('issuance_date') and re.search(r'\d', number) and authority:
                    by_key[(number, s['issuance_date'], authority)].append(h['_id'])
                if s.get('content_sha256'):
                    by_sha[s['content_sha256']].append(h['_id'])
            r = requests.post(f'{args.es}/_search/scroll', json={'scroll': '5m', 'scroll_id': sid}, timeout=600).json()
    finally:
        requests.delete(f'{args.es}/_search/scroll', json={'scroll_id': [sid]}, timeout=60)
    order = lambda ids: sorted(ids, key=lambda i: (int(i) >= 10100000, int(i) if i.isdigit() else 0))  # noqa: E731
    text = lambda i: requests.get(f'{args.es}/legal-docs-v4/_doc/{i}', params={'_source': 'full_content'}, timeout=600).json()['_source'].get('full_content')  # noqa: E731
    alike, other = set(), []
    for ids in (tuple(order(v)) for v in by_key.values() if len(v) > 1):
        first = text(ids[0])
        same = [i for i in ids[1:] if same_text(first, text(i))]
        if same:
            alike.add((ids[0], *same))
        else:
            other.append(ids)
    groups = alike | {tuple(order(v)) for v in by_sha.values() if len(v) > 1}
    rows = [{'ids': list(g), 'so_hieu': docs[g[0]].get('document_number'), 'ngay': docs[g[0]].get('issuance_date'),
             'co_quan': docs[g[0]].get('issuing_authority'), 'origin': [docs[i].get('origin') for i in g]} for g in sorted(groups)]
    print(json.dumps({'van_ban': len(docs), 'nhom_trung': len(rows), 'theo_so_hieu': sum(1 for v in by_key.values() if len(v) > 1),
                      'theo_toan_van': sum(1 for v in by_sha.values() if len(v) > 1),
                      'co_ban_crawler': sum(1 for row in rows if 'crawler' in row['origin']), 'khac_chu': len(other),
                      'vi_du': rows[:3], 'vi_du_khac_chu': other[:5]}, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps({'trung': rows, 'khac_chu': other}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
