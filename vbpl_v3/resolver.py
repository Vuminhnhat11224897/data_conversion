"""Layer 3, reference resolution: from what the model read (layer 2) to the contract fields, in code.

- target_document as written -> the cited number, or "Luật <tên>" for a law named by name. Matching it to a stored document is
  relations.resolve(), run later with the other relations.
- target_text as written -> positions in the contract format (temporal.positions); target_part -> doi_tuong.
- target_section: a position that may belong to the decision or to the Quy định it issues, with nothing saying which, is not linked.
Nothing is guessed: a row the text does not settle keeps resolution_status = unresolved and the reason.
"""

import re

from . import governance
from .structure import NUMBER
from .text import number_key
from .relations import scope
from .temporal import extension, finer_parts, phrase_change, positions, suspension

# A whole document with no position: the act ends, replaces or halts all of it.
WHOLE = {'bai-bo', 'thay-the', 'huy-bo', 'dinh-chi', 'ngung-hieu-luc', 'gia-han'}
# Acts on a document as a whole without one position: "sửa đổi một số điều", guidance of a document.
DOCUMENT_LEVEL = {'sua-doi': 'một số điều', 'bo-sung': 'một số điều', 'huong-dan': 'toàn bộ', 'quy-dinh-chi-tiet': 'toàn bộ',
                  'dinh-chinh': 'toàn bộ', 'thay-cum-tu': 'một số cụm từ'}
LAW = re.compile(r'(Bộ\s+luật|Luật|Pháp\s+lệnh)\s+(?!này\b|số\b)\S')


# Numbers written "number-type/body" (party and old government documents): "38-HD/BTCTW", "20-CT/TW", "481-TTg".
# Q12 (20/10/2026): an act on administrative procedures, not on the document text. The edge still goes to the document that published
# them; doi_tuong_loai tells the two apart, and ma_thu_tuc keeps the national procedure code ("1.008698") a row states.
PROCEDURE = re.compile(r'thủ\s+tục\s+hành\s+chính|\bTTHC\b|^\s*(?:các\s+|\d+\s+|\(\d+\)\s+)*thủ\s+tục\b', re.I)
PROCEDURE_CODE = re.compile(r'(?<![\d.])\d\.\d{6}(?![\d.])')


# The appendix convention (26/10/2026): what is not điều – khoản – điểm (a part named by name, a Mục or Phần of a plan or an old
# circular, a row of a catalogue, "Mục II Phần B Phụ lục I") is its appendix; its words stay as the content (doi_tuong).
ARTICLE_PLACE = re.compile(r'\b(?:điểm|khoản|Điều|Chương)\b', re.I)
APPENDIX_LABEL = re.compile(r'phụ\s+lục\s+(?:số\s+)?([IVXLCDM]+|\d+[a-zđ]?|[A-ZĐ])\b', re.I)


def appendix_place(text):
    """'Phụ lục II' when the words name one appendix, 'Phụ lục' otherwise."""
    labels = list(dict.fromkeys(m[1] for m in APPENDIX_LABEL.finditer(text or '')))
    return f'Phụ lục {labels[0]}' if len(labels) == 1 else 'Phụ lục'


def appendix_scope(record):
    """The final positions of an edge under the appendix convention: every position outside điều – khoản – điểm becomes its appendix,
    and a part named by name with no position becomes the appendix that holds it. The whole document and article positions stay."""
    places = [p for p in record.get('vi_tri') or [] if p != 'toàn bộ']
    if places:
        moved = list(dict.fromkeys(p if ARTICLE_PLACE.search(p) else appendix_place(p) for p in places))
        if moved != places:
            record.update(vi_tri=moved, scope='; '.join(moved))
    elif record.get('doi_tuong'):
        place = appendix_place(record['doi_tuong'])
        record.update(vi_tri=[place], scope=place)


TYPE_ONLY = re.compile(r'(?:toàn\s+bộ\s+|cả\s+)?(?:các\s+)?(?:văn\s+bản|Quyết\s+định|Nghị\s+định|Nghị\s+quyết|Thông\s+tư(?:\s+liên\s+tịch)?|Chỉ\s+thị'
                       r'|Luật|Pháp\s+lệnh|Công\s+văn|Kế\s+hoạch)(?:\s+(?:này|đó|trên|số))?\.?', re.I)


