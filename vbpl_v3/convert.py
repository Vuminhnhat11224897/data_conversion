"""Convert source documents into the v3 indices: rule parser + qwen-legal for routed cases, chunks, vectors, QA'd relations."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import threading
import time

import requests

from .embedding import chunk_input, embed
from .qa import verify
from .legal_status import expiry, normative, provision_effects, rank, retroactive, unit_dates, unit_of, unit_of_path
from .references import amended_targets, guidance, law_by_name, law_named, link_references
from .extract import extract
from .relations import consolidation, detect, lookup_numbers, resolve, row_holders, stamp
from .resolver import appendix_scope, object_kind, resolve_row
from .text import join_split, language, number_key
from .validate import check_positions, only_in_history, own_quotes, validate
from .structure import APPENDIX, NUMBER, appendix_label, build_chunks, normalize, parse
from .structure_ai import refine
from .temporal import SUSPENSIONS, TEMPORAL_EFFECT, effective_date, finer_parts, in_format, normalize_scope, positions

META = ('document_number', 'title', 'legal_type', 'legal_sectors', 'issuing_authority', 'issuance_date', 'signers', 'tom_tat', 'action', 'url')
COPIED = META + ('pdf_minio_path', 'pdf_vbpl_id', 'embedding')
PARSED = ('can_cu', 'can_cu_refs', 'intro', 'noi_nhan', 'phu_luc', 'has_tail')


def within(path, places):
    """Is a relation unit ('Điều 1 Khoản 8 điểm a') inside one of the listed provisions ('khoản 8 Điều 1')? No list: the whole document."""
    if not places:
        return True
    unit = re.match(r'(?:Điều\s+(\S+))?(?:\s+Khoản\s+(\S+))?', path)
    for place in places:
        listed = re.fullmatch(r'(?:điểm\s+\S+\s+)?(?:khoản\s+(\S+)\s+)?Điều\s+(\S+)', place)
        if listed and unit[1] == listed[2] and (listed[1] is None or unit[2] == listed[1]):
            return True
    return False


DOCUMENT_LEVEL = ('intro', 'Tiêu đề', 'Lời dẫn', 'Căn cứ', 'Phần đầu')
PREFIX = re.compile(r'^(?:hidden_|intro_|hhl_|hd_|hn_)?')


def level(row):
    """vi_tri: it names a provision or the appendix holding a form, at any level, wherever the sentence stands (article, preamble, title);
    van_ban_kem_theo / noi_dung: it names a part only by name ("đơn giá ban hành kèm theo Quyết định X", "phần căn cứ");
    van_ban: it is about the document as a whole (whole replacement, "một số điều", guidance or consolidation without provisions);
    chua_xac_dinh: a provision-level change whose location was not found (to review)."""
    places = row.get('vi_tri') or []
    if places and places != ['toàn bộ']:
        return 'vi_tri'
    if row.get('doi_tuong'):
        return 'van_ban_kem_theo' if row.get('kem_theo') else 'noi_dung'
    if places or row.get('detection_mode') in ('intro', 'title_guidance', 'het_hieu_luc', 'hop_nhat') \
            or row['source_path'] in DOCUMENT_LEVEL or row['scope'] in ('toàn bộ', 'một số điều', 'một số cụm từ'):
        return 'van_ban'
    return 'chua_xac_dinh'


def settle(row):
    """cap_quan_he and the edge decision. Graph builds edges from validated relations only. A relation with no position that is not
    about the whole document waits for review, whichever path read it (in llm mode a rule relation the QA kept has no status check)."""
    # kem_theo goes with doi_tuong (contract 9.10.6): it says whether a part named by name is in the attachment. A position in the
    # attachment is told by target_section, not by kem_theo.
    if row.get('doi_tuong'):
        row['kem_theo'] = bool(row.get('kem_theo'))
    else:
        row.pop('kem_theo', None)
        row.pop('doi_tuong', None)
    row['cap_quan_he'] = level(row)
    row.setdefault('extraction', 'rules')
    # A rule relation has no list context: a part named as a procedure is one (Q12).
    row.setdefault('doi_tuong_loai', object_kind(row.get('doi_tuong')))
    if row['cap_quan_he'] == 'chua_xac_dinh':
        row.update(resolution_status='unresolved', resolution_reason=row.get('resolution_reason') or 'vi_tri_chua_xac_dinh')
    elif 'resolution_status' not in row:
        row.update(resolution_status='validated', resolution_reason=None)
    return row


# The rule QA's check of the rule's own scope (contract 4.8.6). It goes when the model's reading replaces that scope: it no longer
# describes the relation (48/3431 relations of v4-1000 kept scope_grounding_correct false on a scope the model read, 21/10/2026).
RULE_SCOPE_CHECK = ('scope_grounding_checked', 'scope_grounding_correct', 'scope_resolution_method', 'llm_refined', 'llm_hallucination_rejected')


def drop_rule_scope_check(row):
    for name in RULE_SCOPE_CHECK:
        row.pop(name, None)


def rows_into_articles(kept, parsed):
    """The kept acts, with the acts read from appendix rows given to the article they detail. An appendix that lists the procedures
    or documents an article acts on details that act; it is not another one ("Điều 2. Bãi bỏ 107 thủ tục … tại Quyết định số 158/…"
    and Phụ lục II listing them: the relations are Điều 2's).
    A record kept for review never hides a checked one: an article whose words name a list, not the target ("Thu hồi … các Quyết
    định … (có danh sách kèm theo)"), leaves its act unresolved, and a row whose column or heading ties the act to the target shows
    it (226447). The article's act is then that row's, validated."""
    article = {}
    for r in kept:
        if ' STT ' not in r['source_path'] and r['source_path'] not in DOCUMENT_LEVEL:
            article.setdefault((r['action'], number_key(r['target_doc'])), []).append(r)
    stated, hidden = set(article), set()
    for r in kept:
        key = (r['action'], number_key(r['target_doc']))
        if ' STT ' in r['source_path'] and r['resolution_status'] == 'validated' and key in article \
                and not any(a['resolution_status'] == 'validated' for a in article[key]):
            records = article.pop(key)
            hidden |= {id(a) for a in records}
            r.update(source_path=records[0]['source_path'], source_in_phu_luc=records[0]['source_in_phu_luc'], _from_rows=True)
    kept = [r for r in kept if id(r) not in hidden]
    # The same holds when the model missed the article's own reading: an article whose words name the target and the act takes the rows.
    for r in kept:
        if ' STT ' in r['source_path'] and (r['action'], number_key(r['target_doc'])) not in stated:
            holder = article_stating(parsed, r['action'], r['target_doc'])
            if holder:
                r.update(source_path=holder, source_in_phu_luc=False, _from_rows=True)
                stated.add((r['action'], number_key(r['target_doc'])))
    seen_keys, merged_rows = set(), []
    for r in kept:
        if ' STT ' in r['source_path'] and (r['action'], number_key(r['target_doc'])) in stated:
            continue
        if r.pop('_from_rows', False):
            k = (r['source_path'], r['action'], number_key(r['target_doc']))
            if k in seen_keys:
                continue
            seen_keys.add(k)
        merged_rows.append(r)
    return merged_rows


def article_stating(parsed, action, target):
    """The main-text unit whose words state this act on this document ("Điều 2. Bãi bỏ 107 thủ tục … tại Quyết định số 537/…"), or None.
    The rows of an appendix that list what it acts on are its detail, not other acts."""
    from .extract import main_units
    from .relations import document_refs
    from .validate import VERBS
    key = number_key(target)
    for path, text in main_units(parsed):
        if key in {number_key(m.group()) for m in document_refs(text)} and re.search(VERBS.get(action, r'^$'), text, re.I) \
                and not re.match(r'\s*(?:Điều\s+\d+\w*\.?\s*)?Công\s+bố\b', text, re.I):
            return path
    return None


def below(inner, outer):
    """inner is a part of outer: "điểm a khoản 16 Điều 2" of "khoản 16 Điều 2", any provision of "toàn bộ"."""
    if inner == outer:
        return False
    if outer == 'toàn bộ':
        return True
    return inner.endswith(' ' + outer) and not inner.startswith('tên ')


def tidy_positions(relations, appendix=False):
    """Positions a relation can be an edge to.
    - A position outside the contract format ("Mục Thời gian thực hiện đối với 11 thủ tục hành chính") names a part by name: it moves to
      doi_tuong, and the relation points to the document (cap_quan_he noi_dung or van_ban_kem_theo).
    - The same unit, act and document never reach both a provision and a part of it: "Sửa đổi điểm a, khoản 16 Điều 2" changes the
      point, not the clause too; a whole document beside its parts is the parts. Only the most specific positions stay, and a relation
      left with none of its own is dropped (it only restated a wider position).
    - appendix (llm mode): the appendix convention again, for the positions read after the merge (resolver.appendix_scope)."""
    for record in relations:
        row = record['_source']
        # "Mục II Phụ lục số 07" is "Mục II Phụ lục 07" (H2 357621).
        places = [re.sub(r'\b(Phụ lục|Chương|Mục|Phần)\s+số\s+', r'\1 ', re.sub(r'^Tên\b', 'tên', p)) for p in row.get('vi_tri') or []]
        row['vi_tri'] = places
        odd = [p for p in places if not in_format(p)]
        if not odd:
            continue
        row['vi_tri'] = [p for p in places if p not in odd]
        for pair in row.get('cum_tu') or []:
            pair['vi_tri'] = [p for p in pair.get('vi_tri') or [] if p not in odd]
        if not row.get('doi_tuong'):
            row.update(doi_tuong=odd[0], kem_theo=bool(re.search(r'kèm\s+theo', (row.get('scope') or '') + ' ' + (row.get('evidence') or ''), re.I)
                                                       or row.get('target_section') == 'kem_theo'))
    for record in relations:
        row = record['_source']
        if row.get('vi_tri') or row.get('doi_tuong') or not re.search(r'\b(?:số\s+thứ\s+tự|stt)\b', row.get('scope') or '', re.I):
            continue
        # Rows of a list named by number have no node (C4): the appendix that holds them, else the list named.
        holders = row_holders((row.get('scope') or '') + ' ' + (row.get('evidence') or ''))
        if holders and holders != 'Phụ lục':
            row['vi_tri'] = holders.split('; ')
            finer = finer_parts(row.get('scope') or '')
            if finer:
                row['_chi_tiet'] = {place: '; '.join(finer) for place in row['vi_tri']}  # the rows, not the whole appendix
            continue
        named = re.search(r'(?:danh\s+mục|thủ\s+tục)[^.;]{0,200}?số\s+thứ\s+tự[^.;]{0,120}', row.get('evidence') or '', re.I)
        part = ' '.join((named.group() if named else row['scope']).split())[:300]
        row.update(doi_tuong=part, kem_theo=bool(re.search(r'kèm\s+theo', row.get('evidence') or '', re.I) or row.get('target_section') == 'kem_theo'),
                   unresolved=False)
        if row.get('resolution_reason') == 'vi_tri_chua_xac_dinh':
            row.update(resolution_status='validated', resolution_reason=None)
    if appendix:
        # A rule's scope read into positions above, a row's appendix, a wording pair's own positions (27/10/2026: 60/9.759 relations
        # of fix7-H56 + fix7-ho kept "Mục I Phụ lục I", "Mục IV" after the merge).
        for record in relations:
            appendix_scope(record['_source'])
    # A provision and a part of it from the same unit, act and document: the part ("Sửa đổi điểm a, khoản 16 Điều 2" is the point).
    # A whole document and a part named by name are two readings of the scope; which one holds is read from the act's object in the
    # resolver (21/10/2026), not decided here by a rule that one kind always wins.
    groups = {}
    for record in relations:
        row = record['_source']
        k = (row['source_path'], row['action'], number_key(row.get('target_doc') or ''))
        groups.setdefault(k, set()).update(row.get('vi_tri') or [])
    # A unit that names a provision and units under it that name its parts: the parts ("Sửa đổi, bổ sung Điều 5 như sau: a) Sửa đổi
    # khoản 1 …; b) Bổ sung khoản 3 …" changes khoản 1 and khoản 3 Điều 5, 433634, 27/10/2026).
    under = {}
    for record in relations:
        row = record['_source']
        for (path, action, target), places in groups.items():
            if path.startswith(row['source_path'] + ' ') and (action, target) == (row['action'], number_key(row.get('target_doc') or '')):
                under.setdefault(id(record), set()).update(places)
    kept = []
    for record in relations:
        row = record['_source']
        places = row.get('vi_tri') or []
        group = groups[(row['source_path'], row['action'], number_key(row.get('target_doc') or ''))]
        parts = under.get(id(record), set())
        narrow = [p for p in places if not any(below(q, p) for q in group) and (p == 'toàn bộ' or not any(below(q, p) for q in parts))]
        if places and not narrow:
            continue
        row['vi_tri'] = narrow
        kept.append(record)
    return kept


# Letters that look Latin in a number typed from a Cyrillic keyboard ("361/2025/NĐ-CР"), and characters with no width.
LOOKALIKE = str.maketrans('АВЕКМНОРСТХаеорсух', 'ABEKMHOPCTXaeopcyx', '\u200b\u200c\u200d\u2060\ufeff')


def clean_number(value):
    return ' '.join(value.translate(LOOKALIKE).split()) if value else value


def distinct_edges(relations):
    """One edge once (27/10/2026; 146/2025 had 1.662 repeated rows): the same act, target, position, part and wording pair read in
    a unit and again in a unit under it ("Điều 1 Khoản 9" and "Điều 1 Khoản 9 điểm a") is the lower unit's; read twice in one unit,
    it is kept once, the validated reading first. A reading the lower unit left for review does not hide a checked one above it.
    A lead with no position, part or wording whose lower units state the same act on the same target is dropped (R2).
    Decisions R1, R2 of docs/07 §7.4."""
    def edge(row):
        return (row.get('action'), number_key(row.get('target_doc') or ''), tuple(row.get('vi_tri') or []), row.get('doi_tuong'),
                json.dumps(sorted((p.get('cu') or '', p.get('moi') or '') for p in row.get('cum_tu') or []), ensure_ascii=False))
    lower, acted, worded = {}, {}, {}
    for record in relations:
        row = record['_source']
        if row.get('resolution_status') == 'validated':
            lower.setdefault(edge(row), set()).add(row.get('source_path') or '')
            if row.get('cum_tu'):
                worded.setdefault(edge(row)[:4], set()).add(row.get('source_path') or '')
            acted.setdefault((row.get('action'), number_key(row.get('target_doc') or '')), set()).add(row.get('source_path') or '')
    kept, at = [], {}
    for record in relations:
        row = record['_source']
        k = edge(row)
        path = row.get('source_path') or ''
        if path and any(lower_path.startswith(path + ' ') for lower_path in lower.get(k, ())):
            continue
        # A lead with no position of its own whose items state the act ("3. Bãi bỏ một số điểm, khoản, cụm từ như sau: a) Bãi bỏ điểm c
        # khoản 1 Điều 21; …"): the items are the edges (R2, 27/10/2026).
        # A lead's phrase change with no pair of its own where a lower unit gives the pairs at that position ("36. Bãi bỏ một số khoản,
        # điểm, cụm từ sau đây: … b) Bỏ cụm từ “cấp đổi,” tại tên Điều 44"): the lower unit's.
        if path and not row.get('cum_tu') and any(p.startswith(path + ' ') for p in worded.get(k[:4], ())):
            continue
        bare = not row.get('vi_tri') and not row.get('doi_tuong') and not row.get('cum_tu')
        if path and bare and any(p.startswith(path + ' ') for p in acted.get((row.get('action'), number_key(row.get('target_doc') or '')), ())):
            continue
        same = at.get((k, path))
        if same is None:
            at[(k, path)] = len(kept)
            kept.append(record)
        elif row.get('resolution_status') == 'validated' and kept[same]['_source'].get('resolution_status') != 'validated':
            kept[same] = record
    return kept


def one_per_position(relations, doc_id):
    """Each position is one edge and one relation. A wording pair keeps only its own position; a pair whose position
    was not found keeps the relation's. Ids are renumbered per prefix in the order the relations come."""
    split = []
    for record in relations:
        row = record['_source']
        places = row.get('vi_tri') or []
        pairs = row.get('cum_tu') or []
        own = [[p for p in pair.get('vi_tri') or [] if p != 'toàn bộ' and in_format(p)] for pair in pairs]
        if pairs and all(own):
            # Every pair says, in the contract's format, where its phrase is replaced: those are the positions of the act (683793:
            # the act read at Điều 40, its pairs at Điều 10, 11, 12 and 52; 694158: read at one of its pairs' positions). A pair with
            # no such position ("tên Mục 5 và") applies at the relation's own positions, which then stand.
            places = row['vi_tri'] = list(dict.fromkeys(p for ps in own for p in ps))
            pairs = row['cum_tu'] = [{**pair, 'vi_tri': ps} for pair, ps in zip(pairs, own)]
        if len(places) <= 1:
            if pairs:
                # A pair's position is the relation's (contract 9.10.6): the pairs at that position, else all of them.
                here = [{**pair, 'vi_tri': places} for pair in pairs if not pair.get('vi_tri') or set(places) & set(pair['vi_tri'])]
                row['cum_tu'] = here or [{**pair, 'vi_tri': places} for pair in pairs]
            split.append(record)
            continue
        for place in places:
            part = {**row, 'vi_tri': [place]}
            if row.get('cum_tu') is not None:
                part['cum_tu'] = [{**pair, 'vi_tri': [place]} for pair in row['cum_tu'] if place in (pair['vi_tri'] or places)]
            split.append({'_id': record['_id'], '_source': part})
    for record in split:
        # A part without a node of its own keeps its limit on the edge to the node that holds it (C, 21/10/2026).
        row = record['_source']
        detail = row.pop('_chi_tiet', None) or {}
        place = (row.get('vi_tri') or [None])[0]
        if detail.get(place):
            row['chi_tiet_vi_tri'] = detail[place]
    split = distinct_edges(split)
    counts = {}
    for record in split:
        prefix = PREFIX.match(record['_id'])[0]
        record['_id'] = f'{prefix}{doc_id}_{counts.get(prefix, 0)}'
        counts[prefix] = counts.get(prefix, 0) + 1
    return split


def model_relations(doc_id, meta, parsed, candidates, root, lookup, provenance, config, caller=None):
    """Layers 2-4: the model states each act with a quote (extract), code resolves it (resolver) and checks it against the source
    (validate). The rule candidates go through the rule QA as before; the two are merged per (unit, act, document): extraction is
    llm+rules when both read it (rule positions, model quote), rules or llm when only one did. Returns (records, errors, rejected rows)."""
    folder = root / 'extract' / doc_id
    if meta.get('legal_type') == 'Văn bản hợp nhất':
        # A consolidated text restates the base document's own acts ("Thông tư này bãi bỏ …"); it performs none of them.
        # Its only relation is hop-nhat, read by rule (relations.consolidation).
        return [], [], []
    try:
        rows, call_errors = extract(doc_id, meta, parsed, folder, caller=caller)
    except (ValueError, TypeError, KeyError, requests.RequestException) as error:
        return [], [{'stage': 'extract', 'type': type(error).__name__, 'message': str(error)[:500]}], []
    kept, rejected = validate(rows, resolve_row)
    # The evidence of each kept act, piece by piece (field, words, role): intermediate data for review, not written to the index.
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'evidence.json').write_text(json.dumps([{'source_path': r['source_path'], 'action': r['action'], 'target_doc': r['target_doc'],
                                                         'resolution_status': r['resolution_status'], 'bang_chung': r.pop('_bang_chung', [])}
                                                        for r in kept], ensure_ascii=False, indent=1), encoding='utf-8')
    kept = rows_into_articles(kept, parsed)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'rejected.json').write_text(json.dumps(rejected, ensure_ascii=False, indent=1), encoding='utf-8')

    def key(row):
        return row['source_path'], row['action'], number_key(row['target_doc'])
    # Every rule candidate still goes through the rule QA, as in rules mode: the two paths are merged per (unit, act, document).
    verified, errors = verify(candidates, root / 'qa' / doc_id, lookup, provenance, config, caller=caller) if candidates else ([], [])
    # A document the rule read only in a note on the past ("… đã được sửa đổi, bổ sung theo Luật số A, Luật số B, …") is no target,
    # the fact validate.only_in_history checks for the model's rows (26/10/2026). Dropped after the QA, so no model input changes.
    noted = {(c['source_path'], number_key(c['target_doc'])) for c in candidates
             if only_in_history(c.get('_unit_evidence') or c['_evidence'], number_key(c['target_doc']))}
    verified = [r for r in verified if (r['_source']['source_path'], number_key(r['_source']['target_doc'])) not in noted]
    errors = list(errors) + call_errors
    by_rule = {}
    for record in verified:
        by_rule.setdefault(key(record['_source']), []).append(record)
    # Acts quoted from the same sentence of a unit share its scope: "Hủy bỏ 44 công trình, dự án … tại các Nghị quyết: số 200/…, số 26/…"
    # acts on a part of each resolution. When the model names that part for some of them and reads the whole document for others,
    # the part stands for all; a whole-document edge the sentence does not state costs the most.
    def sentence(row):
        return (row['source_path'], row['action'], ' '.join((row.get('evidence') or '').split())[:80])
    # The readings vote: a part read for some acts of the sentence stands for the others when they are at least as many; a tie keeps the
    # part (an edge narrower than the act loses less than a whole-document edge the sentence does not state). A part the model read is
    # never turned into the whole document by the other acts of the sentence (26/10/2026: a sentence repealing some documents wholly and
    # others in part lost the parts).
    parts, votes = {}, {}
    for row in kept:
        if (row.get('vi_tri') or []) not in ([], ['toàn bộ']):
            continue  # a provision named: not a part-or-whole reading
        k = sentence(row)
        votes.setdefault(k, [0, 0])[0 if row.get('doi_tuong') else 1] += 1
        if row.get('doi_tuong'):
            parts.setdefault(k, (row['doi_tuong'], row.get('kem_theo', False), row['scope']))
    for row in kept:
        k = sentence(row)
        if k not in parts or (row.get('vi_tri') or []) not in ([], ['toàn bộ']):
            continue
        part_votes, whole_votes = votes[k]
        if part_votes >= whole_votes and not row.get('doi_tuong'):
            part, attached, scope = parts[k]
            row.update(vi_tri=[], doi_tuong=part, kem_theo=attached, scope=scope, unresolved=False)
            if row.get('resolution_reason') == 'vi_tri_chua_xac_dinh':
                row.update(resolution_status='validated', resolution_reason=None)

    def specific(row):
        places = [p for p in row.get('vi_tri') or [] if p != 'toàn bộ']
        return 3 if places else 2 if row.get('doi_tuong') else 1 if row.get('vi_tri') else 0
    # The model may read the same act more than once (a long list asked in parts) and not always alike: the most specific reading of
    # each (unit, act, document) is the one the rule relation takes when the rule found no position.
    best = {}
    for row in kept:
        if row['resolution_status'] == 'validated' and specific(row) >= specific(best.get(key(row), {})):
            best[key(row)] = row
    records, used = [], set()
    for n, row in enumerate(kept):
        k = key(row)
        if k in by_rule and (row['resolution_status'] == 'validated' or k not in used):
            # Both read the act: the rule's positions are the more exact (dev 15/10/2026: 97% against 75%); the model adds its quote.
            # A model row left unresolved gives way to the rule relation the QA kept.
            if k not in used:
                # The rule's positions win, except a whole document against the parts the model read: "số thứ tự 1 Mục II Phụ lục II kèm
                # theo Quyết định số 1659/…" is that appendix, not 1659 as a whole. A wrong whole-document edge costs the most.
                rule_places = {p for rec in by_rule[k] for p in (rec['_source'].get('vi_tri') or positions(rec['_source'].get('scope') or ''))}
                rule_part = any(rec['_source'].get('doi_tuong') for rec in by_rule[k])
                row = best.get(k, row)
                model_places = [p for p in row.get('vi_tri') or [] if p != 'toàn bộ']
                for record in by_rule[k]:
                    record['_source'].update(extraction='llm+rules', resolution_status='validated', resolution_reason=None,
                                             evidence=row['evidence'], target_section=row['target_section'])
                    if row.get('doi_tuong_loai') == 'thu_tuc_hanh_chinh':
                        # The model read the list the act is in; the rule did not (Q12).
                        record['_source'].update({k: row[k] for k in ('doi_tuong_loai', 'ma_thu_tuc') if k in row})
                    if rule_places <= {'toàn bộ'} and model_places:
                        record['_source'].update(vi_tri=model_places, scope='; '.join(model_places))
                        drop_rule_scope_check(record['_source'])
                    elif rule_places == {'toàn bộ'} and not rule_part and row.get('doi_tuong'):
                        # The same for a part the model named by name (26/10/2026): "Thủ tục cấp lại chứng chỉ … tại Quyết định số X"
                        # is that procedure, not X as a whole.
                        record['_source'].update(vi_tri=[], doi_tuong=row['doi_tuong'], kem_theo=row.get('kem_theo', False), scope=row['scope'])
                        drop_rule_scope_check(record['_source'])
                    elif not rule_places and not rule_part and (row.get('doi_tuong') or row.get('vi_tri') or not row.get('unresolved')):
                        # The rule found the act but not what it acts on ("Hủy bỏ 44 công trình, dự án … tại các Nghị quyết"): the
                        # model's reading (a part, the whole document, or the document level: "Quyết định này sửa đổi, bổ sung Quyết
                        # định số 393/…", 506261) stands, instead of a relation left to review.
                        record['_source'].update(vi_tri=row.get('vi_tri') or [], scope=row['scope'], unresolved=False)
                        if row.get('doi_tuong'):
                            record['_source'].update(doi_tuong=row['doi_tuong'], kem_theo=row.get('kem_theo', False))
                        drop_rule_scope_check(record['_source'])
                    records.append(record)
                used.add(k)
            continue
        stamp(row, doc_id, meta)
        row['detection_mode'] = 'llm'
        # Only a document number is looked up; a law named by name is matched later (law_named), anything else stays unresolved.
        if NUMBER.fullmatch(row['target_doc']):
            resolve(row, lookup(lookup_numbers([row['target_doc']])))
        else:
            row.update(target_matched_id=None, target_candidates_count=0)
        for name in ('_unit_evidence', '_parent_evidence', '_evidence'):
            row.pop(name, None)
        records.append({'_id': f"{'intro_' if row['source_path'] == 'intro' else ''}{doc_id}_{n}", '_source': {**row, **provenance}})
    for k, group in by_rule.items():
        if k not in used:
            for record in group:
                record['_source'].update(extraction='rules', resolution_status='validated', resolution_reason=None)
                records.append(record)
    for record in records:
        appendix_scope(record['_source'])  # the appendix convention, for the edges of both paths
    return records, errors, rejected


