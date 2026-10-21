"""Layer 4, validation: every extracted act must be grounded in the source before it can become an edge.

The model read the meaning (who acts, which act, which target). This layer checks evidence and consistency, no model call
(rules of 21/10/2026, docs/08 §8.11):
- the act is stated by a text that governs the unit (governance.performer): the unit itself, or the lead that opens the list the
  unit is an item of, outside inserted wording; the form of the model's quote alone rejects nothing;
- the evidence is the verbatim pieces of the quote found in the unit's frame, or, when the quote is not in the source, the governing
  sentence and the item naming the target, found by the code; each piece keeps its field and role in extract/<id>/evidence.json;
- an item of a list acts on the document it names first, not on one named inside that document's name;
- legal facts: not the name of a catalogue, a history note, a published list, the document itself; the competence to act on a law;
- the target document and every number of every position appear in the source the model read, else the act stays unresolved.
performed = false rows and acts the model gave to another actor (chu_the) are dropped before this layer.
"""

import re

from . import governance
from .governance import TTHC
from .relations import document_refs, strip_quotes
from .text import action_matches, number_key

# "Công bố (kèm theo Quyết định này) Danh mục thủ tục hành chính được sửa đổi, bổ sung, bãi bỏ …": the list is published; the act words
# name the list. The act is on a document only where a row or a sentence names that document.
ANNOUNCES = re.compile(r'\bcông\s+bố\b.{0,160}?\b(?:danh\s+mục|thủ\s+tục\s+hành\s+chính)\b', re.I | re.S)