def object_kind(named, heading='', row=False):
    """'thu_tuc_hanh_chinh' when the part acted on is a procedure: the part is named as one ("107 thủ tục hành chính", "Thủ tục thẩm
    định …"), or the act is a row of a list of procedures (the appendix title or the heading above the row says so); else 'van_ban'."""
    if PROCEDURE.search(named or '') or (row and PROCEDURE.search(heading or '')):
        return 'thu_tuc_hanh_chinh'
    return 'van_ban'


DASHED = governance.DASHED  # one definition, shared with the evidence check


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
    holder = target_of(row.get('van_ban_chua_noi_dung') or '')
    own = number_key((row['_context'].get('van_ban') or {}).get('so_hieu') or '')
    # This document is never the holder: its attachment is its own content, not content it changes (192235).
    if holder and target and number_key(holder) not in (number_key(target), own):
        # The document that holds the changed content is the target, not one named inside that content (P1, 20/10/2026): taken when
        # the source shows its number.
        shown = '\n'.join([unit, lead] + [str(row['_context'].get(k) or '') for k in ('ten_dieu', 'cau_dan_dieu', 'chuong', 'phan_dau')])
        if number_key(holder) in {number_key(m.group()) for m in NUMBER.finditer(shown)}:
            target = holder
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
    whole = row['action'] in WHOLE and row['target_section'] == 'khong_ap_dung'
    if not part and ' STT ' in row['source_path'] and not places and not whole:
        # A row of a list names a procedure or an item, not a provision: the part is the row's name (rubric, 19/10/2026). A row of a
        # list of documents repealed or replaced as a whole names the document itself (336452).
        from .extract import procedure
        part = procedure(unit)
    if TYPE_ONLY.fullmatch(part):
        # "Quyết định", "văn bản": the type of the target names no part of it (336452, 20/10/2026).
        part = ''
    # An item of a list acts on what it names first (C, 21/10/2026): the document itself, or a provision of it. Positions and parts
    # read from the words after the document's number are its name ("Quyết định X về việc sửa đổi khoản 2 Điều 3"), never this scope.
    item = governance.item_object(row, out['target_doc']) if target else None
    if item and item[0] == 'van_ban':
        places, part = [], ''
        whole = whole or row['action'] in WHOLE
    elif item:
        places, part = [p for p in positions(item[1]) if p != 'toàn bộ'] or places, ''
    # A part with no node of its own (a form, a paragraph, a sentence, a row) keeps its limit when the edge goes to the node that holds
    # it (C, 21/10/2026): "Mẫu số 01 Phụ lục I" is Phụ lục I, only the form.
    detail = {}
    for text in list(row['target_text'] or []) + ([item[1]] if item and item[0] == 'vi_tri' else []):
        finer = finer_parts(text)
        for place in positions(text) if finer else []:
            detail.setdefault(place, '; '.join(finer))
    if detail:
        out['_chi_tiet'] = detail
    if row['action'] == 'thay-cum-tu':
        pairs, listed = phrase_change(unit)
        places = places or listed
        out['cum_tu'] = [{**pair, 'vi_tri': pair['vi_tri'] or places} for pair in pairs]
    if places:
        out.update(scope='; '.join(places), vi_tri=places, unresolved=False)
    elif part:
        out.update(scope=part, vi_tri=[], doi_tuong=part, kem_theo=row['target_section'] == 'kem_theo', unresolved=False)
    elif whole:
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
    row_unit = ' STT ' in row['source_path']
    out['doi_tuong_loai'] = object_kind(out.get('doi_tuong'), lead + ' ' + row['_context'].get('ten_dieu', ''), row_unit)
    if out['doi_tuong_loai'] == 'thu_tuc_hanh_chinh':
        code = PROCEDURE_CODE.search(unit if row_unit else row['evidence'])
        if code:
            out['ma_thu_tuc'] = code.group()
    if row['action'] in ('dinh-chi', 'ngung-hieu-luc'):
        out.update(suspension(unit))
    elif row['action'] == 'gia-han':
        out.update(extension(unit))
    return out
