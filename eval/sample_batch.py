"""Sample a batch run for evaluation: every 10.000 new documents converted, 1.000 of them are labeled and scored (26/10/2026).

Usage: python -m eval.sample_batch <name> --run <run> [--size 1000] [--seed N] [--max-chars 200000]
Population: the documents of work/<run> (its ids.json and documents.jsonl), at most --max-chars characters, minus every document of a
labeled set and every document of a group (issuer + title template) such a set holds; one document per group.
Strata: length (ngan <= 30.000 characters < dai) x what the run found for the document:
  khong_quan_he  no relation;
  kho            8 or more relations, an unresolved one, or a title on administrative procedures (TTHC);
  sua_doi        sua-doi, bo-sung or thay-cum-tu among the acts;
  bai_bo         only bai-bo, thay-the, huy-bo;
  khac           any other act.
Allocation is proportional to the stratum sizes, a quarter of it for the strata with no relation, at least --floor per stratum; the
weights N/n of eval.strata keep the estimate of the whole batch unbiased. Writes eval/sets/<name>.txt and <name>.strata.json and records the documents in eval/sets/manifest.json, so that
later batches never draw them again. Next: eval.packets, labels (eval/rubric-gold.md), eval.strata (see eval/README.md).
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval.build_sets import group_key  # noqa: E402
from vbpl_v3 import config as settings  # noqa: E402

SETS = ROOT / 'eval' / 'sets'
TTHC = re.compile(r'thủ\s+tục\s+hành\s+chính|\bTTHC\b', re.I)


def fetch(url, index, ids, fields):
    found = {}
    for start in range(0, len(ids), 200):
        body = {'size': 200, 'query': {'ids': {'values': ids[start:start + 200]}}, '_source': fields}
        found.update({h['_id']: h['_source'] for h in requests.post(f'{url}/{index}/_search', json=body, timeout=300).json()['hits']['hits']})
    return found


def stratum(record, title):
    acts = set(record.get('actions') or [])
    if not record.get('relations'):
        return 'khong_quan_he'
    if record['relations'] >= 8 or record.get('unresolved') or TTHC.search(title or ''):
        return 'kho'
    if acts & {'sua-doi', 'bo-sung', 'thay-cum-tu'}:
        return 'sua_doi'
    if acts and acts <= {'bai-bo', 'thay-the', 'huy-bo'}:
        return 'bai_bo'
    return 'khac'


# A document with no relation tells only what was missed: its strata get a quarter of their share, the rest goes where relations are.
SHARE = {'khong_quan_he': 0.25}


def allocate(sizes, total, floor):
    """Allocation in proportion to the stratum sizes (SHARE lowers some), a floor per stratum, never more than a stratum holds, summing
    to total when the population allows. eval.strata weights each stratum by N/n, so the estimate stays unbiased."""
    share = {k: v * SHARE.get(k[1] if isinstance(k, tuple) else k, 1.0) for k, v in sizes.items()}
    population = sum(share.values())
    n = {k: min(v, max(floor, round(total * share[k] / population))) for k, v in sizes.items()}
    while sum(n.values()) > total:
        k = max((k for k in n if n[k] > min(floor, sizes[k])), key=lambda k: n[k] / sizes[k])
        n[k] -= 1
    while sum(n.values()) < total and any(n[k] < sizes[k] for k in n):
        k = min((k for k in n if n[k] < sizes[k]), key=lambda k: n[k] / sizes[k])
        n[k] += 1
    return n


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('name')
    cli.add_argument('--run', required=True, help='lượt chạy thật của đợt (work/<run>)')
    cli.add_argument('--size', type=int, default=1000)
    cli.add_argument('--floor', type=int, default=20, help='số văn bản tối thiểu mỗi tầng')
    cli.add_argument('--seed', type=int, default=20261026)
    cli.add_argument('--max-chars', type=int, default=200000)
    args = cli.parse_args()
    settings.load()
    config = settings.Config.from_env()
    url, index = config.source_url, config.source['documents']
    manifest = json.loads((SETS / 'manifest.json').read_text())
    if (SETS / f'{args.name}.txt').exists() or any(d['set'] == args.name for d in manifest['documents'].values()):
        sys.exit(f'{args.name} đã có. Chọn tên khác.')
    run = ROOT / 'work' / args.run
    records = {}
    for line in (run / 'documents.jsonl').read_text().splitlines():
        r = json.loads(line)
        records[r['doc_id']] = r  # the last record of a document is its final run
    population = sorted(records)

    used = set(manifest['documents'])
    for path in SETS.glob('*.txt'):
        used |= set(path.read_text().split())
    meta = fetch(url, index, sorted(set(population) | used), ['title', 'issuing_authority', 'full_content'])
    closed = {d['group'] for d in manifest['documents'].values()} | {group_key(meta[i]) for i in used if i in meta}

    frame = {}
    for doc in population:
        text = (meta.get(doc) or {}).get('full_content') or ''
        if doc in used or doc not in meta or not 0 < len(text) <= args.max_chars or records[doc].get('skipped'):
            continue
        if group_key(meta[doc]) in closed:
            continue
        frame.setdefault(('ngan' if len(text) <= 30000 else 'dai', stratum(records[doc], meta[doc].get('title'))), []).append(doc)
    sizes = allocate({k: len(v) for k, v in frame.items()}, args.size, args.floor)

    rng = random.Random(args.seed)
    picked, why, groups, taken = [], {}, {}, set()
    design = {'set': args.name, 'seed': args.seed, 'run': args.run,
              'population': f'work/{args.run} (≤{args.max_chars} ký tự), trừ văn bản và nhóm văn bản của mọi bộ có nhãn',
              'tang': 'độ dài × kết quả của lượt chạy: khong_quan_he, kho (≥8 quan hệ, có unresolved, hoặc TTHC), sua_doi, bai_bo, khac',
              'strata': {}}
    for key in sorted(frame):
        pool = sorted(frame[key])
        rng.shuffle(pool)
        chosen = []
        for doc in pool:
            group = group_key(meta[doc])
            if group in taken:
                continue
            chosen.append(doc)
            taken.add(group)
            if len(chosen) == sizes[key]:
                break
        name = f'{key[0]}_{key[1]}'
        design['strata'][name] = {'N': len(frame[key]), 'n': len(chosen), 'ids': sorted(chosen)}
        picked += chosen
        why.update({d: name for d in chosen})
        groups.update({d: group_key(meta[d]) for d in chosen})

    (SETS / f'{args.name}.txt').write_text('\n'.join(sorted(picked)) + '\n')
    (SETS / f'{args.name}.strata.json').write_text(json.dumps(design, ensure_ascii=False, indent=1))
    manifest['counts'][args.name] = len(picked)
    manifest['strata'][args.name] = {k: s['n'] for k, s in design['strata'].items()}
    manifest['documents'].update({d: {'set': args.name, 'stratum': why[d], 'group': groups[d]} for d in picked})
    (SETS / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps({'set': args.name, 'run': args.run, 'documents': len(picked), 'frame': sum(len(v) for v in frame.values()),
                      'strata': {k: [s['N'], s['n']] for k, s in design['strata'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
