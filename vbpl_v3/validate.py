"""Layer 4, validation: every extracted act must be grounded in the source before it can become an edge.

Rules, no model call:
- the quote (evidence) is in the source, outside the quoted new wording;
- the quote carries the act; the name of a catalogue that lists acts ("Danh mục văn bản cần đình chỉ, sửa đổi, bổ sung, bãi bỏ") is no act;
- the target document and every number of every position appear in the source the model read.
A quote that is not in the source, or that is new wording or a catalogue name, rejects the row. A target or a position the source does
not show leaves it unresolved. performed = false rows are dropped before this layer.
"""

import re

from .relations import document_refs, strip_quotes
from .text import action_matches, number_key, quote_in_text

# "Công bố (kèm theo Quyết định này) Danh mục thủ tục hành chính được sửa đổi, bổ sung, bãi bỏ …": the list is published; the act words
# name the list. The act is on a document only where a row or a sentence names that document.
ANNOUNCES = re.compile(r'\bcông\s+bố\b.{0,160}?\b(?:danh\s+mục|thủ\s+tục\s+hành\s+chính)\b', re.I | re.S)

VERBS = {'sua-doi': r'sửa|điều\s+chỉnh', 'bo-sung': r'bổ\s*sung|thêm', 'bai-bo': r'b[ãả]i\s*bỏ|\bbỏ\b|hết\s+hiệu\s*lực|kết\s*thúc|chấm\s*dứt',
         'thay-the': r'thay\s*thế|\bthay\b', 'thay-cum-tu': r'\bthay\b|cụm\s+từ|từ\s+ngữ', 'huy-bo': r'h(?:uỷ|ủy|uy)\s*bỏ', 'dinh-chi': r'đình\s*chỉ',
         'ngung-hieu-luc': r'ng(?:ư|ừ)ng\s+(?:thi\s+hành\s+)?hiệu\s*lực|tạm\s+ngưng|tạm\s+dừng|chấm\s*dứt|kết\s*thúc', 'dinh-chinh': r'đính\s*chính|\bsửa\b',
         'gia-han': r'gia\s+hạn|kéo\s+dài', 'huong-dan': r'hướng\s+dẫn', 'quy-dinh-chi-tiet': r'quy\s+định\s+chi\s+tiết|chi\s+tiết'}


def sources(row):
    """Every text the model was shown for this unit."""
    context = row['_context']
    return [row['_unit']['noi_dung'], row['_unit']['cau_dan'], row['_unit'].get('danh_sach_kem_theo', ''), context.get('ten_dieu', ''),
            context.get('cau_dan_dieu', ''),
            context.get('chuong', ''), (context.get('van_ban') or {}).get('ten') or '', context.get('phan_dau', '')]


def guides(row, evidence):
    """Guidance is declared by the document of itself ("Thông tư này hướng dẫn …", "Nghị định này quy định chi tiết …"), in its title,
    opening or scope article; "thực hiện theo hướng dẫn tại …", "theo quy định tại …" only cite."""
    if row['source_path'] == 'Phần đầu' or re.search(r'phạm\s+vi', row['_context'].get('ten_dieu', ''), re.I):
        return True
    return bool(re.search(r'\bnày\s+(?:hướng\s+dẫn|quy\s+định\s+chi\s+tiết)', evidence, re.I))


def catalogue_name(evidence):
    """A list of three or more acts under "danh mục" names a catalogue; it performs none of them. Only the words before the first
    document number count: after it comes that document's own name ("Sửa đổi, bổ sung TTHC được công bố tại Quyết định số 2074/QĐ-UBND
    … về việc công bố Danh mục thủ tục hành chính mới ban hành, sửa đổi, bổ sung và thay thế …" acts on 2074)."""
    first = next(iter(document_refs(evidence)), None)
    if first and action_matches(evidence[:first.start()]):
        evidence = evidence[:first.start()]
    acts = {a for _, _, a in action_matches(evidence)}
    listed = len(re.findall(r'đình\s*chỉ|ngưng|sửa\s*đổi|bổ\s*sung|thay\s*thế|bãi\s*bỏ|hủy\s*bỏ|huỷ\s*bỏ|hết\s+hiệu\s*lực', evidence, re.I))
    return bool(re.search(r'danh\s+mục', evidence, re.I)) and (len(acts) >= 3 or listed >= 3)


