"""Relation QA with qwen-legal: keep only relations the source unit itself performs, with grounded scopes."""

from collections import defaultdict
import hashlib
import json
import os
import re

import requests

from .llm import validated_json
from .prompts import load
from .relations import declared_scope, frame, lookup_numbers, resolve
from .temporal import positions
from .text import action_matches, quote_in_text

PAIRED = re.compile(r'(?:sửa\s*đổi|điều\s+chỉnh)\s*,?\s*(?:và\s+)?bổ\s*sung', re.I)
VERDICT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['valid', 'reason'],
                  'properties': {'valid': {'type': 'boolean', 'description': 'true chỉ khi chính đơn vị nguồn thực hiện hành động lên văn bản đích.'},
                                 'reason': {'type': 'string', 'minLength': 1, 'maxLength': 240,
                                            'description': 'Một câu tiếng Việt, tối đa 30 từ, nêu căn cứ của kết luận.'}}}
SCOPE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['scope', 'correct', 'evidence'],
                'properties': {'scope': {'type': 'string', 'minLength': 1, 'maxLength': 200,
                                         'description': 'Vị trí bị tác động trong văn bản đích, nhỏ nhất và đủ cấp ("điểm a khoản 2 Điều 5").'},
                               'correct': {'type': 'boolean', 'description': 'true chỉ khi evidence hỗ trợ cả vị trí và hành động.'},
                               'evidence': {'type': 'string', 'maxLength': 1200,
                                            'description': 'Trích nguyên văn ngắn từ nguồn hỗ trợ vị trí và hành động.'}}}
VERDICT_PROMPT = load('qa_hanh_dong')
SCOPE_PROMPT = load('qa_pham_vi')


def validate_verdict(payload, *, bounded=True):
    if not isinstance(payload, dict) or set(payload) != {'valid', 'reason'} or type(payload['valid']) is not bool:
        raise ValueError('QA must return only boolean valid and reason')
    reason = payload['reason']
    if not isinstance(reason, str) or not reason.strip() or (bounded and (len(reason) > 240 or len(reason.split()) > 30)):
        raise ValueError('QA reason must be nonempty, at most 30 words and 240 characters')


def validate_scope(payload):
    if not isinstance(payload, dict) or set(payload) != {'scope', 'correct', 'evidence'} or type(payload['correct']) is not bool:
        raise ValueError('Scope QA must return only scope, boolean correct and evidence')
    if not isinstance(payload['scope'], str) or not payload['scope'].strip() or len(payload['scope']) > 200:
        raise ValueError('Scope QA must return a nonempty scope of at most 200 characters')
    if not isinstance(payload['evidence'], str) or len(payload['evidence']) > 1200 or (payload['correct'] and not payload['evidence'].strip()):
        raise ValueError('A correct scope needs source evidence of at most 1200 characters')


def stated(candidate):
    """The unit opens with the act itself and names where ("Bỏ gạch đầu dòng thứ ba điểm b …", "Sửa đổi, bổ sung khoản 5 Điều 4
    như sau"): the sentence performs the act directly, so no model verdict is needed."""
    if candidate.get('_stated'):
        return True  # read by a rule that only fires on an explicit sentence ("… hết hiệu lực kể từ ngày …")
    unit = candidate.get('_unit_evidence', candidate['_evidence'])
    declaration = frame(unit).lstrip()
    first = action_matches(declaration[:40])
    opens = bool(first) and first[0][0] == 0 and (first[0][2] == candidate['action']
                                                    or (candidate['action'] in ('sua-doi', 'bo-sung') and PAIRED.match(declaration)))
    return opens and declared_scope(unit, candidate.get('_parent_evidence', ''), candidate['action']) is not None


