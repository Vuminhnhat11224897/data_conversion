"""Build the evaluation sets from the source corpus (read-only).

Usage: python -m eval.build_sets [--seed N]

Writes eval/sets/{regression,dev,blind,challenge}.txt and eval/sets/manifest.json.
- regression: documents already used to fix rules (work/v4-500-ids.txt, work/v4-r6-done29-ids.txt). Only for "nothing broke".
- dev: new documents, labeled; errors here may be inspected and fixed.
- blind: new documents, labeled; never inspected for fixes. Scores only.
- challenge: rare, hard structures (a Quyết định and the Quy định it issues, catalogue names with legal verbs, ...).
A group is an issuer plus a title template. A group lives in one set only, and no dev, blind or challenge group appears in regression:
two decisions from the same province and template are near copies, and would make a score look better than it is.
"""

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vbpl_v3 import config as settings  # noqa: E402

SETS = ROOT / 'eval' / 'sets'


def title_phrase(*phrases):
    return {'bool': {'should': [{'match_phrase': {'title': p}} for p in phrases], 'minimum_should_match': 1}}


def text_phrase(*phrases):
    return {'bool': {'must': [{'match_phrase': {'full_content': p}} for p in phrases]}}


# (name, size of dev + blind, query). About half random, half chosen by act or structure.
STRATA = [
    ('ngau_nhien', 200, {'match_all': {}}),
    ('sua_doi', 30, title_phrase('sửa đổi')),
    ('cong_bo_tthc', 25, {'bool': {'must': [title_phrase('công bố'), title_phrase('thủ tục hành chính')]}}),
    ('kem_theo', 25, {'bool': {'must': [title_phrase('sửa đổi'), text_phrase('ban hành kèm theo Quyết định')]}}),
    ('bai_bo', 15, title_phrase('bãi bỏ')),
    ('thay_the', 10, title_phrase('thay thế')),
    ('huy_bo', 10, title_phrase('hủy bỏ', 'huỷ bỏ')),
    ('huong_dan', 20, title_phrase('hướng dẫn', 'quy định chi tiết')),
    ('hop_nhat', 10, {'term': {'legal_type': 'Văn bản hợp nhất'}}),
    ('hieu_luc_rieng', 10, {'bool': {'must': [text_phrase('có hiệu lực thi hành từ ngày'), text_phrase('quy định tại khoản')]}}),
    ('dinh_chi_ngung', 10, title_phrase('đình chỉ', 'ngưng hiệu lực')),
    ('danh_muc_van_ban', 15, title_phrase('danh mục văn bản')),
    ('van_ban_cu', 20, {'range': {'issuance_date': {'lt': '2000-01-01'}}}),
]
# Challenge: the two cases named on 15/10/2026 and other rare structures. Drawn after dev and blind, from groups in neither.
CHALLENGE = [
    ('A_quyet_dinh_va_quy_dinh_kem_theo', 15, {'bool': {'must': [title_phrase('sửa đổi'), text_phrase('Quy định ban hành kèm theo Quyết định'),
                                                                  text_phrase('khoản'), text_phrase('Điều 3')]}}),
    ('B_ten_danh_muc_co_tu_phap_ly', 10, {'bool': {'must': [title_phrase('danh mục'), text_phrase('bãi bỏ')]}}),
    ('tthc_thay_the_bai_bo_mot_phan', 5, {'bool': {'must': [title_phrase('thủ tục hành chính'), text_phrase('số thứ tự')]}}),
    ('ghi_chu_lich_su', 5, text_phrase('đã được sửa đổi, bổ sung theo')),
    ('khong_chia_dieu_sua_doi', 5, {'bool': {'must': [title_phrase('sửa đổi')], 'filter': [{'range': {'issuance_date': {'lt': '1995-01-01'}}}]}}),
]


