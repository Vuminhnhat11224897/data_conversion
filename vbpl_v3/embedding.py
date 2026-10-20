"""BGE-M3 embedding service: contract check and validated vectors."""

import math
import time

import requests


def health(url):
    response = requests.get(url + '/health', timeout=(10, 30))
    response.raise_for_status()
    report = response.json()
    if report.get('model') != 'BAAI/bge-m3' or report.get('dims') != 1024:
        raise ValueError(f'Embedding service must be BAAI/bge-m3 with 1024 dims, got {report}')
    return report


def chunk_input(source):
    return ' '.join((source.get('tieu_de', '') + ' ' + source.get('noi_dung', '')).split())


def embed(texts, url, batch_size):
    if not url:
        raise ValueError('Chưa điền EMBEDDING_URL trong data_vbpl_v3/.env')
    error = None
    for attempt in range(4):
        try:
            response = requests.post(url + '/embed', json={'texts': texts, 'batch_size': batch_size}, timeout=(10, 120))
            response.raise_for_status()
            vectors = response.json()['embeddings']
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
