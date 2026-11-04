"""Documents that a failed write left half done in -v4 (E1, 03/11/2026). Read-only on ES.

Usage: python -m eval.kiem_ghi_v4 [--es http://10.1.10.23:9200] [--out ids.txt]
The checks are vbpl_v3.integrity (also run by auto at each source scan, and by `python -m vbpl_v3 integrity`):
- chunks or relations of another run than the document record (the write stopped before or after the record);
- chunks or relations with no document record (a new document whose write stopped before the record);
- a document with no chunk (old code deleted the chunks before writing).
A run in progress also shows these signs for a few seconds: run this when no write is going on, or read the job ids.
Writes the ids to --out, one per line, to convert again (same run without --redo, or a new run with --ids).
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from vbpl_v3 import integrity
from vbpl_v3.es import Cluster

V4 = {'documents': 'legal-docs-v4', 'chunks': 'legal-chunk-section-v4', 'changes': 'legal-changed-v4'}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--es', default='http://10.1.10.23:9200')
    cli.add_argument('--out')
    args = cli.parse_args()
    target = Cluster(args.es)  # no writable index: read-only
    docs = integrity.document_jobs(target, V4['documents'])
    report = integrity.broken(target, SimpleNamespace(target=V4), docs)
    print(json.dumps({'documents': len(docs), **{kind: len(ids) for kind, ids in report.items()}}, ensure_ascii=False))
    print(json.dumps({kind: ids[:10] for kind, ids in report.items()}, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(''.join(f'{i}\n' for i in sorted(integrity.to_rewrite(report) | integrity.without_record(report))))


if __name__ == '__main__':
    main()