DOCUMENT_ITEM = re.compile(r'(?:các\s+)?(?:Quyết\s+định|Nghị\s+quyết|Thông\s+tư(?:\s+liên\s+tịch)?|Nghị\s+định|Chỉ\s+thị|Luật|Pháp\s+lệnh|Văn\s+bản)\b', re.I)


def lead_states(row):
    """The act is stated before the quote, in the unit's lead or earlier in its text, and the quote is an item of the list it acts on:
    "Bãi bỏ các thủ tục hành chính tại các Quyết định sau: … Quyết định số 2687/QĐ-BTP …" (quote: the item)."""
    unit = row.get('_unit') or {}
    text = strip_quotes(unit.get('noi_dung') or '')
    quote = ' '.join((row.get('evidence') or '').split())
    at = ' '.join(text.split()).find(quote[:60]) if quote else -1
    flat = ' '.join(text.split())
    before = (unit.get('cau_dan') or '') + ' ' + (flat[:at] if at > 0 else '')
    if not re.search(VERBS[row['action']], before, re.I):
        return False
    if re.search(r'(?:sau|như\s+sau)\s*(?:đây)?\s*:', before, re.I) or re.search(r':\s*$', unit.get('cau_dan') or ''):
        return True  # a lead that opens a list ("Các nghị quyết sau hết hiệu lực …:"), the quote one of its items
    # "Bãi bỏ Quyết định số 71/…; Quyết định số 2687/… và Quyết định số 169/…": the quote is a later item of a list the same sentence acts on.
    sentence = re.split(r'\.\s', flat[:at])[-1] if at > 0 else ''
    return bool(re.search(VERBS[row['action']], sentence, re.I)) and re.match(DOCUMENT_ITEM, quote) is not None


# A history note, not this document's act: "… đã được sửa đổi, bổ sung tại Quyết định số …", "bị thay thế bởi Thông tư số …".
HISTORY = re.compile(r'\b(?:đã\s+)?(?:bị|được)\s+(?:sửa\s*đổi|bổ\s*sung|thay\s*thế|b[ãả]i\s*bỏ|h(?:uỷ|ủy|uy)\s*bỏ|đình\s*chỉ|đính\s*chính)'
                     r'(?:\s*,\s*(?:bổ\s*sung|thay\s*thế))?\s+(?:một\s+số\s+\S+\s+)?(?:bởi|tại|theo)\b', re.I)
TTHC = re.compile(r'thủ\s+tục\s+hành\s+chính|\bTTHC\b', re.I)


LEGISLATIVE = re.compile(r'^(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Hiến\s+pháp)\b|/QH\d*(?:/\d{4})?$|/(?:\d{4}/)?UBTVQH\d*$|/PL-UBTVQH', re.I)
LEGISLATURE_TYPES = {'Hiến pháp', 'Bộ luật', 'Luật', 'Pháp lệnh', 'Nghị quyết'}


def above(row, target):
    """The target is a law, an ordinance or a resolution of the National Assembly or its Standing Committee, and the source is not
    one of these: a decision, a circular or a letter cannot amend, repeal or replace a law ("Tổng hợp nội dung sửa đổi Luật, Pháp lệnh"
    in a Prime Minister's letter lists what to propose, it changes no law)."""
    document = row['_context'].get('van_ban') or {}
    own_type = (document.get('loai') or '').strip()
    own_number = document.get('so_hieu') or ''
    if not LEGISLATIVE.search((target or '').strip()):
        return False
    if own_type in ('Hiến pháp', 'Bộ luật', 'Luật', 'Pháp lệnh'):
        return False
    if own_type == 'Nghị quyết' and re.search(r'/(?:\d{4}/)?(?:QH|UBTVQH)', own_number, re.I):
        return False
    return True


