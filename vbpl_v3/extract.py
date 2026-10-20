"""Layer 2, semantic extraction: the model reads each unit with its structural context and states the acts the unit itself performs,
as written, with a verbatim quote. It never builds node IDs or matches documents: the resolver (layer 3) and the validator (layer 4) do.

One call per article, at most UNITS_PER_CALL units each. Quoted new content is shortened: an act is never inside it.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import re

from .llm import validated_json
from .text import action_matches
from .structure import appendix_label
from .prompts import load

ACTIONS = ['sua-doi', 'bo-sung', 'bai-bo', 'thay-the', 'thay-cum-tu', 'huy-bo', 'dinh-chi', 'ngung-hieu-luc', 'dinh-chinh', 'gia-han',
           'huong-dan', 'quy-dinh-chi-tiet']
SECTIONS = ['quyet_dinh', 'kem_theo', 'khong_ro', 'khong_ap_dung']
ORIGINS = ['don_vi', 'cau_dan', 'ten_dieu', 'ten_chuong', 'ten_van_ban']
# Any word of an act, however weak: only units without one are skipped.
SIGNAL = re.compile(r'sửa|bổ\s*sung|bỏ|thay|h[uủ]y|huỷ|đình\s*chỉ|ngưng|ngừng|hết\s+hiệu\s*lực|đính\s*chính|gia\s+hạn|kéo\s+dài|hướng\s+dẫn'
                    r'|kết\s*thúc|chấm\s*dứt'
                    r'|quy\s+định\s+chi\s+tiết|điều\s+chỉnh', re.I)
UNITS_PER_CALL = 5
QUOTE_KEEP = 160
MAX_PARALLEL = 10  # calls of one document in flight; the gate in llm.py sets the real limit

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['units'], 'properties': {'units': {
    'type': 'array', 'description': 'Một phần tử cho MỖI đơn vị trong don_vi, cùng thứ tự.', 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['source_path', 'acts'], 'properties': {
            'source_path': {'type': 'string', 'description': 'Chép đúng source_path của đơn vị trong don_vi.'},
            'acts': {'type': 'array', 'description': 'Các hành động pháp lý câu của đơn vị nêu; rỗng nếu không có.', 'items': {
                'type': 'object', 'additionalProperties': False,
                'required': ['action', 'performed', 'target_document', 'target_from', 'target_section', 'target_text', 'target_part', 'evidence'],
                'properties': {
                    'action': {'type': 'string', 'enum': ACTIONS, 'description': 'Loại hành động. "Sửa đổi, bổ sung X" là hai act: sua-doi và bo-sung.'},
                    'performed': {'type': 'boolean', 'description': 'true khi chính đơn vị thực hiện hành động; false khi chỉ nhắc tới '
                                  '(lịch sử, căn cứ, trích dẫn, nội dung mới trong ngoặc kép, đề nghị, giao nhiệm vụ, tên danh mục).'},
                    'target_document': {'type': 'string', 'description': 'Số hiệu văn bản đích đúng như nguồn viết ("28/2017/QĐ-UBND"), '
                                        'hoặc "Luật <tên>" khi chỉ nêu tên. Không phải chính văn bản này.'},
                    'target_from': {'type': 'string', 'enum': ORIGINS, 'description': 'Nơi đọc được văn bản đích.'},
                    'target_section': {'type': 'string', 'enum': SECTIONS, 'description': 'Vị trí thuộc chính văn bản đích (quyet_dinh), '
                                       'thuộc văn bản ban hành kèm theo và câu nói rõ (kem_theo), không rõ thuộc phần nào (khong_ro), '
                                       'hoặc tác động lên cả văn bản (khong_ap_dung).'},
                    'target_text': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Mỗi vị trí một phần tử, đủ cấp '
                                    '("điểm b khoản 5 Điều 1", "Phụ lục II", "Mục D.2 Phụ lục I"); rỗng khi tác động lên cả văn bản.'},
                    'target_part': {'type': 'string', 'maxLength': 200, 'description': 'Tên phần bị tác động khi câu chỉ nêu bằng tên; "" nếu không có.'},
                    'evidence': {'type': 'string', 'maxLength': 300,
                                 'description': 'Chép NGUYÊN VĂN đoạn câu ngắn nhất thực hiện hành động, lấy từ một trường của nguồn.'}}}}}}}}}

PROMPT = load('extract_quan_he')
# A document number ("2074/QĐ-UBND", "52/2015/TT-BTC") in a table row: the row may name the document it acts on.
ROW_NUMBER = re.compile(r'\b\d+[a-zđ]?\s*/\s*(?:\d{4}\s*/\s*)?[A-ZĐ][A-ZĐa-zđ0-9\-]*', re.U)
# A heading of a section of an appendix: "A. DANH MỤC …", "II. LĨNH VỰC …", "Phần B - …".
SECTION_HEAD = re.compile(r'^\s*(?:(?:Phần|PHẦN|Mục|MỤC)\s+)?([A-ZĐ]|[IVXLCDM]+|\d+)\s*(?:[.)\-–:]\s*|\s+-\s+)\S')
ROW_TEXT = 1500
# Columns that give a row's legal basis ("Căn cứ pháp lý", "Tên VBQPPL quy định việc bãi bỏ"): the documents there are no targets.
BASIS_COLUMN = re.compile(r'căn\s+cứ|VBQPPL|văn\s+bản\s+quy\s+phạm|quy\s+định\s+(?:việc|nội\s+dung)', re.I)


def procedure(text):
    """The name of the procedure a row lists: its first cell after the row number, before its code or note."""
    cells_ = [c for c in text.split(' | ') if c and not re.fullmatch(r'\d+[a-zđ]?\.?', c)]
    name = cells_[0] if cells_ else text
    return re.split(r'\s*(?:\(|Mã\s+số|Mã\s+TTHC)', name, maxsplit=1)[0].strip(' .;:-')[:200]


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def table_units(parsed):
    """[(key, context, [unit])]: the rows of the appendices that have no articles, one unit per row that names a document and holds
    an act word (in the row, its section heading or the appendix title). source_path "Phụ lục <n> [Mục <section>] STT <k>": n counts the
    appendices from 1, k is the row number of the first column, or the row's place in its table. The legal-basis column ("Căn cứ pháp
    lý") is left out: the documents there are no targets. The heading and the column names are the unit's lead."""
    groups = []
    for index, appendix in enumerate(parsed['phu_luc']):
        if appendix['dieu_luat']:
            continue
        title = ' '.join(appendix['tieu_de'].split())[:500]
        section, heading, header, drop, count, seen, items = None, '', [], set(), 0, set(), []
        for line in (appendix.get('noi_dung') or '').split('\n'):
            line = line.strip()
            if not line:
                continue
            if not line.startswith('|'):
                head = SECTION_HEAD.match(line)
                if head:
                    section, heading, header, count = head[1], line[:300], [], 0
                continue
            row = cells(line)
            filled = [c for c in row if c]
            if not filled:
                continue
            if len(filled) <= 2 and (re.fullmatch(r'(?:[A-ZĐ]|[IVXLCDM]+)\.?', filled[0]) or SECTION_HEAD.match(filled[0])):
                # A section heading written as a row of the table ("| A | DANH MỤC TTHC ĐƯỢC SỬA ĐỔI |").
                head = SECTION_HEAD.match(' '.join(filled)) or re.match(r'([A-ZĐ]|[IVXLCDM]+)', filled[0])
                section, heading, count = head[1], ' '.join(filled)[:300], 0
                continue
            first = row[0].rstrip('.')
            if not header and not re.fullmatch(r'\d+[a-zđ]?', first):
                header = row
                drop = {k for k, name in enumerate(header) if BASIS_COLUMN.search(name)}
                continue
            count += 1
            number = first if re.fullmatch(r'\d+[a-zđ]?', first) else str(count)
            text = ' | '.join(c for k, c in enumerate(row) if c and k not in drop)[:ROW_TEXT]
            lead = '\n'.join(x for x in (heading, ' | '.join(h for k, h in enumerate(header) if k not in drop)) if x)
            columns = ' | '.join(h for k, h in enumerate(header) if k not in drop)
            # The act may be written in the row, its section heading, the appendix title, or a column name ("Áp dụng thay thế").
            if not ROW_NUMBER.search(text) or not (action_matches(text) or action_matches(heading) or action_matches(title)
                                                   or re.search(r'thay\s*thế|b[ãả]i\s*bỏ|sửa\s*đổi|bổ\s*sung|h(?:uỷ|ủy)\s*bỏ', columns, re.I)):
                continue
            path = f'Phụ lục {index + 1}' + (f' Mục {section}' if section else '') + f' STT {number}'
            if path in seen:
                continue  # a second table restarting its numbers under the same heading: its rows have no path of their own
            seen.add(path)
            items.append({'source_path': path, 'cau_dan': lead, 'noi_dung': text})
        if items:
            # What the main text says of this appendix ("Công bố kèm theo Quyết định này Danh mục văn bản hết hiệu lực …" or "Bãi bỏ các
            # văn bản tại Phụ lục II"): the model needs it to tell a list of this document's acts from a list it only publishes.
            about = article_about(parsed, appendix)
            context = {'chuong': '', 'ten_dieu': title,
                       'cau_dan_dieu': f'{about["source_path"]} nói về phụ lục này: {about["noi_dung"][:800]}' if about else ''}
            holder = acting_article(parsed, appendix)
            if holder:
                context['_dieu_thuc_hien'] = holder
            groups.append((f'Phụ lục {index + 1}', context, items))
    return groups


