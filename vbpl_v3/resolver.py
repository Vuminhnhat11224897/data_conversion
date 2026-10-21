"""Layer 3, reference resolution: from what the model read (layer 2) to the contract fields, in code.

- target_document as written -> the cited number, or "Luật <tên>" for a law named by name. Matching it to a stored document is
  relations.resolve(), run later with the other relations.
- target_text as written -> positions in the contract format (temporal.positions); target_part -> doi_tuong.
- target_section: a position that may belong to the decision or to the Quy định it issues, with nothing saying which, is not linked.
Nothing is guessed: a row the text does not settle keeps resolution_status = unresolved and the reason.
"""

import re

from .structure import NUMBER
from .relations import scope
from .temporal import extension, phrase_change, positions, suspension

# A whole document with no position: the act ends, replaces or halts all of it.
WHOLE = {'bai-bo', 'thay-the', 'huy-bo', 'dinh-chi', 'ngung-hieu-luc', 'gia-han'}
# Acts on a document as a whole without one position: "sửa đổi một số điều", guidance of a document.
DOCUMENT_LEVEL = {'sua-doi': 'một số điều', 'bo-sung': 'một số điều', 'huong-dan': 'toàn bộ', 'quy-dinh-chi-tiet': 'toàn bộ',
                  'dinh-chinh': 'toàn bộ', 'thay-cum-tu': 'một số cụm từ'}
LAW = re.compile(r'(Bộ\s+luật|Luật|Pháp\s+lệnh)\s+(?!này\b|số\b)\S')


# Numbers written "number-type/body" (party and old government documents): "38-HD/BTCTW", "20-CT/TW", "481-TTg".
DASHED = re.compile(r'(?<![\w/-])\d{1,6}-[A-ZĐ][A-Za-zĐđ]{1,9}(?:/[A-ZĐ][A-ZĐa-zđ0-9-]*)?(?![\w-])')
# Q12 (20/10/2026): an act on administrative procedures, not on the document text. The edge still goes to the document that published
# them; doi_tuong_loai tells the two apart, and ma_thu_tuc keeps the national procedure code ("1.008698") a row states.
PROCEDURE = re.compile(r'thủ\s+tục\s+hành\s+chính|\bTTHC\b|^\s*(?:các\s+|\d+\s+|\(\d+\)\s+)*thủ\s+tục\b', re.I)
PROCEDURE_CODE = re.compile(r'(?<![\d.])\d\.\d{6}(?![\d.])')


TYPE_ONLY = re.compile(r'(?:toàn\s+bộ\s+|cả\s+)?(?:các\s+)?(?:văn\s+bản|Quyết\s+định|Nghị\s+định|Nghị\s+quyết|Thông\s+tư(?:\s+liên\s+tịch)?|Chỉ\s+thị'
                       r'|Luật|Pháp\s+lệnh|Công\s+văn|Kế\s+hoạch)(?:\s+(?:này|đó|trên|số))?\.?', re.I)


def object_kind(named, heading='', row=False):
    """'thu_tuc_hanh_chinh' when the part acted on is a procedure: the part is named as one ("107 thủ tục hành chính", "Thủ tục thẩm
    định …"), or the act is a row of a list of procedures (the appendix title or the heading above the row says so); else 'van_ban'."""
    if PROCEDURE.search(named or '') or (row and PROCEDURE.search(heading or '')):
        return 'thu_tuc_hanh_chinh'
    return 'van_ban'




def target_of(text):
    """'Quyết định số 28/2017/QĐ-UBND ngày …' -> '28/2017/QĐ-UBND'; 'Hướng dẫn số 38-HD/BTCTW' -> '38-HD/BTCTW';
    'Luật Đất đai' -> 'Luật Đất đai'; otherwise None."""
    match = NUMBER.search(text or '') or DASHED.search(text or '')
    if match:
        return re.sub(r'\s+', '', match.group()).replace('Ð', 'Đ')
    if LAW.match((text or '').strip()):
        return ' '.join(text.split())
    return None


