"""Score a run against the gold labels, by layer and by document group.

Usage: python -m eval.score <set> <run> [--json out.json]
Reads eval/gold/<set>/*.json (labels) and work/<run>/dry-run/<id>.json (tool output; run convert with --dry-run).

Measures, each on its own:
- document P/R: the source reaches the right target document (any unit, act, position);
- structural: share of labeled documents with no structure error the labeler found;
- relation P/R: the tool states the act of the right unit on the right document (source_path, action, target);
- position: for matched relations, the positions (vi_tri, or a part named by name) are the gold ones;
- end-to-end P/R: unit, act, document and position all right, one item per position;
- unresolved: share of tool relations left for review, and how many of them are real (in the gold);
- errors by kind: structural, semantic, reference, scope, classification, graph_mapping.
Precision counts validated relations only: an unresolved relation is not an edge.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vbpl_v3.resolver import appendix_like  # noqa: E402
from vbpl_v3.temporal import positions  # noqa: E402
from vbpl_v3.text import number_key  # noqa: E402

OPENING = {'intro', 'Tiêu đề', 'Lời dẫn', 'Phần đầu', 'Căn cứ'}
NUMBER_ONLY = re.compile(r'\d+/')


ROWS = 'keep'  # keep | appendix (a row counts as the appendix that holds it) | drop (rows are not counted), set by --rows


def row_path(path):
    """One spelling for a row of an appendix table: "Phụ lục 2 Mục I STT 01" and "Phụ lục 2 STT 1" are the same row. The section label
    is dropped (labelers and the tool read headings like "PHẦN I" differently) and the row number loses its leading zeros. Rows stay
    apart by appendix and number; two sections restarting their numbers under one act on one document would merge (rare)."""
    m = re.match(r'^(Phụ lục \d+)\b.*?\bSTT\s+0*(\d+[a-zđ]?)\b', path)
    return f'{m[1]} STT {m[2]}' if m else path


def unit(path):
    path = 'Phần đầu' if path in OPENING else ' '.join((path or '').split())
    path = row_path(path)
    if ROWS == 'appendix':
        path = re.sub(r'^(Phụ lục \d+)\b.*\bSTT\b.*$', r'\1', path)
    return path


def counted(path):
    return not (ROWS == 'drop' and re.search(r'^Phụ lục \d+\b.*\bSTT\b', path or ''))


def document(target):
    target = ' '.join((target or '').split())
    return target.casefold() if re.match(r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s', target, re.I) else number_key(target)


# The appendix convention (26/10/2026): a position outside điều – khoản – điểm (a part named by name, a Mục or Phần of a plan or an
# old circular, a row of a catalogue, "Mục II Phần B Phụ lục I") counts as its appendix, the same on both sides.
ARTICLE_PLACE = re.compile(r'\b(?:điểm|khoản|điều|chương)\b', re.I)
APPENDIX_LABEL = re.compile(r'phụ\s+lục\s+(?:số\s+)?([IVXLCDM]+|\d+[a-zđ]?|[A-ZĐ])\b', re.I)


def appendix(text):
    """'Phụ lục II' when the words name one appendix ('Phụ lục 06' is 'Phụ lục 6'), 'Phụ lục' otherwise."""
    labels = list(dict.fromkeys(m[1].upper().lstrip('0') or '0' for m in APPENDIX_LABEL.finditer(text or '')))
    return f'Phụ lục {labels[0]}' if len(labels) == 1 else 'Phụ lục'


def place(value):
    """A position in contract form; '' for none ('toàn bộ' and none are both the whole document). A position outside điều – khoản – điểm
    and a part named by name that an appendix holds are their appendix (appendix convention); another part named by name is '#'; a
    provision written outside the format stays '?<text>'."""
    if not value or value == 'toàn bộ':
        return ''
    if value.startswith('#'):
        # The same test as the tool (resolver.appendix_like): a part an appendix holds is that appendix; another part keeps '#'.
        return appendix(value[1:]) if appendix_like(value[1:]) else '#'
    found = positions(value)
    if not found:
        text = ' '.join(value.split())
        if ARTICLE_PLACE.search(text) and not re.search(r'\b(?:mục|phần)\b', text, re.I):
            return '?' + text.casefold()
        return appendix(text)
    return found[0] if ARTICLE_PLACE.search(found[0]) else appendix(found[0])


# The pairing convention (26/10/2026): "Sửa đổi, bổ sung X" gives sua-doi and bo-sung; a label may keep one of them.
PAIR = {'sua-doi': 'bo-sung', 'bo-sung': 'sua-doi'}


def extra_halves(gold, tool):
    """Tool items (action, target[, place]) not counted as wrong: one half of the pair sua-doi / bo-sung whose other half is right."""
    right = gold & tool
    return {x for x in tool - gold if x[0] in PAIR and (PAIR[x[0]],) + x[1:] in right}


def related(a, b):
    """The same unit, or one holding the other ("Điều 2 Khoản 2" holds "Điều 2 Khoản 2 điểm a"): the act may be stated in the lead."""
    return a == b or a.startswith(b + ' ') or b.startswith(a + ' ')


def align(tool, expected):
    """Give a tool item the gold unit it matches up or down the tree, for the same act on the same document. An item whose own unit is
    in the gold keeps it: gold with both "Điều 10" and "Điều 10 Khoản 1" must not take the clause's item for the article (fixed 20/10/2026)."""
    out = set()
    exact = {g[:3] for g in expected}
    for item in tool:
        if item[:3] in exact:
            out.add(item)
            continue
        # Sorted, so that every run picks the same gold unit when several are related (a set has no fixed order).
        match = next((g for g in sorted(expected) if g[1:3] == item[1:3] and g[0] != item[0] and related(g[0], item[0])), None)
        out.add((match[0],) + item[1:] if match else item)
    return out


