"""Effective dates, affected positions and time semantics of relations, read from the source text."""

import calendar
from datetime import date, timedelta
import re

from .structure import unquoted

DATE = r'(\d{1,2})\s*(?:tháng|/|-|\.)\s*(\d{1,2})\s*(?:năm|/|-|\.)\s*(\d{4})'
SUBJECT = (r'(?:Thông\s+tư\s+liên\s+tịch|Thông\s+tư|Nghị\s+định|Nghị\s+quyết\s+liên\s+tịch|Nghị\s+quyết|Quyết\s+định|Bộ\s+luật|Luật|Hiến\s+pháp'
           r'|Pháp\s+lệnh|Chỉ\s+thị|Văn\s+bản|Kế\s+hoạch|Thông\s+báo|Hướng\s+dẫn|Công\s+văn|Lệnh|Sắc\s+lệnh|Công\s+điện|Thông\s+tri)')
EFFECT = r'\bcó\s+hiệu\s+lực(?:\s+thi\s+hành)?\s*(?P<rest>[^\n]{0,160})'


def own_subject(legal_type):
    """How the document names itself: its own type ("Thông tư (liên tịch)") or "Văn bản"; any type when the type is unknown.
    A công văn quoting "Luật này có hiệu lực …" is speaking about the law, not about itself."""
    words = r'\s+'.join(re.escape(w) for w in (legal_type or '').split()[:2])
    return rf'(?:{words}(?:\s+liên\s+tịch)?|Văn\s+bản)' if words else SUBJECT


def statements(legal_type):
    subject = own_subject(legal_type)
    # "Thông tư (liên tịch) này ... (và) có hiệu lực ...", including "Nghị quyết này đã được HĐND ... thông qua ngày ... và có hiệu lực ..."
    return [re.compile(subject + r'(?:\s+[^\s.;:,]+){0,2}?\s+này\b[^.;\n]{0,300}?' + EFFECT, re.I),
            # "Điều 3. Quyết định có hiệu lực kể từ ngày ký." (the document's own type opening the sentence, without "này")
            re.compile(r'(?:^|\.\s+)(?:Điều\s+\d+\w*[.:]\s*)?(?:\d+\.\s*)?' + subject + r'\s+' + EFFECT, re.I)]
TEMPORAL_EFFECT = {'bai-bo': 've_sau', 'huy-bo': 'tu_dau', 'sua-doi': 've_sau', 'bo-sung': 've_sau', 'thay-the': 've_sau',
                   'thay-cum-tu': 've_sau', 'dinh-chi': 'tam_ngung', 'huong-dan': 'khong_ap_dung', 'quy-dinh-chi-tiet': 'khong_ap_dung',
                   # A corrected text counts as right from the start; a halt reuses the suspension period; an extension moves the end.
                   'dinh-chinh': 'tu_dau', 'ngung-hieu-luc': 'tam_ngung', 'gia-han': 've_sau',
                   # A consolidated text restates other documents; it changes none of them.
                   'hop-nhat': 'khong_ap_dung'}
SUSPENSIONS = ('dinh-chi', 'ngung-hieu-luc')
UNIT = r'(?:điểm|khoản|điều|chương|mục|phụ\s+lục|tên|mẫu)'


