"""Hybrid structure: the rule parser decides; qwen-legal only labels routed ambiguities by source line numbers."""
import hashlib
import json
import os
import re

from .llm import validated_json
from .prompts import load
from .structure import (ARTICLE, ATTACHED, CHAPTER, TAIL, APPENDIX, appendix_header, issued_note, parse, refs,
                        source_lines, title_line)

SUBJECT = re.compile(r'^(?:Quyết định|Thông tư|Nghị định|Nghị quyết|Chỉ thị|Luật|Pháp lệnh|Văn bản|Kế hoạch|Quy chế|Quy định)\s+(?:này|liên tịch này)\b'
                     r'|^(?:Các|Chánh|Giám đốc|Thủ trưởng|Chủ tịch|Bộ trưởng|Tổng|Cục trưởng|Ủy ban|Uỷ ban|Hội đồng|Sở|Ban|Ông|Bà|Người|Cơ quan|Tổ chức|Đơn vị|Trưởng|Viện trưởng)\b', re.I)
TITLE_PROMPT = load('phan_loai_ten_dieu')
TITLE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['articles'], 'properties': {'articles': {'type': 'array', 'items': {
    'type': 'object', 'additionalProperties': False, 'required': ['line', 'has_title'],
    'properties': {'line': {'type': 'integer', 'description': 'Số dòng của dòng "Điều N" được hỏi.'},
                   'has_title': {'type': 'boolean', 'description': 'true khi chữ sau "Điều N." là tên Điều; false khi đã là nội dung.'}}}}}}
LAYOUT_PROMPT = load('bo_cuc_van_ban')
OUTLINE_PROMPT = load('dan_y_van_ban')
OUTLINE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['mo_dau_ket_thuc', 'ket_thuc_bat_dau', 'muc'], 'properties': {
    'mo_dau_ket_thuc': {'type': 'integer', 'description': 'id dòng cuối của phần mở đầu (quốc hiệu, số hiệu, Kính gửi, căn cứ, đoạn mở đầu); -1 nếu không có.'},
    'ket_thuc_bat_dau': {'type': 'integer', 'description': 'id dòng đầu của phần kết (đoạn kết chung, Nơi nhận, chữ ký); -1 nếu không có.'},
    'muc': {'type': 'array', 'description': 'Các tiêu đề mục theo thứ tự xuất hiện.', 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['dong', 'nhan', 'cap'], 'properties': {
            'dong': {'type': 'integer', 'description': 'id dòng chứa tiêu đề mục.'},
            'nhan': {'type': 'string', 'description': 'Nhãn đúng như đầu dòng, không kèm dấu: "I", "1", "A".'},
            'cap': {'type': 'integer', 'description': 'Cấp của mục: 1 là cấp lớn nhất của văn bản, 2 là mục con của cấp 1, 3 là mục con của cấp 2.'}}}}}}
HEADING = re.compile(r'^([IVXLCDM]+|\d{1,2}|[A-ZĐ])\s*[.)\-–:]\s*\S')
LAYOUT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['parts'], 'properties': {'parts': {'type': 'array', 'items': {
    'type': 'object', 'additionalProperties': False, 'required': ['start_line'],
    'properties': {'start_line': {'type': 'integer', 'description': 'id (số dòng) của dòng mở đầu một phần sau văn bản chính.'}}}}}}


def articles_of(parsed):
    return parsed['dieu_luat'] + [a for part in parsed['phu_luc'] for a in part['dieu_luat']]


def ambiguous(article):
    """Rules settle short inline names; long, punctuated, subject-led or next-line headings go to the model."""
    title = article['tieu_de'].strip()
    if not title:
        return False
    sure = (article['title_inline'] and len(title) <= 90 and not title.endswith(('.', ';', ',', ':'))
            and not SUBJECT.match(title))
    return not sure


def layout_signals(parsed, stats):
    signals = []
    if stats['tail_dieu']:
        signals.append('tail_dieu')
    if sum(map(len, parsed['noi_nhan'])) > 2000:
        signals.append('long_noi_nhan')
    if any(a.get('van_ban_kem_theo') for a in parsed['dieu_luat']):
        signals.append('segment_in_main')
    if any(p['loai'] == 'unlabeled' and not issued_note(p['tieu_de']) for p in parsed['phu_luc']):
        signals.append('unlabeled_without_note')
    if any(p['loai'] == 'labeled' and not p['dieu_luat'] and len(p['noi_dung']) < 80 for p in parsed['phu_luc']):
        signals.append('empty_labeled_part')
    return signals


