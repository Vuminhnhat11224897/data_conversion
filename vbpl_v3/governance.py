"""The frame of a unit the model read (tầng 2): which text performs the act on it, and where its evidence may stand.

Roles (set 21/10/2026, docs/08 §8.11):
- The parser gives the units and their structure: the clause lead of a point, the article lead and heading of a clause, the list
  heading and column names of a table row, the article that names an attachment, the printed title.
- The model reads the meaning: who acts, which act, which target, which part.
- This module checks, from the structure only, that the source shows it: the text that performs the act on this unit, the verbatim
  pieces of the model's quote with the field each stands in, and the spans of quoted new wording. It reads no meaning.

A lead performs the act on the items under it only when it opens a list of what is acted on ("Bãi bỏ các văn bản sau:", "Các Thông
tư sau hết hiệu lực:", "Bãi bỏ các quy định sau của Quyết định số X:"). A lead that names one provision and ends in "như sau:"
introduces the new wording ("Khoản 2 Điều 3 được sửa đổi như sau:"): the items under it are that wording, not acts.
"""

import re

from .relations import document_refs, strip_quotes
from .text import number_key

# Fields of a row of the model, as validate.sources() gives them, by name.
FIELDS = ('don_vi', 'cau_dan', 'danh_sach', 'ten_dieu', 'cau_dan_dieu', 'chuong', 'ten_van_ban', 'phan_dau')
MIN_PIECE = 12      # a shorter piece could match by chance
COVER = 0.9         # share of the quote (non-space characters) the verbatim pieces must cover

# What a list opener acts on is a set: "các văn bản", "15 văn bản", "một số điều", "những nội dung", "sau đây".
COLLECTIVE = re.compile(r'\b(?:các|những|một\s+số|\d+\s*(?:\([^)]*\)\s*)?(?:văn\s+bản|quyết\s+định|thông\s+tư|nghị\s+quyết|nghị\s+định|chỉ\s+thị'
                        r'|thủ\s+tục|quy\s+định|nội\s+dung|điều|khoản|điểm))\b|\bsau\s+đây\b|\bsau\s*:', re.I)
OPENER = re.compile(r'(?:\bsau(?:\s+đây)?|\bnhư\s+sau|\bgồm|\bcụ\s+thể(?:\s+như\s+sau)?|\bbao\s+gồm)?\s*:\s*$', re.I)
# A quote that is a phrase or a name, not inserted wording: "thay cụm từ “A” bằng cụm từ “B”", "Quyết định số X “Về việc …”".
PHRASE_BEFORE = re.compile(r'(?:cụm\s+từ|từ\s+ngữ|\btừ|\bchữ|tên\s+gọi|\btên|\bcó\s+tên|\blà|\bbằng|\bthành|\bgọi\s+là)\s*$', re.I)
NAME_BEFORE = re.compile(r'\d+[a-zđ]?\s*/\s*(?:\d{4}\s*/\s*)?[A-ZĐ][\w./-]*(?:\s+ngày\s+[\d/.\-]+(?:\s+năm\s+\d{4})?)?[^“"]{0,40}$', re.I)
# A list of administrative procedures: its heading carries the act on each row (rubric "Phụ lục và dòng bảng"). A list of documents
# is acted on by the article that names it, not by its own heading (a heading is the list's name).
TTHC = re.compile(r'thủ\s+tục\s+hành\s+chính|\bTTHC\b', re.I)
ACT_COLUMN = re.compile(r'thay\s*thế|b[ãả]i\s*bỏ|sửa\s*đổi|bổ\s*sung|h(?:uỷ|ủy)\s*bỏ', re.I)
# Where the model may say the target came from (extract.ORIGINS), as fields.
ORIGIN_FIELD = {'don_vi': 'don_vi', 'cau_dan': 'cau_dan', 'ten_dieu': 'ten_dieu', 'ten_chuong': 'chuong', 'ten_van_ban': 'ten_van_ban'}
# A lead that names one provision ("Sửa đổi, bổ sung khoản 2 Điều 3 như sau:") introduces its new wording, not a list of targets.
PROVISION = re.compile(r'\b(?:điểm\s+[a-zđ]\w?|khoản\s+\d+[a-zđ]?|điều\s+\d+[a-zđ]?|chương\s+[IVXLCDM\d]+|mục\s+[IVXLCDM\d]+(?:\.\d+)*|phụ\s+lục\s+(?:số\s+)?[IVXLCDM\d]+|tên\s+(?:điều|chương|mục))\b', re.I)


