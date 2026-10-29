"""Deterministic line parser and ES-compatible legal chunks."""

from collections import Counter
import re
import unicodedata

NUMBER = re.compile(r'(?<![\w:/])\d{1,6}/(?:\d{4}/)?[A-ZĐ][A-Za-zÀ-ỹĐ0-9]*(?:[ \t]*[-./][ \t]*[A-Za-zÀ-ỹĐ0-9]+)*')
# "Điều thứ 1" (old texts) and the misspelling "Điêu 3" are article labels too.
ARTICLE = re.compile(r'^(?:Điều|ĐIỀU|Điêu|ĐIÊU)\s+(?:thứ\s+)?(\d{1,4})([a-zđ]{0,2})\s*([.:–—-])?\s*(.*)$')
# A consolidated text's closing block, and an adopted text's closing sentence, end the body: they belong to no article.
CLOSING = re.compile(r'^(?:XÁC THỰC VĂN BẢN HỢP NHẤT|(?:Nghị quyết|Luật|Bộ luật|Pháp lệnh) này (?:đã )?được\b.{0,300}?\bthông qua\b)')
CLAUSE = re.compile(r'^(\d{1,3})([a-zđ]{0,2})\.\s+(.*)$')
POINT = re.compile(r'^([a-zđ][a-zđ0-9]?)\)\s+(.*)$')
CHAPTER = re.compile(r'^(Chương|CHƯƠNG|Mục|MỤC)\s+([IVXLCDM]+|\d+)\b\s*[.:–—-]?\s*(.*)$')
# A Roman label is a whole word: "PHỤ LỤC DANH SÁCH", "PHỤ LỤC MẪU" have no label (not D, M). I/V/X may carry a sub-label
# ("PHỤ LỤC IA", "PHỤ LỤC Vb", "PHỤ LỤC I4"); a word such as "MA TRẬN" is no label.
APPENDIX = re.compile(r'^(?:PHỤ LỤC|PHU LUC|Phụ lục)(?:\s+(?:SỐ\s+|số\s+)?((?:[IVX]+(?:[A-Ha-h]|\d{1,2})|[IVXLCDM]+)(?!\w)|\d+[A-Za-z]?))?\s*[.:]?\s*(.*)$')
ATTACHED = re.compile(r'^(?:QUY ĐỊNH|QUY CHẾ|QUY TRÌNH|QUY TẮC|QUY CHUẨN|QUY HOẠCH|DANH MỤC|DANH SÁCH|BẢNG|ĐỀ ÁN|ĐỀ CƯƠNG|CHƯƠNG TRÌNH|ĐIỀU LỆ|NỘI QUY|BIỂU MẪU|MẪU SỐ|PHỤ BIỂU|TIÊU CHÍ|KẾ HOẠCH|THUYẾT MINH|HƯỚNG DẪN|TIÊU CHUẨN)\b')
BASIS_DOCUMENT = re.compile(r'^(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Nghị\s+định|Nghị\s+quyết|Quyết\s+định|Thông\s+tư)\s')
# A signature with no TM./KT. and no "Nơi nhận": the signer's title alone on its line, or the passing sentence of a law.
SIGNED = re.compile(r'^(?:CHỦ\s+TỊCH(?:\s+QUỐC\s+HỘI|\s+NƯỚC)?|THỦ\s+TƯỚNG|BỘ\s+TRƯỞNG|CHÁNH\s+ÁN|VIỆN\s+TRƯỞNG|TỔNG\s+KIỂM\s+TOÁN\s+NHÀ\s+NƯỚC|GIÁM\s+ĐỐC|TỔNG\s+GIÁM\s+ĐỐC|THỐNG\s+ĐỐC)\s*$'
                    r'|đã\s+được\s+Quốc\s+hội\s+.{0,120}?thông\s+qua\s+ngày')
TAIL = re.compile(r'^(?:Nơi nhận\s*:|T\.?M[./]|T/M|K\.?T[./]|K/T|KT\.|TM\.)', re.I)
ISSUED_WITH = re.compile(r'\((?:Ban hành|Kèm theo|Phê duyệt|Được ban hành)\b[^)]{0,60}?\b(?:Quyết định|Nghị định|Nghị quyết|Thông tư|Chỉ thị|Công văn|Văn bản)', re.I)
# Blanks a printed form leaves for the user: dot leaders, "……", "(Tên tổ chức)", "(*)", "…(1)".
BLANK = re.compile(r'\.{4,}|…{2,}|…\s*[.…]|_{4,}|\.\s?\.\s?\.\s?\.|\((?:Tên|tên|ghi rõ|Ghi rõ)\b[^)]{0,80}\)|\(\*+\)|…\s*\(\d{1,2}\)|\.{2,}\s*\(\d{1,2}\)')
FORM_TITLE = re.compile(r'^(?:\[\d+\]\s*)?(?:VỀ\s+|CÁC\s+|DANH MỤC\s+|DANH SÁCH\s+)?(?:BIỂU\s+)?MẪU\b')
TABLE_SEPARATOR = re.compile(r'[|\s:-]*')
VI_LETTERS = 'abcdđeghiklmnopqrstuvxy'


def refs(text):
    text = re.sub(r'-\s+(?=[A-ZĐ])', '-', text)
    return list(dict.fromkeys(re.sub(r'\s+','',m.group()) for m in NUMBER.finditer(text)))


def normalize(text):
    # PDF extraction can emit NULs; PostgreSQL text/JSONB cannot store them.
    text = text.replace('\x00', '')
    text = unicodedata.normalize('NFC', text).replace('Ð', 'Đ').replace('ð', 'đ')
    text = text.replace('\u200b', '').replace('\ufeff', '').replace('\xa0', ' ')
    text = re.sub(r'(?<=[A-ZĐ])-\s*\n\s*(?=[A-ZĐ])', '-', text)
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.replace('\f', '\n').splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def appendix_header(line):
    m = APPENDIX.match(line)
    if m and re.match(r'^(?:kèm theo|ban hành kèm theo|của|tại|quy định tại)\b',m[2],re.I):return False
    # "Phụ lục (Ban hành kèm theo .................(1))": a line of a printed form, whose document is still a blank.
    if m and re.match(r'^\(\s*(?:ban hành\s+)?kèm theo\s*[.…]{3,}', m[2], re.I):return False
    # "Phụ lục I.1; các bộ, ngành là cơ quan chủ trì.": a label right before ";" cites an appendix in a list (a cell of a flattened
    # table, audit 29/10/2026, 730744); a heading never goes on after its label with ";".
    if m and m[1] and re.match(r'^[\d.]*\s*;', m[2]):return False
    return bool(m and (line.isupper() or not m[2] or m[2].isupper() or len(line) < 60))