def to_date(day, month, year):
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def when(rest, issued, sentence=''):
    """(date, base, days) that a "... có hiệu lực <rest>" clause sets.

    base is the day the clause counts from (ngay_ky, ngay_thong_qua, ngay_dang_cong_bao) or ngay_cu_the;
    days is the stated offset ("sau 45 ngày" -> 45, "kể từ ngày ký" -> 0). The date is None when the base day is unknown.
    """
    rest = rest.strip()
    days = r'(?:sau\s+(\d+)\s*(?:\([^)]*\))?\s*ngày,?\s+)?(?:kể\s+)?từ\s+ngày\s+'
    passed = re.search(r'thông\s+qua\s+(?:vào\s+)?ngày\s+' + DATE, sentence, re.I)  # the effect clause first, then the closing line
    passed = to_date(*passed.groups()) if passed else issued
    explicit = re.match(r'(?:thi\s+hành\s+)?(?:kể\s+)?từ\s+(?:ngày\s+)?' + DATE, rest, re.I)
    if explicit:
        return to_date(*explicit.groups()), 'ngay_cu_the', None

    def plus(day, offset):
        return (date.fromisoformat(day) + timedelta(days=int(offset or 0))).isoformat() if day else None
    gazette = re.match(r'(?:thi\s+hành\s+)?' + days + r'(?:đăng|được\s+đăng)\s+(?:trên\s+)?công\s+báo', rest, re.I)
    if gazette:
        return None, 'ngay_dang_cong_bao', int(gazette[1] or 0)
    signed = re.match(r'(?:thi\s+hành\s+)?' + days + r'(?:ký|ban\s+hành)', rest, re.I)
    if signed and issued:
        return plus(issued, signed[1]), 'ngay_ky', int(signed[1] or 0)
    adopted = re.match(r'(?:thi\s+hành\s+)?' + days + r'(?:được\s+)?(?:(?:HĐND|Hội\s+đồng\s+nhân\s+dân)[^.;]{0,60}?\s)?thông\s+qua', rest, re.I)
    if adopted and passed:
        return plus(passed, adopted[1]), 'ngay_thong_qua', int(adopted[1] or 0)
    return None, 'khong_doc_duoc', None


def provision_led(line, start):
    """Is the subject at `start` led by a provision ("Khoản 3 Điều 2 Thông tư này có hiệu lực …")? Then it dates that provision only."""
    # "Điều 5. Thông tư này …" is the article heading, not a provision leading the subject.
    return bool(re.search(r'\b(?:điểm|khoản|điều|chương|mục)\s+\w+(?:\.\d+)*\s+(?:của\s+)?$', line[max(0, start - 60):start], re.I))


def effective_date(text, legal_type, issued, is_normative=None):
    """{ngay_hieu_luc, ngay_hieu_luc_cach, ngay_hieu_luc_so_ngay, ngay_hieu_luc_trich} from the document's own effect clause.
    Quoted amendment text is skipped: it states the effect of another document."""
    none = {'ngay_hieu_luc': None, 'ngay_hieu_luc_so_ngay': None, 'ngay_hieu_luc_trich': None}
    if legal_type == 'Văn bản hợp nhất':
        return {**none, 'ngay_hieu_luc_cach': 'van_ban_hop_nhat'}
    lines = text.split('\n')
    found = None
    patterns = statements(legal_type)
    # "… kỳ họp thứ 10 thông qua ngày 04 tháng 12 năm 2014": the passing day is often in the closing line, not the effect clause.
    passing = list(re.finditer(r'thông\s+qua\s+(?:vào\s+)?ngày\s+' + DATE, text, re.I))
    passing = passing[-1].group() if passing else ''
    for line, visible in zip(lines, unquoted(lines)):
        if not visible:
            continue
        # A quotation opened on this line (closed here or later) is amendment text, not this document speaking.
        line = re.sub(r'“[^”]*”|"[^"]*"', ' ', line).split('“')[0]
        for match in (m for pattern in patterns for m in pattern.finditer(line)):
            if provision_led(line, match.start()) or re.search(r'(?:sau|trước|từ|đến)\s+ngày\s*$', line[:match.start()], re.I):
                continue  # "… sau ngày Thông tư này có hiệu lực thi hành thì …" refers to the effect; it does not set it
            value, how, offset = when(match['rest'], issued, match.group() + ' ' + passing)
            row = {'ngay_hieu_luc': value, 'ngay_hieu_luc_cach': how, 'ngay_hieu_luc_so_ngay': offset,
                   'ngay_hieu_luc_trich': match.group().strip()[:300]}
            if value:
                return row
            if found is None or (found['ngay_hieu_luc_cach'] == 'khong_doc_duoc' and how != 'khong_doc_duoc'):
                found = row
    if found:
        return found
    # Taking the issuance date without an effect clause is a guess: only for documents known not to be normative.
    if issued and is_normative is False:
        return {**none, 'ngay_hieu_luc': issued, 'ngay_hieu_luc_cach': 'mac_dinh_ngay_ban_hanh'}
    return {**none, 'ngay_hieu_luc_cach': 'khong_tim_thay'}