def group_key(source):
    """Issuer + title template: the title without numbers, dates, the document type and the issuer suffix."""
    title = (source.get('title') or '').casefold()
    title = re.sub(r'\bdo\b.*?ban hành\s*$', '', title)
    title = re.sub(r'[\d/.\-]+', ' ', title)
    title = re.sub(r'\b(?:năm|ngày|tháng|số)\b', ' ', title)
    words = title.split()[2:10]  # drop "quyết định 123/..." leading type words
    return f"{source.get('issuing_authority') or ''}|{' '.join(words)}"


def search(url, index, query, size, seed):
    body = {'size': size, '_source': ['title', 'issuing_authority', 'legal_type', 'issuance_date'],
            'query': {'function_score': {'query': {'bool': {'must': [query], 'filter': [{'exists': {'field': 'full_content'}}]}},
                                         'random_score': {'seed': seed, 'field': '_seq_no'}, 'boost_mode': 'replace'}}}
    return requests.post(f'{url}/{index}/_search', json=body, timeout=300).json()['hits']['hits']


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--seed', type=int, default=20261015)
    cli.add_argument('--dev', type=int, default=150)
    args = cli.parse_args()
    settings.load()
    config = settings.Config.from_env()
    url, index = config.source_url, config.source['documents']
    regression = []
    for name in ('v4-500-ids.txt', 'v4-r6-done29-ids.txt'):
        regression += (ROOT / 'work' / name).read_text().split()
    regression = list(dict.fromkeys(regression))
    used = {h['_id']: h['_source'] for start in range(0, len(regression), 500)
            for h in requests.post(f'{url}/{index}/_search', json={'size': 500, 'query': {'ids': {'values': regression[start:start + 500]}},
                                   '_source': ['title', 'issuing_authority']}, timeout=120).json()['hits']['hits']}
    closed = {group_key(s) for s in used.values()}

    picked, why, groups = [], {}, {}
    for n, (name, size, query) in enumerate(STRATA):
        hits = search(url, index, query, size * 6, args.seed + n)
        taken = 0
        for h in hits:
            key = group_key(h['_source'])
            if h['_id'] in why or h['_id'] in used or key in closed or taken >= size:
                continue
            picked.append(h['_id']); why[h['_id']] = name; groups[h['_id']] = key; taken += 1
        print(f'{name}: {taken}/{size}', file=sys.stderr)

    # Allocate whole groups: dev first (stratified by drawing groups in random order), the rest blind.
    by_group = defaultdict(list)
    for i in picked:
        by_group[groups[i]].append(i)
    order = sorted(by_group, key=lambda k: hashlib.sha256(f'{args.seed}{k}'.encode()).hexdigest())
    dev, blind = [], []
    for key in order:
        (dev if len(dev) + len(by_group[key]) <= args.dev else blind).extend(by_group[key])

    challenge, rng = [], random.Random(args.seed)
    taken_groups = set(groups.values()) | closed
    for n, (name, size, query) in enumerate(CHALLENGE):
        hits = search(url, index, query, size * 8, args.seed + 100 + n)
        rng.shuffle(hits)
        taken = 0
        for h in hits:
            key = group_key(h['_source'])
            if h['_id'] in why or h['_id'] in used or key in taken_groups or taken >= size:
                continue
            challenge.append(h['_id']); why[h['_id']] = name; groups[h['_id']] = key; taken_groups.add(key); taken += 1
        print(f'challenge {name}: {taken}/{size}', file=sys.stderr)

    SETS.mkdir(parents=True, exist_ok=True)
    for name, ids in (('regression', regression), ('dev', dev), ('blind', blind), ('challenge', challenge)):
        (SETS / f'{name}.txt').write_text('\n'.join(ids) + '\n')
    manifest = {'seed': args.seed, 'counts': {'regression': len(regression), 'dev': len(dev), 'blind': len(blind), 'challenge': len(challenge)},
                'strata': {name: dict(Counter(why[i] for i in ids)) for name, ids in (('dev', dev), ('blind', blind), ('challenge', challenge))},
                'documents': {i: {'set': s, 'stratum': why[i], 'group': groups[i]}
                              for s, ids in (('dev', dev), ('blind', blind), ('challenge', challenge)) for i in ids}}
    (SETS / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps(manifest['counts']))


if __name__ == '__main__':
    main()