def signature_cut(item):
    """A recipient item up to a blank line followed by a line in capitals of two words or more: the signer's title ("BỘ TRƯỞNG")."""
    for m in re.finditer(r'\n[ \t]*\n[ \t]*([^\n]*)', item):
        line = m[1].strip()
        if line.isupper() and len(re.findall(r'\w{2,}', line)) >= 2:
            return item[:m.start()]
    return item


def attached_heading(lines, i):
    """Title of an attached document (QUY CHẾ, QUY ĐỊNH...), not a chapter name such as "Chương I / QUY ĐỊNH CHUNG"."""
    if not (lines[i].isupper() and ATTACHED.match(lines[i])):
        return False
    previous = next((lines[j] for j in range(i - 1, -1, -1) if lines[j]), '')
    return not CHAPTER.match(previous)


def issued_note(line):
    """"(Ban hành kèm theo Quyết định số ...)" as a title note, not a parenthetical reference inside body text."""
    m = ISSUED_WITH.search(line)
    return bool(m) and (not line[:m.start()].strip() or line[:m.start()].isupper())


def title_line(line):
    return not line.startswith('|') and ((line.isupper() and not TAIL.match(line)) or bool(CHAPTER.match(line)) or issued_note(line))


def title_start(lines, i, floor):
    """First line of the title block directly above line i: uppercase titles, chapters and issuance notes."""
    while i - 1 > floor and (not lines[i - 1] or title_line(lines[i - 1])):
        i -= 1
    while i < len(lines) and not lines[i]:
        i += 1
    return i


def attached_titles(lines, candidates, floor, after_title=False):
    """Starts of attached documents: a titled block above an article chain beginning after `floor`.
    Untitled restarts of "Điều 1" stay segments. `after_title`: inside an appendix region, whose start
    is itself a title; a block reaching back to it continues that title, and only an issuance note
    opens another document, since sample forms there carry headings such as "HƯỚNG DẪN GHI CHÉP MẪU"."""
    opens = (lambda j: issued_note(lines[j])) if after_title else (lambda j: attached_heading(lines, j) or issued_note(lines[j]))
    starts = []
    for pos, (i, _, segment) in enumerate(candidates):
        if i <= floor or (pos and candidates[pos - 1][2] == segment):
            continue
        previous = max(floor, candidates[pos - 1][0] if pos else floor)
        start = title_start(lines, i, previous)
        if not any(opens(j) for j in range(start, i)):
            # A preamble may separate the title from "Chương I / Điều 1": use the nearest title above the chain.
            heading = next((j for j in range(i - 1, previous, -1) if opens(j)), None)
            if heading is None:
                continue
            start = title_start(lines, heading, previous)
        if after_title and previous == floor and not any(x and not title_line(x) for x in lines[floor + 1:start]):
            continue
        starts.append(start)
    return starts


def note_number(line):
    m = NUMBER.search(line[line.find('('):]) if issued_note(line) else None
    return re.sub(r'\s+', '', m.group()) if m else None


def sibling_attachments(region, boundaries):
    """Inside an unlabeled part, a later title block issued with the same document as the part's own
    note (Biểu số 1, Biểu số 2 of one Thông tư) is a separate attachment. Forms citing another document stay inside."""
    starts = []
    for pos, start in enumerate(boundaries):
        end = boundaries[pos + 1] if pos + 1 < len(boundaries) else len(region)
        if appendix_header(region[start]):
            continue
        head = next((j for j in range(start, end) if region[j] and not title_line(region[j]) and j > start), end)
        own = next((note_number(region[j]) for j in range(start, head) if note_number(region[j])), None)
        previous = start
        for j in range(head, end):
            if own and note_number(region[j]) == own:
                first = title_start(region, j, previous)
                if any(x and not title_line(x) for x in region[previous + 1:first]):
                    starts.append(first); previous = j
    return starts


def unquoted(lines):
    """Keep quoted amendment text in bodies without treating its labels as source labels.
    A quote still open at the end of the text was never closed (OCR dropped its pair); it is ignored
    and the text rescanned, so it cannot hide every later Điều."""
    ignored=set()
    for _ in range(5):
        depth=0;straight=False;result=[];opened=[];straight_at=None;chapter=0;stray=[]
        for n,line in enumerate(lines):
            heading=re.fullmatch(r'\s*Chương\s+([IVXLCDM]+)\s*',line)
            if heading and (depth or straight) and roman(heading[1])==chapter+1:
                # The next chapter of the text itself cannot sit inside a quote: the quote still open is a stray one whose pair is
                # far below (689697: "“8 Đối với …" left open hid Điều 27–37 under Chương IV). It is ignored and the text rescanned.
                stray=opened+([straight_at] if straight else []);break
            if heading and not depth and not straight:chapter=roman(heading[1])
            result.append(not depth and not straight)
            for i,char in enumerate(line):
                if (n,i) in ignored:continue
                if char=='“':depth+=1;opened.append((n,i))
                elif char=='’' and depth and opened[-1][0]==n and '”' not in line[i:]:
                    # Typed “name’ pair on one line: closing it here keeps it from swallowing later articles.
                    depth-=1;opened.pop()
                elif char=='”':
                    if depth:depth-=1;opened.pop()
                    else:straight=False;straight_at=None
                elif char=='"' and (not i or line[i-1]!='\\'):
                    # OCR may open with a curly quote and close with an ASCII quote.
                    # A closing quote at the end of the line must end the curly block,
                    # while embedded ASCII pairs inside it remain nested quotations.
                    if depth and not straight and re.fullmatch(r'\s*[.;,:]?\s*',line[i+1:]):
                        depth-=1;opened.pop()
                    else:
                        straight=not straight;straight_at=(n,i) if straight else None
        unclosed=stray or opened+([straight_at] if straight else [])
        if not unclosed:break
        ignored.update(unclosed)
    return result