LABEL = {'điểm': r'(?:[a-zđ]\w?|\d+(?:\.\d+)+)', 'khoản': r'\d+[a-zđ]?', 'điều': r'\d+[a-zđ]?'}
ORDINALS = {'nhất': 1, 'một': 1, 'hai': 2, 'ba': 3, 'tư': 4, 'bốn': 4, 'năm': 5, 'sáu': 6, 'bảy': 7, 'tám': 8, 'chín': 9, 'mười': 10}
# A dash item inside a point (tiết, gạch đầu dòng): "gạch đầu dòng thứ ba điểm b" names sub-point 3 of point b.
SUB_POINT = re.compile(r'(?:dấu\s+)?(?:gạch\s+đầu\s+dòng|gạch\s+ngang|tiết)\s+(?:thứ\s+)?(\d+|' + '|'.join(ORDINALS) + r')\b\s*(?:(?:của|tại|thuộc)\s+)?', re.I)
# Smaller parts with no node of their own: the position stops at the provision that holds them ("đoạn 3, điểm a, khoản 2, Điều 4").
WITHIN = re.compile(r'(?:(?:dấu\s+)?(?:gạch\s+đầu\s+dòng|gạch\s+ngang|tiết)|câu|đoạn|dòng)\s+(?:thứ\s+)?(?:\d+|' + '|'.join(ORDINALS)
                    + r'|đầu|cuối)\b\s*,?\s*(?:(?:của|tại|thuộc)\s+)?(?=(?:khoản|điều|điểm)\b)'
                    # A Roman-numbered section or a "tiết 3.5" inside an article ("điểm b tiết 3.5, mục III, Điều 1") has no node either.
                    + r'|(?:mục\s+[IVXLCDM]+|tiết\s+\d+(?:\.\d+)+)\s*,\s*(?:(?:của|tại|thuộc)\s+)?(?=điều\s+\d)', re.I)
# Label of a section: Roman or Arabic number, or a capital, with decimals ("III", "6", "D.2"); never a word ("mục tiêu").
SECTION = r'(?:[IVXLCDM]+|\d+|[A-Z])(?:\.\w+)*\b'
# A section written with commas before what holds it ("Mục I, Phần I Phụ lục", "Mục 2, Chương III") is one position.
SECTION_CHAIN = re.compile(r'\b((?:mục|tiết)\s+' + SECTION + r')\s*,\s*(?:(?:của|tại|thuộc)\s+)?(?=(?:phần|chương|phụ\s+lục)\b)'
                           r'|\b(phần\s+' + SECTION + r')\s*,\s*(?:(?:của|tại|thuộc)\s+)?(?=phụ\s+lục\b)', re.I)
# Label chain of sections, up to the appendix that holds them: "Mục D.2 của Phụ lục I" -> "Mục D.2 Phụ lục I".
CHAIN = re.compile(r'(?:mục|chương|phần)\s+' + SECTION + r'(?:\s+(?:của\s+|thuộc\s+)?(?:mục|chương|phần)\s+' + SECTION + r')*'
                   r'(?:\s+(?:của\s+|thuộc\s+|tại\s+)?phụ\s+lục(?:\s+(?:số\s+)?(?:[IVXLCDM]+|\d+[A-Za-z]?)\b)?)?', re.I)
# The same chain when it ends at an appendix ("Mục I Phần I Phụ lục", "Mục 6 Phụ lục III"), after levels().
IN_APPENDIX = re.compile(r'\b(?:mục|phần)\s+' + SECTION + r'(?:\s+(?:của\s+|thuộc\s+)?(?:mục|chương|phần)\s+' + SECTION + r')*'
                         r'\s+(?:của\s+|thuộc\s+|tại\s+)?phụ\s+lục(?:\s+(?:số\s+)?(?:[IVXLCDM]+|\d+[A-Za-z]?)\b)?', re.I)


def ordinal(word):
    return int(word) if word.isdigit() else ORDINALS[word.casefold()]


def sub_points(text):
    """'gạch đầu dòng thứ ba điểm b khoản 3 Điều 17' -> 'tiểu điểm 3 điểm b khoản 3 Điều 17'; a dash item of a clause
    or an article ('gạch đầu dòng thứ hai khoản 3') stays at that clause or article."""
    text = SUB_POINT.sub(lambda m: f'tiểu điểm {ordinal(m[1])} ' if re.match(r'điểm\b', text[m.end():], re.I) else m.group(), text)
    return WITHIN.sub('', text)


