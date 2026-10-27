"""The embedding service (27/10/2026): the OpenAI-style bge-m3 API, the older /embed service, and no mixing of cut and whole vectors."""

import unittest
from unittest.mock import MagicMock, patch

from vbpl_v3 import embedding
from tests.test_guard import config


def reply(data):
    response = MagicMock(status_code=200)
    response.json.return_value = data
    return response


class Service(unittest.TestCase):
    def test_openai_style_api(self):
        answer = reply({'data': [{'index': 1, 'embedding': [0.2] * 1024}, {'index': 0, 'embedding': [0.1] * 1024}]})
        with patch('vbpl_v3.embedding.requests.post', return_value=answer) as post:
            vectors = embedding.embed(['a', 'b'], 'http://embed:9999/v1', 32, 'key', 'bge-m3')
        # Vectors come back in input order, whatever order the server lists them in.
        self.assertEqual([v[0] for v in vectors], [0.1, 0.2])
        self.assertEqual(post.call_args.args, ('http://embed:9999/v1/embeddings',))
        self.assertEqual((post.call_args.kwargs['headers'], post.call_args.kwargs['json']),
                         ({'Authorization': 'Bearer key'}, {'model': 'bge-m3', 'input': ['a', 'b']}))
        # 256 gives the vectors of the v2 and v3 indices.
        with patch('vbpl_v3.embedding.requests.post', return_value=reply({'data': [{'index': 0, 'embedding': [0.1] * 1024}]})) as post:
            embedding.embed(['a'], 'http://embed:9999/v1', 32, 'key', 'bge-m3', truncate=256)
        self.assertEqual(post.call_args.kwargs['json']['truncate_prompt_tokens'], 256)

    def test_older_service(self):
        with patch('vbpl_v3.embedding.requests.post', return_value=reply({'embeddings': [[0.1] * 1024]})) as post:
            embedding.embed(['a'], 'http://embed:8989', 64)
        self.assertEqual((post.call_args.args, post.call_args.kwargs['json']), (('http://embed:8989/embed',), {'texts': ['a'], 'batch_size': 64}))

    def test_cut_vectors_are_not_reused_beside_whole_ones(self):
        with self.assertRaises(ValueError):
            config(embedding_url='http://embed:9999/v1', embedding_reuse=True).validate()
        config(embedding_url='http://embed:9999/v1', embedding_reuse=True, embedding_truncate=256).validate()
        config(embedding_url='http://embed:9999/v1', embedding_reuse=False).validate()
        config(embedding_url='http://embed:8989', embedding_reuse=True).validate()  # the older service makes the v2 vectors
        # The target's own vectors (-v4) are whole chunks: reused only beside whole-chunk vectors.
        config(embedding_url='http://embed:9999/v1', embedding_reuse=False, embedding_reuse_target=True).validate()
        with self.assertRaises(ValueError):
            config(embedding_url='http://embed:9999/v1', embedding_reuse=False, embedding_reuse_target=True, embedding_truncate=256).validate()