def numeric_sequence(lines, pattern, restart=False, start_mid=False, unlabeled_first=False):
    candidates = []
    for i, (line,visible) in enumerate(zip(lines,unquoted(lines))):
        if not visible or line.startswith('|'):
            continue
        m = pattern.match(line)
        if not m:
            continue
        if pattern is ARTICLE and not m[3] and m[4] and (m[4][0].islower() or re.match(r'^(?:Quyết định|Nghị định|Nghị quyết|Thông tư|Luật|Bộ luật)\b',m[4])):
            continue
        candidates.append((i, m))
    accepted, last, suffix, segment = [], 0, '', 0
    for pos, (i, m) in enumerate(candidates):
        number, extra = int(m[1]), m[2]
        next_number = int(candidates[pos + 1][1][1]) if pos + 1 < len(candidates) else None
        if not accepted:
            # unlabeled_first: the first clause sometimes lost its "1." label; a run 2, 3, ... is still the clause list.
            valid = number == 1 or (start_mid and next_number == number + 1) or (unlabeled_first and number == 2 and next_number == 3)
        elif restart and number == 1 and next_number == 2:
            segment += 1
            valid = True
        elif extra:
            valid = (number == last and next_point(suffix,extra)) or (number == last + 1 and extra == 'a')
        else:
            valid = number == last + 1 or (number > last + 1 and next_number == number + 1)
        if valid:
            accepted.append((i, m, segment))
            last, suffix = number, extra
    return accepted


def next_point(previous, current):
    if not previous:
        return current == 'a'
    if current[0] == previous[0] and current[1:].isdigit():
        return int(current[1:]) == (int(previous[1:]) + 1 if previous[1:].isdigit() else 1)
    if current == 'aa' and previous[0] in 'xyz':
        return True
    if len(previous) == len(current) == 2 and previous[0] == previous[1] and current[0] == current[1]:
        return ord(current[0]) == ord(previous[0]) + 1
    if len(current) > 1 and current[1:] != '1':
        return False
    return any(a in alphabet and b in alphabet and alphabet.index(b) == alphabet.index(a) + 1
               for alphabet in (VI_LETTERS, 'abcdefghijklmnopqrstuvwxyz') for a, b in [(previous[0], current[0])])


def skipped_point(previous, current, later):
    """Source lists sometimes skip one letter (a, b, c, đ): keep the later points instead of merging them,
    unless the skipped letter still appears below (then `current` belongs to quoted amendment text)."""
    if not (len(previous) == len(current) == 1 and previous in VI_LETTERS and current in VI_LETTERS
            and VI_LETTERS.index(current) == VI_LETTERS.index(previous) + 2):
        return False
    missing = VI_LETTERS[VI_LETTERS.index(previous) + 1]
    return not any((m := POINT.match(line)) and m[1] == missing for line in later)


def split_sub_points(text):
    """Dash items of a point (tiết, gạch đầu dòng): (lead, items). Only lines opening with the first item's own mark split,
    so "+" items under a "-" item stay inside it; quoted amendment text never splits."""
    lines = text.splitlines()
    starts, mark = [], None
    for i, (line, visible) in enumerate(zip(lines, unquoted(lines))):
        m = re.match(r'^([-+•–—])\s*\S', line)
        if visible and m and (mark is None or m[1] == mark):
            mark = m[1]
            starts.append(i)
    if len(starts) < 2:
        return '', []
    items = ['\n'.join(lines[i:j]).strip() for i, j in zip(starts, starts[1:] + [len(lines)])]
    return '\n'.join(lines[:starts[0]]).strip(), [re.sub(r'^[-+•–—]\s*', '', item) for item in items]


def split_points(text):
    lines = text.splitlines()
    candidates, previous = [], ''
    for i, (line,visible) in enumerate(zip(lines,unquoted(lines))):
        m = POINT.match(line)
        if visible and m and (next_point(previous, m[1]) or skipped_point(previous, m[1], lines[i + 1:])):
            candidates.append((i, m))
            previous = m[1]
    if len(candidates) < 2:
        return '', []
    points = []
    for pos, (i, m) in enumerate(candidates):
        end = candidates[pos + 1][0] if pos + 1 < len(candidates) else len(lines)
        body = '\n'.join([m[2], *lines[i + 1:end]]).strip()
        point = {'ky_hieu': m[1], 'noi_dung': body, 'so_van_ban_refs': refs(body)}
        lead, items = split_sub_points(body)
        if items:
            point.update(mo_dau=lead, tieu_diem=[{'ky_hieu': str(n), 'noi_dung': item, 'so_van_ban_refs': refs(item)}
                                                 for n, item in enumerate(items, 1)])
        points.append(point)
    return '\n'.join(lines[:candidates[0][0]]).strip(), points


def split_clauses(text):
    lines = text.splitlines()
    candidates = numeric_sequence(lines, CLAUSE, unlabeled_first=True)
    clauses = []
    for pos, (i, m, _) in enumerate(candidates):
        end = candidates[pos + 1][0] if pos + 1 < len(candidates) else len(lines)
        body = '\n'.join([m[3], *lines[i + 1:end]]).strip()
        opening, points = split_points(body)
        clause = {'so_khoan': int(m[1]), 'ky_hieu': m[1] + m[2], 'noi_dung': body,
                  'so_van_ban_refs': refs(body), 'diem': points}
        if points:
            clause['mo_dau'] = opening
        clauses.append(clause)
    opening = '\n'.join(lines[:candidates[0][0]]).strip() if candidates else ''
    if candidates and int(candidates[0][1][1]) == 2 and opening:
        # The run starts at "2.": the text before it is clause 1 whose "1." label was lost, not a lead sentence.
        first_text, first_points = split_points(opening)
        first = {'so_khoan': 1, 'ky_hieu': '1', 'noi_dung': opening, 'so_van_ban_refs': refs(opening), 'diem': first_points,
                 'khong_nhan': True}
        if first_points:
            first['mo_dau'] = first_text
        return '', [first, *clauses]
    return opening, clauses


def chapter_marks(lines):
    marks = []
    for i, (line,visible) in enumerate(zip(lines,unquoted(lines))):
        m = CHAPTER.match(line)
        if not visible or not m:
            continue
        names = [m[3]] if m[3] else []
        for next_line in [x for x in lines[i + 1:] if x][:3]:
            if not next_line.isupper() or ARTICLE.match(next_line) or CHAPTER.match(next_line) or next_line.startswith('|'):
                break
            names.append(next_line)
        kind = 'chuong' if m[1].casefold() == 'chương' else 'muc'
        marks.append((i, kind, f'{"Chương" if kind == "chuong" else "Mục"} {m[2]} - {" ".join(names)}'.rstrip(' -')))
    return marks