# Parts that have no node (contract 9.5, decisions C3, C4, E1): a form, a paragraph, a sentence, a dash item of a clause, a "tiết",
# a row of a list. Their position is the node that holds them; the part itself is kept in chi_tiet_vi_tri.
FINER = re.compile(r'\b(?:mẫu(?:\s+biểu)?\s+(?:số\s+)?[\w./-]*\d[\w./-]*'
                   r'|(?:câu|đoạn|dòng|tiết|gạch\s+đầu\s+dòng|gạch\s+ngang)\s+(?:thứ\s+)?(?:\d+|nhất|hai|ba|tư|bốn|năm|sáu|bảy|tám|chín|mười|đầu|cuối)'
                   r'|(?:số\s+thứ\s+tự|stt)\s+\d+[a-zđ]?(?:\s*(?:,|và|đến|-)\s*\d+[a-zđ]?)*)', re.I)


def finer_parts(text):
    """The parts without a node named in a position text, as written: "Mẫu số 01 Phụ lục I" -> ["Mẫu số 01"]. A dash item of a point
    is a node (tiểu điểm) and is not one of them."""
    plain = re.sub(r'(?:dấu\s+)?(?:gạch\s+đầu\s+dòng|gạch\s+ngang|tiết)\s+(?:thứ\s+)?\S+\s+(?=(?:của\s+|tại\s+|thuộc\s+)?điểm\b)', ' ', text or '', flags=re.I)
    return list(dict.fromkeys(' '.join(m.group().split()) for m in FINER.finditer(plain)))


def levels(text):
    """One position written with commas between its levels, joined: "điểm a, khoản 2, Điều 4" -> "điểm a khoản 2 Điều 4",
    "Mục I, Phần I Phụ lục" -> "Mục I Phần I Phụ lục". Parts without a node of their own are dropped first (sub_points)."""
    text = sub_points(re.sub(r'\s+', ' ', text or '').strip(' .;:'))
    text = re.sub(r'\b(điểm\s+[a-zđ]\w?)\s*,\s*(khoản\s+\d+[a-zđ]?)\s*,\s*(điều\s+\d+[a-zđ]?)\b', r'\1 \2 \3', text, flags=re.I)
    # "điểm a, khoản 16 Điều 2": one point of one clause, not the point and its clause. A list goes on with another label of the
    # same level ("điểm a, b khoản 2", "khoản 1, khoản 2 Điều 3") and is left alone.
    text = re.sub(r'(?<![,\w])(điểm\s+[a-zđ]\w?(?:\s*(?:,|và)\s*(?:điểm\s+)?[a-zđ]\w?\b(?!\s+khoản))*)\s*,\s*(khoản\s+\d+[a-zđ]?)'
                  r'(?=\s+điều\s+\d|\s*(?:[;.]|$))', r'\1 \2', text, flags=re.I)
    return SECTION_CHAIN.sub(lambda m: (m[1] or m[2]) + ' ', text)


def labels(text, kind):
    """'1, 7 và 8a' -> ['1', '7', '8a']; a word that is not a label of this kind is dropped, never turned into one."""
    items = re.split(r'\s*(?:,|\bvà\b)\s*(?:(?:các\s+)?(?:điểm|khoản|điều)\s+)?', text.strip(), flags=re.I)
    return [x for x in items if re.fullmatch(LABEL[kind], x, re.I)]


def heading(text):
    """'tên mục 2 chương II' -> 'tên Mục 2 Chương II'."""
    return re.sub(r'\b(chương|mục|phần|điều|phụ\s+lục)\b', lambda m: m[1][0].upper() + m[1][1:], text, flags=re.I)