def quote_spans(text):
    """[(start, end)] of the outermost quoted spans. Curly quotes nest: the new wording “i) Thay thế cụm từ “A” bằng cụm từ “B” tại …”
    is one span with two phrases inside. A straight quote runs to the next one. A curly quote that never closes runs to the end; one
    that never balances (“A bằng cụm từ “B”: a mark is missing) ends at its first closing mark, so the rest of the text stays visible."""
    spans, k, n = [], 0, len(text)
    while k < n:
        if text[k] == '“':
            depth, j, first = 0, k, None
            while j < n:
                if text[j] == '“':
                    depth += 1
                elif text[j] == '”':
                    depth -= 1
                    first = j if first is None else first
                    if depth == 0:
                        break
                j += 1
            end = j + 1 if j < n else first + 1 if first is not None else n
        elif text[k] == '"':
            j = text.find('"', k + 1)
            end = j + 1 if j >= 0 else n
        else:
            k += 1
            continue
        spans.append((k, end))
        k = end
    return spans


def quotes(text):
    """[(start, end, role)] of the quoted spans of a text: 'noi_dung_moi' for wording inserted into the target (after "như sau:" or
    a colon, or a quote that starts with a provision label, spans lines or is long), 'cum_tu' for a phrase or a name, 'trich' for any
    other quotation (a retold sentence). Only 'noi_dung_moi' and 'trich' hold no act of this document."""
    out, text = [], text or ''
    for start, end in quote_spans(text):
        inner = text[start + 1:end].rstrip('”"')
        before = text[max(0, start - 60):start]
        short = len(inner) <= 200 and '\n' not in inner
        # A colon right before the quote opens wording, also after a document number ("Quyết định số X như sau: “…”").
        colon = re.search(r'(?:như\s+sau|sau\s+đây)?\s*:\s*$', before)
        if short and not colon and (PHRASE_BEFORE.search(before) or NAME_BEFORE.search(before)):
            role = 'cum_tu'
        elif colon or re.match(r'\s*(?:Điều\s+\d|\d+[a-zđ]?\.|[a-zđ]\))', inner) or not short:
            role = 'noi_dung_moi'
        else:
            role = 'trich'
        out.append((start, end, role))
    return out


def outside_wording(text):
    """The text with inserted wording and retold quotations blanked out (same length, so offsets stay)."""
    chars = list(text or '')
    for start, end, role in quotes(text):
        if role != 'cum_tu':
            chars[start:end] = ' ' * (end - start)
    return ''.join(chars)


def only_in_new_wording(row, target):
    """The fields the model read name the target, but only inside wording inserted into a document. Such a document ("Sửa đổi, bổ
    sung khoản 10 Điều 18 như sau: “a) Sửa đổi … Thông tư số 31/2023/TT-BGDĐT …”") is a target of the amending act whose wording it
    is, not of this document."""
    seen = False
    for text in fields(row).values():
        if not names(text, target):
            continue
        seen, chars = True, list(text)
        for start, end, role in quotes(text):
            if role == 'noi_dung_moi':
                chars[start:end] = ' ' * (end - start)
        if names(''.join(chars), target):
            return False
    return seen


