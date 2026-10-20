"""Benchmark: documents with Phần / Chương / Mục / Tiểu mục above Điều, and section levels of documents without Điều.
Only structure counts: headings in a table row, in quotes, or in an appendix without Điều (catalogue, table, form) are left out.
Read-only on the source ES. Same sample as eval.survey_appendix.
Usage: python -m eval.survey_levels <sample size> <out.json>; then python -m eval.survey_levels_report <out.json>. Results: docs/10, 16/10/2026.
"""
import json
import re
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from eval.survey_appendix import sample  # noqa: E402
from vbpl_v3 import config as settings  # noqa: E402
from vbpl_v3.structure import ARTICLE, parse, source_lines, unquoted  # noqa: E402

HEADS = {
    'phan': re.compile(r'^(?:Phần|PHẦN)\s+(?:thứ\s+\w+|THỨ\s+\w+|[IVXLCDM]+|\d+)\b'),
    'chuong': re.compile(r'^(?:Chương|CHƯƠNG)\s+(?:[IVXLCDM]+|\d+)\b'),
    'muc': re.compile(r'^(?:Mục|MỤC)\s+(?:[IVXLCDM]+|\d+)\b'),
    'tieu_muc': re.compile(r'^(?:Tiểu mục|TIỂU MỤC)\s+\d+\b'),
}
SUB = re.compile(r'^(?:\d+(?:\.\d+)*\.|[a-zđ]\))\s+\S')


def heads(lines, above_articles=False):
    """Structural headings on visible (unquoted, non-table) lines. above_articles: only before the last Điều heading, since a level
    above Điều precedes an Điều (a "Phần I" after the signature opens an attached catalogue, not a part of the text)."""
    found = Counter()
    visible_lines = list(zip(lines, unquoted(lines)))
    last = max((i for i, (line, visible) in enumerate(visible_lines) if visible and ARTICLE.match(line)), default=-1)
    for i, (line, visible) in enumerate(visible_lines):
        if not visible or line.startswith('|') or (above_articles and i > last):
            continue
        for kind, pattern in HEADS.items():
            if pattern.match(line):
                found[kind] += 1
    return found


def leaked(articles):
    """Articles whose body holds a structural heading line: the parser did not cut there."""
    out = Counter()
    for article in articles:
        body = article['noi_dung'].splitlines()
        for kind, n in heads(body).items():
            out[kind] += 1
    return out


def measure(src):
    text = src.get('full_content') or ''
    out = {'id': src['_id'], 'type': src.get('legal_type') or '', 'vbhn': bool(re.search(r'/\s*VBHN\s*-', src.get('document_number') or ''))}
    if not text.strip():
        out['empty'] = True
        return out
    try:
        parsed, _ = parse(text, positions=True)
    except Exception as error:  # noqa: BLE001
        out['error'] = str(error)[:200]
        return out
    lines = source_lines(text)
    starts = sorted(a['line'] for a in parsed['phu_luc'] if 'line' in a)
    body = lines[:starts[0] if starts else len(lines)]
    articles = parsed['dieu_luat']
    out['n_dieu'] = len(articles)
    out['body'] = dict(heads(body, above_articles=True))
    out['assigned'] = {'chuong': len({a['chuong'] for a in articles if a.get('chuong')}),
                       'muc': len({(a.get('chuong'), a['muc']) for a in articles if a.get('muc')})}
    out['leak'] = dict(leaked(articles))
    attached = []
    for k, appendix in enumerate(parsed['phu_luc']):
        if not appendix['dieu_luat'] or 'line' not in appendix:
            continue  # catalogue, table, form: not structure
        end = next((s for s in starts if s > appendix['line']), len(lines))
        attached.append({'n_dieu': len(appendix['dieu_luat']), 'heads': dict(heads(lines[appendix['line']:end], above_articles=True)),
                         'assigned_chuong': len({a['chuong'] for a in appendix['dieu_luat'] if a.get('chuong')}),
                         'leak': dict(leaked(appendix['dieu_luat']))})
    out['attached'] = attached
    sections = parsed.get('noi_dung_sections') or []
    out['sections'] = len(sections)
    out['nested_sections'] = sum(1 for s in sections if sum(1 for line in s['noi_dung'].splitlines() if SUB.match(line)) >= 2)
    return out


def main():
    size, path = int(sys.argv[1]), sys.argv[2]
    settings.load()
    config = settings.Config.from_env()
    rows = []
    with Pool(10) as pool:
        for k, row in enumerate(pool.imap_unordered(measure, sample(config, size), chunksize=20), 1):
            rows.append(row)
            if k % 1000 == 0:
                print(k, flush=True)
    with open(path, 'w') as f:
        json.dump(rows, f, ensure_ascii=False)
    print('done', len(rows), flush=True)


if __name__ == '__main__':
    main()