# A word of another verb is not the verb of this act: 'bỏ' of "hủy bỏ" (huy-bo), 'sửa' of "sửa đổi", 'thay' of "thay đổi".
VERBS = {'sua-doi': r'sửa|điều\s+chỉnh', 'bo-sung': r'bổ\s*sung|thêm', 'bai-bo': r'b[ãả]i\s*bỏ|(?<!h[uủ][yỷ]\s)\bbỏ\b|hết\s+hiệu\s*lực|kết\s*thúc|chấm\s*dứt',
         'thay-the': r'thay\s*thế|\bthay\b(?!\s*đổi)', 'thay-cum-tu': r'\bthay\b(?!\s*đổi)|cụm\s+từ|từ\s+ngữ', 'huy-bo': r'h(?:uỷ|ủy|uy)\s*bỏ', 'dinh-chi': r'đình\s*chỉ',
         'ngung-hieu-luc': r'ng(?:ư|ừ)ng\s+(?:thi\s+hành\s+)?hiệu\s*lực|tạm\s+ngưng|tạm\s+dừng|chấm\s*dứt|kết\s*thúc', 'dinh-chinh': r'đính\s*chính|\bsửa\b(?!\s*đổi)',
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


# A history note, not this document's act: "… đã được sửa đổi, bổ sung tại Quyết định số …", "bị thay thế bởi Thông tư số …".
HISTORY = re.compile(r'\b(?:đã\s+)?(?:bị|được)\s+(?:sửa\s*đổi|bổ\s*sung|thay\s*thế|b[ãả]i\s*bỏ|h(?:uỷ|ủy|uy)\s*bỏ|đình\s*chỉ|đính\s*chính)'
                     r'(?:\s*,\s*(?:bổ\s*sung|thay\s*thế))?\s+(?:một\s+số\s+\S+\s+)?(?:bởi|tại|theo)\b', re.I)
PLANNED = re.compile(r'\b(?:cần|dự\s+kiến|đề\s+nghị|kiến\s+nghị)\s+(?:được\s+|phải\s+)?(?:sửa\s+đổi|bổ\s+sung|bãi\s+bỏ|thay\s+thế|ban\s+hành|xây\s+dựng)'
                     r'|thời\s+hạn\s+(?:thực\s+hiện|hoàn\s+thành|trình|ban\s+hành)|cơ\s+quan\s+chủ\s+trì|chương\s+trình\s+xây\s+dựng', re.I)


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
    if not own_type:
        return False  # the source's type is not known: the competence cannot be checked, which is no conflict
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
    The row must name its target; a list of work to do and a list of another body's procedures act on nothing. Who performs the act
    on the row (the row, the heading of a list of procedures, an act column, or the article acting on the listed documents) is
    governance.governing's."""
    unit, context = row['_unit'], row['_context']
    target = number_key(row.get('target_document') or '')
    if not governance.names(unit['noi_dung'], row.get('target_document') or ''):
        return 'reject', 'dong_bang_khong_neu_van_ban'
    # A list of procedures acts on the decision of the same body that published them. "Thủ tục … được công bố tại Quyết định số
    # 636/QĐ-LĐTBXH" in a provincial decision names the ministry's standard procedure, and "… quy định tại Thông tư số 29/2015/TT-BYT"
    # names its basis: a province neither amends nor repeals them.
    # A list of work to do ("Danh mục văn bản cần sửa đổi, bổ sung, ban hành mới", a column "Thời hạn thực hiện", "Cơ quan chủ trì"):
    # its rows name documents to be drafted later, not acts of this document (684851, 20/10/2026).
    if PLANNED.search(unit['cau_dan'] + ' ' + context.get('ten_dieu', '')):
        return 'reject', 'dong_bang_ke_hoach'
    own = issuer_code((context.get('van_ban') or {}).get('so_hieu') or '')
    if TTHC.search(unit['cau_dan'] + ' ' + context.get('ten_dieu', '') + ' ' + unit['noi_dung'][:300]) and own and issuer_code(target) not in ('', own):
        return 'reject', 'dong_bang_khac_co_quan'
    return None, None


def only_in_history(text, target):
    """Every mention of the target stands right after a note on the past ("đã được sửa đổi, bổ sung tại …", "bị thay thế bởi …")."""
    mentions = [m for m in document_refs(text) if number_key(m.group()) == target]
    notes = list(HISTORY.finditer(text))
    return bool(mentions) and all(any(0 <= m.start() - h.end() <= 80 and not re.search(r'[.;\n]', text[h.end():m.start()]) for h in notes)
                                  for m in mentions)


def check(row, resolved):
    """(verdict, reason): verdict is 'reject', 'unresolved' or 'ok'. Sets resolved['evidence'] to the verbatim evidence and
    resolved['_bang_chung'] to its pieces (field, text, role)."""
    verb = VERBS.get(row['action'])
    target = number_key(row.get('target_document') or '')
    unit = row['_unit']
    acting = row.get('_performer')
    if resolved.get('resolution_reason') == 'khong_xac_dinh_van_ban_dich':
        return 'reject', 'khong_co_van_ban_dich'  # "các quy định trái với …", a catalogue: no document to link
    if not acting:
        # The verb stands only inside quoted wording: the act belongs to the text inserted into the target, not to this document.
        inside = verb and any(re.search(verb, t or '', re.I) for t in (unit['noi_dung'], unit['cau_dan']))
        return 'reject', 'trong_noi_dung_moi' if inside else 'chua_co_cau_thuc_hien'
    field, sentence, kind, tied = acting
    if kind in ('lead', 'holder'):
        # The act is the lead's own ("Sửa đổi, bổ sung Mục II Phụ lục … như sau:" over its new wording; "Bãi bỏ các văn bản tại Phụ
        # lục II" for the rows of that appendix): its source unit is the unit that holds the lead.
        holder = row['_context'].get('_dieu_thuc_hien') if kind == 'holder' else None
        row['source_path'] = holder['source_path'] if holder else governance.owner(row['source_path'], field)
        resolved.update(source_path=row['source_path'], source_in_phu_luc=row['source_path'].startswith('Phụ lục'))
    found = governance.pieces(row.get('evidence') or '', row, governance.allowed(row))
    if found is None:
        # The quote is not in the source, not even in pieces: the evidence is what the code finds, the governing sentence and,
        # when it is a lead, the item that names the target.
        found = [{'field': field, 'text': ' '.join(sentence.split())}]
        item = governance.target_snippet(row) if kind in ('list', 'holder') else None
        if item:
            found.append({'field': 'don_vi', 'text': item})
    evidence = ' … '.join(p['text'] for p in found)
    resolved['evidence'] = evidence[:2000]
    resolved['_bang_chung'] = [{'truong': p['field'], 'doan': p['text'][:400], 'vai_tro': governance.role(p, verb, target)} for p in found]
    resolved['_bang_chung'].insert(0, {'truong': field, 'doan': ' '.join(sentence.split())[:400], 'vai_tro': 'cau_thuc_hien'})
    named = row.get('target_document') or ''
    if kind == 'list' and target and not governance.acts_on(unit['noi_dung'], named) and not governance.listed(row, named):
        return 'reject', 'dich_khong_phai_doi_tuong'  # "Bãi bỏ các văn bản sau: 1. Quyết định X về sửa đổi … Quyết định Y": Y is X's name
    # Words after the first document number are that document's name ("… Quyết định số 3577/QĐ-UBND về công bố Danh mục …").
    first = next(iter(document_refs(sentence)), None)
    stated = sentence[:first.start()] if first else sentence
    if target and only_in_history(unit['noi_dung'] + '\n' + sentence, target):
        return 'reject', 'ghi_chu_lich_su'  # "… Quyết định X đã được sửa đổi tại Quyết định Y": Y is named only in a note on the past
    if catalogue_name(stated):
        return 'reject', 'ten_danh_muc'
    if HISTORY.search(sentence) and not re.search(verb, HISTORY.sub(' ', strip_quotes(sentence)), re.I):
        return 'reject', 'ghi_chu_lich_su'
    if ' STT ' in row['source_path']:
        verdict, reason = table_row(row, evidence)
        if verdict:
            return verdict, reason
        resolved.update(source_path=row['source_path'], source_in_phu_luc=row['source_path'].startswith('Phụ lục'))
    if ANNOUNCES.search(stated) and not governance.names(sentence, row.get('target_document') or ''):
        return 'reject', 'cong_bo_danh_muc'
    texts = sources(row)
    whole = '\n'.join(texts)
    own = number_key((row['_context'].get('van_ban') or {}).get('so_hieu') or '')
    if own and own in (target, number_key(resolved.get('target_doc') or '')):
        return 'reject', 'chinh_van_ban_nguon'
    target_text = resolved.get('target_doc') or ''
    if row['action'] in ('sua-doi', 'bo-sung', 'bai-bo', 'thay-the', 'huy-bo', 'thay-cum-tu') and above(row, target_text):
        return 'reject', 'vuot_tham_quyen'
    if row['action'] in ('huong-dan', 'quy-dinh-chi-tiet') and not guides(row, evidence):
        return 'reject', 'dan_chieu_khong_phai_huong_dan'
    if resolved['resolution_status'] == 'validated' and not tied:
        # A sentence states the act, but nothing in the structure ties it to this target: a candidate to resolve, not an edge.
        named = governance.names(whole, ' '.join((row.get('target_document') or '').split())) or governance.names(whole, target_text)
        return 'unresolved', 'dich_chua_gan_cau_thuc_hien' if named else 'van_ban_dich_khong_co_trong_nguon'
    if resolved['resolution_status'] == 'validated':
        if re.match(r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s', target_text):
            name = target_text.split(' ', 1)[1] if ' ' in target_text else target_text
            if name.casefold() not in ' '.join(whole.split()).casefold():
                return 'unresolved', 'van_ban_dich_khong_co_trong_nguon'
        elif number_key(target_text) not in {number_key(m.group()) for m in document_refs(whole)} and number_key(target_text) not in number_key(whole):
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
        actor = row.get('chu_the') or 'van_ban_nay'
        if actor != 'van_ban_nay':
            # A proposal, a task for another body, a retold act or a quotation: the document does not act itself (P1, 20/10/2026).
            rejected.append({'source_path': row['source_path'], 'action': row['action'], 'target_document': row['target_document'],
                             'reason': f'chu_the_{actor}', 'evidence': (row.get('evidence') or '')[:300]})
            continue
        # Who performs the act on this unit, from the structure: the resolver reads the act's object from it, the check its evidence.
        row['_performer'] = governance.performer(row, VERBS.get(row['action']), ' '.join((row.get('target_document') or '').split()))
        resolved = resolve_row(row)
        verdict, reason = check(row, resolved)
        if verdict == 'reject':
            rejected.append({'source_path': row['source_path'], 'action': row['action'], 'target_document': row['target_document'],
                             'reason': reason, 'evidence': (row.get('evidence') or '')[:300]})
            continue
        if verdict == 'unresolved' and resolved['resolution_status'] == 'validated':
            resolved.update(resolution_status='unresolved', resolution_reason=reason)
        kept.append(resolved)
    return pair_amendments(distinct(kept)), rejected


def distinct(kept):
    """Two readings that moved to the same unit (the lead's act read on each of its items, a row's act moved to the article acting
    on its list) are one act, kept once. A record kept for review never hides a checked one: the validated reading is kept."""
    unique, seen = [], {}
    for r in kept:
        k = (r['source_path'], r['action'], number_key(r.get('target_doc') or ''), tuple(r.get('vi_tri') or []), r.get('doi_tuong'))
        if k not in seen:
            seen[k] = len(unique)
            unique.append(r)
        elif r['resolution_status'] == 'validated' and unique[seen[k]]['resolution_status'] != 'validated':
            unique[seen[k]] = r
    return unique


def pair_amendments(kept):
    """"Sửa đổi, bổ sung X" is two acts, sua-doi and bo-sung (settled 14/10/2026): the second is added when the model gave only one."""
    have = {(r['source_path'], r['action'], number_key(r.get('target_doc') or '')) for r in kept}
    extra = []
    for r in kept:
        # A note on the past ("… đã được sửa đổi, bổ sung tại …") inside the quote states no pair of this document's acts.
        if r['action'] not in ('sua-doi', 'bo-sung') or not re.search(r'sửa\s*đổi\s*,?\s*(?:và\s+)?bổ\s*sung', HISTORY.sub(' ', strip_quotes(r.get('evidence') or '')), re.I):
            continue
        other = 'bo-sung' if r['action'] == 'sua-doi' else 'sua-doi'
        key = (r['source_path'], other, number_key(r.get('target_doc') or ''))
        if key not in have:
            have.add(key)
            extra.append({**r, 'action': other, 'cum_tu': r.get('cum_tu')} if 'cum_tu' in r else {**r, 'action': other})
    return kept + extra