def fields(row):
    """{field: text} the model was shown for this unit (validate.sources, by name)."""
    unit, ctx = row.get('_unit') or {}, row.get('_context') or {}
    return {'don_vi': unit.get('noi_dung') or '', 'cau_dan': unit.get('cau_dan') or '', 'danh_sach': unit.get('danh_sach_kem_theo') or '',
            'ten_dieu': ctx.get('ten_dieu') or '', 'cau_dan_dieu': ctx.get('cau_dan_dieu') or '', 'chuong': ctx.get('chuong') or '',
            'ten_van_ban': (ctx.get('van_ban') or {}).get('ten') or '', 'phan_dau': ctx.get('phan_dau') or ''}


def opens_list(lead):
    """The lead opens a list of what it acts on: it ends with a colon, names a set (not one provision) and names no provision as its
    object. "Bãi bỏ 15 văn bản … sau:" opens a list; "Sửa đổi khoản 2 Điều 3 như sau:" introduces new wording."""
    plain = ' '.join(strip_quotes(lead or '').split())
    return bool(plain) and bool(OPENER.search(plain)) and bool(COLLECTIVE.search(plain)) and not PROVISION.search(plain)


# A lead whose act on whole documents stands right before the colon ("Quyết định này bãi bỏ:"): its object is the list below.
# Used only to tie the act to an item; opens_list (what goes to the model) is unchanged (audit 29/10/2026, 730798).
BARE_ACT = re.compile(r'\b(?:b[ãả]i\s*bỏ|h(?:uỷ|ủy|uy)\s*bỏ|thay\s*thế)(?:\s+toàn\s+bộ)?\s*:\s*$', re.I)


def bare_list_lead(lead):
    plain = ' '.join(strip_quotes(lead or '').split())
    return bool(BARE_ACT.search(plain)) and not PROVISION.search(plain)


def clause_of_article(path):
    return bool(re.fullmatch(r'(?:Phụ lục \d+ )?(?:Văn bản kèm theo \d+ )?Điều \S+ Khoản \S+', path or ''))


def owner(path, field):
    """The unit that holds a lead: the article for its lead or heading, the clause for the lead of its points."""
    if field == 'cau_dan':
        return re.sub(r'\s+điểm\s+\S+$', '', path)
    return re.sub(r'\s+Khoản\s+\S+(?:\s+điểm\s+\S+)?$', '', path)


LAW = re.compile(r'^(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Hiến\s+pháp)\s+\S', re.I)
# A number of the old form, with a dash and no slash before the body ("83-CP", "50-HĐBT", "38-HD/BTCTW").
DASHED = re.compile(r'(?<![\w/-])\d{1,6}-[A-ZĐ][A-Za-zĐđ]{1,9}(?:/[A-ZĐ][A-ZĐa-zđ0-9-]*)?(?![\w-])')


def refs(text):
    """Document numbers in text, in order: the usual form and the old dashed one."""
    found = list(document_refs(text or '')) + [m for m in DASHED.finditer(text or '')]
    return sorted(found, key=lambda m: m.start())


SPACE = '[\\s\u200b\u200c\u200d\u2060\ufeff]*'


def spans(text, target):
    """[(start, end)] where the text names the target, as printed: spaces may stand inside the number ("32/2012/QĐ- U BND"), 'Đ'
    may be typed 'Ð', a dash '–', and a leading zero may be left out. A longer number that holds the target ("132/2012/QĐ-UBND",
    "32/2012/QĐ-UBND-VX") does not name it."""
    key = number_key(target)
    if not key:
        return []
    body = SPACE.join('[đĐðÐ]' if ch == 'đ' else '[-–—]' if ch == '-' else re.escape(ch) for ch in key)
    head = r'(?<![\d/])(?<!\w-)0*' if key[0].isdigit() else r'(?<!\w)'
    return [m.span() for m in re.finditer(head + body + r'(?!\w|[-–—/]\w)', text or '', re.I)]


