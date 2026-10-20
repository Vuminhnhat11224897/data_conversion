"""Labeling packets: the units of each document, with the context a reader needs, and none of the tool's relations.

Usage: python -m eval.packets <set> <parse cache run> [--per-batch N]
Writes eval/packets/<set>/batch-<k>.json. Units come from the rule parser (structure_ai cache of the run), so labels use the
same source_path as the tool. A unit is kept when its text has any word of an act, however weak ("sửa", "thay", "bỏ", ...):
the filter only drops units that cannot hold an act. Short documents also carry their full text.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vbpl_v3 import config as settings  # noqa: E402
from vbpl_v3.structure_ai import refine  # noqa: E402

SIGNAL = re.compile(r'sửa|bổ\s*sung|bỏ|thay|h[uủ]y|huỷ|đình\s*chỉ|ngưng|ngừng|hết\s+hiệu\s*lực|đính\s*chính|gia\s+hạn|kéo\s+dài|hướng\s+dẫn'
                    r'|quy\s+định\s+chi\s+tiết|điều\s+chỉnh|hợp\s+nhất', re.I)
FULL_TEXT_LIMIT = 30000


def units(parsed):
    """(source_path, heading, lead, text) for every unit, as relations.detect names them."""
    out = []
    articles = [(a, '') for a in parsed['dieu_luat']] + [(a, f'Phụ lục {i + 1} ') for i, p in enumerate(parsed['phu_luc']) for a in p['dieu_luat']]
    for article, prefix in articles:
        if article.get('van_ban_kem_theo'):
            prefix += f'Văn bản kèm theo {article["van_ban_kem_theo"]} '
        path = prefix + 'Điều ' + article['ky_hieu']
        head = ' '.join(x for x in (article.get('chuong', ''), article['tieu_de']) if x)
        if not article['khoan']:
            out.append((path, head, '', article['noi_dung']))
            continue
        if article.get('mo_dau'):
            out.append((path, head, '', article['mo_dau']))
        for clause in article['khoan']:
            clause_path = f'{path} Khoản {clause["ky_hieu"]}'
            out.append((clause_path, head, '', clause['noi_dung']))
            for point in clause['diem']:
                out.append((f'{clause_path} điểm {point["ky_hieu"]}', head, clause.get('mo_dau', ''), point['noi_dung']))
    if not parsed['dieu_luat']:
        for section in parsed.get('noi_dung_sections') or [{'so_muc': None, 'noi_dung': parsed.get('noi_dung', '')}]:
            out.append((f'Mục {section["so_muc"]}' if section['so_muc'] else 'Nội dung', '', '', section['noi_dung']))
    return out


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('set')
    cli.add_argument('run', help='Lượt có cache parse (work/<run>/cache)')
    cli.add_argument('--per-batch', type=int, default=10)
    cli.add_argument('--full-text-limit', type=int, default=FULL_TEXT_LIMIT, help='Kèm toan_van khi văn bản dài tối đa chừng này ký tự')
    cli.add_argument('--batch-chars', type=int, default=0, help='Nếu > 0: chia gói theo tổng ký tự toan_van, không theo số văn bản')
    args = cli.parse_args()
    settings.load()
    config = settings.Config.from_env()
    ids = (ROOT / 'eval' / 'sets' / f'{args.set}.txt').read_text().split()
    out = ROOT / 'eval' / 'packets' / args.set
    out.mkdir(parents=True, exist_ok=True)
    packets = []
    for doc_id in ids:
        src = requests.get(f'{config.source_url}/{config.source["documents"]}/_doc/{doc_id}', timeout=60).json()['_source']
        parsed, _ = refine(src['full_content'], ROOT / 'work' / args.run / 'cache' / doc_id, title=src.get('title'))
        # An untitled article's first sentence is read as its heading ("Điều 1. Sửa đổi khoản 1 …"): the heading counts too.
        kept = [{'source_path': p, 'ten_dieu': h[:400], 'cau_dan': lead[:800], 'noi_dung': t[:6000]}
                for p, h, lead, t in units(parsed) if SIGNAL.search(t) or SIGNAL.search(lead) or SIGNAL.search(h)]
        packet = {'doc_id': doc_id, 'so_hieu': src.get('document_number'), 'loai': src.get('legal_type'), 'co_quan': src.get('issuing_authority'),
                  'ngay_ban_hanh': src.get('issuance_date'), 'ten': src.get('title'), 'phan_dau': (parsed.get('phan_dau') or '')[:3000],
                  'loi_dan': (parsed.get('intro') or '')[:3000], 'don_vi': kept,
                  # The appendices in the order the tool numbers them ("Phụ lục <so>" in source_path), with or without a label.
                  'phu_luc': [{'so': i + 1, 'tieu_de': p['tieu_de'][:300], 'chia_dieu': bool(p['dieu_luat'])}
                              for i, p in enumerate(parsed['phu_luc'])]}
        if len(src['full_content']) <= args.full_text_limit:
            packet['toan_van'] = src['full_content']
        packets.append(packet)
    batches = []
    if args.batch_chars:
        for packet in packets:
            size = len(packet.get('toan_van', ''))
            if not batches or (batches[-1][1] + size > args.batch_chars and batches[-1][0]):
                batches.append([[], 0])
            batches[-1][0].append(packet); batches[-1][1] += size
        batches = [b for b, _ in batches]
    else:
        batches = [packets[k:k + args.per_batch] for k in range(0, len(packets), args.per_batch)]
    for k, batch in enumerate(batches):
        (out / f'batch-{k:02}.json').write_text(json.dumps(batch, ensure_ascii=False, indent=1))
    print(json.dumps({'set': args.set, 'documents': len(packets), 'units': sum(len(p['don_vi']) for p in packets),
                      'batches': len(batches)}))


if __name__ == '__main__':
    main()