def convert_document(doc_id, config, source, target, run_id, root, qa=True, dry_run=False, caller=None):
    """Rebuild one document from the source cluster and write it to the v3 indices (or to local JSON when dry_run)."""
    started = time.time()
    doc_id = str(doc_id)
    hit = source.get(config.source['documents'], doc_id)
    if hit is None:
        raise LookupError('Không thấy văn bản nguồn')
    src = hit['_source']
    text = src.get('full_content') or ''
    if not text.strip():
        raise ValueError('Văn bản nguồn không có full_content')
    full = normalize(text)
    # An English translation stored as the full text ("Article 1.-", 39074): no Vietnamese structure or relation can be read from it.
    # Skipped before any model call, like a document before START_YEAR (20/10/2026).
    if language(full) == 'en':
        return {'doc_id': doc_id, 'skipped': 'tieng_anh', 'ngon_ngu': 'en', 'dry_run': dry_run, 'seconds': round(time.time() - started, 2)}
    issued = src.get('issuance_date')
    is_normative, normative_how = normative(src)
    effect = effective_date(full, src.get('legal_type'), issued, is_normative)
    first_day = f'{config.start_year:04d}-01-01'
    # In scope when signed/issued, or in effect, on or after 1 Jan START_YEAR; checked before any model call.
    if (issued or '') and issued < first_day and not ((effect.get('ngay_hieu_luc') or '') >= first_day):
        return {'doc_id': doc_id, 'skipped': 'truoc_nam_bat_dau', 'start_year': config.start_year, 'issuance_date': issued,
                'ngay_hieu_luc': effect.get('ngay_hieu_luc'), 'dry_run': dry_run, 'seconds': round(time.time() - started, 2)}
    parsed, stats = refine(text, root / 'cache' / doc_id, title=src.get('title'), caller=caller)
    meta = {k: src.get(k) for k in META}
    meta['document_number'] = clean_number(meta.get('document_number'))
    meta['legal_sectors'] = src.get('legal_sectors') or []
    provenance = {'origin': src.get('origin') or 'legacy', 'ingest_job_id': f'v3:{run_id}', 'ingest_revision': 1,
                  'ingested_at': datetime.now(timezone.utc).isoformat(), 'uploaded_by': 'migration-v3'}
    rank_number, rank_label, rank_note = rank(src, is_normative)
    document = {**{k: src[k] for k in COPIED if src.get(k) is not None}, 'document_number': meta['document_number'], **{k: parsed[k] for k in PARSED},
                'phu_luc': [{**p, 'ky_hieu': appendix_label(p)} for p in parsed['phu_luc']],
                'full_content': join_split(full), 'n_dieu': stats['n_dieu'], 'grade': stats['grade'],
                'content_sha256': hashlib.sha256(join_split(full).encode('utf-8')).hexdigest(),
                'text_source': src.get('text_source') or 'source_full_content', **provenance,
                'la_vbqppl': is_normative, 'la_vbqppl_cach': normative_how,
                'cap_hieu_luc': rank_number, 'cap_hieu_luc_nhan': rank_label, 'cap_hieu_luc_ghi_chu': rank_note,
                **effect, **expiry(full, issued, src.get('legal_type')), **retroactive(full, issued, effect, src.get('legal_type')),
                'hieu_luc_rieng': provision_effects(full, issued, src.get('legal_type'))}
    if join_split(full) != full and (not document['noi_nhan'] or not document['has_tail']):
        # "N ơi nh ận:" split by the PDF text: the recipients and the signature read again on the joined text (R15). The structure
        # the model reads stays the one of the source text.
        joined, _ = parse(join_split(text))
        document.update(noi_nhan=document['noi_nhan'] or joined['noi_nhan'], has_tail=document['has_tail'] or joined['has_tail'])
    # Vectors go to the index only: a dry run's preview leaves them out, so a dry run neither reads nor computes them.
    if not document.get('embedding') and not dry_run:
        document['embedding'] = embed([src.get('title') or ''], config.embedding_url, config.embedding_batch, **config.embedding_options)[0]

    def lookup(numbers):
        return source.by_numbers(config.source['documents'], numbers) if numbers else []

    def law_lookup(name, day):
        return law_by_name(source, config.source['documents'], name, day)

    chunks = build_chunks(doc_id, meta, parsed)
    for chunk in chunks:
        for field in ('tieu_de', 'noi_dung'):
            if chunk['_source'].get(field):
                chunk['_source'][field] = join_split(chunk['_source'][field])
    candidates = detect(doc_id, meta, parsed)
    hits = lookup(lookup_numbers(list({c['target_doc'] for c in candidates})))
    candidates = [resolve(c, hits) for c in candidates]
    referenced = link_references(chunks, doc_id, meta, parsed, lookup, law_lookup, amended_targets(candidates))
    old = {}
    if config.embedding_reuse and not dry_run:
        # A chunk whose tieu_de + noi_dung text is unchanged keeps its existing vector.
        for row in source.scan(config.source['chunks'], {'term': {'doc_id': doc_id}}, ['tieu_de', 'noi_dung', 'embedding']):
            if row['_source'].get('embedding'):
                old.setdefault(chunk_input(row['_source']), row['_source']['embedding'])
    fresh = []
    for chunk in chunks:
        chunk['_source'].update(provenance)
        # Each unit carries its own effective day: the one the document states for it, else the document's.
        chunk['_source'].update(unit_dates(unit_of(chunk['_source']), document, document['hieu_luc_rieng']))
        vector = old.get(chunk_input(chunk['_source']))
        if vector:
            chunk['_source']['embedding'] = vector
        else:
            fresh.append(chunk)
    for start in range(0, len(fresh) if not dry_run else 0, config.embedding_batch):
        batch = fresh[start:start + config.embedding_batch]
        for chunk, vector in zip(batch, embed([chunk_input(c['_source']) for c in batch], config.embedding_url, config.embedding_batch,
                                              **config.embedding_options)):
            chunk['_source']['embedding'] = vector

    relations, errors, qa_status, rejected = [], [], 'skipped', []
    if qa and config.extractor == 'llm':
        relations, errors, rejected = model_relations(doc_id, meta, parsed, candidates, root, lookup, provenance, config, caller=caller)
        qa_status = 'incomplete' if errors else 'done'
    elif qa and candidates:
        relations, errors = verify(candidates, root / 'qa' / doc_id, lookup, provenance, config, caller=caller)
        qa_status = 'incomplete' if errors else 'done'
    for record in relations:
        row = record['_source']
        if row.get('target_matched_id') is None and re.match(r'(?:Bộ luật|Luật|Pháp lệnh)\s', row['target_doc']):
            # A law named without a number ("Luật Quy hoạch đô thị và nông thôn"): the base law of that name in force before the source.
            hit = law_named(source, config.source['documents'], row['target_doc'], row['source_issuance_date'])
            if hit:
                row.update(target_matched_id=int(hit['_id']), target_candidates_count=1)
    guided = guidance(doc_id, meta, parsed, lookup, law_lookup)
    # A consolidated text names what it restates in its opening; the rule reads it directly, without QA.
    merged = [resolve(row, lookup(lookup_numbers([row['target_doc']]))) for row in consolidation(doc_id, meta, parsed)]
    for row in merged:
        row.pop('_evidence', None)
    if qa:
        # Guidance named in the title or the issuing sentence is read by rule (hd_); the model's copy of it is not kept twice.
        guided_targets = {number_key(g['target_doc']) for g in guided}
        relations = [r for r in relations if not (r['_source']['source_path'] == 'intro' and r['_source']['action'] in ('huong-dan', 'quy-dinh-chi-tiet')
                                                  and number_key(r['_source']['target_doc']) in guided_targets)]
        relations += [{'_id': row.pop('_id'), '_source': {**row, **provenance}} for row in guided + merged]
    # R6 (27/10/2026): no relation is read from the title, the issuing sentence or the opening (intro_, hd_); the articles carry the
    # acts. A consolidated text's hop-nhat to the documents it restates stays (V6).
    relations = [r for r in relations if r['_source']['source_path'] not in DOCUMENT_LEVEL or r['_source']['action'] == 'hop-nhat']
    for record in relations:
        # Time semantics for the graph: when the change starts and whether it reaches back to the target's start.
        row = record['_source']
        row['scope'] = normalize_scope(row.get('scope'))
        row['vi_tri'] = row.get('vi_tri') or positions(row['scope'])
        if '_chi_tiet' not in row:
            detail = {}
            for group in re.split(r'\s*;\s*', row['scope'] or ''):
                finer = finer_parts(group)
                for place in positions(group) if finer else []:
                    detail.setdefault(place, '; '.join(finer))
            if detail:
                row['_chi_tiet'] = detail
        # The source unit's own effective day when the document states one for it.
        unit = unit_of_path(row['source_path'])
        row['source_ngay_hieu_luc'] = unit_dates(unit, document, document['hieu_luc_rieng'])['ngay_hieu_luc'] if unit else document['ngay_hieu_luc']
        row['hieu_luc_tac_dong'] = TEMPORAL_EFFECT.get(row['action'])
        if document['hoi_to'] and row['hieu_luc_tac_dong'] == 've_sau' and within(row['source_path'], document['hoi_to_vi_tri']):
            # The source applies from before its signing day: the change reaches back to that day.
            row.update(hieu_luc_tac_dong='ve_truoc', source_ngay_hoi_to=document['ngay_hoi_to'])
        if row['action'] in SUSPENSIONS and not row.get('dinh_chi_tu_ngay'):
            row['dinh_chi_tu_ngay'] = row['source_ngay_hieu_luc']
    relations = own_quotes(one_per_position(tidy_positions(check_positions(relations, parsed), appendix=config.extractor == 'llm'), doc_id), parsed)
    for record in relations:
        settle(record['_source'])
    review = [r['_source'] for r in relations if r['_source']['cap_quan_he'] == 'chua_xac_dinh']
    if review:
        with (root / 'review.jsonl').open('a', encoding='utf-8') as stream:
            for row in review:
                stream.write(json.dumps({k: row.get(k) for k in ('source_id', 'source_document_number', 'source_path', 'action', 'target_doc', 'scope')}, ensure_ascii=False) + '\n')

    if dry_run:
        preview = {'document': {k: v for k, v in document.items() if k not in ('embedding', 'full_content')},
                   'chunks': [{'_id': c['_id'], **{k: v for k, v in c['_source'].items() if k != 'embedding'}} for c in chunks],
                   'relations': relations}
        (root / 'dry-run').mkdir(exist_ok=True)
        (root / 'dry-run' / f'{doc_id}.json').write_text(json.dumps(preview, ensure_ascii=False, indent=1), encoding='utf-8')
    else:
        if target.count(config.target['chunks'], {'term': {'doc_id': doc_id}}):
            target.remove_group(config.target['chunks'], 'doc_id', doc_id)
        if chunks:
            target.bulk(config.target['chunks'], chunks)
        target.put(config.target['documents'], doc_id, document)
        if qa:
            if target.count(config.target['changes'], {'term': {'source_id': int(doc_id)}}):
                target.remove_group(config.target['changes'], 'source_id', int(doc_id))
            if relations:
                target.bulk(config.target['changes'], relations)

    ai = stats['structure_ai']
    return {'doc_id': doc_id, 'legal_type': src.get('legal_type'), 'n_dieu_source': src.get('n_dieu'),
            'n_dieu': stats['n_dieu'], 'n_dieu_total': stats['n_dieu_total'], 'grade': stats['grade'], 'tail_dieu': stats['tail_dieu'],
            'chunks': len(chunks), 'vectors_reused': len(chunks) - len(fresh), 'vectors_new': len(fresh),
            'empty_dieu': sum(1 for c in chunks if c['_source']['chunk_type'] == 'dieu' and not c['_source']['noi_dung'].strip()),
            'routed': ai['routed_articles'], 'untitled': len(ai['untitled_lines']), 'layout': ai['layout'], 'ai_warnings': ai['warnings'],
            'ngon_ngu': language(src.get('full_content') or ''),
            'ngay_hieu_luc': document['ngay_hieu_luc'], 'ngay_hieu_luc_cach': document['ngay_hieu_luc_cach'],
            'la_vbqppl': is_normative, 'la_vbqppl_cach': normative_how, 'cap_hieu_luc': rank_number,
            'cap_hieu_luc_ghi_chu': rank_note, 'ngay_het_hieu_luc': document['ngay_het_hieu_luc'], 'hoi_to': document['hoi_to'],
            'chunks_dan_chieu': referenced, 'guidance': len(guided), 'consolidation': len(merged),
            'hieu_luc_rieng': len(document['hieu_luc_rieng']), 'tieu_diem': sum(1 for c in chunks if c['_source']['chunk_type'] == 'tieu_diem'), 'guidance_resolved': sum(1 for g in guided if g.get('target_matched_id')),
            'actions': sorted({r['_source']['action'] for r in relations}),
            'relations_without_position': len(review),
            'candidates': len(candidates), 'qa': qa_status, 'qa_errors': errors[:5], 'relations': len(relations),
            'extractor': config.extractor, 'model_rejected': len(rejected),
            'unresolved': sum(1 for r in relations if r['_source'].get('resolution_status') == 'unresolved'),
            'resolved': sum(1 for r in relations if r['_source'].get('target_matched_id') is not None),
            'dry_run': dry_run, 'seconds': round(time.time() - started, 2)}