def names(text, target):
    """The text names the target: its number, or the name of a law named by name ("Luật Đất đai")."""
    if not target:
        return False
    if LAW.match(target) and ' '.join(target.split()).casefold() in ' '.join((text or '').split()).casefold():
        return True
    return bool(spans(text, target))


# Words that start a document's name after its number ("Quyết định X về việc …", "Thông tư Y hướng dẫn …"): a document named after
# them, before the next ";", is part of that name.
NAME_WORD = re.compile(r'\b(?:v\s*ề|v/v|quy\s+định|hướng\s+dẫn|ban\s+hành|sửa\s+đổi|bổ\s+sung|b[ãả]i\s+bỏ|thay\s+thế|h(?:uỷ|ủy|uy)\s+bỏ'
                       r'|công\s+bố|phê\s+duyệt|thành\s+lập|đính\s+chính|gia\s+hạn|áp\s+dụng|thực\s+hiện)\b', re.I)


def heads(text):
    """[(start, end, begin)] of the documents an item acts on: the first document it names, and each next one joined to it by a
    date, an issuer, "và", "," or ";" ("1307/QĐ-BXD ngày 29/10/2008 và 91/QĐ-BXD …"). A document after a name word ("Quyết định X về
    việc sửa đổi Điều 2 của Quyết định Y"), in another cell or on another line is no head. begin: where the words before the head
    start (the text, or the end of the head before it)."""
    found, out = refs(text), []
    for i, m in enumerate(found):
        if i:
            gap = text[found[i - 1].end():m.start()]
            if '|' in gap or '\n' in gap or NAME_WORD.search(gap.rsplit(';', 1)[-1]):
                break
        out.append((m.start(), m.end(), found[i - 1].end() if i else 0))
    return out


def head_of(text, target):
    """The head of the item that is the target, or None. A target named before any number the item reads as a document heads the
    item too: a law named by name, a number printed with a space before its slash ("96 /QĐ-UBND")."""
    at = spans(text, target)
    if not at:
        return None
    found = heads(text)
    head = next((h for h in found if any(start == h[0] for start, _ in at)), None)
    if head is None and (not found or at[0][0] < found[0][0]):
        head = (at[0][0], at[0][1], 0)
    return head


def acts_on(text, target):
    """The item acts on the target: the target is one of its heads."""
    return head_of(text, target) is not None


def listed(row, target):
    """A row of the documents listed with the unit (an attachment the unit acts on) acts on the target."""
    return any(acts_on(line, target) for line in fields(row)['danh_sach'].split('\n') if line.strip())


def governing(row):
    """[(field, text, kind)] that may perform the act on this unit, nearest first. kind:
    - 'unit': the unit itself (an article with no clauses includes its heading);
    - 'lead': the lead of the unit's parent ("Sửa đổi, bổ sung Mục II Phụ lục … như sau:", "Thông tư này hướng dẫn … Quyết định số
      X …:"): the act is the parent's, and moves to it;
    - 'list': a lead that opens a list of what is acted on; the item names the target and the act stays on the item;
    - 'row_heading', 'row_column': the heading of a list of procedures, a column naming the act ("Áp dụng thay thế"), for a table row;
    - 'holder': the article acting on the documents an attachment lists, for a row of that attachment; the act moves to it."""
    f, path = fields(row), row.get('source_path') or ''
    out = [('don_vi', f['don_vi'], 'unit')]
    if ' STT ' in path:
        if TTHC.search(f['cau_dan'] + ' ' + f['ten_dieu']):
            out += [('cau_dan', f['cau_dan'], 'row_heading'), ('ten_dieu', f['ten_dieu'], 'row_heading')]
        else:
            columns = f['cau_dan'].split('\n')[-1]
            if ACT_COLUMN.search(columns):
                out.append(('cau_dan', columns, 'row_column'))  # "Áp dụng thay thế": the column names the act of each row
        holder = (row.get('_context') or {}).get('_dieu_thuc_hien')
        if holder:
            out.append(('cau_dan_dieu', holder.get('noi_dung') or '', 'holder'))
        return out
    if re.fullmatch(r'(?:Phụ lục \d+ )?(?:Văn bản kèm theo \d+ )?Điều \S+', path):
        out.append(('ten_dieu', f['ten_dieu'], 'unit'))  # an article's heading states the act of its own body ("Điều 2. Bãi bỏ …")
        return out
    leads = [('cau_dan', f['cau_dan'])] if ' điểm ' in path else [('cau_dan_dieu', f['cau_dan_dieu']), ('ten_dieu', f['ten_dieu'])] \
        if clause_of_article(path) else []
    for name, text in leads:
        if text:
            out.append((name, text, 'list' if opens_list(text) else 'lead'))
    return out