def issuer_code(number):
    """The issuing-body part of a document number: '2074/QĐ-UBND' -> 'ubnd', '636/QĐ-LĐTBXH' -> 'lđtbxh', '29/2015/TT-BYT' -> 'byt'."""
    last = (number or '').split('/')[-1]
    code = last.split('-', 1)[1].casefold() if '-' in last else ''
    # The provincial committee and its chair sign the same body's decisions: QĐ-UBND, QĐ-CT, QĐ-UBND-KGVX.
    return 'ubnd' if code.startswith('ubnd') or code in ('ct', 'ub') else code


def table_row(row, evidence):
    """(verdict, reason) for an act read from a row of an appendix table; (None, None) when the row may stand.
    The row must name its target. The act word must be in the row, or in the heading of a list of administrative procedures (the row
    names the decision that published the procedure), or in the article that acts on the documents the appendix lists: then the act
    is that article's ("Bãi bỏ các văn bản tại Phụ lục II" -> Điều 1 for each document listed). A list of documents that expired,
    published after a review, is no act."""
    unit, context = row['_unit'], row['_context']
    target = number_key(row.get('target_document') or '')
    if target not in {number_key(m.group()) for m in document_refs(unit['noi_dung'])}:
        return 'reject', 'dong_bang_khong_neu_van_ban'
    # A list of procedures acts on the decision of the same body that published them. "Thủ tục … được công bố tại Quyết định số
    # 636/QĐ-LĐTBXH" in a provincial decision names the ministry's standard procedure, and "… quy định tại Thông tư số 29/2015/TT-BYT"
    # names its basis: a province neither amends nor repeals them.
    own = issuer_code((context.get('van_ban') or {}).get('so_hieu') or '')
    if TTHC.search(unit['cau_dan'] + ' ' + context.get('ten_dieu', '') + ' ' + unit['noi_dung'][:300]) and own and issuer_code(target) not in ('', own):
        return 'reject', 'dong_bang_khac_co_quan'
    if re.search(VERBS[row['action']], strip_quotes(unit['noi_dung']), re.I):
        return None, None
    if TTHC.search(unit['cau_dan'] + ' ' + context.get('ten_dieu', '')) and re.search(VERBS[row['action']], unit['cau_dan'] + ' ' + context.get('ten_dieu', ''), re.I):
        return None, None
    holder = context.get('_dieu_thuc_hien')
    if holder and re.search(VERBS[row['action']], holder['noi_dung'], re.I):
        row['source_path'] = holder['source_path']
        return None, None
    return 'reject', 'dong_bang_khong_co_hanh_dong'


