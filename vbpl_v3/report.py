"""Read-only comparison of converted documents: source indices vs v3 indices."""

from collections import Counter
import json
import statistics
import unicodedata


def side(cluster, names, ids):
    result = Counter()
    docs = {}
    for start in range(0, len(ids), 500):
        batch = ids[start:start + 500]
        docs.update({h['_id']: h['_source'] for h in cluster.scan(names['documents'], {'ids': {'values': batch}}, ['n_dieu', 'full_content'])})
    result['documents'] = len(docs)
    result['full_content_nfd'] = sum(unicodedata.normalize('NFC', s.get('full_content') or '') != (s.get('full_content') or '') for s in docs.values())
    per_doc, dieu_empty, docs_empty = Counter(), 0, set()
    for start in range(0, len(ids), 500):
        for hit in cluster.scan(names['chunks'], {'terms': {'doc_id': ids[start:start + 500]}}, ['doc_id', 'chunk_type', 'noi_dung']):
            source = hit['_source']
            per_doc[source['doc_id']] += 1
            if source['chunk_type'] == 'dieu' and not (source.get('noi_dung') or '').strip():
                dieu_empty += 1
                docs_empty.add(source['doc_id'])
    result['chunks'] = sum(per_doc.values())
    result['documents_without_chunks'] = sum(1 for i in ids if per_doc[i] == 0)
    result['dieu_chunks_empty_noi_dung'] = dieu_empty
    result['documents_with_empty_dieu'] = len(docs_empty)
    relations = []
    for start in range(0, len(ids), 500):
        numeric = [int(i) for i in ids[start:start + 500] if i.isdigit()]
        relations += list(cluster.scan(names['changes'], {'terms': {'source_id': numeric}}, ['target_matched_id']))
    result['relations'] = len(relations)
    result['relations_with_target'] = sum(1 for r in relations if r['_source'].get('target_matched_id') is not None)
    return result, {k: v.get('n_dieu') for k, v in docs.items()}


def report(config, source, target, root):
    # A --redo appends a newer line for the same document; the latest one counts.
    records = list({r['doc_id']: r for r in map(json.loads, (root / 'documents.jsonl').read_text(encoding='utf-8').splitlines())}.values())
    skipped = sum(1 for r in records if r.get('skipped'))
    records = [r for r in records if not r.get('skipped')]
    if not records:
        raise ValueError(f'Lượt này chưa có văn bản nào hoàn tất ({skipped} văn bản bị bỏ qua vì trước năm bắt đầu)')
    ids = [r['doc_id'] for r in records if not r.get('dry_run')]
    lines = [f'Lượt {root.name}: {len(records)} văn bản hoàn tất ({len(records) - len(ids)} dry-run)' + (f', {skipped} bỏ qua vì trước năm bắt đầu' if skipped else '')]
    if ids:
        old, old_n = side(source, config.source, ids)
        new, new_n = side(target, config.target, ids)
        lines.append(f'{"chỉ số":34s} {"nguồn":>12s} {"v3":>12s}')
        lines += [f'{k:34s} {old[k]:12d} {new[k]:12d}' for k in old]
        changed = [i for i in ids if old_n.get(i) != new_n.get(i)]
        lines.append(f'văn bản đổi n_dieu: {len(changed)}; ít Điều hơn nguồn: {sum(1 for i in changed if (new_n.get(i) or 0) < (old_n.get(i) or 0))}')
    total = Counter()
    for r in records:
        total['routed_documents'] += r['routed'] > 0
        total['routed_articles'] += r['routed']
        total['untitled_by_model'] += r['untitled']
        total['layout_reviewed'] += bool(r['layout'])
        total['layout_applied'] += bool(r['layout'] and r['layout'].get('applied'))
        total['ai_warnings'] += bool(r['ai_warnings'])
        total['vectors_reused'] += r['vectors_reused']
        total['vectors_new'] += r['vectors_new']
        total['candidates'] += r['candidates']
        total['relations'] += r['relations']
        total['resolved'] += r['resolved']
        total['qa_incomplete'] += r['qa'] == 'incomplete'
    lines.append('AI/vector/quan hệ: ' + json.dumps(dict(total), ensure_ascii=False))
    lines.append(f'giây/văn bản trung vị: {statistics.median(r["seconds"] for r in records)}')
    text = '\n'.join(lines)
    (root / 'report.txt').write_text(text + '\n', encoding='utf-8')
    return text