def select_ids(config, source, args):
    if args.ids:
        raw = Path(args.ids).read_text(encoding='utf-8').strip()
        return [str(x) for x in json.loads(raw)] if raw.startswith('[') else [line.strip() for line in raw.splitlines() if line.strip()]
    filters = []
    if args.from_date or args.to_date:
        filters.append({'range': {'issuance_date': {k: v for k, v in (('gte', args.from_date), ('lte', args.to_date)) if v}}})
    if args.legal_type:
        filters.append({'term': {'legal_type': args.legal_type}})
    if getattr(args, 'action', None):
        filters.append({'term': {'action': args.action}})
    query = {'bool': {'filter': filters}} if filters else {'match_all': {}}
    if args.sample:
        if not 1 <= args.sample <= 10000:
            raise ValueError('--sample phải trong khoảng 1..10000')
        body = {'size': args.sample, '_source': False, 'query': {'function_score': {'query': query,
                'random_score': {'seed': args.seed, 'field': '_seq_no'}, 'boost_mode': 'replace'}}}
        return [h['_id'] for h in source.request('POST', f"/{config.source['documents']}/_search", body)['hits']['hits']]
    return [h['_id'] for h in source.scan(config.source['documents'], query, False, size=5000)]


def run(config, source, target, args, caller=None):
    root = config.workdir / args.run
    root.mkdir(parents=True, exist_ok=True)
    state = root / 'run.json'
    if state.exists():
        meta = json.loads(state.read_text())
    else:
        meta = {'run_id': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'), 'source': config.source_url, 'target': config.target_url,
                'target_indices': config.target, 'selection': {k: getattr(args, k) for k in ('ids', 'sample', 'seed', 'all', 'from_date', 'to_date', 'legal_type')}}
        state.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    ids_file = root / 'ids.json'
    if not ids_file.exists():
        ids_file.write_text(json.dumps(select_ids(config, source, args)))
    ids = json.loads(ids_file.read_text())
    log = root / 'documents.jsonl'
    done = {json.loads(line)['doc_id'] for line in log.read_text(encoding='utf-8').splitlines()} if log.exists() and not getattr(args, 'redo', False) else set()
    todo = [i for i in ids if i not in done]
    if args.limit:
        todo = todo[:args.limit]
    mode = 'DRY-RUN, không ghi ES' if args.dry_run else 'ghi ' + ', '.join(config.target.values())
    print(f'Lượt {args.run}: {len(ids)} văn bản đã chọn, {len(done)} đã xong, {len(todo)} sẽ chạy ({mode})', flush=True)
    source.use_number_index(config.source['documents'], config.workdir)
    lock, failures, started = threading.Lock(), [], time.time()

    def work(doc_id):
        try:
            record = convert_document(doc_id, config, source, target, meta['run_id'], root, qa=not args.no_qa, dry_run=args.dry_run, caller=caller)
        except Exception as exc:
            failure = {'doc_id': doc_id, 'error': f'{type(exc).__name__}: {str(exc)[:500]}', 'at': datetime.now(timezone.utc).isoformat()}
            with lock, (root / 'failures.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(failure, ensure_ascii=False) + '\n')
            failures.append(failure)
            return None
        with lock, log.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        return record

    with ThreadPoolExecutor(args.workers) as pool:
        for n, _ in enumerate(as_completed([pool.submit(work, i) for i in todo]), 1):
            if n % 25 == 0 or n == len(todo):
                print(f'{n}/{len(todo)} sau {time.time() - started:.0f} giây, lỗi {len(failures)}', flush=True)
    summary = {'run_id': meta['run_id'], 'selected': len(ids), 'attempted': len(todo), 'failures': len(failures),
               'seconds': round(time.time() - started), 'dry_run': args.dry_run}
    (root / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(f'Xong: {summary}. Nhật ký ở {root}', flush=True)
    return 1 if failures else 0