def parse_articles(lines, offset=0, untitled=frozenset(), positions=False):
    """`offset`: source line of lines[0]; `untitled`: source lines of article headings decided to carry no article name."""
    candidates = numeric_sequence(lines, ARTICLE, restart=True, start_mid=True)
    marks = chapter_marks(lines)
    articles = []
    for pos, (i, m, segment) in enumerate(candidates):
        end = candidates[pos + 1][0] if pos + 1 < len(candidates) else len(lines)
        end = min([end, *[j for j, _, _ in marks if i < j < end]])
        body = '\n'.join(lines[i + 1:end]).strip()
        following=next((x for x in body.splitlines() if x),'')
        title=m[4] or (following if not CLAUSE.match(following) and not POINT.match(following) else '')
        if (m[4] and not body) or offset + i in untitled:
            # No article name: the text after "Điều N." is already the article's content.
            body, title = ('\n'.join([m[4], body]).strip() if m[4] else body), ''
        opening, clauses = split_clauses(body)
        article = {'so_dieu': int(m[1]), 'ky_hieu': m[1] + m[2], 'tieu_de': title,
                   'noi_dung': body, 'so_van_ban_refs': refs(title + '\n' + body), 'khoan': clauses}
        if positions:
            article.update(line=offset + i, title_inline=bool(m[4]))
        if clauses:
            article['mo_dau'] = opening
        if segment:
            article['van_ban_kem_theo'] = segment
        chapter, section = None, None
        for j, kind, name in marks:
            if j >= i:
                break
            if kind == 'chuong':
                chapter, section = name, None
            else:
                section = name
        if chapter:
            article['chuong'] = chapter
        if section:
            article['muc'] = section
        articles.append(article)
    return articles, candidates


def sample_form(title, articles):
    """Articles of a printed form (a sample decision or licence: "Điều 1. Cho phép ……(Tên tổ chức)……", then its own "Nơi nhận"),
    not articles of an attached regulation. Only the part's first chain counts: a real Quy chế followed by a sample decision stays.
    A form: a blank in an article name; or its own recipients and blanks, with at most 6 articles or a blank in Điều 1;
    or a part titled as a form ("MẪU …", "CÁC BIỂU MẪU …") whose articles have blanks."""
    chain = [a for a in articles if a.get('van_ban_kem_theo', 0) == articles[0].get('van_ban_kem_theo', 0)]
    text = '\n'.join(a['tieu_de'] + '\n' + a['noi_dung'] for a in chain)
    if any(BLANK.search(a['tieu_de']) for a in chain):
        return True
    if re.search(r'^Nơi nhận\s*:', text, re.M) and BLANK.search(text) and (
            len(chain) <= 6 or BLANK.search(chain[0]['tieu_de'] + '\n' + chain[0]['noi_dung'])):
        return True
    label = APPENDIX.match(title)
    return bool(FORM_TITLE.match((label[2] if label else title).upper()) and BLANK.search(text))


def roman(value):
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    return sum(-values[c] if i + 1 < len(value) and values[c] < values[value[i + 1]] else values[c] for i, c in enumerate(value))


def split_sections(text, with_start=False):
    """Numbered sections of a text without articles. The lines above the first section are the opening (national motto, number,
    "Kính gửi", the opening paragraph): with_start=True also returns the line where the first section starts."""
    lines = text.splitlines()
    # "I.", "I)", "I-", "I:", "1.", "1)": not "V/v" (về việc), which is no section.
    for pattern in (r'^([IVXLCDM]+)\s*[.)\-–:]\s*(.*\S.*)$', r'^(\d+)[.)]\s+(.*)$'):
        accepted, last = [], 0
        for i, (line,visible) in enumerate(zip(lines,unquoted(lines))):
            m = re.match(pattern, line)
            if visible and m:
                number = int(m[1]) if m[1].isdigit() else roman(m[1])
                if number == last + 1:
                    accepted.append((i, m)); last = number
        if len(accepted) >= 2:
            result = []
            for pos, (i, m) in enumerate(accepted):
                end = accepted[pos + 1][0] if pos + 1 < len(accepted) else len(lines)
                body = '\n'.join([m[2], *lines[i + 1:end]]).strip()
                result.append({'so_muc': m[1], 'noi_dung': body, 'so_van_ban_refs': refs(body)})
            return (result, accepted[0][0]) if with_start else result
    return ([], None) if with_start else []


def strip_notes(lines, consolidated=False):
    """Footnote markers glued to labels: "4.[2]", "đ)[3]", "Điều 3[2]" anywhere; in a consolidated text also "4.8 ", "46.", "5a.76",
    "d4)", "đ)5", "Điều 32." -- but only where the running numbering expects that label (clause 4 after clause 3), so a real clause 46
    or Điều 32 stays. Line count and order never change: decisions keep referring to the same source lines."""
    out, article, clause, point = [], 0, 0, ''
    for line, visible in zip(lines, unquoted(lines)):
        if not visible:
            out.append(line)
            continue
        line = re.sub(r'^((?:Điều|ĐIỀU)\s+\d{1,4}[a-zđ]{0,2})\[\d{1,3}\]', r'\1', line)
        line = re.sub(r'^(\d{1,3}[a-zđ]{0,2}\.)\s*\[\d{1,3}\]\s*', r'\1 ', line)
        line = re.sub(r'^([a-zđ][a-zđ0-9]?\))\s*\[\d{1,3}\]\s*', r'\1 ', line)
        # "2 . Trên cơ sở …": a stray space before the dot of the clause the numbering expects.
        line = re.sub(r'^(%d)\s+\.\s+' % (clause + 1), r'\1. ', line)
        if consolidated:
            expected = str(article + 1)
            m = re.match(r'^((?:Điều|ĐIỀU)\s+)(\d{2,4})(?=\s*[.:])', line)
            if m and m[2] != expected and m[2].startswith(expected):
                line = m[1] + expected + line[m.end(2):]
            expected = str(clause + 1)
            m = re.match(r'^(\d{1,3})([a-zđ]?)\.(\d{1,3})\s+(.*)$', line)
            if m and (m[1] == expected or (m[2] and int(m[1]) == clause)):
                line = f'{m[1]}{m[2]}. {m[4]}'
            m = re.match(r'^(\d{2,4})\.\s+(.*)$', line)
            if m and m[1] != expected and m[1].startswith(expected):
                line = f'{expected}. {m[2]}'
            m = re.match(r'^([a-zđ])(?:(\d{1,3})\)|\)(\d{1,3}))\s*(.*)$', line)
            if m and next_point(point, m[1]):
                line = f'{m[1]}) {m[4]}'
        if (m := ARTICLE.match(line)):
            article, clause, point = int(m[1]), 0, ''
        elif (m := CLAUSE.match(line)) and (int(m[1]) == clause + 1 or (m[2] and int(m[1]) == clause)):
            clause, point = int(m[1]), ''
        elif (m := POINT.match(line)) and next_point(point, m[1]):
            point = m[1]
        out.append(line)
    return out


