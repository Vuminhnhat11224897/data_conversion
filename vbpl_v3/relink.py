"""Link again the relations whose target was not found (target_matched_id missing), from their stored fields only (A2, 04/11/2026).

No model call and no new reading of the source document: the relation keeps its action, position and evidence; only the link to
the target document is looked up again, by relations.resolve, the same rule the conversion uses (number, cited day, authority; no
link when two documents remain). Run after the source gained documents: auto does it after each source scan.

An update carries the _seq_no and _primary_term the relation had when it was read: a relation rewritten since then (its document
converted again) refuses the update (409) and is counted, never overwritten.
"""

from collections import defaultdict
from datetime import datetime
import json

from .relations import is_number, lookup_numbers, resolve
from .text import number_key

FIELDS = ['source_id', 'source_issuance_date', 'source_issuing_authority', 'target_doc', 'target_issuance_date',
          'target_issuing_authority', 'target_candidates_count', 'target_match_note', 'evidence', 'action']
CHANGED = ('target_issuance_date', 'target_issuing_authority', 'target_match_note')


def unmatched(target, index):
    """Relations with a document number as target and no target_matched_id, with their sequence numbers."""
    query = {'bool': {'must_not': [{'exists': {'field': 'target_matched_id'}}]}}
    return [h for h in target.scan(index, query, FIELDS, size=5000, seq_no=True) if is_number((h.get('_source') or {}).get('target_doc'))]


def relink(config, source, target, write=False, out=None):
    """{'checked', 'linked', 'written', 'conflicts', 'at'}; out: one JSON line per relation that gets a target."""
    index = config.target['changes']
    rows = unmatched(target, index)
    numbers = sorted({n for h in rows for n in lookup_numbers([h['_source']['target_doc']])})
    found = defaultdict(dict)
    for hit in source.by_numbers(config.source['documents'], numbers) if numbers else []:
        found[number_key(hit['_source'].get('document_number'))][hit['_id']] = hit
    updates, lines = [], []
    for hit in rows:
        row = hit['_source']
        candidate = {**{k: row.get(k) for k in FIELDS}, '_evidence': row.get('evidence') or ''}
        pool = {i: h for n in lookup_numbers([row['target_doc']]) for i, h in found.get(number_key(n), {}).items()}
        resolve(candidate, list(pool.values()))
        if not candidate.get('target_matched_id'):
            continue
        change = {'target_matched_id': candidate['target_matched_id'], 'target_candidates_count': candidate['target_candidates_count']}
        change.update({k: candidate[k] for k in CHANGED if candidate.get(k) and candidate.get(k) != row.get(k)})
        updates.append({'_id': hit['_id'], '_source': change, 'if_seq_no': hit['_seq_no'], 'if_primary_term': hit['_primary_term']})
        lines.append({'_id': hit['_id'], 'source_id': row.get('source_id'), 'target_doc': row['target_doc'], **change})
    conflicts = target.bulk(index, updates, action='update', skip_status={409}) if write and updates else []
    if out:
        with open(out, 'w', encoding='utf-8') as stream:
            stream.writelines(json.dumps(line, ensure_ascii=False) + '\n' for line in lines)
    return {'checked': len(rows), 'linked': len(updates), 'written': len(updates) - len(conflicts) if write else 0,
            'conflicts': len(conflicts), 'at': datetime.now().astimezone().isoformat(timespec='seconds')}