# How a main text names the part attached to it: "danh mục / danh sách / phụ lục / biểu … kèm theo, đính kèm", "có danh sách kèm theo".
ATTACHED = r'(?:danh\s+mục|danh\s+sách|phụ\s+lục|biểu)'
GENERIC_APPENDIX = (ATTACHED + r'[^.;]{0,160}?(?:kèm\s+theo|đính\s+kèm)|(?:kèm\s+theo|đính\s+kèm)[^.;]{0,40}?' + ATTACHED)


PROSE_CHUNK = 5000


def prose_units(parsed):
    """[(key, context, [unit])]: appendices written as prose (no articles, hardly a table), cut into their numbered sections like a
    text without articles: "Phụ lục <n> Mục <m>", or "Phụ lục <n>" when they have none. A long section goes in parts with its path."""
    from .structure import split_sections
    groups = []
    for index, appendix in enumerate(parsed['phu_luc']):
        if appendix['dieu_luat']:
            continue
        lines = [l for l in (appendix.get('noi_dung') or '').split('\n') if l.strip()]
        rows = sum(1 for l in lines if l.lstrip().startswith('|'))
        if not lines or rows >= 3 and rows > 0.3 * len(lines):
            continue  # a table: its rows are units of table_units()
        text = '\n'.join(l for l in lines if not l.lstrip().startswith('|'))
        sections = split_sections(text) or [{'so_muc': None, 'noi_dung': text}]
        title = ' '.join(appendix['tieu_de'].split())[:500]
        items = []
        for section in sections:
            body = section['noi_dung']
            if not SIGNAL.search(body) or not ROW_NUMBER.search(body):
                continue
            path = f'Phụ lục {index + 1}' + (f' Mục {section["so_muc"]}' if section['so_muc'] else '')
            parts = [body[k:k + PROSE_CHUNK] for k in range(0, len(body), PROSE_CHUNK)]
            items += [{'source_path': path, 'cau_dan': '', 'noi_dung': part} for part in parts]
        for item in items:
            groups.append((item['source_path'], {'chuong': '', 'ten_dieu': title, 'cau_dan_dieu': ''}, [item]))
    return groups