def positions(text, context=None):
    """Expand a location list into single positions, each naming its Điều.

    "các khoản 1, 7, 8a Điều 3" -> khoản 1/7/8a Điều 3; "khoản 10, khoản 11 Điều 3" -> both of Điều 3;
    "các khoản 3, 7 và tên Điều 50" -> khoản 3/7 Điều 50 and tên Điều 50; "điểm d, khoản 1, điều 1" -> one position.
    context = (clause, article) of the lead sentence fills levels the list leaves out ("tại điểm a" under "khoản 3 Điều 2").
    """
    text = levels(text)
    text = re.sub(r'^(khoản\s+\d+[a-zđ]?)\s*,\s*(điều\s+\d+[a-zđ]?)$', r'\1 \2', text, flags=re.I)
    groups = []
    for group in re.split(r'\s*;\s*', text):
        # "khoản 2 Điều 7 của Thông tư số 85/2014/TT-BGTVT": the position ends before the document it belongs to.
        group = re.split(r'\s+(?:của|thuộc)\s+(?=(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Nghị\s+định|Nghị\s+quyết|Thông\s+tư|Quyết\s+định|Chỉ\s+thị|[Vv]ăn\s+bản|Quy\s+định|Quy\s+chế)\b)', group, maxsplit=1)[0]
        items = []
        for part in re.split(r'\s*,\s*(?=(?:các\s+)?' + UNIT + r'\b)|\s+và\s+(?=(?:các\s+)?' + UNIT + r'\b)', group, flags=re.I):
            part = re.sub(r'^(?:và\s+)?(?:(?:các\s+)?(?:quy\s+định|nội\s+dung)(?:\s+quy\s+định)?\s+)?(?:tại\s+)?(?:các\s+)?', '', part.strip(), flags=re.I)
            # "điểm b khoản 1 Điều 19 Quy định về quản lý …": a provision ends at its article; the words after it name the document.
            ends = re.match(r'(?:điểm|khoản|điều)\b.*?\bđiều\s+\d+[a-zđ]?\b', part, re.I)
            part = ends.group() if ends else part
            name = re.fullmatch(r'tên\s+(?:mục\s+\d+\s+)?(?:chương\s+[IVXLCDM\d]+|điều\s+\d+[a-zđ]?|phụ\s+lục\s+[IVXLCDM\d]+)|tên\s+mục\s+\d+', part, re.I)
            sub = re.fullmatch(r'tiểu\s+điểm\s+(\d+)\s+điểm\s+([a-zđ]\w?)\s+khoản\s+(\d+[a-zđ]?)\s+điều\s+(\d+[a-zđ]?)', part, re.I)
            point = re.fullmatch(r'điểm\s+(.+?)(?:\s+khoản\s+(\S+))?(?:\s+điều\s+(\S+))?', part, re.I)
            clause = re.fullmatch(r'khoản\s+(.+?)(?:\s+điều\s+(\S+))?', part, re.I)
            article = re.fullmatch(r'điều\s+(.+)', part, re.I)
            numbered = lambda label: label if label and re.fullmatch(r'\d+[a-zđ]?', label, re.I) else None  # "Điều này" names no number
            if sub:
                items.append(['ten', f'tiểu điểm {sub[1]} điểm {sub[2].lower()} khoản {sub[3]} Điều {sub[4]}', None, None])
            elif name:
                items.append(['ten', heading(part), None, None])
            elif point:
                point = [point[0], point[1], point[2] if numbered(point[2]) or point[2] is None else None, numbered(point[3])]
                items += [['diem', p, point[2], point[3]] for p in labels(point[1], 'điểm')]
            elif clause:
                items += [['khoan', k, None, numbered(clause[2])] for k in labels(clause[1], 'khoản')]
            elif article:
                items += [['dieu', a, None, None] for a in labels(article[1], 'điều')]
            elif re.match(r'toàn\s+(?:bộ|văn)', part, re.I):
                items.append(['ten', 'toàn bộ', None, None])
            elif re.match(r'mẫu\b', part, re.I):
                # A form has no node: the position is the appendix that holds it, or "Phụ lục" when the sentence names none.
                appendix = re.search(r'phụ\s+lục\s+(?:số\s+)?([IVXLCDM]+|\d+[A-Za-z]?)\b', part, re.I)
                items.append(['ten', f'Phụ lục {appendix[1]}' if appendix else 'Phụ lục', None, None])
            elif re.match(UNIT + r'\b', part, re.I):
                # "Phụ lục IV ban hành kèm theo Thông tư số …": the position ends before what it belongs to,
                # but a section keeps the appendix that holds it ("Mục D.2 của Phụ lục I").
                part = re.split(r'\s+(?:ban\s+hành|kèm\s+theo|(?:của|tại|thuộc)(?!\s+(?:mục|chương|phần|phụ\s+lục)\b))\b', part, maxsplit=1, flags=re.I)[0]
                part = re.sub(r'^(phụ\s+lục)\s+số\s+', r'\1 ', part, flags=re.I)
                # "Mục 1 Chương IV Quy định kỹ thuật …": the position is the label chain, not the name after it.
                chain = CHAIN.match(part)
                label = re.sub(r'\s+(?:của|thuộc|tại)\s+', ' ', chain.group()) if chain else part
                items.append(['ten', heading(label), None, None])
        groups.append(items)
    # "điểm a, điểm b khoản 3; điểm a khoản 5 và điểm a khoản 6 Điều 3": a group that names no article takes the one of the group after it.
    found, later = [], None
    for items in reversed(groups):
        # A trailing "Điều N" (and "khoản N" for points) belongs to every earlier item that names none.
        clause_of_point, article = context if context else (None, None)
        article = later or article
        for item in reversed(items):
            kind, label, clause_label, article_label = item
            if kind == 'ten' and re.search(r'Điều\s+(\S+)$', label):
                article = re.search(r'Điều\s+(\S+)$', label)[1]
            elif kind == 'dieu':
                article = label
            elif kind in ('khoan', 'diem'):
                item[3] = article_label = article_label or article
                article = article_label
                if kind == 'khoan':
                    clause_of_point = label
                else:
                    # "điểm a và điểm b khoản 2 Điều 11": the earlier point takes the clause of the later one.
                    item[2] = clause_of_point = clause_label or clause_of_point
        later = article if any(i[0] in ('dieu', 'khoan', 'diem') for i in items) else later
        group = []
        for kind, label, clause_label, article_label in items:
            if kind == 'ten':
                group.append(label)
            elif kind == 'dieu':
                group.append(f'Điều {label}')
            elif kind == 'khoan' and article_label:
                group.append(f'khoản {label} Điều {article_label}')
            elif kind == 'diem' and clause_label and article_label:
                group.append(f'điểm {label} khoản {clause_label} Điều {article_label}')
        found = group + found
    return list(dict.fromkeys(found))


