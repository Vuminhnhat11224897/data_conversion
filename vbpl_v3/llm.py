"""OpenAI-compatible chat completions (LiteLLM or vLLM) with JSON schema output, a cache of validated answers,
and a cap on concurrent calls that follows the model server's day and night capacity."""

from datetime import datetime
import hashlib
import json
import os
import re
import threading
import time

import requests

from .config import required


def setting(name, default):
    return float(os.getenv(name, default))


def concurrency(now=None):
    """Calls the model server takes at once: LLM_CONCURRENCY_DAY, or LLM_CONCURRENCY_NIGHT in LLM_NIGHT_HOURS ("22-6": 22:00 to 06:00)."""
    start, end = (int(x) for x in os.getenv('LLM_NIGHT_HOURS', '22-6').split('-'))
    hour = (now or datetime.now()).hour
    night = (hour >= start or hour < end) if start > end else start <= hour < end
    return max(1, int(os.getenv('LLM_CONCURRENCY_NIGHT' if night else 'LLM_CONCURRENCY_DAY', '10' if night else '3')))


class Gate:
    """At most concurrency() model calls in flight in this process. A waiting call re-reads the clock, so 22:00 opens more slots."""

    def __init__(self):
        self.active = 0
        self.condition = threading.Condition()

    def __enter__(self):
        with self.condition:
            while self.active >= concurrency():
                self.condition.wait(timeout=30)
            self.active += 1

    def __exit__(self, *error):
        with self.condition:
            self.active -= 1
            self.condition.notify_all()


GATE = Gate()


def timeouts(max_tokens, timeout=None):
    """(connect, read) seconds. Read is LLM_TIMEOUT_READ, longer only for answers that may be long (LLM_MIN_TOKENS_PER_SECOND),
    never over the caller's limit."""
    read = max(setting('LLM_TIMEOUT_READ', '30'), max_tokens / setting('LLM_MIN_TOKENS_PER_SECOND', '20'))
    return setting('LLM_TIMEOUT_CONNECT', '5'), min(read, timeout) if timeout else read


