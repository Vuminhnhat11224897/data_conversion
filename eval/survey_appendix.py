"""Survey: share of appendices, tables, forms and catalogues in the source legal-docs, on a random sample. Read-only on the source ES.

Usage: python -m eval.survey_appendix <sample size> <out.json>; then python -m eval.survey_appendix_report <out.json>
The sample is fixed by the seed (random_score on _seq_no), so two runs read the same documents. Results: docs/10, 15/10/2026.
"""
import json
import re
import sys
from collections import Counter
from multiprocessing import Pool

import requests

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from vbpl_v3 import config as settings  # noqa: E402
from vbpl_v3.structure import parse, source_lines  # noqa: E402

FORM = re.compile(r'\b(?:MẪU SỐ|Mẫu số|MẪU\s+\d|Mẫu\s+\d|BIỂU MẪU|Biểu mẫu|BIỂU SỐ|Biểu số|PHỤ BIỂU|Phụ biểu|TỜ KHAI|MẪU (?:ĐƠN|GIẤY|BÁO CÁO|BIÊN BẢN|QUYẾT ĐỊNH|TỜ))')
CATALOGUE = re.compile(r'\b(?:DANH MỤC|Danh mục|DANH SÁCH|Danh sách)\b')
TABLE_TITLE = re.compile(r'\b(?:BẢNG|Bảng)\b')
FILL = re.compile(r'(?:\.{8,}|…{3,}|_{6,})')
HEAD_CATALOGUE = re.compile(r'^(?:DANH MỤC|DANH SÁCH)\b')
HEAD_FORM = re.compile(r'^(?:MẪU SỐ|Mẫu số|BIỂU MẪU|BIỂU SỐ|Biểu số|PHỤ BIỂU|Mẫu\s+\d|MẪU\s+\d)')


def kind(appendix):
    """One content kind per appendix: articles, form, catalogue, table, text."""
    if appendix['dieu_luat']:
        return 'quy_dinh_co_dieu'
    head = appendix['tieu_de'] + '\n' + appendix['noi_dung'][:600]
    if FORM.search(head) or len(FILL.findall(appendix['noi_dung'])) >= 5:
        return 'bieu_mau'
    if CATALOGUE.search(head):
        return 'danh_muc'
    if appendix['has_table'] or TABLE_TITLE.search(appendix['tieu_de']):
        return 'bang_khac'
    return 'van_ban_khac'


def measure(src):
    text = src.get('full_content') or ''
    out = {'id': src['_id'], 'type': src.get('legal_type') or '', 'chars': len(text), 'vbhn': bool(re.search(r'/\s*VBHN\s*-', src.get('document_number') or ''))}
    if not text.strip():
        out['empty'] = True
        return out
    try:
        parsed, _ = parse(text, positions=True)
    except Exception as error:  # noqa: BLE001
        out['error'] = str(error)[:200]
        return out
    lines = source_lines(text)
    start = min((a['line'] for a in parsed['phu_luc'] if 'line' in a), default=len(lines))
    body = lines[:start]
    out['table_chars'] = sum(len(line) for line in lines if line.startswith('|'))
    out['body_table_rows'] = sum(1 for line in body if line.startswith('|'))
    out['body_catalogue'] = sum(1 for line in body if HEAD_CATALOGUE.match(line))
    out['body_form'] = sum(1 for line in body if HEAD_FORM.match(line))
    out['appendices'] = [{'kind': kind(a), 'chars': len(a['noi_dung']) + len(a['tieu_de']), 'table': a['has_table'],
                          'rows': a['n_table_rows'], 'labeled': a['loai'] == 'labeled', 'title': a['tieu_de'][:150], 'start': a['noi_dung'][:150]} for a in parsed['phu_luc']]
    return out


def sample(config, size, seed=20261015):
    url = f'{config.source_url}/{config.source["documents"]}'
    body = {'size': 500, '_source': ['full_content', 'legal_type', 'document_number'],
            'query': {'function_score': {'query': {'match_all': {}}, 'random_score': {'seed': seed, 'field': '_seq_no'}, 'boost_mode': 'replace'}}}
    page = requests.post(f'{url}/_search?scroll=5m', json=body, timeout=300).json()
    scroll, got = page['_scroll_id'], 0
    try:
        while page['hits']['hits'] and got < size:
            for hit in page['hits']['hits'][:size - got]:
                yield {'_id': hit['_id'], **hit['_source']}
                got += 1
            page = requests.post(f'{config.source_url}/_search/scroll', json={'scroll': '5m', 'scroll_id': scroll}, timeout=300).json()
    finally:
        requests.delete(f'{config.source_url}/_search/scroll', json={'scroll_id': scroll}, timeout=60)


def main():
    size, out = int(sys.argv[1]), sys.argv[2]
    settings.load()
    config = settings.Config.from_env()
    rows = []
    with Pool(10) as pool:
        for k, row in enumerate(pool.imap_unordered(measure, sample(config, size), chunksize=20), 1):
            rows.append(row)
            if k % 1000 == 0:
                print(k, flush=True)
    with open(out, 'w') as f:
        json.dump(rows, f, ensure_ascii=False)
    print(json.dumps(Counter(a['kind'] for r in rows for a in r.get('appendices', [])), ensure_ascii=False))


if __name__ == '__main__':
    main()
