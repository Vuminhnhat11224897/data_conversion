"""BGE-M3 embedding service: contract check and validated vectors.

Two kinds of service (27/10/2026): the OpenAI-style API, when EMBEDDING_URL ends with /v1 (POST /v1/embeddings with a key; vLLM
bge-m3 at 10.1.10.22:9999), and the older service (POST /embed). `truncate` keeps each input's first N tokens: 256 gives the vectors
of the v2 and v3 indices; None keeps the server's limit (8192 tokens), the whole chunk."""

import math
import time

import requests


def openai_style(url):
    return (url or '').rstrip('/').endswith('/v1')


def health(url, key='', model='bge-m3'):
    if openai_style(url):
        response = requests.get(url + '/models', headers={'Authorization': f'Bearer {key}'}, timeout=(10, 30))
        response.raise_for_status()
        served = {m['id']: m for m in response.json().get('data', [])}
        if model not in served:
            raise ValueError(f'Embedding service does not serve {model}: {sorted(served)}')
        dims = len(embed(['kiểm tra'], url, 1, key, model)[0])
        return {'model': model, 'dims': dims, 'max_model_len': served[model].get('max_model_len')}
    response = requests.get(url + '/health', timeout=(10, 30))
    response.raise_for_status()
    report = response.json()
    if report.get('model') != 'BAAI/bge-m3' or report.get('dims') != 1024:
        raise ValueError(f'Embedding service must be BAAI/bge-m3 with 1024 dims, got {report}')
    return report


def chunk_input(source):
    return ' '.join((source.get('tieu_de', '') + ' ' + source.get('noi_dung', '')).split())


def request(texts, url, batch_size, key, model, truncate):
    if openai_style(url):
        body = {'model': model, 'input': texts, **({'truncate_prompt_tokens': truncate} if truncate else {})}
        response = requests.post(url + '/embeddings', headers={'Authorization': f'Bearer {key}'}, json=body, timeout=(10, 300))
        response.raise_for_status()
        return [d['embedding'] for d in sorted(response.json()['data'], key=lambda d: d['index'])]
    response = requests.post(url + '/embed', json={'texts': texts, 'batch_size': batch_size}, timeout=(10, 120))
    response.raise_for_status()
    return response.json()['embeddings']


def embed(texts, url, batch_size, key='', model='bge-m3', truncate=None):
    if not url:
        raise ValueError('Chưa điền EMBEDDING_URL trong data_vbpl_v3/.env')
    error = None
    for attempt in range(4):
        try:
            vectors = request(texts, url, batch_size, key, model, truncate)
            if len(vectors) != len(texts) or any(len(v) != 1024 or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in v)
                                                 or sum(x * x for x in v) == 0 for v in vectors):
                raise ValueError('Embedding returned invalid vectors')
            return vectors
        except (requests.ConnectionError, requests.Timeout) as exc:
            error = exc
        except requests.HTTPError as exc:
            if exc.response.status_code < 500 and exc.response.status_code != 429:
                raise
            error = exc
        if attempt < 3:
            time.sleep(2 ** (attempt + 1))
    raise error


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