def call_llm(prompt, text, folder, model=None, json_output=True, json_schema=None, *, max_tokens=8192, timeout=240):
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError('max_tokens must be a positive integer')
    max_tokens = min(max_tokens, int(setting('LLM_MAX_TOKENS', '4000')))
    body = {'model': model or required('LITELLM_MODEL'), 'temperature': 0, 'max_tokens': max_tokens,
            'chat_template_kwargs': {'enable_thinking': False},
            'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}]}
    if json_schema is not None:
        body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'legal_extraction', 'strict': True, 'schema': json_schema}}
    elif json_output:
        body['response_format'] = {'type': 'json_object'}
    # The server may refuse connections for minutes when busy (seen 15/10/2026, 10:34-10:41): wait and retry a refused connection,
    # outside the gate so a waiting call holds no slot. A read timeout is not retried here: the server did take the request.
    waits = [int(x) for x in os.getenv('LLM_CONNECT_RETRY_WAITS', '10,20,40,60,90').split(',') if x.strip()]
    for attempt in range(len(waits) + 1):
        try:
            with GATE:
                response = requests.post(required('LITELLM_BASE_URL').rstrip('/') + '/chat/completions',
                                         headers={'Authorization': 'Bearer ' + required('LITELLM_API_KEY')},
                                         json=body, timeout=timeouts(max_tokens, timeout))
            break
        except (requests.ConnectionError, requests.ConnectTimeout):
            if attempt == len(waits):
                raise
            time.sleep(waits[attempt])
    response.raise_for_status()
    completion = response.json()
    (folder / 'llm_response.json').write_text(json.dumps(completion, ensure_ascii=False, indent=2), encoding='utf-8')
    choices = completion.get('choices') if isinstance(completion, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError('LLM response must contain a completion choice')
    if choices[0].get('finish_reason') != 'stop':
        raise ValueError(f"LLM chưa hoàn tất: {choices[0].get('finish_reason')}; xem llm_response.json")
    message = choices[0].get('message')
    content = message.get('content') if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ValueError('LLM response must contain nonempty text')
    return content, completion.get('usage')


def describe(schema, path=''):
    """The field descriptions of a JSON schema as lines the model reads ("- units[].acts[].action: …; một trong: a, b").
    The schema is the single place that says what each field means; the response format only enforces its shape."""
    lines = []
    for name, field in (schema.get('properties') or {}).items():
        here = f'{path}.{name}' if path else name
        if field.get('description'):
            choices = field.get('enum') or (field.get('items') or {}).get('enum')
            lines.append(f'- {here}: {field["description"]}' + (f' Một trong: {", ".join(choices)}.' if choices else ''))
        items = field.get('items') or {}
        if items.get('type') == 'object':
            lines += describe(items, here + '[]')
        elif field.get('type') == 'object':
            lines += describe(field, here)
    return lines


def validated_json(prompt, text, folder, cache_name, validate, attempts=3, schema=None, *,
                   max_tokens=None, timeout=None, caller=None, check=None, stop_on_length=False):
    """Cache only validated JSON; keep invalid attempts and request a bounded repair."""
    cache = folder / cache_name
    error = None
    if schema is not None and describe(schema):
        prompt = prompt + '\n\nCác trường JSON trả về:\n' + '\n'.join(describe(schema))
    # An answer is kept with the hash of the full prompt that produced it: a changed prompt or field description asks again.
    stamp = folder / (cache.stem + '-prompt.sha256')
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    if check:
        check()
    if cache.exists() and stamp.exists() and stamp.read_text().strip() == digest:
        try:
            payload = json.loads(cache.read_text())
            validate(payload)
            return payload
        except (ValueError, TypeError, KeyError) as exc:
            error = exc
    attempts_folder = folder / (cache.stem + '-attempts')
    existing = max((int(p.name) for p in attempts_folder.glob('*') if p.is_dir() and p.name.isdigit()), default=0)
    for attempt in range(attempts):
        audit = attempts_folder / str(existing + attempt + 1)
        audit.mkdir(parents=True, exist_ok=True)
        repair = '' if error is None else ('\nPhản hồi trước không hợp lệ: ' + str(error)[:800] +
            '. Hãy sửa schema/quy tắc đã yêu cầu. Chép dẫn chứng NGUYÊN VĂN từ nguồn nếu cần dẫn chứng. '
            'Trả một JSON hoàn chỉnh, ngắn gọn; giữ đủ các field yêu cầu. Không viết quá trình suy luận.')
        try:
            if check:
                check()
            options = {'json_schema': schema}
            if max_tokens is not None:
                options['max_tokens'] = max_tokens
            if timeout is not None:
                options['timeout'] = timeout
            content, usage = (caller or call_llm)(prompt + repair, text, audit, **options)
            payload = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip()))
            validate(payload)
            cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            stamp.write_text(digest)
            (folder / (cache.stem + '-usage.json')).write_text(json.dumps(usage))
            return payload
        except (ValueError, TypeError, KeyError, requests.ConnectionError, requests.Timeout) as exc:
            error = exc
            if stop_on_length and 'chưa hoàn tất: length' in str(exc):
                (audit / 'error.json').write_text(json.dumps({'type': type(error).__name__, 'message': str(error)}, ensure_ascii=False))
                raise  # the caller asks again with less input; the same request would overflow again
        except requests.HTTPError as exc:
            if exc.response.status_code < 500 and exc.response.status_code != 429:
                raise
            error = exc
        (audit / 'error.json').write_text(json.dumps({'type': type(error).__name__, 'message': str(error)}, ensure_ascii=False))
        if attempt + 1 < attempts:
            time.sleep(attempt + 1)
    raise error