def outline_signals(parsed, lines):
    """A text without articles whose layout rules cannot settle: no sections, or headings of several numbering styles
    (I/II with 1/2, A/B with I/II), or one section holding most of the text."""
    if parsed['dieu_luat']:
        return []
    styles = set()
    for line in lines:
        m = HEADING.match(line)
        if m and not line.startswith('|'):
            label = m[1]
            styles.add('roman' if re.fullmatch(r'[IVXLCDM]+', label) else 'number' if label.isdigit() else 'letter')
    sections = parsed.get('noi_dung_sections') or []
    size = sum(len(m['noi_dung']) for m in sections)
    signals = []
    if not sections and len(parsed.get('noi_dung') or '') > 1500:
        signals.append('no_sections')
    if len(styles) >= 2:
        signals.append('several_numbering_styles')
    if sections and size > 3000 and max(len(m['noi_dung']) for m in sections) > 0.6 * size:
        signals.append('one_section_holds_most')
    return signals


def apply_outline(parsed, lines, answer):
    """Sections from the model's outline, cut from the source lines by code: cap-1 headings start sections; the opening and the
    closing stay outside every section."""
    top = [m for m in answer['muc'] if m['cap'] == 1]
    end = answer['ket_thuc_bat_dau'] if answer['ket_thuc_bat_dau'] >= 0 else len(lines)
    sections = []
    for pos, m in enumerate(top):
        stop = top[pos + 1]['dong'] if pos + 1 < len(top) else end
        body = re.sub(r'^\s*' + re.escape(m['nhan']) + r'\s*[.)\-–:]\s*', '', '\n'.join(lines[m['dong']:stop]).strip())
        sections.append({'so_muc': m['nhan'], 'noi_dung': body, 'so_van_ban_refs': refs(body)})
    opening = lines[:top[0]['dong']]
    basis = [i for i, line in enumerate(opening) if line.startswith('Căn cứ ')]
    head_end = basis[0] if basis else answer['mo_dau_ket_thuc'] + 1 if 0 <= answer['mo_dau_ket_thuc'] < top[0]['dong'] else 0
    parsed.update(noi_dung_sections=sections, phan_dau='\n'.join(opening[:head_end]).strip(),
                  intro='\n'.join(opening[(basis[-1] + 1) if basis else head_end:]).strip())
    return parsed


def skeleton(lines):
    keep = [i for i, line in enumerate(lines) if line and (ARTICLE.match(line) or (line.isupper() and len(line) > 3) or CHAPTER.match(line)
                                                           or TAIL.match(line) or re.match(r'^Nơi nhận', line) or APPENDIX.match(line) or issued_note(line))]
    out, run = [], []

    def flush():
        shown = run[:2] + run[-1:] if len(run) > 4 else run
        out.extend({'id': i, 'text': lines[i][:110]} for i in shown)
        if len(run) > 4:
            out.insert(len(out) - 1, {'id': None, 'text': f'… ({len(run) - 3} Điều lược bớt)'})
    for i in keep:
        if ARTICLE.match(lines[i]):
            run.append(i)
        else:
            flush(); run = []; out.append({'id': i, 'text': lines[i][:110]})
    flush()
    return out[:170]


def ask(prompt, payload, folder, name, validate, schema, max_tokens, caller, check):
    raw = json.dumps(payload, ensure_ascii=False)
    # Another model gets its own cache: answers of the old model are not reused.
    target = folder / 'structure_ai' / hashlib.sha256((prompt + raw + os.getenv('LITELLM_MODEL', '')).encode()).hexdigest()[:24]
    target.mkdir(parents=True, exist_ok=True)
    return validated_json(prompt, raw, target, name, validate, schema=schema, max_tokens=max_tokens, timeout=240, caller=caller, check=check)