def source_lines(text):
    """Numbered lines every structure decision refers to."""
    # Separate introductory declarations even if OCR joined them to a basis line.
    text = re.sub(r';\s*(?=Theo đề nghị\b|Chính phủ ban hành\b)', ';\n', text)
    text = re.sub(r'\bCăn\s+cứ\s+(?:các\s+)?(?:quy\s+định\s+)?(?:nêu\s+)?trên\b', lambda m:'\n'+re.sub(r'\s+',' ',m.group()), text)
    return normalize(text).splitlines()


def parse(text, untitled=frozenset(), parts=None, positions=False):
    """Rule parser. `untitled` (source lines of article headings) and `parts` (source lines where attached
    documents/appendices start) carry validated decisions from structure_ai; `positions` adds source lines."""
    # A consolidated text cites its amending acts in footnotes glued to the labels.
    lines = strip_notes(source_lines(text), consolidated=bool(re.search(r'VĂN BẢN HỢP NHẤT|/\s*VBHN\s*-|XÁC THỰC VĂN BẢN', text, re.I)))
    visible=unquoted(lines)
    labeled = [i for i, line in enumerate(lines) if visible[i] and appendix_header(line)]
    probe = lines[:labeled[0]] if labeled else lines
    _, candidates = parse_articles(probe)
    anchor = max((i for i, _, seg in candidates if not seg), default=0)
    recipients = next((i for i in range(anchor, len(probe)) if visible[i] and re.match(r'^Nơi nhận\s*:', probe[i], re.I)), None)
    tail_start = recipients
    if tail_start is None:
        tail_start = next((i if TAIL.match(probe[i]) else i+1 for i in range(anchor, len(probe)) if visible[i] and (TAIL.match(probe[i]) or './.' in probe[i])), None)
    signature_start = tail_start
    closing = next((i for i in range(anchor + 1, len(probe)) if visible[i] and CLOSING.match(probe[i])), None)
    if closing is not None and (tail_start is None or closing < tail_start):
        tail_start = closing
    # A titled attached document (Quy chế, Quy định...) is an unlabeled appendix, whether or not the
    # signature was recognised and even when labeled appendices follow; otherwise it falls into the tail.
    limit = labeled[0] if labeled else len(lines)
    found = attached_titles(lines, candidates, anchor)[:1]
    end = tail_start if tail_start is not None else limit
    found += [title_start(lines, j, anchor) for j in range(anchor + 1, end) if visible[j] and issued_note(lines[j])][:1]
    if tail_start is not None:
        # Quote tracking is unreliable past the signature, so these searches ignore it.
        found += [title_start(lines, j, tail_start) for j in range(tail_start + 1, limit) if attached_heading(lines, j) or issued_note(lines[j])][:1]
        # An article chain restarting after the signature is attached even without a recognised title.
        found += [title_start(lines, i, tail_start) for i, _, seg in candidates if seg and i > tail_start][:1]
    appendix_start = min(found) if found else (labeled[0] if labeled else None)
    if parts is not None:
        appendix_start = min(parts) if parts else None
    if appendix_start is not None and (tail_start is None or appendix_start < tail_start):
        body_end, tail = appendix_start, ''
    else:
        body_end = tail_start if tail_start is not None else (appendix_start if appendix_start is not None else len(lines))
        tail = '\n'.join(lines[body_end:appendix_start]).strip() if tail_start is not None else ''
    main = lines[:body_end]
    articles, candidates = parse_articles(main, 0, untitled, positions)
    first_article = candidates[0][0] if candidates else len(main)
    basis, basis_end = [], 0
    i = 0
    while i < first_article:
        if main[i].startswith('Căn cứ ') and not re.match(r'^Căn cứ (?:các )?(?:quy định )?(?:nêu )?trên\b', main[i], re.I):
            start = i; i += 1
            while i < first_article and main[i] and not main[i-1].rstrip().endswith(';') and not main[i].startswith(('Căn cứ ', 'Theo đề nghị ', 'Chính phủ ban hành ')) and not CHAPTER.match(main[i]):
                i += 1
            basis.append(' '.join(main[start:i]).strip().rstrip(';'))
            basis_end = i
        elif basis and BASIS_DOCUMENT.match(main[i]) and main[i].rstrip().endswith(';') \
                and any(main[j].startswith('Căn cứ ') for j in range(i + 1, first_article)):
            # A basis whose "Căn cứ" the source lost, between two bases ("Luật Hợp tác xã số 17/2023/QH15;", 692549). The bases end
            # where they ended before, so the opening the model reads does not move.
            basis.append(main[i].strip().rstrip(';'))
            i += 1
        else:
            i += 1
    marks = [i for i, _, _ in chapter_marks(main) if basis_end <= i < first_article]
    intro_end = marks[-1] if marks else first_article
    intro = '\n'.join(main[basis_end:intro_end]).strip()
    appendices = []
    if appendix_start is not None:
        region = lines[appendix_start:]
        boundaries = [i for i, line in enumerate(region) if appendix_header(line)]
        # Several attached documents: each titled chain of Điều is its own part.
        region_articles = numeric_sequence(region, ARTICLE, restart=True, start_mid=True)
        boundaries = sorted({0, *boundaries, *attached_titles(region, region_articles, 0, after_title=True)})
        boundaries = sorted({*boundaries, *sibling_attachments(region, boundaries)})
        if parts is not None:
            boundaries = sorted(p - appendix_start for p in parts)
        for pos, start in enumerate(boundaries):
            end = boundaries[pos + 1] if pos + 1 < len(boundaries) else len(region)
            part = region[start:end]
            # An untitled attached chain starts on its "Điều 1" line, which is content, not a title.
            untitled_part = bool(part) and bool(ARTICLE.match(part[0]))
            title_lines = [part[0]] if part and not untitled_part else []
            offset = 0 if untitled_part else 1
            for line in ([] if untitled_part else part[1:]):
                if not line:
                    offset += 1; continue
                if len(title_lines) >= 5 or line.startswith('|') or not (line.isupper() or line.startswith(('(Ban hành', '(Kèm theo')) or issued_note(line)):
                    break
                title_lines.append(line); offset += 1
                if line.endswith(')'):
                    break
            content = '\n'.join(part[offset:]).strip()
            appendix_articles, _ = parse_articles(part[offset:], appendix_start + start + offset, untitled, positions)
            if appendix_articles and sample_form(' '.join(title_lines), appendix_articles):
                # A form keeps its text as one flat part, like a table: its "Điều" are blanks to fill, not provisions.
                appendix_articles = []
            rows = [line for line in part if line.startswith('|')]
            table_groups = re.findall(r'(?:^\|.*(?:\n|$)(?:\s*\n)*){2,}', '\n'.join(part), re.M)
            appendices.append({'tieu_de': ' '.join(title_lines), 'noi_dung': content,
                               'loai': 'labeled' if part and appendix_header(part[0]) else 'unlabeled',
                               'has_table': len(rows) >= 2, 'n_tables': len(table_groups), 'n_table_rows': len(rows),
                               'dieu_luat': appendix_articles})
            if positions:
                appendices[-1]['line'] = appendix_start + start
    places = []
    if tail:
        # Recipients start at "Nơi nhận" or the signature, not at the closing sentence above them.
        signed = '\n'.join(lines[signature_start:appendix_start]) if signature_start is not None and signature_start >= body_end else tail
        # No "Nơi nhận": the block is the signature ("CHỦ TỊCH Phùng Quang Hùng"), and there are no recipients.
        if not re.search(r'Nơi nhận', signed, re.I):
            signed = ''
        for item in re.split(r'(?:\n\s*-|;)', re.sub(r'^.*?Nơi nhận\s*:', '', signed, flags=re.S | re.I)):
            if TAIL.match(item.strip()) or not item.strip():
                continue
            # The signature ends the last recipient: "KT./TM./TL./TUQ./Q." on a new line, or after a blank line a line with no
            # lower-case letter and two capitalised words ("BỘ TRƯỞNG", "CỤC TRƯỞNG", "BỘ TƯ PHÁP"). A single line break may
            # continue a recipient in capitals ("Cục:\nKTTH, PL"), so a bare title counts only after a blank line.
            value = re.split(r'\n(?:KT\.|TM\.|T/M|K/T|TL\.|TUQ\.|Q\.\s)', item, maxsplit=1)[0]
            value = signature_cut(value)
            # Recipients and the signature side by side in a table row ("Lưu: VT. | TM. ỦY BAN NHÂN DÂN … Nguyễn Văn Đảm"): the
            # recipients are the first cell only.
            value = re.split(r'\s*\|\s*', value.strip().strip('|'), maxsplit=1)[0].strip().strip('- ;.,')
            if value:
                places.append(value)
    # The lines above the legal basis: title block, and for a consolidated text the documents it restates.
    sections, section_start = (split_sections('\n'.join(main), with_start=True) if not articles else ([], None))
    if section_start is not None:
        first_article = intro_end = min(first_article, section_start)
        intro = '\n'.join(main[basis_end:intro_end]).strip()
    head_end = next((i for i in range(first_article) if main[i].startswith('Căn cứ ')), first_article)
    result = {'phan_dau': '\n'.join(main[:head_end]).strip(), 'can_cu': basis, 'can_cu_refs': refs(' '.join(basis)), 'intro': intro,
              'dieu_luat': articles, 'noi_nhan': places, 'phu_luc': appendices,
              'has_tail': any(TAIL.match(line) or './.' in line or SIGNED.search(line) for line in lines)}
    if not articles:
        # A letter's bases and quoted rules are part of its reasoning, not a removable preamble.
        letter_content='\n'.join(main).strip()
        result.update(noi_dung=letter_content, noi_dung_refs=refs(letter_content), noi_dung_sections=sections)
    all_articles = articles + [a for p in appendices for a in p['dieu_luat']]
    seq_ok, last, seg = True, 0, 0
    for a in articles:
        current_seg = a.get('van_ban_kem_theo', 0)
        if current_seg != seg:
            last, seg = 0, current_seg
        if a['so_dieu'] not in (last, last + 1):
            seq_ok = False
        last = a['so_dieu']
    if 'bãi bỏ' in text.casefold():
        seq_ok = True
    clauses = [k for a in all_articles for k in a['khoan']]
    # Articles left in the signature/recipient tail have no chunks; coverage alone counts them as covered.
    # Counted without quote tracking: a stray quote after the signature is how they get hidden. Only a chain
    # starting "Điều 1, Điều 2" counts; consolidated-text footnotes cite scattered articles of amending acts.
    numbers = [int(m[1]) for m in map(ARTICLE.match, tail.splitlines()) if m]
    chain = next((k for k in range(len(numbers) - 1) if numbers[k:k + 2] == [1, 2]), None)
    tail_dieu = len(numbers) - chain if chain is not None else 0
    count = lambda value: len(re.sub(r'\s', '', value))
    reconstructed = '\n'.join(main[:basis_end]) + intro + tail
    reconstructed += ''.join(a['tieu_de'] + a['noi_dung'] for a in articles)
    reconstructed += ''.join(p['tieu_de'] + p['noi_dung'] for p in appendices)
    reconstructed += ''.join(m['noi_dung'] for m in sections)
    covered = sum(count(a.get('mo_dau', '')) + sum(count(k['noi_dung']) for k in a['khoan']) for a in all_articles if a['khoan'])
    denominator = sum(count(a['noi_dung']) for a in all_articles if a['khoan'])
    grade = 'full' if result['has_tail'] and not tail_dieu and ((articles and seq_ok) or result.get('noi_dung_sections')) else ('partial' if all_articles or appendices or result.get('noi_dung_sections') else 'minimal')
    stats = {'grade': grade, 'n_dieu': sum(not a.get('van_ban_kem_theo') for a in articles),
             'n_dieu_total': len(all_articles), 'n_khoan': len(clauses), 'n_diem': sum(len(k['diem']) for k in clauses),
             'n_phu_luc': len(appendices), 'n_muc': len(result.get('noi_dung_sections', [])),
             'dieu_seq_ok': seq_ok, 'has_tail': result['has_tail'], 'tail_dieu': tail_dieu,
             'coverage': min(1, count(reconstructed) / max(1, count(text))),
             'khoan_coverage': min(1, covered / max(1, denominator)) if denominator else 1}
    return result, stats