def appendix_named(appendix):
    """How the main text names this appendix: "Phụ lục II", "Phụ lục Danh mục II", "Danh mục II"."""
    label = appendix.get('ky_hieu') or appendix_label(appendix)
    return rf'(?:phụ\s+lục|danh\s+mục)(?:\s+danh\s+mục)?\s+(?:số\s+)?{re.escape(label)}\b' if label else None


def main_units(parsed):
    """(source_path, text) of the main text: the article with its heading ("Điều 2. Bãi bỏ các Quyết định … (Phụ lục Danh mục II kèm
    theo)" may put the act in the heading), then its clauses."""
    for article in parsed['dieu_luat']:
        path = 'Điều ' + article['ky_hieu']
        head = ' '.join(x for x in (article['tieu_de'], article.get('mo_dau') or ('' if article['khoan'] else article['noi_dung'])) if x)
        yield path, head
        yield from [(f'{path} Khoản {k["ky_hieu"]}', k['noi_dung']) for k in article['khoan']]


def naming(parsed, appendix, test):
    """The first main-text unit that names this appendix and passes test: by its label first, then, when the document has a single
    appendix without articles, by "danh mục / phụ lục … kèm theo, đính kèm"."""
    label = appendix_named(appendix)
    tables = [p for p in parsed['phu_luc'] if not p['dieu_luat']]
    for pattern in [label] + ([GENERIC_APPENDIX] if len(tables) == 1 or not label else []):
        if not pattern:
            continue
        for unit_path, text in main_units(parsed):
            if re.search(pattern, text, re.I) and test(text):
                return {'source_path': unit_path, 'noi_dung': text[:3000]}
    return None