def refine(text, folder, title=None, caller=None, check=None):
    """Parse with rules, then apply validated model decisions. Returns (parsed, stats) like parse()."""
    lines = source_lines(text)
    draft, stats = parse(text, positions=True)
    report = {'method': 'rules_with_qwen', 'routed_articles': 0, 'untitled_lines': [], 'layout': None, 'warnings': []}
    articles = articles_of(draft)
    routed = [a for a in articles if ambiguous(a)]
    report['routed_articles'] = len(routed)
    untitled = set()
    if routed:
        nonempty = [i for i, x in enumerate(lines) if x]
        items = [{'line': a['line'], 'dong': [{'id': i, 'text': lines[i][:300]} for i in [a['line'], *[j for j in nonempty if j > a['line']][:3]]]}
                 for a in routed]
        asked = {a['line'] for a in routed}

        def valid(answer):
            got = [x['line'] for x in answer['articles']]
            if len(got) != len(set(got)) or not set(got) <= asked or not all(isinstance(x['has_title'], bool) for x in answer['articles']):
                raise ValueError('Answer must cover only the asked article lines, once each, with boolean has_title')
        payload = {'ten_van_ban': (title or '')[:200], 'ten_cac_dieu': [a['tieu_de'][:80] for a in articles][:60], 'dieu_can_xac_dinh': items}
        try:
            answer = ask(TITLE_PROMPT, payload, folder, 'titles.json', valid, TITLE_SCHEMA, 2000, caller, check)
            decided = {x['line']: x['has_title'] for x in answer['articles']}
            untitled = {line for line, has_title in decided.items() if not has_title}
            if asked - set(decided):
                report['warnings'].append(f'{len(asked - set(decided))} routed article(s) unanswered; rule decision kept')
        except Exception as exc:
            report['warnings'].append('Article title model failed; rule decisions kept: ' + type(exc).__name__)
    report['untitled_lines'] = sorted(untitled)
    signals = layout_signals(draft, stats)
    parts = None
    if signals:
        report['layout'] = {'signals': signals, 'applied': False}
        first = min([a['line'] for a in draft['dieu_luat']] or [0])

        def valid_layout(answer):
            starts = [p['start_line'] for p in answer['parts']]
            if len(starts) != len(set(starts)) or any(not (first < s < len(lines)) or not (title_line(lines[s]) or appendix_header(lines[s])
                                                       or ATTACHED.match(lines[s].upper())) for s in starts):
                raise ValueError('Part starts must be distinct title lines after the first article of the main document')
        try:
            answer = ask(LAYOUT_PROMPT, {'ten': (title or '')[:200], 'khung': skeleton(lines)}, folder, 'layout.json', valid_layout,
                         LAYOUT_SCHEMA, 800, caller, check)
            proposal = sorted(p['start_line'] for p in answer['parts'])
            trial, trial_stats = parse(text, untitled=frozenset(untitled), parts=proposal)
            # A labeled appendix with real content stays its own part; the model may only drop empty/table-of-contents labels.
            kept_labels = all(p['line'] in proposal for p in draft['phu_luc'] if p['loai'] == 'labeled' and len(p['noi_dung']) >= 1000)
            # Accept only a layout that keeps every main article and leaves no article in the recipient tail.
            if not kept_labels:
                report['layout']['reason'] = 'Proposal would merge a labeled appendix with content; rule layout kept'
            elif trial_stats['tail_dieu'] or trial_stats['n_dieu'] != stats['n_dieu'] or trial_stats['n_dieu_total'] < stats['n_dieu_total'] \
                    or sum(map(len, trial['noi_nhan'])) > sum(map(len, draft['noi_nhan'])):
                report['layout']['reason'] = 'Proposal would lose articles or move content into the tail; rule layout kept'
            else:
                parts = proposal
                report['layout'].update(applied=True, parts=proposal)
        except Exception as exc:
            report['warnings'].append('Layout model failed; rule layout kept: ' + type(exc).__name__)
    parsed, stats = parse(text, untitled=frozenset(untitled), parts=parts)
    signals = outline_signals(parsed, lines)
    if signals:
        # Layouts the rules cannot settle go to the model, which returns line ids only; code checks them and cuts the text.
        report['outline'] = {'signals': signals, 'applied': False}
        shown = [i for i, line in enumerate(lines) if line][:600]

        def valid_outline(answer):
            rows = answer['muc']
            ids = [m['dong'] for m in rows]
            if ids != sorted(set(ids)) or any(not (0 <= i < len(lines)) for i in ids):
                raise ValueError('Heading lines must be distinct, increasing source line ids')
            for m in rows:
                if m['cap'] not in (1, 2, 3) or not re.match(r'^\s*' + re.escape(m['nhan']) + r'\s*[.)\-–:]', lines[m['dong']]):
                    raise ValueError(f'Line {m["dong"]} does not open with label {m["nhan"]!r}, or cap is not 1-3')
            top = [m['dong'] for m in rows if m['cap'] == 1]
            if len(top) < 2:
                return  # one section or none: nothing to cut, the rule sections stay (asking again would not change that)
            if answer['mo_dau_ket_thuc'] >= top[0] or (answer['ket_thuc_bat_dau'] >= 0 and answer['ket_thuc_bat_dau'] <= top[-1]):
                raise ValueError('The opening must end before the first section and the closing start after the last one')
        try:
            answer = ask(OUTLINE_PROMPT, {'ten': (title or '')[:200], 'dong': [{'id': i, 'text': lines[i][:100]} for i in shown]},
                         folder, 'outline.json', valid_outline, OUTLINE_SCHEMA, 3000, caller, check)
            if sum(1 for m in answer['muc'] if m['cap'] == 1) >= 2:
                parsed = apply_outline(parsed, lines, answer)
                stats['n_muc'] = len(parsed['noi_dung_sections'])
                report['outline'].update(applied=True, sections=[m['so_muc'] for m in parsed['noi_dung_sections']])
            else:
                report['outline']['reason'] = 'Fewer than two top-level sections; rule sections kept'
        except Exception as exc:
            report['warnings'].append('Outline model failed; rule sections kept: ' + type(exc).__name__)
    report['status'] = 'needs_review' if report['warnings'] else 'checked'
    stats['structure_ai'] = report
    return parsed, stats
