"""Documents that a failed write left half done in -v4 (E1, 03/11/2026). Read-only on ES.

Usage: python -m eval.kiem_ghi_v4 [--es http://10.1.10.23:9200] [--out ids.txt]
A write deletes nothing before the new records are in (code after 03/11/2026), but earlier runs did: a batch that failed left
- chunks of a newer run than the document record (the document kept its old record, its chunks are the first lots of the new run);
- chunks with no document record (a new document whose write stopped before the record);
- a document with no chunk (the old chunks deleted, the first new lot lost).
A run in progress also shows chunks without a record for a few minutes: run this when no write is going on, or read the job ids.
Writes the ids to --out, one per line, to convert again (same run without --redo, or a new run with --ids).
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import requests


def scroll_ids(es, index, source):
    out = {}
    r = requests.post(f'{es}/{index}/_search?scroll=5m', json={'size': 10000, '_source': source}, timeout=600).json()
    sid = r['_scroll_id']
    try:
        while r['hits']['hits']:
            out.update({h['_id']: h.get('_source') or {} for h in r['hits']['hits']})
            r = requests.post(f'{es}/_search/scroll', json={'scroll': '5m', 'scroll_id': sid}, timeout=600).json()
    finally:
        requests.delete(f'{es}/_search/scroll', json={'scroll_id': [sid]}, timeout=60)
    return out


def chunk_jobs(es):
    jobs, after = defaultdict(dict), None
    while True:
        agg = {'composite': {'size': 10000, 'sources': [{'d': {'terms': {'field': 'doc_id'}}}, {'j': {'terms': {'field': 'ingest_job_id'}}}]}}
        if after:
            agg['composite']['after'] = after
        r = requests.post(f'{es}/legal-chunk-section-v4/_search', json={'size': 0, 'aggs': {'c': agg}}, timeout=600).json()['aggregations']['c']
        for b in r['buckets']:
            jobs[str(b['key']['d'])][b['key']['j']] = b['doc_count']
        after = r.get('after_key')
        if not r['buckets'] or not after:
            return jobs


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--es', default='http://10.1.10.23:9200')
    cli.add_argument('--out')
    args = cli.parse_args()
    docs = {i: s.get('ingest_job_id') for i, s in scroll_ids(args.es, 'legal-docs-v4', ['ingest_job_id']).items()}
    jobs = chunk_jobs(args.es)
    stale = {d: {'van_ban': docs[d], 'chunk': j} for d, j in jobs.items() if d in docs and set(j) != {docs[d]}}
    orphan = {d: {'chunk': j} for d, j in jobs.items() if d not in docs}
    empty = sorted(d for d in docs if d not in jobs)
    report = {'documents': len(docs), 'chunk_doc_ids': len(jobs), 'chunk_khac_luot_van_ban': stale, 'chunk_khong_van_ban': orphan,
              'van_ban_khong_chunk': empty}
    print(json.dumps({k: (len(v) if isinstance(v, (dict, list)) else v) for k, v in report.items()}, ensure_ascii=False))
    print(json.dumps({'vi_du_chunk_khac_luot': dict(list(stale.items())[:5]), 'vi_du_chunk_khong_van_ban': dict(list(orphan.items())[:5]),
                      'van_ban_khong_chunk': empty[:10]}, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text('\n'.join(sorted(set(stale) | set(orphan) | set(empty))) + '\n')


if __name__ == '__main__':
    main()