def article_about(parsed, appendix):
    """{source_path, noi_dung} of the main-text unit that names an appendix, whatever it does with it; None if none does."""
    return naming(parsed, appendix, lambda text: True)


def acting_article(parsed, appendix):
    """{source_path, noi_dung} of the main-text unit that performs an act on the documents an appendix lists ("Bãi bỏ các văn bản tại Phụ
    lục II", "Bãi bỏ các Quyết định có tên trong Danh mục kèm theo"), or None. "Công bố kèm theo Quyết định này Danh mục …" acts on none."""
    return naming(parsed, appendix, lambda text: bool(action_matches(text)) and not re.search(r'\bcông\s+bố\b', text[:200], re.I))


def listed_documents(appendix, limit=12000):
    """The rows of an appendix that name a document, as "STT <k>: <row>", the legal-basis column left out: what an article acting on
    "các văn bản tại Phụ lục II" acts on."""
    out, header, drop = [], [], set()
    for line in (appendix.get('noi_dung') or '').split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            continue
        row = cells(line)
        if not header and not re.fullmatch(r'\d+[a-zđ]?\.?', row[0] or ''):
            header, drop = row, {k for k, name in enumerate(row) if BASIS_COLUMN.search(name)}
            continue
        text = ' | '.join(c for k, c in enumerate(row) if c and k not in drop)
        if ROW_NUMBER.search(text):
            out.append(text[:400])
    return '\n'.join(out)[:limit]


def acting_lists(parsed):
    """{source_path: rows}: the documents listed in the appendices a main-text unit acts on."""
    lists = {}
    for appendix in parsed['phu_luc']:
        if appendix['dieu_luat']:
            continue
        holder = acting_article(parsed, appendix)
        rows = listed_documents(appendix) if holder else ''
        if rows:
            lists[holder['source_path']] = (lists.get(holder['source_path'], '') + '\n' + rows).strip()
    return lists


LIST_PART = 5    # documents per call when a unit acts on a long list
LIST_MIN = 8     # a unit naming at least this many documents is asked in parts


def list_parts(unit):
    """The unit as it is asked: itself, or copies that keep its lead and carry LIST_PART documents each, when it names LIST_MIN or
    more ("Hủy bỏ 44 công trình … tại các Nghị quyết: số 200/…; số 26/…; …", or a danh_sach_kem_theo of 25 rows)."""
    listed = unit.get('danh_sach_kem_theo') or ''
    if listed:
        rows = [r for r in listed.split('\n') if r.strip()]
        if len(rows) < LIST_MIN:
            return [unit]
        return [{**unit, 'danh_sach_kem_theo': '\n'.join(rows[k:k + LIST_PART])} for k in range(0, len(rows), LIST_PART)]
    text = unit['noi_dung']
    found = list(ROW_NUMBER.finditer(text))
    if len(found) < LIST_MIN:
        return [unit]
    # Cut just before every LIST_PART-th document, whatever separates the items (",", ";", "và", new lines). Each part keeps the lead
    # ("Hủy bỏ 44 công trình, dự án … tại các Nghị quyết:") that states the act.
    def start(m):
        before = re.search(r'(?:\b(?:số|Nghị\s+quyết|Quyết\s+định|Thông\s+tư|Nghị\s+định|Chỉ\s+thị)\s+)*$', text[:m.start()], re.I)
        return before.start() if before else m.start()
    cuts = [start(found[k]) for k in range(0, len(found), LIST_PART)]
    lead = text[:cuts[0]]
    bounds = cuts[1:] + [len(text)]
    return [{**unit, 'noi_dung': (lead + text[a:b]).strip()} for a, b in zip(cuts, bounds)]