def check(row, resolved):
    """(verdict, reason): verdict is 'reject', 'unresolved' or 'ok'."""
    evidence = (row.get('evidence') or '').strip()
    texts = sources(row)
    whole = '\n'.join(texts)
    # A quote may join pieces with "…"; each piece must be in one of the texts.
    pieces = [p for p in re.split(r'\s*(?:…|\.\.\.)\s*', evidence) if len(p) >= 8] or [evidence]
    if len(evidence) < 8 or not all(any(quote_in_text(p, t) for t in texts if t) for p in pieces):
        return 'reject', 'trich_dan_khong_co_trong_nguon'
    # The act is outside the quoted new wording; a quote that runs on into it ("Sửa đổi khoản 4 Điều 3 như sau: “4. …") is fine.
    outside = [strip_quotes(row['_unit']['noi_dung'])] + texts[1:]
    bare = [p for p in (strip_quotes(p).strip(' :;,.\n') for p in pieces) if len(p) >= 8]
    if not bare or not any(any(quote_in_text(p, t) for t in outside if t) for p in bare):
        return 'reject', 'trong_noi_dung_moi'
    if catalogue_name(evidence):
        return 'reject', 'ten_danh_muc'
    if HISTORY.search(evidence) and not re.search(VERBS[row['action']], HISTORY.sub(' ', strip_quotes(evidence)), re.I):
        return 'reject', 'ghi_chu_lich_su'
    if ' STT ' in row['source_path']:
        verdict, reason = table_row(row, evidence)
        if verdict:
            return verdict, reason
        resolved.update(source_path=row['source_path'], source_in_phu_luc=row['source_path'].startswith('Phụ lục'))
    if ANNOUNCES.search(evidence) and number_key(resolved.get('target_doc') or '') not in {number_key(m.group()) for m in document_refs(evidence)}:
        return 'reject', 'cong_bo_danh_muc'
    heading_act = ' STT ' in row['source_path'] and TTHC.search(row['_unit']['cau_dan'] + ' ' + row['_context'].get('ten_dieu', '')) \
        and re.search(VERBS[row['action']], row['_unit']['cau_dan'] + ' ' + row['_context'].get('ten_dieu', ''), re.I)
    if not re.search(VERBS[row['action']], evidence, re.I) and not lead_states(row) and not heading_act:
        return 'reject', 'trich_dan_khong_co_hanh_dong'  # a row of a list of procedures carries the act of its heading
    target = resolved.get('target_doc') or ''
    if resolved.get('resolution_reason') == 'khong_xac_dinh_van_ban_dich':
        return 'reject', 'khong_co_van_ban_dich'  # "các quy định trái với …", a catalogue: no document to link
    if number_key(target) and number_key(target) == number_key((row['_context'].get('van_ban') or {}).get('so_hieu') or ''):
        return 'reject', 'chinh_van_ban_nguon'
    if row['action'] in ('sua-doi', 'bo-sung', 'bai-bo', 'thay-the', 'huy-bo', 'thay-cum-tu') and above(row, target):
        return 'reject', 'vuot_tham_quyen'
    if row['action'] in ('huong-dan', 'quy-dinh-chi-tiet') and not guides(row, evidence):
        return 'reject', 'dan_chieu_khong_phai_huong_dan'
    if resolved['resolution_status'] == 'validated':
        if re.match(r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s', target):
            name = target.split(' ', 1)[1] if ' ' in target else target
            if name.casefold() not in ' '.join(whole.split()).casefold():
                return 'unresolved', 'van_ban_dich_khong_co_trong_nguon'
        elif number_key(target) not in {number_key(m.group()) for m in document_refs(whole)} and number_key(target) not in number_key(whole):
            return 'unresolved', 'van_ban_dich_khong_co_trong_nguon'
        for place in resolved.get('vi_tri') or []:
            for label in re.findall(r'\b(?:Điều|khoản|điểm|Chương|Mục|Phụ lục|Phần)\s+([\w.]+)', place):
                if not re.search(r'(?<![\w.])' + re.escape(label) + r'(?![\w])', whole, re.I):
                    return 'unresolved', 'vi_tri_khong_co_trong_nguon'
    return 'ok', None


def validate(rows, resolve_row):
    """[(row, resolved)] -> kept relation candidates (validated or unresolved) and a log of rejected rows."""
    kept, rejected = [], []
    for row in rows:
        if not row.get('performed'):
            continue
        resolved = resolve_row(row)
        verdict, reason = check(row, resolved)
        if verdict == 'reject':
            rejected.append({'source_path': row['source_path'], 'action': row['action'], 'target_document': row['target_document'],
                             'reason': reason, 'evidence': (row.get('evidence') or '')[:300]})
            continue
        if verdict == 'unresolved' and resolved['resolution_status'] == 'validated':
            resolved.update(resolution_status='unresolved', resolution_reason=reason)
        kept.append(resolved)
    return pair_amendments(kept), rejected


def pair_amendments(kept):
    """"Sửa đổi, bổ sung X" is two acts, sua-doi and bo-sung (settled 14/10/2026): the second is added when the model gave only one."""
    have = {(r['source_path'], r['action'], number_key(r.get('target_doc') or '')) for r in kept}
    extra = []
    for r in kept:
        if r['action'] not in ('sua-doi', 'bo-sung') or not re.search(r'sửa\s*đổi\s*,?\s*(?:và\s+)?bổ\s*sung', strip_quotes(r.get('evidence') or ''), re.I):
            continue
        other = 'bo-sung' if r['action'] == 'sua-doi' else 'sua-doi'
        key = (r['source_path'], other, number_key(r.get('target_doc') or ''))
        if key not in have:
            have.add(key)
            extra.append({**r, 'action': other, 'cum_tu': r.get('cum_tu')} if 'cum_tu' in r else {**r, 'action': other})
    return kept + extra