PASSAGE_WORDS = 200  # stays under the embedding service's 256-token input (Vietnamese syllables tokenize near one each)


def passages(text, limit=PASSAGE_WORDS):
    """Split long unstructured text into passages of at most `limit` words, at paragraph, then sentence boundaries."""
    if len(text.split()) <= limit:
        return [text]
    pieces = []
    for paragraph in (p.strip() for p in re.split(r'\n\s*\n|\n', text) if p.strip()):
        if len(paragraph.split()) <= limit:
            pieces.append(paragraph)
            continue
        for sentence in re.split(r'(?<=[.;:!?])\s+', paragraph):
            words = sentence.split()
            pieces += [' '.join(words[i:i + limit]) for i in range(0, len(words), limit)] if len(words) > limit else [sentence]
    result, current = [], []
    for piece in pieces:
        if current and len(' '.join(current + [piece]).split()) > limit:
            result.append('\n'.join(current))
            current = []
        current.append(piece)
    if current:
        result.append('\n'.join(current))
    return result


SEARCH_PASSAGE_WORDS = 150  # an appendix runs ~1.5 tokens a word (p90 1.8, 27/10/2026): 150 words stay under 256 tokens
# With whole-chunk vectors (no 256-token cut, 27/10/2026) an appendix finds best at ~300 words a passage (Hit@5 0.767 against 0.667 at
# 150, 170 questions on 400 documents), a section of a letter at ~150 (0.854 against 0.732 at 300).
APPENDIX_PASSAGE_WORDS = 300
SECTION_PASSAGE_WORDS = SEARCH_PASSAGE_WORDS


