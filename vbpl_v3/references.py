"""Relations that are not amendments: a document guiding a higher one, and in-text cross references (dẫn chiếu)."""

import re

from .relations import DOCUMENT_TYPE, lookup_numbers, resolve
from .structure import NUMBER
from .temporal import DATE, positions, to_date
from .text import action_matches, number_key

GUIDE = re.compile(r'\b(quy\s+định\s+chi\s+tiết|hướng\s+dẫn)\b', re.I)
LAW_NAME = re.compile(r'\b(Bộ\s+luật|Luật|Pháp\s+lệnh)\s+([A-ZĐÀ-Ỹ](?:[^,;()]|,\s*(?=chống\b))*?)(?=\s+(?:và|do|về|năm|số|ngày|của|đã|được|sửa|tại|theo|nhằm|trong|trên|cho|đối|thuộc)\b|\s*(?:,(?!\s*chống\b)|[;()])|\s*$)')
DOC_TYPE = (r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Nghị\s+định|Nghị\s+quyết(?:\s+liên\s+tịch)?|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định'
            r'|Chỉ\s+thị|Quy\s+chế|Quy\s+định)')
POSITION = r'((?:điểm\s+[a-zđ]\w?\s+)?(?:khoản\s+\d+[a-zđ]?\s+)?Điều\s+\d+[a-zđ]?)'
SELF_DOC = re.compile(POSITION + r'\s+(?:của\s+)?' + DOC_TYPE + r'\s+này\b', re.I)
OTHER_DOC = re.compile(POSITION + r'\s+(?:của\s+)?' + DOC_TYPE + r'\s+(?:số\s+)?(' + NUMBER.pattern + ')', re.I)
OTHER_LAW = re.compile(POSITION + r'\s+(?:của\s+)?(Bộ\s+luật|Luật|Pháp\s+lệnh)\s+(?!này\b|số\b)([A-ZĐÀ-Ỹ][^,.;()\n]{1,60}?)'
                       r'(?=\s+(?:và|thì|được|đã|có|về|năm|số|ngày|hoặc|để)\b|\s*[,.;()\n]|\s*$)')
IMPLICIT = re.compile(r'(?:theo|tại|nêu\s+tại|nêu\s+ở|như)\s+(?:quy\s+định\s+tại\s+)?' + POSITION
                      + r'(?!\s+(?:của\s+)?(?:' + DOC_TYPE + r'|này\b|số\b|năm\b))', re.I)
SAME_ARTICLE = re.compile(r'((?:điểm\s+[a-zđ]\w?\s+)?khoản\s+\d+[a-zđ]?|điểm\s+[a-zđ]\w?)\s+Điều\s+này\b', re.I)
SAME_CLAUSE = re.compile(r'(điểm\s+[a-zđ]\w?)\s+khoản\s+này\b', re.I)


def tidy(position):
    position = re.sub(r'\s+', ' ', position).strip()
    return re.sub(r'\b(?:Điểm|ĐIỂM)\b', 'điểm', re.sub(r'\b(?:Khoản|KHOẢN)\b', 'khoản', re.sub(r'\b(?:điều|ĐIỀU)\b', 'Điều', position)))


def basis_targets(can_cu):
    """{law name (casefolded): (number, date)} for laws/ordinances named in the legal basis."""
    found = {}
    for entry in can_cu or []:
        for match in LAW_NAME.finditer(entry):
            name = re.sub(r'\s+', ' ', match[2]).strip().casefold()
            tail = entry[match.end():match.end() + 160]
            number = NUMBER.match(re.sub(r'^\s*(?:số\s+)?', '', tail, flags=re.I))
            day = re.search(r'ngày\s+' + DATE, tail, re.I)
            found.setdefault(name, (number.group() if number else None, to_date(*day.groups()) if day else None))
    return found


def law_by_name(source, index, name, day):
    """The one law/ordinance with this name issued on this day (or in this year, for "Luật Nhà ở 2023"), or None."""
    when = {'term': {'issuance_date': day}} if len(day) == 10 else {'range': {'issuance_date': {'gte': f'{day}-01-01', 'lte': f'{day}-12-31'}}}
    body = {'size': 3, '_source': ['document_number', 'title', 'issuance_date', 'issuing_authority'], 'query': {'bool': {
        'filter': [{'terms': {'legal_type': ['Luật', 'Bộ luật', 'Pháp lệnh']}}, when],
        'must': [{'match_phrase': {'title': name}}]}}}
    hits = source.request('POST', f'/{index}/_search', body)['hits']['hits']
    return hits[0] if len(hits) == 1 else None