def verify(candidates, folder, lookup, provenance, config, caller=None):
    """Return (verified relation records, errors). lookup(numbers) returns target hits for resolve()."""
    groups = defaultdict(list)
    for candidate in candidates:
        groups[(candidate['source_path'], candidate['target_doc'], candidate['action'])].append(candidate)
    verified, errors, verdicts, caches = [], [], {}, {}
    for key, group in groups.items():
        # Changed evidence/scope, or another model, must never reuse a verdict.
        cache_key = hashlib.sha256(json.dumps([key, [(c['_evidence'], c.get('_unit_evidence'), c.get('_parent_evidence'), c['scope'])
                                                     for c in group], os.getenv('LITELLM_MODEL', '')], ensure_ascii=False).encode()).hexdigest()
        cache = caches[key] = folder / cache_key
        cache.mkdir(parents=True, exist_ok=True)
        if all(stated(c) for c in group):
            verdicts[key] = True
            continue
        try:
            payload = json.dumps({'target': key[1], 'action': key[2], 'source_path': key[0],
                                  'source': '\n\n'.join(dict.fromkeys(c['_evidence'] for c in group))[:12000],
                                  'unit': '\n\n'.join(dict.fromkeys(c.get('_unit_evidence', c['_evidence']) for c in group))}, ensure_ascii=False)
            verdicts[key] = validated_json(VERDICT_PROMPT, payload, cache, 'verdict-v3.json', validate_verdict, attempts=2,
                                           schema=VERDICT_SCHEMA, max_tokens=config.qa_max_tokens, timeout=120, caller=caller)['valid']
        except (ValueError, TypeError, KeyError, requests.RequestException) as error:
            errors.append({'group': list(key), 'type': type(error).__name__, 'message': str(error)[:500]})
    for (path, target, action), valid in list(verdicts.items()):
        # "Sửa đổi, bổ sung X" states both acts in one verb pair: the two relations stand or fall together.
        twin = (path, target, {'sua-doi': 'bo-sung', 'bo-sung': 'sua-doi'}.get(action))
        if twin in verdicts and any(PAIRED.search(c.get('_unit_evidence', c['_evidence'])) for c in groups[(path, target, action)]):
            verdicts[(path, target, action)] = valid or verdicts[twin]
    for key, group in groups.items():
        if not verdicts.get(key):
            continue
        cache = caches[key]
        for candidate in group:
            row = dict(candidate)
            unit = row.get('_unit_evidence', row['_evidence'])
            listed = row['action'] in ('thay-cum-tu', 'dinh-chinh') and row.get('vi_tri')
            # A correction's own list of places outranks one declared location ("Tại khoản 7 Điều 3, đính chính tên điểm …").
            explicit = None if listed and row['action'] == 'dinh-chinh' else declared_scope(unit, row.get('_parent_evidence', ''), row['action'])
            if explicit:
                row.update(scope=explicit, unresolved=False, scope_grounding_checked=True,
                           scope_grounding_correct=True, scope_resolution_method='explicit_declaration')
            elif listed:
                # The listed locations are copied from the unit itself; asking for one "correct" scope would drop the rest.
                explicit = row['scope']
                row.update(scope_grounding_checked=True, scope_grounding_correct=True, scope_resolution_method='liet_ke_vi_tri')
            exact_decimal_point = (re.fullmatch(r'Điểm\s+\d+(?:\.\d+)+\s+Khoản\s+\d+\s+Điều\s+\d+', row['scope'], re.I)
                                   and quote_in_text(row['scope'], unit))
            if (re.search(r'\d', row['scope']) or row['unresolved']) and not exact_decimal_point and not explicit:
                try:
                    answer = validated_json(SCOPE_PROMPT, json.dumps({'scope': row['scope'], 'source': row['_evidence'], 'unit': unit,
                                                                      'parent': row.get('_parent_evidence', '')}, ensure_ascii=False),
                                            cache, row['_id'] + '.json', validate_scope, attempts=2, schema=SCOPE_SCHEMA,
                                            max_tokens=config.qa_scope_max_tokens, timeout=120, caller=caller)
                except (ValueError, TypeError, KeyError, requests.RequestException) as error:
                    errors.append({'group': list(key), 'candidate': row['_id'], 'type': type(error).__name__, 'message': str(error)[:500]})
                    continue
                suggested, evidence = answer['scope'], answer['evidence']
                grounded = quote_in_text(evidence, row['_evidence']) and all(n in evidence for n in re.findall(r'\d+[a-zđ]?', suggested))
                row['scope_grounding_checked'] = True
                row['scope_grounding_correct'] = answer['correct'] and grounded
                if row['scope_grounding_correct'] and not positions(suggested):
                    # A description ("Nguyên tắc bán nợ xấu ...") is not a location; keep the declared scope.
                    row.update(scope_grounding_suggestion=suggested)
                elif row['scope_grounding_correct'] and (row['unresolved'] or suggested != row['scope']):
                    row.update(scope=suggested, unresolved=False, llm_refined=True)
                elif not row['scope_grounding_correct']:
                    row.update(unresolved=True, scope_grounding_suggestion=suggested, llm_hallucination_rejected=not grounded)
            resolve(row, lookup(lookup_numbers([row['target_doc']])))
            for name in ('_unit_evidence', '_parent_evidence', '_evidence', '_stated'):
                row.pop(name, None)
            rid = row.pop('_id')
            verified.append({'_id': rid, '_source': {**row, **provenance}})
    return verified, errors