def gold_items(relations):
    items = set()
    for r in relations:
        if not counted(r['source_path']):
            continue
        key = (unit(r['source_path']), r['action'], document(r['target_document']))
        places = [place(p) for p in r.get('vi_tri') or []] or ([place('#' + r['doi_tuong'])] if r.get('doi_tuong') else [''])
        items |= {key + (p,) for p in places}
    return items


def tool_items(relations, status=None):
    items = set()
    for r in relations:
        if status and r.get('resolution_status', 'validated') != status:
            continue
        if not counted(r['source_path']):
            continue
        key = (unit(r['source_path']), r['action'], document(r['target_doc']))
        places = [place(p) for p in r.get('vi_tri') or []] or ([place('#' + r['doi_tuong'])] if r.get('doi_tuong') else [''])
        items |= {key + (p,) for p in places}
    return items


def normalize_gold(labels, packet):
    """Apply the settled conventions the same way to every batch, whatever a labeler chose:
    a consolidated text keeps one hop-nhat, to its base document (the first one named); its restated acts are not its own."""
    relations = labels['relations']
    if (packet or {}).get('loai') == 'Văn bản hợp nhất':
        base = [r for r in relations if r['action'] == 'hop-nhat'][:1]
        relations = base
    return relations


TITLES = {}


def law_title(source_url, index, number):
    """Title of the stored document with this number (read-only), to match a law the labeler named by name."""
    if number not in TITLES:
        import requests
        hits = requests.post(f'{source_url}/{index}/_search', json={'size': 1, '_source': ['title'],
                             'query': {'term': {'document_number': number}}}, timeout=30).json().get('hits', {}).get('hits', [])
        TITLES[number] = (hits[0]['_source'].get('title') or '').casefold() if hits else ''
    return TITLES[number]