def law_named(source, index, name, before):
    """The law or ordinance a text names without a number: the base law with that exact name, latest one issued before `before`.
    Amending laws ("… sửa đổi …") and consolidated texts are not the base law. None when no law has that name."""
    kind, _, rest = name.partition(' ')
    kind = 'Bộ luật' if name.startswith('Bộ luật') else kind
    title = name if kind != 'Bộ luật' else name
    body = {'size': 20, '_source': ['document_number', 'title', 'issuance_date', 'issuing_authority'], 'sort': [{'issuance_date': 'desc'}],
            'query': {'bool': {'filter': [{'terms': {'legal_type': ['Luật', 'Bộ luật', 'Pháp lệnh']}}, {'range': {'issuance_date': {'lt': before}}}],
                               'must': [{'match_phrase': {'title': title}}]}}}
    for hit in source.request('POST', f'/{index}/_search', body)['hits']['hits']:
        rest_of_title = re.sub(r'^\S+\s+\S+\s+', '', hit['_source'].get('title') or '')
        if not re.search(r'sửa\s+đổi|bổ\s+sung|hợp\s+nhất', hit['_source'].get('title') or '', re.I):
            return hit
    return None


def guidance(doc_id, meta, parsed, lookup, law_lookup):
    """Title-declared guidance ("Thông tư hướng dẫn Nghị định X", "Nghị định quy định chi tiết Luật Y") as relation candidates.
    Only a title or preamble that names the guided document counts; a line of the legal basis is a citation, not a guidance act."""
    title = re.sub(r'\s+do\s+[^,;]*ban\s+hành\s*$', '', meta.get('title') or '')
    verb = GUIDE.search(title)
    if not verb or meta.get('legal_type') in ('Công văn', 'Văn bản hợp nhất') or action_matches(title[:verb.start()]):
        return []  # "sửa đổi Thông tư X hướng dẫn Nghị định Y": Y is guided by X, not by this document
    action = 'quy-dinh-chi-tiet' if verb[1].casefold().startswith('quy') else 'huong-dan'
    rest = title[verb.end():]
    scope = 'một số điều' if re.match(r'\s*(?:thi\s+hành\s+)?một\s+số\s+điều', rest, re.I) else 'toàn bộ'
    own = number_key(meta.get('document_number'))
    path = 'Tiêu đề'
    if not NUMBER.search(rest) and not LAW_NAME.search(rest):
        # The title names only a subject; the preamble may say which document it carries out.
        intro = GUIDE.search(parsed.get('intro') or '')
        if intro:
            # The guided document follows the verb in the same sentence; "xét đề nghị tại Công văn …" names a request, not it.
            rest = re.split(r'(?:theo|xét)\s+đề\s+nghị|[;:]|\.(?:\s|$)', parsed['intro'][intro.end():intro.end() + 400], maxsplit=1, flags=re.I)[0]
            path = 'Lời dẫn'
    # "… hướng dẫn Nghị định 56/1998/NĐ-CP, thay thế Thông tư 24/1999 …": the replaced documents are not the guided ones.
    rest = re.split(r'\b(?:thay\s+thế|bãi\s+bỏ|hủy\s+bỏ|huỷ\s+bỏ)\b', rest, maxsplit=1, flags=re.I)[0]
    # Provisions named before the guided document are the direct position ("quy định chi tiết khoản 3 Điều 25 Luật …").
    named_at = min([m.start() for m in NUMBER.finditer(rest)] + [m.start() for m in LAW_NAME.finditer(rest)] + [len(rest)])
    lead = re.sub(r'^\s*(?:thi\s+hành\s+)?(?:một\s+số\s+(?:điều|nội\s+dung)\s+(?:của\s+)?)?', '', rest[:named_at], flags=re.I)
    # The type word of the guided document stays before its number ("… Điều 55 Nghị định số"): it is not part of the place.
    lead = re.sub(r'\s*' + DOCUMENT_TYPE + r'\s*(?:số\s*)?$', '', lead.strip(' ,'), flags=re.I)
    lead = re.sub(r'\s+(?:của|thuộc|tại)\s*$', '', lead.strip(' ,'), flags=re.I).strip(' ,')
    places = positions(lead) if re.match(r'(?:các\s+)?(?:điểm|khoản|điều|chương|mục)\b', lead, re.I) else []
    if not places:
        # "hướng dẫn thực hiện xóa nợ … của Điều 55 Nghị định số 83/2013/NĐ-CP": the provision right before the guided document.
        tail = re.search(r'\b(?:của|thi\s+hành|thực\s+hiện)\s+((?:các\s+)?(?:điểm\s+[a-zđ]|khoản\s+\d|điều\s+\d|chương\s+[IVXLCDM\d]|mục\s+\d)[^()]*)$', lead, re.I)
        places = positions(tail[1]) if tail else []
    if places:
        scope = '; '.join(places)
    numbers = [m.group() for m in NUMBER.finditer(rest) if number_key(m.group()) != own]
    named = []
    if not numbers:
        # A law cited by name is identified through its numbered or dated entry in the legal basis.
        basis = basis_targets(parsed.get('can_cu'))
        for match in LAW_NAME.finditer(rest):
            name = re.sub(r'\s+', ' ', match[2]).strip()
            year = re.search(r'\s((?:19|20)\d{2})$', name)
            name = name[:year.start()].strip() if year else name
            number, day = basis.get(name.casefold(), (None, year[1] if year else None))
            if number:
                numbers.append(number)
            else:
                named.append((re.sub(r'\s+', ' ', match[1]) + ' ' + name, name, day))
    rows = []

    def row():
        return {'_id': f'hd_{doc_id}_{len(rows)}', 'action': action, 'source_path': path, 'scope': scope, 'unresolved': False,
                'source_in_phu_luc': False, 'detection_mode': 'title_guidance',
                'source_id': int(doc_id), 'source_document_number': meta.get('document_number'), 'source_title': meta.get('title'),
                'source_action': meta.get('action'), 'source_issuing_authority': meta.get('issuing_authority'),
                'source_issuance_date': meta.get('issuance_date'), 'source_legal_type': meta.get('legal_type'),
                'source_legal_sectors': ', '.join(meta.get('legal_sectors') or []), 'source_url': meta.get('url')}
    for number in dict.fromkeys(numbers):
        candidate = {**row(), 'target_doc': re.sub(r'\s+', '', number), '_evidence': meta.get('title') or ''}
        resolve(candidate, lookup(lookup_numbers([candidate['target_doc']])))
        candidate.pop('_evidence')
        rows.append(candidate)
    for label, name, day in named:
        hit = law_lookup(name, day) if day else None
        rows.append({**row(), 'target_doc': label, 'target_issuance_date': day,
                     'target_matched_id': int(hit['_id']) if hit else None, 'target_candidates_count': 1 if hit else 0})
    return rows


