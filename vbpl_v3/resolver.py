"""Layer 3, reference resolution: from what the model read (layer 2) to the contract fields, in code.

- target_document as written -> the cited number, or "Luật <tên>" for a law named by name. Matching it to a stored document is
  relations.resolve(), run later with the other relations.
- target_text as written -> positions in the contract format (temporal.positions); target_part -> doi_tuong.
- target_section: a position that may belong to the decision or to the Quy định it issues, with nothing saying which, is not linked.
Nothing is guessed: a row the text does not settle keeps resolution_status = unresolved and the reason.
"""

import re

from . import governance
from .governance import TTHC
from .structure import NUMBER
from .text import number_key
from .relations import scope, strip_quotes
from .temporal import extension, finer_parts, phrase_change, positions, suspension
from .validate import tied_places

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
# circular, a row of a catalogue, "Mục II Phần B Phụ lục I") is its appendix; its words stay as the content (doi_tuong, chi_tiet_vi_tri).
ARTICLE_PLACE = re.compile(r'\b(?:điểm|khoản|Điều|Chương)\b', re.I)
APPENDIX_LABEL = re.compile(r'phụ\s+lục\s+(?:số\s+)?([IVXLCDM]+|\d+[a-zđ]?|[A-ZĐ])\b', re.I)


def appendix_place(text):
    """'Phụ lục II' when the words name one appendix, 'Phụ lục' otherwise."""
    labels = list(dict.fromkeys(m[1] for m in APPENDIX_LABEL.finditer(text or '')))
    return f'Phụ lục {labels[0]}' if len(labels) == 1 else 'Phụ lục'


# What an appendix holds (27/10/2026): a part named by name goes to its appendix only when it is one of these; "một số điều của các
# Thông tư …", "phần căn cứ" are no appendix and keep their name.
APPENDIX_KIND = re.compile(r'phụ\s+lục|danh\s+mục|thủ\s+tục|\bTTHC\b|biểu\s+mẫu|\bmẫu\s+(?:số\s+)?[\w.]|phương\s+án|quy\s+trình\s+nội\s+bộ'
                           r'|\bmục\s+[IVXLCDM\d]|\bphần\s+[IVXLCDM\dA-ZĐ]\b|số\s+thứ\s+tự|\bSTT\b', re.I)


def appendix_like(part):
    """The part named by name is held by an appendix: a catalogue, a procedure, a form, a plan, a Mục or Phần, a row."""
    return bool(APPENDIX_KIND.search(part or ''))


# Positions of the body the contract names besides điều – khoản – điểm (contract 9.5): the document's title and the name of a Mục
# ("tên Mục 1"); a Mục under a Chương ("Mục 1 Chương II") is one by ARTICLE_PLACE. A Mục on its own is most often a part of a plan or
# a list, also when numbered (683435: "Mục 89" of a decision's appendix), so it is the appendix.
BODY_PLACE = re.compile(r'^(?:tên văn bản|tên Mục \d+)$')


def body_place(place):
    """The position is a part of the document's body: an article level, a Mục under a Chương, the title, the name of a Mục."""
    return bool(ARTICLE_PLACE.search(place) or BODY_PLACE.match(place))


def appendix_scope(record):
    """The final positions of an edge under the appendix convention: every position outside the body (body_place) becomes its
    appendix, and a part named by name that an appendix holds (appendix_like, a procedure, a row of a list) becomes that appendix.
    Other parts named by name, the whole document and body positions stay. A position moved keeps its words as the limit on the edge
    to the appendix (_chi_tiet, written as chi_tiet_vi_tri), so nothing the sentence names is lost (27/10/2026). Run more than once:
    positions read late (a rule's scope, a row of a list) go through it too."""
    places = [p for p in record.get('vi_tri') or [] if p != 'toàn bộ']
    if places:
        moved = {p: p if body_place(p) else appendix_place(p) for p in places}
        if any(p != q for p, q in moved.items()):
            detail = record.setdefault('_chi_tiet', {})
            for p, q in moved.items():
                if p != q:
                    finer = detail.pop(p, None)
                    detail[q] = '; '.join(x for x in dict.fromkeys([detail.get(q), p, finer]) if x)
            kept = list(dict.fromkeys(moved.values()))
            record.update(vi_tri=kept, scope='; '.join(kept))
        for pair in record.get('cum_tu') or []:
            pair['vi_tri'] = list(dict.fromkeys(p if p == 'toàn bộ' or body_place(p) else appendix_place(p) for p in pair.get('vi_tri') or []))
    elif record.get('doi_tuong') and (appendix_like(record['doi_tuong']) or record.get('doi_tuong_loai') == 'thu_tuc_hanh_chinh'
                                      or ' STT ' in record.get('source_path', '') or record.get('source_path', '').startswith('Phụ lục')):
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