def search_passages(text, limit=SEARCH_PASSAGE_WORDS):
    """Passages of a long appendix or section, for search only: whole table rows and paragraphs, then sentences, then words, up to
    `limit` words. A passage that opens inside a table repeats the table's column names. [] when the text fits in one passage."""
    if len(text.split()) <= limit:
        return []
    units, header, lines = [], None, text.splitlines()
    for n, line in enumerate(lines):
        if not line.strip():
            continue
        if not line.startswith('|'):
            header = None
            units += [(piece, None) for piece in passages(line, limit)]
            continue
        if n == 0 or not lines[n - 1].startswith('|'):
            # First row of a table: its column names, with the empty separator row the source puts under them.
            rows = [line] + ([lines[n + 1]] if n + 1 < len(lines) and TABLE_SEPARATOR.fullmatch(lines[n + 1]) else [])
            header = '\n'.join(rows) if len(' '.join(rows).split()) <= limit // 3 else None
            units.append((line, None))
            continue
        if TABLE_SEPARATOR.fullmatch(line):
            continue
        words = line.split()
        units += [(' '.join(words[i:i + limit]), header) for i in range(0, len(words), limit)]
    result, current, size = [], [], 0
    for unit, columns in units:
        count = len(unit.split())
        if current and size + count > limit:
            result.append('\n'.join(current))
            current, size = [], 0
        if not current and columns:
            current, size = [columns], len(columns.split())
        current.append(unit)
        size += count
    if current:
        result.append('\n'.join(current))
    return result


def build_chunks(doc_id, metadata, parsed, passage_words=None):
    appendix_words, section_words = (passage_words, passage_words) if passage_words else (APPENDIX_PASSAGE_WORDS, SECTION_PASSAGE_WORDS)
    common = {k: metadata[k] for k in ('document_number', 'title', 'action', 'legal_type', 'issuing_authority', 'issuance_date', 'url', 'signers') if metadata.get(k)}
    common['doc_id'] = str(doc_id)
    if metadata.get('legal_sectors'):
        common['legal_sectors'] = ', '.join(metadata['legal_sectors'])
    chunks, seen = [], Counter()

    def emit(uid, kind, title, body, fields, references=None, full=False):
        if not (title + body).strip():
            return
        seen[uid] += 1
        key = uid if seen[uid] == 1 else f'{uid}_{seen[uid]}'
        source = {**common, **fields, 'chunk_type': kind, 'tieu_de': title, 'noi_dung': body,
                  'so_van_ban_refs': references if references is not None else refs(title + ' ' + body)}
        if full:
            source['is_full'] = True
        chunks.append({'_id': key, '_source': source})
        return key

    def article_chunks(article, prefix, extra):
        segment = article.get('van_ban_kem_theo', 0)
        uid = prefix + (f'_s{segment}' if segment else '') + '_d' + article['ky_hieu']
        fields = {**extra, 'dieu_uid': uid, 'segment': segment, 'so_dieu': article['so_dieu'], 'ky_hieu_dieu': article['ky_hieu']}
        for key, target in [('chuong', 'chuong'), ('muc', 'muc_lon')]:
            if article.get(key):
                fields[target] = article[key]
        title = article['tieu_de']
        clauses = article['khoan']
        emit(uid + ('_full' if clauses else ''), 'dieu_full' if clauses else 'dieu', title, article['noi_dung'], fields, article['so_van_ban_refs'], True)
        if len(article.get('mo_dau', '')) >= 40:
            emit(uid + '_md', 'dieu_mo_dau', title, article['mo_dau'], fields, [])
        for clause in clauses:
            kid = uid + '_k' + clause['ky_hieu']
            kfields = {**fields, 'khoan_uid': kid, 'so_khoan': clause['so_khoan'], 'ky_hieu_khoan': clause['ky_hieu']}
            points = clause['diem']
            emit(kid + ('_full' if points else ''), 'khoan_full' if points else 'khoan', title, clause['noi_dung'], kfields, clause['so_van_ban_refs'], True)
            if len(clause.get('mo_dau', '')) >= 40:
                emit(kid + '_md', 'khoan_mo_dau', title, clause['mo_dau'], kfields, [])
            for point in points:
                pid = kid + '_p' + point['ky_hieu']
                pfields = {**kfields, 'so_diem': point['ky_hieu'], 'diem_uid': pid}
                emit(pid, 'diem', title, point['noi_dung'], pfields, point['so_van_ban_refs'])
                for sub in point.get('tieu_diem', []):
                    emit(pid + '_t' + sub['ky_hieu'], 'tieu_diem', title, sub['noi_dung'], {**pfields, 'so_tieu_diem': int(sub['ky_hieu'])},
                         sub['so_van_ban_refs'])

    for article in parsed['dieu_luat']:
        article_chunks(article, str(doc_id), {})
    for i, appendix in enumerate(parsed['phu_luc']):
        prefix = f'{doc_id}_pl{i}'
        # loai_phan: kem_theo = an attached regulation kept as Điều; phu_luc = a table, list, form or plain text kept flat.
        extra = {'in_phu_luc': True, 'phu_luc_tieu_de': appendix['tieu_de'][:500], 'has_table': appendix['has_table'],
                 'phu_luc_uid': prefix, 'loai_phan': 'kem_theo' if appendix['dieu_luat'] else 'phu_luc'}
        if appendix['dieu_luat']:
            for article in appendix['dieu_luat']:
                article_chunks(article, prefix, extra)
        else:
            # The whole part stays one chunk: the graph node. Passages are for search only and repeat the part's title.
            parts = search_passages(appendix['noi_dung'], appendix_words)
            emit(prefix, 'phu_luc', appendix['tieu_de'], appendix['noi_dung'], extra, full=bool(parts))
            for k, part in enumerate(parts, 1):
                emit(f'{prefix}_doan{k}', 'phu_luc_doan', appendix['tieu_de'], part, {**extra, 'so_doan': k})
    if not parsed['dieu_luat']:
        sections = parsed.get('noi_dung_sections', [])
        for section in sections:
            parts = search_passages(section['noi_dung'], section_words)
            key = emit(f'{doc_id}_m{section["so_muc"]}', 'muc', '', section['noi_dung'], {'so_muc': section['so_muc']},
                       section['so_van_ban_refs'], full=bool(parts))
            if key:
                chunks[-1]['_source']['muc_uid'] = key
            heading = section['noi_dung'].split('\n', 1)[0][:200]
            for k, part in enumerate(parts, 1):
                # Passages after the first repeat the section's heading line as their title.
                emit(f'{key}_doan{k}', 'muc_doan', heading if k > 1 else '', part, {'so_muc': section['so_muc'], 'muc_uid': key, 'so_doan': k})
        if not sections and parsed.get('noi_dung'):
            parts = passages(parsed['noi_dung'])
            if len(parts) == 1:
                emit(f'{doc_id}_nd', 'noi_dung', '', parsed['noi_dung'], {}, parsed.get('noi_dung_refs', []))
            else:
                # Like Điều/Khoản: one full chunk, plus passages short enough to be embedded whole.
                emit(f'{doc_id}_nd_full', 'noi_dung_full', '', parsed['noi_dung'], {}, parsed.get('noi_dung_refs', []), True)
                for i, part in enumerate(parts, 1):
                    emit(f'{doc_id}_nd{i}', 'noi_dung', '', part, {'so_doan': i})
    return chunks