def sentence_at(text, start, end):
    """The sentence of text around [start, end): from the last stop (". ", a new line) before it to the next new line."""
    dot = text.rfind('. ', 0, start)
    begin = max(text.rfind('\n', 0, start) + 1, dot + 2 if dot >= 0 else 0)
    stop = text.find('\n', end)
    return text[begin:stop if stop > 0 else len(text)].strip()


def performer(row, verb, target=''):
    """(field, sentence, kind, tied) of the text that performs the act on this unit, nearest first; None if no governing text states
    the act's verb outside inserted wording. tied: the text is tied to the target by structure. The unit's sentence names the verb and
    the target together, or the target is named above the unit (its lead, the article heading, the chapter, the title); a lead names
    the target itself ('lead'), or opens a list whose item names it ('list'); a row heading, an act column or the acting article
    governs a row that names it. A verb elsewhere in a long unit is no evidence for this target: the act stays untied."""
    f = fields(row)
    above = any(names(f[name], target) for name in ('cau_dan', 'ten_dieu', 'cau_dan_dieu', 'chuong', 'ten_van_ban'))
    in_list = listed(row, target)
    loose = None
    for name, text, kind in governing(row):
        if not verb or not text:
            continue
        plain = outside_wording(text)
        hits = [m for m in re.finditer(verb, plain, re.I)]
        if not hits:
            continue
        if kind == 'unit':
            for m in hits:
                sentence = sentence_at(text, m.start(), m.end())
                rest = text[text.find(sentence) + len(sentence):] if sentence in text else ''
                # The same sentence names the target; or it opens a list in the unit that names it ("Bổ sung, sửa đổi 13 thủ tục hành
                # chính như sau: - … Quyết định số X"); or the heading states the act of the body that names it; or the opening
                # (title and issuing sentence) is one statement.
                if names(sentence, target) or above or in_list or ((opens_list(sentence) or bare_list_lead(sentence)) and names(rest, target)) \
                        or (name == 'ten_dieu' and names(f['don_vi'], target)) or (row.get('source_path') == 'Phần đầu' and names(text, target)):
                    return name, sentence, kind, True
            loose = loose or (name, sentence_at(text, hits[0].start(), hits[0].end()), kind, False)
            continue
        sentence = sentence_at(text, hits[0].start(), hits[0].end())
        if kind == 'list':
            if names(f['don_vi'], target) or in_list:
                return name, sentence, kind, True
            if names(text, target):
                return name, sentence, 'lead', True  # the lead names its own target: the items are its content
        elif kind == 'lead' and (names(text, target) or above):
            return name, sentence, kind, True
        elif kind in ('row_heading', 'row_column', 'holder') and names(f['don_vi'], target):
            return name, sentence, kind, True
        loose = loose or (name, sentence, kind, False)
    return loose