# The act's object is the document itself, named right after the verb, which opens the sentence or follows "… này" or "và": "Quyết
# định này sửa đổi, bổ sung Quyết định số 3533/…", "và thay thế Quyết định số 5143/…", a heading "SỬA ĐỔI, BỔ SUNG NGHỊ QUYẾT SỐ
# 112/2003/NQ-HĐND". Not a task ("khẩn trương thực hiện sửa đổi Thông tư số …") or a verb inside a sentence.
ON_DOCUMENT = re.compile(r'(?:^|[.;:\n]\s*|\b(?:này|và)\s+)(?:sửa\s+đổi(?:\s*,\s*|\s+và\s+|\s+)bổ\s+sung|sửa\s+đổi|bổ\s+sung|b[ãả]i\s+bỏ|thay\s+thế|h(?:uỷ|ủy|uy)\s+bỏ)\s+(?:toàn\s+bộ\s+)?'
                         r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Nghị\s+định|Nghị\s+quyết|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định|Chỉ\s+thị)\s+(?:số\s*)?$', re.I)

OWN_ARTICLES = re.compile(r'/(?:QH\d*|UBTVQH\d*|NĐ-CP|TT-|TTLT-)', re.I)

# Procedures named as the act's object: "sửa đổi, bổ sung 29 (hai mươi chín) thủ tục hành chính đã được công bố theo Quyết định số …".
ON_PROCEDURES = re.compile(r'(?:sửa\s+đổi(?:\s*,\s*|\s+và\s+|\s+)bổ\s+sung|sửa\s+đổi|bổ\s+sung|b[ãả]i\s+bỏ|thay\s+thế|h(?:uỷ|ủy|uy)\s+bỏ)\s+'
                           r'(?P<obj>(?:\d+\s+(?:\([^)]{0,40}\)\s+)?)?(?:các\s+)?thủ\s+tục\s+hành\s+chính\b[^.;:]{0,160}?)\s+'
                           r'(?:(?:đã\s+)?(?:được\s+)?(?:công\s+bố|ban\s+hành)|tại|theo)\b', re.I)


def on_document(text, target):
    plain = strip_quotes(text or '')
    return any(number_key(m.group()) == number_key(target or '') and ON_DOCUMENT.search(plain[max(0, m.start() - 120):m.start()])
               for m in NUMBER.finditer(plain))


def named_before(part, row, target):
    """The part the model read is the item's own words before the target's number, under a lead or item that names procedures or a
    part an appendix holds: "Bãi bỏ các thủ tục hành chính gồm: 1. Cấp giấy phép hoạt động đo đạc và bản đồ được công bố tại Quyết
    định số 3086/QĐ-BTNMT" is that procedure, not 3086 as a whole (411815, 27/10/2026). Both readings must agree: the model's part and
    the words of the item."""
    words = ' '.join(re.sub(r'[^\w\s]', ' ', part or '').split()[:4]).casefold()
    if len(words.split()) < 3:
        return False
    f = governance.fields(row)
    kind = appendix_like(part) or PROCEDURE.search(part) or TTHC.search(' '.join((f['cau_dan'], f['cau_dan_dieu'], f['ten_dieu'])))
    for line in (f['don_vi'] + '\n' + f['danh_sach']).split('\n'):
        at = next((m for m in NUMBER.finditer(line) if number_key(m.group()) == number_key(target)), None)
        if kind and at and words in ' '.join(re.sub(r'[^\w\s]', ' ', line[:at.start()]).split()).casefold():
            return True
    return False


