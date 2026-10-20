"""Build a hold-out set: new documents from groups in no other set, labeled once and scored, never inspected for fixes.

Usage: python -m eval.build_holdout <name> [--seed N] [--size-random N]
Writes eval/sets/<name>.txt and adds the documents to eval/sets/manifest.json (set = <name>).
- Same strata as eval.build_sets, about half random and half chosen by act or structure, at a smaller size.
- A group (issuer + title template) already in regression, dev, blind, challenge or any earlier hold-out is closed, and the set takes
  one document per group: near copies would make a score look better than it is.
- Only documents of at most --max-chars characters (30.000 by default), so the labeler reads the whole text, tables included.
- Only documents from START_YEAR (1980), the year the conversion starts from by default.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval.build_sets import STRATA, group_key  # noqa: E402
from eval.packets import FULL_TEXT_LIMIT  # noqa: E402
from vbpl_v3 import config as settings  # noqa: E402

SETS = ROOT / 'eval' / 'sets'
# Size of each act stratum in the hold-out; the random stratum is set on the command line.
SIZES = {'sua_doi': 10, 'cong_bo_tthc': 8, 'kem_theo': 6, 'bai_bo': 6, 'thay_the': 4, 'huy_bo': 3, 'huong_dan': 6, 'hop_nhat': 3,
         'hieu_luc_rieng': 5, 'dinh_chi_ngung': 3, 'danh_muc_van_ban': 4, 'van_ban_cu': 6}


def search(url, index, query, size, seed):
    body = {'size': size, '_source': ['title', 'issuing_authority', 'issuance_date', 'full_content'],
            'query': {'function_score': {'query': {'bool': {'must': [query], 'filter': [
                {'exists': {'field': 'full_content'}}, {'range': {'issuance_date': {'gte': '1980-01-01'}}}]}},
                'random_score': {'seed': seed, 'field': '_seq_no'}, 'boost_mode': 'replace'}}}
    return requests.post(f'{url}/{index}/_search', json=body, timeout=300).json()['hits']['hits']


def titles(url, index, ids):
    found = {}
    for start in range(0, len(ids), 500):
        body = {'size': 500, 'query': {'ids': {'values': ids[start:start + 500]}}, '_source': ['title', 'issuing_authority']}
        found.update({h['_id']: h['_source'] for h in requests.post(f'{url}/{index}/_search', json=body, timeout=120).json()['hits']['hits']})
    return found


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('name')
    cli.add_argument('--seed', type=int, default=20261020)
    cli.add_argument('--size-random', type=int, default=60)
    cli.add_argument('--max-chars', type=int, default=FULL_TEXT_LIMIT, help='Độ dài tối đa của toàn văn (mặc định 30.000)')
    cli.add_argument('--scale', type=float, default=1.0, help='Nhân cỡ các tầng theo loại tác động')
    args = cli.parse_args()
    settings.load()
    config = settings.Config.from_env()
    url, index = config.source_url, config.source['documents']
    manifest = json.loads((SETS / 'manifest.json').read_text())
    if (SETS / f'{args.name}.txt').exists() or any(d['set'] == args.name for d in manifest['documents'].values()):
        sys.exit(f'{args.name} đã có. Chọn tên khác.')
    # Every document any set or earlier review has used, and the groups they belong to.
    used = set(manifest['documents'])
    for path in list(SETS.glob('*.txt')) + [ROOT / 'work' / 'fresh50-ids.txt']:
        if path.exists():
            used |= set(path.read_text().split())
    closed = {d['group'] for d in manifest['documents'].values()}
    closed |= {group_key(s) for s in titles(url, index, sorted(used - set(manifest['documents']))).values()}

    sizes = {'ngau_nhien': args.size_random, **{k: max(1, round(v * args.scale)) for k, v in SIZES.items()}}
    picked, why, groups = [], {}, {}
    for n, (name, _, query) in enumerate(STRATA):
        size = sizes[name]
        taken = 0
        for h in search(url, index, query, size * 8, args.seed + n):
            key = group_key(h['_source'])
            if taken >= size or h['_id'] in why or h['_id'] in used or key in closed:
                continue
            if not 300 <= len(h['_source'].get('full_content') or '') <= args.max_chars:
                continue
            picked.append(h['_id']); why[h['_id']] = name; groups[h['_id']] = key; closed.add(key); taken += 1
        print(f'{name}: {taken}/{size}', file=sys.stderr)

    (SETS / f'{args.name}.txt').write_text('\n'.join(picked) + '\n')
    manifest['counts'][args.name] = len(picked)
    manifest['strata'][args.name] = dict(Counter(why[i] for i in picked))
    manifest['documents'].update({i: {'set': args.name, 'stratum': why[i], 'group': groups[i]} for i in picked})
    (SETS / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps({'set': args.name, 'seed': args.seed, 'documents': len(picked), 'strata': manifest['strata'][args.name]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