def classify(miss, tool, structure_units):
    """The layer a gold item the tool did not produce exactly points to."""
    source, action, target, position = miss
    if source in structure_units:
        return 'structural'
    same_unit = [t for t in tool if t[0] == source]
    if any(t[1] == action and t[2] == target for t in same_unit):
        return 'scope'
    if any(t[2] == target for t in same_unit):
        return 'classification'
    if any(t[1] == action for t in same_unit):
        return 'reference'
    return 'semantic'


def ratio(a, b):
    return round(a / b, 3) if b else None


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('set')
    cli.add_argument('run')
    cli.add_argument('--json')
    cli.add_argument('--no-opening', action='store_true', help='Bỏ quan hệ ở Phần đầu (tên, lời dẫn) ở cả nhãn lẫn công cụ')
    cli.add_argument('--rows', choices=['keep', 'appendix', 'drop'], default='keep',
                     help='Dòng bảng phụ lục: giữ từng dòng; tính là phụ lục chứa dòng; hoặc không tính (cả nhãn lẫn công cụ)')
    args = cli.parse_args()
    global ROWS
    ROWS = args.rows
    manifest = json.loads((ROOT / 'eval' / 'sets' / 'manifest.json').read_text())['documents']
    gold = {g['doc_id']: g for f in sorted((ROOT / 'eval' / 'gold' / args.set).glob('*.json')) for g in json.loads(f.read_text())}
    packets = {p['doc_id']: p for f in sorted((ROOT / 'eval' / 'packets' / args.set).glob('*.json')) for p in json.loads(f.read_text())}
    from vbpl_v3 import config as settings
    settings.load()
    config = settings.Config.from_env()
    totals = defaultdict(Counter)
    errors = Counter()
    examples = defaultdict(list)
    for doc_id, labels in gold.items():
        output = ROOT / 'work' / args.run / 'dry-run' / f'{doc_id}.json'
        if not output.exists():
            continue
        relations = [r['_source'] for r in json.loads(output.read_text())['relations']]
        labeled = normalize_gold(labels, packets.get(doc_id))
        # A law the labeler named by name matches the tool's number when the stored document with that number bears the name.
        names = {document(r['target_document']) for r in labeled if re.match(r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s', r['target_document'] or '', re.I)}
        for r in relations:
            if names and NUMBER_ONLY.match(r.get('target_doc') or ''):
                title = law_title(config.source_url, config.source['documents'], r['target_doc'])
                for name in names:
                    if name and name in title:
                        r['target_doc'] = next(x['target_document'] for x in labeled if document(x['target_document']) == name)
        if args.no_opening:
            relations = [r for r in relations if unit(r['source_path']) != 'Phần đầu']
            labeled = [r for r in labeled if unit(r['source_path']) != 'Phần đầu']
        group = manifest.get(doc_id, {}).get('stratum', '?')
        expected = gold_items(labeled)
        validated = align(tool_items(relations, 'validated'), expected)
        unresolved = align(tool_items(relations, 'unresolved'), expected)
        structure_units = {unit(e['source_path']) for e in labels.get('loi_cau_truc') or []}
        for scope in ('all', group):
            t = totals[scope]
            t['documents'] += 1
            t['structure_ok'] += not structure_units
            gold_keys, tool_keys = {i[:3] for i in expected}, {i[:3] for i in validated}
            # Relation level: same act on the same document from the same unit or one up or down its tree. A gold act stated by the
            # article lead is found by the tool's acts of its clauses, and the other way round (20/10/2026). Recall counts gold items
            # found, precision counts tool items that match some gold item.
            found = {g for g in gold_keys if any(k[1:3] == g[1:3] and related(k[0], g[0]) for k in tool_keys)}
            right = {k for k in tool_keys if any(g[1:3] == k[1:3] and related(g[0], k[0]) for g in gold_keys)}
            t['rel_tp'] += len(found); t['rel_fn'] += len(gold_keys - found)
            t['rel_tp_p'] += len(right); t['rel_fp'] += len(tool_keys - right)
            matched = gold_keys & tool_keys
            t['pos_total'] += len({i for i in expected if i[:3] in matched})
            t['pos_right'] += len({i for i in expected if i[:3] in matched} & validated)
            t['e2e_tp'] += len(expected & validated); t['e2e_fp'] += len(validated - expected); t['e2e_fn'] += len(expected - validated)
            # Document level: the source reaches the right target document, whatever unit, act or position.
            gold_docs, tool_docs = {i[2] for i in expected}, {i[2] for i in validated}
            t['doc_tp'] += len(gold_docs & tool_docs); t['doc_fp'] += len(tool_docs - gold_docs); t['doc_fn'] += len(gold_docs - tool_docs)
            t['unresolved'] += len(unresolved); t['unresolved_real'] += len({i[:3] for i in unresolved} & gold_keys)
            t['tool_total'] += len(validated) + len(unresolved)
            # Macro: every document weighs the same, so one decree with 99 relations does not decide the score.
            if gold_keys or tool_keys:
                t['macro_docs'] += 1
                t['macro_p'] += len(right) / len(tool_keys) if tool_keys else (1 if not gold_keys else 0)
                t['macro_r'] += len(found) / len(gold_keys) if gold_keys else 1
        for miss in expected - validated:
            kind = classify(miss, validated, structure_units)
            errors[kind] += 1
            examples[kind].append([doc_id, 'thieu', list(miss)])
        for extra in validated - expected:
            if extra[:3] in {i[:3] for i in expected}:
                continue  # counted as a scope miss above
            kind = 'structural' if extra[0] in structure_units else 'semantic'
            errors[kind] += 1
            examples[kind].append([doc_id, 'thua', list(extra)])
        for r in relations:
            for p in r.get('vi_tri') or []:
                if p != 'toàn bộ' and positions(p) != [p] and not r.get('doi_tuong'):
                    errors['graph_mapping'] += 1
                    examples['graph_mapping'].append([doc_id, 'dinh_dang', p])

    def report(t):
        return {'documents': t['documents'], 'structural_ok': ratio(t['structure_ok'], t['documents']),
                'document_precision': ratio(t['doc_tp'], t['doc_tp'] + t['doc_fp']), 'document_recall': ratio(t['doc_tp'], t['doc_tp'] + t['doc_fn']),
                'relation_precision': ratio(t['rel_tp_p'], t['rel_tp_p'] + t['rel_fp']), 'relation_recall': ratio(t['rel_tp'], t['rel_tp'] + t['rel_fn']),
                'position_accuracy': ratio(t['pos_right'], t['pos_total']),
                'e2e_precision': ratio(t['e2e_tp'], t['e2e_tp'] + t['e2e_fp']), 'e2e_recall': ratio(t['e2e_tp'], t['e2e_tp'] + t['e2e_fn']),
                'unresolved_rate': ratio(t['unresolved'], t['tool_total']), 'unresolved_real': ratio(t['unresolved_real'], t['unresolved']),
                'macro_precision': ratio(t['macro_p'], t['macro_docs']), 'macro_recall': ratio(t['macro_r'], t['macro_docs'])}
    result = {'set': args.set, 'run': args.run, 'all': report(totals['all']),
              'by_group': {g: report(t) for g, t in sorted(totals.items()) if g != 'all'},
              'errors': dict(errors.most_common()), 'examples': {k: v[:15] for k, v in examples.items()}}
    print(json.dumps({k: result[k] for k in ('set', 'run', 'all', 'errors')}, ensure_ascii=False, indent=1))
    for g, r in result['by_group'].items():
        print(f"{g:>20}: n={r['documents']:>3} P={r['relation_precision']} R={r['relation_recall']} vi_tri={r['position_accuracy']} "
              f"e2e P/R={r['e2e_precision']}/{r['e2e_recall']} unresolved={r['unresolved_rate']}")
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
