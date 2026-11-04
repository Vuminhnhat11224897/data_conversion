"""Check the source before a run links relation targets in it (A2, 04/11/2026).

The 27/10/2026 runs read legal-docs on 10.1.10.10 (518,261 documents), which lacks 263815 (08/2015/NĐ-CP), 379366, 461197 …; the
later runs read the copy on 10.1.10.23 (566,606 then). 2,097 relations to documents that exist were left with no target_matched_id.
A run now stops before writing when:
- a known number (SOURCE_CANARIES, "number=id;…") does not come back with its id from the source documents index;
- the source has fewer documents than SOURCE_MIN_DOCUMENTS, or than 99% of the count the last check saw on the same cluster and index.
The result is kept in <workdir>/source-check.json and returned, for the run's log.
"""

from datetime import datetime
import json
import os

# Documents present on 10.1.10.23 and missing on 10.1.10.10 (04/11/2026): a run reading the smaller source stops.
DEFAULT_CANARIES = '08/2015/NĐ-CP=263815;156/2018/NĐ-CP=379366;98/2020/TT-BTC=461197'
DROP = 0.99


class SourceCheckFailed(RuntimeError):
    """The source documents index cannot be trusted for linking targets."""


def canaries(text=None):
    """'number=id;number=id' -> ((number, id), …). 'off' or empty: no canary."""
    text = os.getenv('SOURCE_CANARIES', DEFAULT_CANARIES) if text is None else text
    if text.strip().lower() in ('', 'off', 'no', '0'):
        return ()
    pairs = [item.rsplit('=', 1) for item in text.split(';') if item.strip()]
    if any(len(p) != 2 or not p[1].strip().isdigit() for p in pairs):
        raise ValueError('SOURCE_CANARIES phải có dạng "số hiệu=id;số hiệu=id"')
    return tuple((number.strip(), id_.strip()) for number, id_ in pairs)


def check(config, source):
    """None when no check is configured; else the facts checked. Raises SourceCheckFailed."""
    if not config.source_canaries and not config.source_min_documents:
        return None
    index = config.source['documents']
    count = source.count(index)
    problems = []
    if count < config.source_min_documents:
        problems.append(f'{index} có {count} văn bản, ít hơn SOURCE_MIN_DOCUMENTS={config.source_min_documents}')
    state = config.workdir / 'source-check.json'
    last = json.loads(state.read_text()) if state.exists() else None
    if last and last.get('url') == config.source_url and last.get('index') == index and count < DROP * last.get('count', 0):
        problems.append(f'{index} còn {count} văn bản, lần kiểm trước ({last.get("at")}) có {last["count"]}')
    for number, expected in config.source_canaries:
        found = {h['_id'] for h in source.by_numbers(index, [number])}
        if expected not in found:
            problems.append(f'tra {number} không ra văn bản {expected} (ra {sorted(found)[:3]})')
    if problems:
        raise SourceCheckFailed(f'Nguồn {config.source_url}/{index} không dùng được để nối văn bản đích: ' + '; '.join(problems))
    info = {'url': config.source_url, 'index': index, 'count': count, 'canaries': len(config.source_canaries),
            'at': datetime.now().astimezone().isoformat(timespec='seconds')}
    config.workdir.mkdir(parents=True, exist_ok=True)
    part = state.with_name(state.name + '.part')
    part.write_text(json.dumps(info, ensure_ascii=False, indent=1))
    part.replace(state)
    return info