# The type line that opens the printed title ("QUYẾT ĐỊNH", "THÔNG TƯ LIÊN TỊCH", "NGHỊ QUYẾT VỀ …").
TITLE_TYPE = re.compile(r'^(?:BỘ\s+LUẬT|LUẬT|PHÁP\s+LỆNH|LỆNH|HIẾN\s+PHÁP|SẮC\s+LỆNH|NGHỊ\s+ĐỊNH|NGHỊ\s+QUYẾT(?:\s+LIÊN\s+TỊCH)?'
                        r'|THÔNG\s+TƯ(?:\s+LIÊN\s+TỊCH)?|THÔNG\s+TRI|QUYẾT\s+ĐỊNH|CHỈ\s+THỊ|VĂN\s+BẢN\s+HỢP\s+NHẤT|KẾ\s+HOẠCH|THÔNG\s+BÁO'
                        r'|HƯỚNG\s+DẪN|QUY\s+ĐỊNH|QUY\s+CHẾ|ĐIỀU\s+LỆ|CHƯƠNG\s+TRÌNH|ĐỀ\s+ÁN|BÁO\s+CÁO|CÔNG\s+ĐIỆN)\b')
# A line that names the issuer above the issuing sentence ("ỦY BAN NHÂN DÂN TỈNH BÌNH ĐỊNH", "CHỦ TỊCH HỘI ĐỒNG BỘ TRƯỞNG") ends the title.
TITLE_ISSUER = re.compile(r'^(?:ỦY\s+BAN|UỶ\s+BAN|UBND|HỘI\s+ĐỒNG|CHÍNH\s+PHỦ|THỦ\s+TƯỚNG|BỘ\s+TRƯỞNG|CHỦ\s+TỊCH|QUỐC\s+HỘI|TỔNG\s+CỤC\s+TRƯỞNG'
                          r'|CỤC\s+TRƯỞNG|GIÁM\s+ĐỐC|THỐNG\s+ĐỐC|VIỆN\s+TRƯỞNG|CHÁNH\s+ÁN|TỔNG\s+KIỂM\s+TOÁN|BAN\s+CHẤP\s+HÀNH|BỘ\s+CHÍNH\s+TRỊ'
                          r'|TRƯỞNG\s+BAN|BAN\s+THƯỜNG\s+VỤ)\b')


def printed_title(head):
    """The title printed in the document (Q11, 20/10/2026), from the lines above the legal basis (parse()['phan_dau']).
    The stored `title` is the database's own description ("… bãi bỏ các Quyết định 29/2020/QĐ-UBND và 11/2021/QĐ-UBND",
    "Nghị định 31/CP-1996"): relations are read from the printed words only. A letter's title is its "V/v …" line.
    '' when the opening has no title the parser can read."""
    # "BAN HÀNHxml:namespace prefix = u1 / KÈM THEO …": markup left in some old source texts.
    head = re.sub(r'xml:namespace\s+prefix\s*=\s*\w+\s*/', ' ', head or '')
    lines = [' '.join(line.split()) for line in head.splitlines() if line.strip()]
    for line in lines:
        subject = re.search(r'\b(?:V/v|V/V|Về\s+việc)\s*[.:]?\s*([^|]+)', line)
        if subject and not TITLE_TYPE.match(line):
            return subject[1].strip(' .;')
    for n, line in enumerate(lines):
        if '|' in line or not TITLE_TYPE.match(line):
            continue
        title = [line]
        for following in lines[n + 1:n + 7]:
            # "… KÈM THEO QUYẾT ĐỊNH SỐ 188-CT CỦA" / "CHỦ TỊCH HỘI ĐỒNG BỘ TRƯỞNG": a line ending in "của", "và" goes on.
            open_end = re.search(r'\b(?:CỦA|VÀ)$', title[-1])
            if '|' in following or (TITLE_ISSUER.match(following) and not open_end) \
                    or not (following.isupper() or following.startswith(('(', 'Về', 'về'))):
                break
            title.append(following)
        return ' '.join(title)[:700].strip(' .;')
    return ''


DOCUMENT_WORDS = re.compile(r'\b(bộ luật|luật|pháp lệnh|hiến pháp|nghị định|nghị quyết|thông tư|quyết định|chỉ thị)\b')


def sentence_case(text):
    """'HƯỚNG DẪN THỰC HIỆN NGHỊ ĐỊNH SỐ 31/CP' -> 'Hướng dẫn thực hiện Nghị định số 31/CP', for rules written on stored titles
    ("Luật Đất đai" is a law named by name only when "Luật" and the name are capitalized). Numbers keep their case."""
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) < 0.8 * len(letters):
        return text
    words = [w if re.search(r'\d', w) else w.lower() for w in text.split()]
    out = DOCUMENT_WORDS.sub(lambda m: m[1][0].upper() + m[1][1:], ' '.join(words))
    out = re.sub(r'\b(Bộ luật|Luật|Pháp lệnh)\s+(\w)', lambda m: m[1] + ' ' + m[2].upper(), out)
    return out[:1].upper() + out[1:]


def appendix_label(part):
    """'PHỤ LỤC SỐ 01 …' -> '01', 'PHỤ LỤC II' -> 'II'; unlabeled attached documents have none."""
    match = APPENDIX.match(part.get('tieu_de') or '') if part.get('loai') == 'labeled' else None
    return match[1] if match and match[1] else None