LISTED = (r'\b(?:tại|ở)\s+((?:các\s+)?' + UNIT + r'\b.*?)'
          # The list ends at punctuation that no further label follows, or where the sentence goes on to the change itself.
          r'(?=\s*[,;.:](?!\s*(?:và\s+)?(?:các\s+)?(?:' + UNIT + r'\b|\d|[a-zđ](?:\s|,|$)))'
          r'|\s+(?:bỏ|bổ\s+sung|sửa|đính\s+chính|thay|thêm|của|thuộc|ban\s+hành|Quyết\s+định|Thông\s+tư|Nghị\s+định|Nghị\s+quyết|Luật|Quy\s+định)\b|$)')


def stated_positions(text, context=None):
    """Every location listed after "tại"/"ở" in a declaration (quotes already removed):
    "Tại điểm b khoản 7 Điều 3 và khoản 2 Điều 6, bỏ dấu …; … tại khoản 4 Điều 8" -> all three."""
    found = []
    for match in re.finditer(LISTED, text, re.I | re.S):
        found += positions(match[1], context)
    return list(dict.fromkeys(found))


def phrase_change(unit, context=None):
    """Each "thay (thế) cụm từ “X” bằng “Y” tại ..." in the unit: [{cu, moi, vi_tri}] with its own locations, and all locations.

    "thay cụm từ “cấp huyện” bằng “cấp xã” tại A; thay từ “huyện” bằng từ “xã” tại B" gives cấp huyện→cấp xã at A only.
    """
    starts = [m.start() for m in re.finditer(r'\bthay\s+(?:thế\s+)?(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ|từ)\b', unit, re.I)] or [0]
    pairs, everywhere = [], []
    for begin, end in zip(starts, starts[1:] + [len(unit)]):
        segment = unit[begin:end]
        olds, found, last = [], [], 0
        for quote in re.finditer(r'[“"]([^”"]*)[”"]', segment):
            if re.search(r'\b(?:tại|ở|trong)\s+(?:cột|dòng|hàng|ô|tiêu\s+đề)\s*$', segment[last:quote.start()], re.I):
                last = quote.end()
                continue  # "tại cột “Tên tiêu chí”" names where, not a wording to replace
            if re.search(r'\b(?:bằng|thành)\b', segment[last:quote.start()], re.I) and olds:  # "thay cụm từ “X” thành cụm từ “Y”"
                found += [(old, quote[1].strip()) for old in olds]
                olds = []
            else:
                olds.append(quote[1].strip())
            last = quote.end()
        plain = re.sub(r'“[^”]*”|"[^"]*"', ' ', segment)
        plain = re.sub(r'\s*\((?:đã\s+)?được\s+[^()]*\)', '', plain)
        # The list ends where the sentence names what the provisions belong to ("… của Quy định ban hành kèm theo Thông tư …").
        # The place starts at a unit ("ở Mục D.2 của Phụ lục I"); "tại cột “Điểm tối đa”" is a column, not a place of its own.
        where = re.search(r'\b(?:tại|ở|trong)\s+((?:các\s+)?' + UNIT + r'\b.+?)(?:\s+(?:của|thuộc)\s+(?!(?:các\s+)?(?:điểm|khoản|điều|mục|chương|phần|phụ\s+lục)\b)'
                          r'|\s+ban\s+hành\s+kèm\s+theo\b|\.\s*$|$)', plain, re.I | re.S)
        places = positions(where[1], context) if where else []
        if not places and re.search(r'toàn\s+(?:bộ|văn)', plain, re.I):
            places = ['toàn bộ']
        pairs += [{'cu': old, 'moi': new, 'vi_tri': places} for old, new in found]
        everywhere += places
    return pairs + deleted_phrases(unit, context), list(dict.fromkeys(everywhere))