def target_of(text):
    """'Quyết định số 28/2017/QĐ-UBND ngày …' -> '28/2017/QĐ-UBND'; 'Hướng dẫn số 38-HD/BTCTW' -> '38-HD/BTCTW';
    'Luật Đất đai' -> 'Luật Đất đai'; otherwise None."""
    match = NUMBER.search(text or '') or DASHED.search(text or '')
    if match:
        number = re.sub(r'\s+', '', match.group()).replace('Ð', 'Đ')
        # A number typed without its Đ ("18/2022/NQ-HDND", 562142, 27/10/2026) is the number documents are filed under.
        return re.sub(r'(?<=[-/])(QD|ND|HDND)(?=[-/\d]|$)', lambda m: {'QD': 'QĐ', 'ND': 'NĐ', 'HDND': 'HĐND'}[m[1]], number)
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
    listed = bool(item and item[0] == 'van_ban' and named_before(part, row, out['target_doc']))
    if item and item[0] == 'van_ban' and not listed:
        places, part = [], ''
        whole = whole or row['action'] in WHOLE
    elif item and item[0] == 'vi_tri':
        # A provision named first is the scope; an item that names a part with no position to read ("Thủ tục hành chính có số thứ tự
        # 21, 22 Mục I Phụ lục I", 679692, 27/10/2026) keeps the part, not the whole document.
        read = [p for p in positions(item[1]) if p != 'toàn bộ']
        if read or places:
            places, part = read or places, ''
        else:
            part = part or (item[1] if appendix_like(item[1]) else '')
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
        # the document as a whole, whatever part the model guessed; the articles carry the positions. An article that names procedures
        # as the act's object acts on those procedures (273699, 27/10/2026).
        named = ON_PROCEDURES.search(strip_quotes(row['evidence'])) if row['source_path'] != 'Phần đầu' else None
        if named:
            part = ' '.join(named['obj'].split())
            out.update(scope=part, vi_tri=[], doi_tuong=part, kem_theo=row['target_section'] == 'kem_theo', unresolved=False)
        else:
            out.update(scope=DOCUMENT_LEVEL[row['action']], vi_tri=[], unresolved=False)
    elif row['action'] in WHOLE.union(DOCUMENT_LEVEL) and on_document(row['evidence'], out['target_doc']):
        # The quote names the document itself as the act's object and no part of it (27/10/2026): the whole document for an act on
        # a whole, the document level for an amendment, as for the title, whatever section the model chose.
        whole = row['action'] in WHOLE
        out.update(scope='toàn bộ' if whole else DOCUMENT_LEVEL[row['action']], vi_tri=['toàn bộ'] if whole else [], unresolved=False)
    else:
        out.update(scope='chưa xác định', vi_tri=[], unresolved=True)
        unresolved('vi_tri_chua_xac_dinh')

    # Case A: a decision and the Quy định it issues both have an Điều 3; "khoản 7 Điều 3" alone does not say which. A law, a resolution
    # of the National Assembly, a decree or a circular issues no Quy định with articles of its own: positions the quote ties to its
    # number are its own ("… điểm c2 khoản 1 Điều 9, khoản 3 Điều 30 của Nghị quyết số 222/2025/QH15", 685777, 27/10/2026).
    if row['target_section'] == 'khong_ro' and any(re.search(r'\bĐiều\s', p) for p in places) \
            and not (OWN_ARTICLES.search(out['target_doc']) and set(places) <= set(tied_places(strip_quotes(row['evidence']), out['target_doc']))):
        unresolved('phan_kem_theo_chua_ro')
    if row['target_section'] == 'kem_theo':
        out['kem_theo'] = True
    row_unit = ' STT ' in row['source_path']
    # An item of a list that names a part is a row of that list: the lead above it says what the list holds (411815: "Bãi bỏ các thủ
    # tục hành chính gồm:").
    out['doi_tuong_loai'] = object_kind(out.get('doi_tuong'), ' '.join((lead, row['_context'].get('ten_dieu', ''), row['_context'].get('cau_dan_dieu', '') if listed else '')),
                                        row_unit or listed)
    if out['doi_tuong_loai'] == 'thu_tuc_hanh_chinh':
        code = PROCEDURE_CODE.search(unit if row_unit else row['evidence'])
        if code:
            out['ma_thu_tuc'] = code.group()
    if row['action'] in ('dinh-chi', 'ngung-hieu-luc'):
        out.update(suspension(unit))
    elif row['action'] == 'gia-han':
        out.update(extension(unit))
    return out