def shorten_quotes(text):
    """New wording in quotes holds no act of this document: keep its start only."""
    return re.sub(r'“([^”]{%d})[^”]+”' % QUOTE_KEEP, r'“\1 …”', text)


def units(parsed):
    """[(article key, context, [unit])]: units of each article (and of the opening part), with what the model needs to read them.
    A unit is {source_path, cau_dan, noi_dung}; the article context holds its chapter, heading and lead."""
    groups = []
    lists = acting_lists(parsed)
    articles = [(a, '') for a in parsed['dieu_luat']] + [(a, f'Phụ lục {i + 1} ') for i, p in enumerate(parsed['phu_luc']) for a in p['dieu_luat']]
    for article, prefix in articles:
        if article.get('van_ban_kem_theo'):
            prefix += f'Văn bản kèm theo {article["van_ban_kem_theo"]} '
        path = prefix + 'Điều ' + article['ky_hieu']
        context = {'chuong': article.get('chuong', ''), 'ten_dieu': article['tieu_de'], 'cau_dan_dieu': article.get('mo_dau', '')}
        items = []
        if not article['khoan']:
            items.append({'source_path': path, 'cau_dan': '', 'noi_dung': article['noi_dung']})
        for clause in article['khoan']:
            clause_path = f'{path} Khoản {clause["ky_hieu"]}'
            items.append({'source_path': clause_path, 'cau_dan': '', 'noi_dung': clause['noi_dung']})
            items += [{'source_path': f'{clause_path} điểm {p["ky_hieu"]}', 'cau_dan': clause.get('mo_dau', ''), 'noi_dung': p['noi_dung']}
                      for p in clause['diem']]
        for u in items:
            if u['source_path'] in lists:
                u['danh_sach_kem_theo'] = lists[u['source_path']]  # the documents the unit acts on, listed in an appendix
        if path in lists and not any(u['source_path'] == path for u in items):
            items.insert(0, {'source_path': path, 'cau_dan': '', 'noi_dung': article.get('mo_dau') or article['tieu_de'],
                             'danh_sach_kem_theo': lists[path]})
        signal = [u for u in items if SIGNAL.search(u['noi_dung']) or SIGNAL.search(u['cau_dan']) or u.get('danh_sach_kem_theo')]
        if signal or SIGNAL.search(context['ten_dieu'] + ' ' + context['cau_dan_dieu']):
            groups.append((path, context, signal or items[:1]))
    if not parsed['dieu_luat']:
        sections = parsed.get('noi_dung_sections') or [{'so_muc': None, 'noi_dung': parsed.get('noi_dung', '')}]
        items = [{'source_path': f'Mục {s["so_muc"]}' if s['so_muc'] else 'Nội dung', 'cau_dan': '', 'noi_dung': s['noi_dung']}
                 for s in sections if SIGNAL.search(s['noi_dung'])]
        if items:
            groups.append(('Nội dung', {'chuong': '', 'ten_dieu': '', 'cau_dan_dieu': ''}, items))
    return groups


def opening(meta, parsed):
    """The title and the issuing sentence ("Bộ trưởng … ban hành Thông tư sửa đổi …") as one unit, 'Phần đầu'. The title printed in the
    document comes first: the stored title is a shortened one that may stop before the number it acts on ("… kèm theo Quyết")."""
    printed = ' '.join((parsed.get('phan_dau') or '').split())[-1500:]
    text = '\n'.join(x for x in (printed, meta.get('title') or '', parsed.get('intro') or '') if x)
    return {'source_path': 'Phần đầu', 'cau_dan': '', 'noi_dung': text} if SIGNAL.search(text) else None