def pieces(quote, row, allowed):
    """[{field, text}] verbatim pieces of the model's quote, each found in one allowed field, when together they cover the quote
    (the model may join a lead and an item and leave the items between out); None when the quote is not in the source."""
    texts = {name: ' '.join(text.split()) for name, text in fields(row).items() if name in allowed and text}
    q = ' '.join((quote or '').split())
    found, i = [], 0
    while i < len(q):
        if q[i] == ' ':
            i += 1  # a piece starts at a word: " Quyết định s" from a lead would cut "Quyết định số 3155/…" of the item in two
            continue
        n, where = 0, None
        for size in range(len(q) - i, MIN_PIECE - 1, -1):
            where = next((name for name, text in texts.items() if q[i:i + size] in text), None)
            if where:
                n = size
                break
        if not n:
            i += 1
            continue
        found.append({'field': where, 'text': q[i:i + n]})
        i += n
    covered = sum(len(p['text'].replace(' ', '')) for p in found)
    return found if found and covered >= COVER * len(q.replace(' ', '')) else None


def allowed(row):
    """Fields the evidence of this act may stand in: its governing texts, the unit and the documents listed with it, and the field
    the model said the target came from."""
    found = {name for name, _, _ in governing(row)} | {'don_vi', 'danh_sach'}
    origin = ORIGIN_FIELD.get(row.get('target_from') or '')
    if origin:
        found.add(origin)
    if (row.get('source_path') or '') == 'Phần đầu':
        found |= {'ten_van_ban', 'phan_dau'}
    return found


def target_snippet(row):
    """The sentence of the unit (or of the documents listed with it) that names the target: the target part of evidence the code finds."""
    for name in ('don_vi', 'danh_sach'):
        text = fields(row)[name]
        for start, stop in spans(text, row.get('target_document') or '')[:1]:
            dot = text.rfind('. ', 0, start)
            begin = max(text.rfind('\n', 0, start) + 1, dot + 2 if dot >= 0 else 0)
            end = text.find('\n', stop)
            return ' '.join(text[begin:end if end > 0 else len(text)].split())[:300]
    return None


def role(piece, verb, target):
    """'thuc_hien' (the piece states the act), 'dich' (it names the target), or 'ngu_canh' (context)."""
    if verb and re.search(verb, outside_wording(piece['text']), re.I):
        return 'thuc_hien'
    if target and spans(piece['text'], target):
        return 'dich'
    return 'ngu_canh'


ITEM_LABEL = re.compile(r'^\s*(?:\d+[a-zđ]?\s*[.)]|[a-zđ]\)|[-–+•])\s*', re.I)


def item_object(row, target):
    """What an item of a list acts on, when a lead performs the act on it (or the unit acts on the documents listed with it):
    ('van_ban', None) when the item names the target document itself; ('vi_tri', text) when it names a provision of it first
    ("Khoản 2 Điều 3 Quyết định số X"); None when the unit is no item or the target is not the document it names first. What follows
    the document's number is its name ("Quyết định X về việc sửa đổi khoản 2 Điều 3 …"): never the scope of this act."""
    acting = row.get('_performer')
    f = fields(row)
    lines = [f['don_vi']] if acting and acting[2] in ('list', 'holder') else []
    lines += [line for line in f['danh_sach'].split('\n') if line.strip()]
    for line in lines:
        head = head_of(line, target)
        if head is None:
            continue
        before = ITEM_LABEL.sub('', line[head[2]:head[0]].split('|')[-1])
        # A head joined to the one before: its own words start after that document's date and the joining word.
        before = re.sub(r'^\s*(?:ngày\s+[\d\s/.\-]+(?:tháng\s+\d+\s+năm\s+\d{4})?)?[\s,;]*(?:và|hoặc)?\s+', '', before, flags=re.I).strip(' ,;:')
        before = re.sub(r'\s*(?:của|tại|thuộc|trong|ban\s+hành\s+kèm\s+theo|kèm\s+theo)\s*(?:Quyết\s+định|Thông\s+tư|Nghị\s+định|Nghị\s+quyết|Chỉ\s+thị)?\s*(?:số)?$', '', before, flags=re.I)
        return ('vi_tri', before) if PROVISION.search(before) else ('van_ban', None)
    return None
