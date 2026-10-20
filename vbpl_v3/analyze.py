"""Read-only coverage measurement for the graph metadata: rules only, no model calls, no vectors, no writes."""

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import time

from .references import cross_references, guidance, law_by_name
from .relations import detect
from .structure import build_chunks, normalize, parse
from .temporal import effective_date
from .text import action_matches

META = ('document_number', 'title', 'legal_type', 'legal_sectors', 'issuing_authority', 'issuance_date', 'signers', 'tom_tat', 'action', 'url')
NORMATIVE = {'Luật', 'Bộ luật', 'Pháp lệnh', 'Lệnh', 'Sắc lệnh', 'Nghị định', 'Nghị quyết', 'Nghị quyết liên tịch',
             'Thông tư', 'Thông tư liên tịch', 'Quyết định', 'Chỉ thị'}


def measure(doc_id, config, source):
    src = source.get(config.source['documents'], doc_id)['_source']
    text = normalize(src.get('full_content') or '')
    parsed, _ = parse(text)
    meta = {k: src.get(k) for k in META}
    meta['legal_sectors'] = src.get('legal_sectors') or []

    def lookup(numbers):
        return source.by_numbers(config.source['documents'], numbers) if numbers else []
    effect = effective_date(text, src.get('legal_type'), src.get('issuance_date'))
    candidates = detect(doc_id, meta, parsed)
    guided = guidance(doc_id, meta, parsed, lookup, lambda name, day: law_by_name(source, config.source['documents'], name, day))
    chunks = build_chunks(doc_id, meta, parsed)
    amending = bool(action_matches(meta.get('title') or ''))
    refs = [cross_references(c['_source'], implicit=not amending) for c in chunks]
    return {'doc_id': doc_id, 'legal_type': src.get('legal_type'), 'action': src.get('action'),
            'issuance_date': src.get('issuance_date'), **effect,
            'candidate_actions': sorted({c['action'] for c in candidates}),
            'scopes': Counter(c['scope'] for c in candidates if c['scope'] in ('toàn bộ', 'toan-bo', 'toàn văn')),
            'guidance': len(guided), 'guidance_resolved': sum(1 for g in guided if g.get('target_matched_id')),
            'guidance_targets': [(g['action'], g['target_doc'], g.get('target_matched_id'), g['source_path']) for g in guided],
            'chunks': len(chunks), 'chunks_dan_chieu': sum(1 for r in refs if r),
            'chunks_so_van_ban_refs': sum(1 for c in chunks if c['_source'].get('so_van_ban_refs')),
            'chunks_either': sum(1 for c, r in zip(chunks, refs) if r or c['_source'].get('so_van_ban_refs')),
            'dan_chieu_kinds': Counter(x['loai'] for r in refs for x in r)}


def analyze(config, source, ids, root, workers=8):
    root.mkdir(parents=True, exist_ok=True)
    started, rows, failures = time.time(), [], []

    def work(doc_id):
        try:
            return measure(doc_id, config, source)
        except Exception as exc:
            failures.append({'doc_id': doc_id, 'error': f'{type(exc).__name__}: {str(exc)[:300]}'})
            return None
    with ThreadPoolExecutor(workers) as pool:
        rows = [r for r in pool.map(work, ids) if r]
    with (root / 'documents.jsonl').open('w', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps({**row, 'scopes': dict(row['scopes']), 'dan_chieu_kinds': dict(row['dan_chieu_kinds'])}, ensure_ascii=False) + '\n')

    def share(part, whole):
        return round(100 * part / whole, 1) if whole else None
    effect = {'all': [r for r in rows], 'normative': [r for r in rows if r['legal_type'] in NORMATIVE]}
    by_type = defaultdict(list)
    for r in rows:
        by_type[r['legal_type']].append(r)
    summary = {
        'documents': len(rows), 'failures': len(failures), 'seconds': round(time.time() - started),
        'ngay_hieu_luc': {name: {'documents': len(group),
                                 'coverage_percent': share(sum(1 for r in group if r['ngay_hieu_luc']), len(group)),
                                 'coverage_from_text_percent': share(sum(1 for r in group if r['ngay_hieu_luc'] and r['ngay_hieu_luc_cach'] != 'mac_dinh_ngay_ban_hanh'), len(group)),
                                 'methods': dict(Counter(r['ngay_hieu_luc_cach'] for r in group))} for name, group in effect.items()},
        'ngay_hieu_luc_by_type': {t: {'documents': len(g), 'coverage_percent': share(sum(1 for r in g if r['ngay_hieu_luc']), len(g))}
                                  for t, g in sorted(by_type.items(), key=lambda x: -len(x[1]))[:15]},
        'ngay_hieu_luc_before_issuance': sum(1 for r in rows if r['ngay_hieu_luc'] and r['issuance_date'] and r['ngay_hieu_luc'] < r['issuance_date']),
        'relation_actions_documents': dict(Counter(a for r in rows for a in r['candidate_actions'])),
        'guidance': {'documents_action_huongdan': sum(1 for r in rows if r['action'] == 'huongdan'),
                     'with_relation': sum(1 for r in rows if r['action'] == 'huongdan' and r['guidance']),
                     'with_resolved_target': sum(1 for r in rows if r['action'] == 'huongdan' and r['guidance_resolved']),
                     'all_documents_with_relation': sum(1 for r in rows if r['guidance']),
                     'relations': sum(r['guidance'] for r in rows), 'resolved': sum(r['guidance_resolved'] for r in rows)},
        'dan_chieu': {'chunks': sum(r['chunks'] for r in rows), 'chunks_with_dan_chieu': sum(r['chunks_dan_chieu'] for r in rows),
                      'chunks_with_so_van_ban_refs': sum(r['chunks_so_van_ban_refs'] for r in rows),
                      'chunks_with_either': sum(r['chunks_either'] for r in rows),
                      'kinds': dict(sum((r['dan_chieu_kinds'] for r in rows), Counter()))},
        'scope_whole_values': dict(sum((r['scopes'] for r in rows), Counter())),
    }
    summary['dan_chieu']['coverage_percent'] = share(summary['dan_chieu']['chunks_with_dan_chieu'], summary['dan_chieu']['chunks'])
    summary['dan_chieu']['so_van_ban_refs_percent'] = share(summary['dan_chieu']['chunks_with_so_van_ban_refs'], summary['dan_chieu']['chunks'])
    summary['dan_chieu']['either_percent'] = share(summary['dan_chieu']['chunks_with_either'], summary['dan_chieu']['chunks'])
    (root / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    (root / 'failures.json').write_text(json.dumps(failures, ensure_ascii=False, indent=1), encoding='utf-8')
    return summary