def extract(doc_id, meta, parsed, folder, caller=None, check=None):
    """All acts the model states, one row per act: {source_path, action, performed, target_document, target_from, target_section,
    target_text, target_part, evidence, _unit, _context}. Answers are cached per call, keyed by the model name."""
    document = {'so_hieu': meta.get('document_number'), 'loai': meta.get('legal_type'), 'ten': meta.get('title')}
    tables = table_units(parsed)
    calls = []
    for key, context, items in units(parsed) + tables + prose_units(parsed):
        plain = [u for u in items if len(list_parts(u)) == 1]
        calls += [(key, context, plain[k:k + UNITS_PER_CALL]) for k in range(0, len(plain), UNITS_PER_CALL)]
        # A unit acting on a long list of documents is asked in parts, each its own call: one answer for 25 documents would not
        # fit the answer limit (LLM_MAX_TOKENS), and a cut answer loses them all.
        calls += [(key, context, [part]) for u in items if len(list_parts(u)) > 1 for part in list_parts(u)]
    head = opening(meta, parsed)
    if head:
        calls.insert(0, ('Phần đầu', {'chuong': '', 'ten_dieu': '', 'cau_dan_dieu': ''}, [head]))
    errors = []

    def ask(call):
        """(answer, None), or (None, [two halves]) when the answer would be too long for one call."""
        key, context, items = call
        payload = {'van_ban': document, **{k: v for k, v in context.items() if not k.startswith('_')},
                   'don_vi': [{**u, 'noi_dung': shorten_quotes(u['noi_dung'])[:6000], 'cau_dan': u['cau_dan'][:1500]} for u in items]}
        raw = json.dumps(payload, ensure_ascii=False)
        target = folder / 'extract' / hashlib.sha256((PROMPT + raw + os.getenv('LITELLM_MODEL', '')).encode()).hexdigest()[:24]
        target.mkdir(parents=True, exist_ok=True)
        wanted = {u['source_path'] for u in items}

        def valid(answer):
            paths = [u['source_path'] for u in answer['units']]
            if set(paths) - wanted:
                raise ValueError(f'source_path không có trong đầu vào: {sorted(set(paths) - wanted)[:3]}')
        try:
            return validated_json(PROMPT, raw, target, 'acts.json', valid, schema=SCHEMA, max_tokens=4000, caller=caller, check=check,
                                  stop_on_length=len(items) > 1), None
        except ValueError as error:
            if 'chưa hoàn tất: length' not in str(error) or len(items) < 2:
                raise
            half = len(items) // 2
            return None, [(key, context, items[:half]), (key, context, items[half:])]

    # The calls of one document run side by side; llm.GATE keeps the server's limit across all documents.
    rows, calls = [], list(calls)
    while calls:
        def safe(call):
            try:
                return ask(call)
            except (ValueError, TypeError, KeyError) as error:
                # One failed call loses its own units only, not the document's other acts.
                errors.append({'stage': 'extract', 'type': type(error).__name__, 'message': str(error)[:500],
                               'units': [u['source_path'] for u in call[2]]})
                return None, None
        with ThreadPoolExecutor(min(len(calls), MAX_PARALLEL)) as pool:
            results = list(pool.map(safe, calls))
        retry = []
        for (key, context, items), (answer, halves) in zip(calls, results):
            if answer is None and halves is None:
                continue
            if halves:
                retry += halves  # too many acts for one answer: ask again in two halves
                continue
            by_path = {u['source_path']: u for u in items}
            for unit in answer['units']:
                for act in unit['acts']:
                    rows.append({**act, 'source_path': unit['source_path'], '_unit': by_path[unit['source_path']],
                                 '_context': {**context, 'van_ban': document, 'phan_dau': parsed.get('intro') or ''}})
        calls = retry
    return rows, errors