def resolve_row(row):
    """Contract fields for one extracted act, plus resolution_status / resolution_reason."""
    unit = row['_unit']['noi_dung']
    lead = row['_unit']['cau_dan']
    out = {'action': row['action'], 'source_path': 'intro' if row['source_path'] == 'Phần đầu' else row['source_path'],
           'source_in_phu_luc': row['source_path'].startswith('Phụ lục'), 'evidence': row['evidence'][:2000],
           'target_section': row['target_section'], 'extraction': 'llm', 'resolution_status': 'validated', 'resolution_reason': None,
           '_unit_evidence': unit[:4000], '_parent_evidence': (lead or row['_context'].get('ten_dieu', ''))[:2000],
           '_evidence': '\n'.join(x for x in (row['_context'].get('chuong', ''), row['_context'].get('ten_dieu', ''), lead, unit) if x)[:4000]}

    def unresolved(reason):
        if out['resolution_status'] == 'validated':
            out.update(resolution_status='unresolved', resolution_reason=reason)
    target = target_of(row['target_document'])
    out['target_doc'] = target or ' '.join((row['target_document'] or '').split())[:200]
    if not target:
        unresolved('khong_xac_dinh_van_ban_dich')
    places = list(dict.fromkeys(p for text in row['target_text'] for p in positions(text)))
    if not places and row['target_section'] != 'khong_ap_dung':
        # The model named no position, but its quote does ("Khoản 3 Điều 5 được sửa đổi, bổ sung như sau"): read it from the quote.
        value, unclear = scope(row['evidence'])
        places = [] if unclear else [p for p in positions(value) if p != 'toàn bộ']
    part = (row['target_part'] or '').strip()
    if not part and not places and row['target_text']:
        # A position outside the contract format ("khoản 2 mục II" of an old circular) names a part: it is the part (19/10/2026 rule).
        part = '; '.join(' '.join(t.split()) for t in row['target_text'])[:300]
    if not part and ' STT ' in row['source_path'] and not places:
        # A row of a list names a procedure or an item, not a provision: the part is the row's name (rubric, 19/10/2026).
        from .extract import procedure
        part = procedure(unit)
    if row['action'] == 'thay-cum-tu':
        pairs, listed = phrase_change(unit)
        places = places or listed
        out['cum_tu'] = [{**pair, 'vi_tri': pair['vi_tri'] or places} for pair in pairs]
    if places:
        out.update(scope='; '.join(places), vi_tri=places, unresolved=False)
    elif part:
        out.update(scope=part, vi_tri=[], doi_tuong=part, kem_theo=row['target_section'] == 'kem_theo', unresolved=False)
    elif row['action'] in WHOLE and row['target_section'] == 'khong_ap_dung':
        out.update(scope='toàn bộ', vi_tri=['toàn bộ'], unresolved=False)
    elif row['action'] in DOCUMENT_LEVEL and (row['target_section'] == 'khong_ap_dung' or row['action'] in ('huong-dan', 'quy-dinh-chi-tiet')
                                             or row['source_path'] == 'Phần đầu'):
        # The title or the issuing sentence names the act on the document ("Quyết định sửa đổi Quyết định số 307/QĐ-UBND"): it is about
        # the document as a whole, whatever part the model guessed; the articles carry the positions.
        out.update(scope=DOCUMENT_LEVEL[row['action']], vi_tri=[], unresolved=False)
    else:
        out.update(scope='chưa xác định', vi_tri=[], unresolved=True)
        unresolved('vi_tri_chua_xac_dinh')

    # Case A: a decision and the Quy định it issues both have an Điều 3; "khoản 7 Điều 3" alone does not say which.
    if row['target_section'] == 'khong_ro' and any(re.search(r'\bĐiều\s', p) for p in places):
        unresolved('phan_kem_theo_chua_ro')
    if row['target_section'] == 'kem_theo':
        out['kem_theo'] = True
    if row['action'] in ('dinh-chi', 'ngung-hieu-luc'):
        out.update(suspension(unit))
    elif row['action'] == 'gia-han':
        out.update(extension(unit))
    return out
    row_unit = ' STT ' in row['source_path']
    out['doi_tuong_loai'] = object_kind(out.get('doi_tuong'), lead + ' ' + row['_context'].get('ten_dieu', ''), row_unit)
    if out['doi_tuong_loai'] == 'thu_tuc_hanh_chinh':
        code = PROCEDURE_CODE.search(unit if row_unit else row['evidence'])
        if code:
            out['ma_thu_tuc'] = code.group()