OWNER = re.compile(r'\s+(?:(?:của|thuộc)\s+)?(?:Quyết\s+định|Nghị\s+định|Thông\s+tư|Nghị\s+quyết|Quy\s+định|Quy\s+chế)\b'
                   r'(?:\s+(?:này|(?:ban\s+hành\s+)?kèm\s+theo(?:\s+(?:Quyết\s+định|Nghị\s+định|Thông\s+tư|Nghị\s+quyết))?))?(?=[\s,;.]|$)')
DELETES = re.compile(r'\b(?:bãi\s+)?bỏ\s+(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ|từ)\b', re.I)


def deleted_phrases(unit, context=None):
    """Each "bỏ cụm từ “X” tại …" in the unit: [{cu: X, moi: '', vi_tri}], each phrase with the places written after it (R4,
    27/10/2026: an empty moi is a phrase removed). "Bỏ cụm từ “A” tại Điều 6, cụm từ “B” tại Điều 9" gives A at Điều 6, B at Điều 9;
    a phrase with no place of its own takes the next one written ("cụm từ “A”, “B” tại Điều 6")."""
    marks = [m.start() for m in DELETES.finditer(unit)]
    ends = sorted(set(marks + [m.start() for m in re.finditer(r'\bthay\s+(?:thế\s+)?(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ|từ)\b', unit, re.I)] + [len(unit)]))
    pairs = []
    for begin in marks:
        segment = unit[begin:next(e for e in ends if e > begin)]
        quotes = list(re.finditer(r'[“"]([^”"]*)[”"]', segment))
        waiting = []
        for n, quote in enumerate(quotes):
            waiting.append(quote[1].strip())
            tail = re.sub(r'“[^”]*”|"[^"]*"', ' ', segment[quote.end():quotes[n + 1].start() if n + 1 < len(quotes) else len(segment)])
            # "tại Điều 2 của Quyết định, Điều 13 và khoản 2 Điều 16 Quy định kèm theo Quyết định": the owners are not where the list ends.
            tail = OWNER.sub(' ', tail)
            where = re.search(r'\b(?:tại|ở|trong)\s+((?:các\s+)?' + UNIT + r'\b.+?)(?:\s+(?:của|thuộc)\s+(?!(?:các\s+)?(?:điểm|khoản|điều|mục|chương|phần|phụ\s+lục)\b)'
                              r'|\s+ban\s+hành\s+kèm\s+theo\b|,\s*(?:và\s+)?(?:cụm\s+)?từ\b|\s*;|\.\s*$|$)', tail, re.I | re.S)
            places = positions(where[1], context) if where else (['toàn bộ'] if re.search(r'toàn\s+(?:bộ|văn)', tail, re.I) else [])
            if places:
                pairs += [{'cu': old, 'moi': '', 'vi_tri': places} for old in waiting if old]
                waiting = []
        pairs += [{'cu': old, 'moi': '', 'vi_tri': []} for old in waiting if old]
    return pairs