def quoted_spans(text):
    return [(m.start(), m.end()) for m in re.finditer(r'“[^”]*(?:”|$)|"[^"]*(?:"|$)', text, re.S)]


def cross_references(chunk, implicit=True):
    """Dẫn chiếu in a chunk: positions in this document, in this article/clause, or in another numbered document/law.
    References inside quotation marks are flagged (_trich): in an amending text they belong to the amended document."""
    text = chunk.get('noi_dung') or ''
    article, clause = chunk.get('ky_hieu_dieu'), chunk.get('ky_hieu_khoan')
    spans = quoted_spans(text)

    def quote_of(position):
        return next(((a, b) for a, b in spans if a <= position < b), None)
    refs = []
    for match in SELF_DOC.finditer(text):
        refs.append({'loai': 'noi_bo', 'vi_tri': tidy(match[1]), 'van_ban': None, 'trich': match.group()[:200], '_trich': bool(quote_of(match.start()))})
    if article:
        for match in SAME_ARTICLE.finditer(text):
            quote = quote_of(match.start())
            owner = article
            if quote:
                # "khoản 2 Điều này" inside the new text of "Điều 15a" means Điều 15a of the amended document.
                heads = re.findall(r'(?:^|“|\n)\s*Điều\s+(\d+[a-zđ]?)\s*[.:]', text[quote[0]:match.start()])
                owner = heads[-1] if heads else None
            refs.append({'loai': 'noi_bo', 'vi_tri': tidy(match[1]) + f' Điều {owner}' if owner else None, 'van_ban': None,
                         'trich': match.group()[:200], '_trich': bool(quote)})
        if clause:
            for match in SAME_CLAUSE.finditer(text):
                quote = quote_of(match.start())
                refs.append({'loai': 'noi_bo', 'vi_tri': None if quote else tidy(match[1]) + f' khoản {clause} Điều {article}',
                             'van_ban': None, 'trich': match.group()[:200], '_trich': bool(quote)})
    if implicit:
        bare = re.sub(r'“[^”]*”|"[^"]*"', ' ', text)  # quoted amendment text cites the amended document
        for match in IMPLICIT.finditer(bare):
            refs.append({'loai': 'noi_bo_ngam', 'vi_tri': tidy(match[1]), 'van_ban': None, 'trich': match.group()[:200], '_trich': False})
    for match in OTHER_DOC.finditer(text):
        refs.append({'loai': 'ngoai', 'vi_tri': tidy(match[1]), 'van_ban': re.sub(r'\s+', '', match[2]), 'trich': match.group()[:200], '_trich': False})
    for match in OTHER_LAW.finditer(text):
        refs.append({'loai': 'ngoai', 'vi_tri': tidy(match[1]), 'van_ban': re.sub(r'\s+', ' ', match[2] + ' ' + match[3]).strip(),
                     'trich': match.group()[:200], '_trich': False})
    unique = {}
    for ref in refs:
        # An explicit reference to the same position wins over its implicit reading.
        key = (ref['vi_tri'], ref['van_ban'], ref['_trich'])
        if key not in unique or unique[key]['loai'] == 'noi_bo_ngam':
            unique[key] = ref
    return list(unique.values())