def suspension(unit):
    """Start/end of a suspension declared in the unit; the start defaults to the source's effective date later."""
    start = re.search(r'(?:kể\s+)?từ\s+ngày\s+' + DATE, unit, re.I)
    end = re.search(r'(?:đến|tới)\s+(?:hết\s+)?ngày\s+' + DATE, unit, re.I)
    until = re.search(r'(?:cho\s+)?(?:đến|tới)\s+khi\s+([^.;\n]{3,200})', unit, re.I)
    span = re.search(r'trong\s+(?:thời\s+hạn\s+)?(\d+)\s+(ngày|tháng)', unit, re.I)
    return {'dinh_chi_tu_ngay': to_date(*start.groups()) if start else None,
            'dinh_chi_den_ngay': to_date(*end.groups()) if end else None,
            'dinh_chi_den_khi': until[1].strip() if until else (f'{span[1]} {span[2]}' if span else None)}


def extension(unit):
    """New end of an extended validity: "đến hết tháng 12 năm 2016" -> 2016-12-31; a condition or a length stays words."""
    day = re.search(r'(?:đến|tới)\s+(?:hết\s+)?ngày\s+' + DATE, unit, re.I)
    month = re.search(r'(?:đến|tới)\s+hết\s+tháng\s+(\d{1,2})\s*(?:năm|/)\s*(\d{4})', unit, re.I)
    year = re.search(r'(?:đến|tới)\s+hết\s+năm\s+(\d{4})', unit, re.I)
    until = re.search(r'(?:cho\s+)?(?:đến|tới)\s+khi\s+([^.;\n]{3,200})', unit, re.I)
    span = re.search(r'\bthêm\s+(\d+)\s+(ngày|tháng|năm)', unit, re.I)
    end = None
    if day:
        end = to_date(*day.groups())
    elif month and 1 <= int(month[1]) <= 12:
        end = to_date(calendar.monthrange(int(month[2]), int(month[1]))[1], month[1], month[2])
    elif year:
        end = f'{year[1]}-12-31'
    return {'gia_han_den_ngay': end,
            'gia_han_den_khi': until[1].strip() if until else (f'thêm {span[1]} {span[2]}' if span else None)}


def normalize_scope(value):
    return 'toàn bộ' if re.fullmatch(r'\s*(?:toan[-\s]bo|toàn\s+bộ|toàn\s+văn)\s*', value or '', re.I) else value


_Y = r'\d+[a-zđ]?'
_Z = r'(?:[a-zđ]\d*|\d+(?:\.\d+)+)'
_C = r'(?:[IVXLCDM]+|\d+)'
_S = r'[A-Za-zĐđ\d][\w.\-]*'
# The position format of the data contract (docs/09, 9.5). A position outside it has no node.
POSITION = re.compile('^(?:' + '|'.join([
    rf'Điều {_Y}', rf'khoản {_Y} Điều {_Y}', rf'điểm {_Z} khoản {_Y} Điều {_Y}', rf'tiểu điểm \d+ điểm {_Z} khoản {_Y} Điều {_Y}',
    rf'tên Điều {_Y}', rf'tên Chương {_C}', rf'tên Mục {_C}(?: Chương {_C})?', rf'Chương {_C}', rf'Mục {_C}(?: Chương {_C})?',
    r'Phụ lục', rf'Phụ lục {_S}', rf'Mục {_S} Phụ lục(?: {_S})?', rf'Mục {_S} Phần {_S} Phụ lục(?: {_S})?',
    'tên văn bản', 'toàn bộ']) + ')$')


def in_format(position):
    return bool(POSITION.match(position or ''))