def amended_targets(candidates):
    """Which document each article of an amending text changes: {'Điều 1': (number, id), ...} plus a document-wide fallback."""
    by_article, overall = {}, {}
    for candidate in candidates:
        if not candidate.get('target_matched_id'):
            continue
        key = re.match(r'(.*?Điều \S+)', candidate['source_path'])
        target = (candidate['target_doc'], candidate['target_matched_id'])
        overall[target] = overall.get(target, 0) + 1
        if key:
            counts = by_article.setdefault(key[1], {})
            counts[target] = counts.get(target, 0) + 1
    result = {key: max(counts, key=counts.get) for key, counts in by_article.items()}
    if len(overall) == 1:
        result[None] = next(iter(overall))
    return result


def chunk_article(source):
    """'Phụ lục 1 Điều 3' / 'Điều 3': the article path of a chunk, matching relation source paths."""
    if not source.get('ky_hieu_dieu'):
        return None
    appendix = re.search(r'_pl(\d+)', source.get('dieu_uid') or '')
    return (f'Phụ lục {int(appendix[1]) + 1} ' if appendix else '') + 'Điều ' + source['ky_hieu_dieu']


def link_references(chunks, doc_id, meta, parsed, lookup, law_lookup, amended=None):
    """Attach dan_chieu to each chunk; external targets are resolved once per document.
    amended (from amended_targets) re-targets "… này" inside quoted new text to the document being amended."""
    numbers, names = set(), set()
    amending = bool(action_matches(meta.get('title') or ''))  # bare positions in an amending text belong to the amended document
    for chunk in chunks:
        refs = cross_references(chunk['_source'], implicit=not amending)
        chunk['_refs'] = refs
        for ref in refs:
            if ref['loai'] == 'ngoai':
                (numbers if NUMBER.fullmatch(ref['van_ban']) else names).add(ref['van_ban'])
    hits = lookup(lookup_numbers(sorted(numbers))) if numbers else []
    resolved = {}
    for number in numbers:
        row = resolve({'target_doc': number, 'source_id': int(doc_id), 'source_issuance_date': meta.get('issuance_date'),
                       'source_issuing_authority': meta.get('issuing_authority'), '_evidence': ''}, hits)
        resolved[number] = row['target_matched_id']
    basis = basis_targets(parsed.get('can_cu'))
    for name in names:
        short = re.sub(r'^(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s+', '', name)
        number, day = basis.get(short.casefold(), (None, None))
        if number:
            row = resolve({'target_doc': number, 'source_id': int(doc_id), 'source_issuance_date': meta.get('issuance_date'),
                           'source_issuing_authority': meta.get('issuing_authority'), '_evidence': ''}, lookup(lookup_numbers([number])))
            resolved[name] = row['target_matched_id']
        elif day:
            hit = law_lookup(short, day)
            resolved[name] = int(hit['_id']) if hit else None
    count = 0
    for chunk in chunks:
        kept = []
        for ref in chunk.pop('_refs'):
            inside = ref.pop('_trich')
            if ref['loai'] == 'noi_bo' and inside and amending:
                target = (amended or {}).get(chunk_article(chunk['_source'])) or (amended or {}).get(None)
                if not target or not ref['vi_tri']:
                    continue  # cannot tell which amended document or article is meant: drop rather than guess
                ref.update(loai='van_ban_bi_sua', van_ban=target[0], target_id=target[1])
            elif not ref['vi_tri']:
                continue
            else:
                ref['target_id'] = int(doc_id) if ref['loai'] in ('noi_bo', 'noi_bo_ngam') else resolved.get(ref['van_ban'])
            kept.append(ref)
        if kept:
            chunk['_source']['dan_chieu'] = kept
            count += 1
    return count
