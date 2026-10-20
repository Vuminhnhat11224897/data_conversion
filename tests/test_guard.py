"""The source cluster is read-only and the target writes only the v3 indices."""

from pathlib import Path
import unittest
from unittest.mock import patch

from vbpl_v3.config import Config
from vbpl_v3.es import Cluster, WriteRefused

V3 = {'documents': 'legal-docs-v3', 'chunks': 'legal-chunk-section-v3', 'changes': 'legal-changed-v3'}
SOURCE = {'documents': 'legal-docs', 'chunks': 'legal-chunk-section-v2', 'changes': 'legal-changed-v2'}


def config(**changes):
    values = dict(source_url='http://source:9200', source=SOURCE, target_url='http://target:9200', target=V3,
                  embedding_url='http://embed', embedding_batch=8, embedding_reuse=True, workdir=Path('/tmp/v3'),
                  qa_max_tokens=512, qa_scope_max_tokens=1024)
    values.update(changes)
    return Config(**values)


class GuardCheck(unittest.TestCase):
    def test_source_never_writes(self):
        source = Cluster('http://source:9200')
        with patch('vbpl_v3.es.requests.request') as network:
            for call in (lambda: source.put('legal-docs', '1', {}), lambda: source.bulk('legal-docs-v3', [{'_id': '1', '_source': {}}]),
                         lambda: source.remove_group('legal-docs', 'doc_id', '1'), lambda: source.create_index('legal-docs-v3', {}),
                         lambda: source.request('DELETE', '/legal-docs')):
                with self.assertRaises(WriteRefused):
                    call()
            network.assert_not_called()
        self.assertTrue(source.allowed('POST', '/legal-docs/_search?scroll=5m', None))
        self.assertTrue(source.allowed('POST', '/legal-docs/_count', None))
        self.assertTrue(source.allowed('DELETE', '/_search/scroll', None))
        self.assertFalse(source.allowed('POST', '/legal-docs/_update/1', None))
        self.assertFalse(source.allowed('POST', '/legal-docs/_delete_by_query', None))

    def test_target_writes_only_v3_indices(self):
        target = Cluster('http://target:9200', writable=V3.values())
        self.assertTrue(target.allowed('PUT', '/legal-docs-v3/_doc/1', None))
        self.assertTrue(target.allowed('POST', '/legal-chunk-section-v3/_delete_by_query?refresh=true', None))
        self.assertTrue(target.allowed('POST', '/_bulk', b'{"index":{"_index":"legal-changed-v3","_id":"1"}}\n{}\n'))
        for method, path, raw in (('PUT', '/legal-docs/_doc/1', None), ('POST', '/legal-docs-v3,legal-docs/_delete_by_query', None),
                                  ('POST', '/_bulk', b'{"index":{"_index":"legal-docs","_id":"1"}}\n{}\n'),
                                  ('POST', '/_bulk', b'{"index":{"_index":"legal-docs-v3","_id":"1"}}\n{}\n{"index":{"_index":"legal-docs","_id":"2"}}\n{}\n'),
                                  ('DELETE', '/legal-docs-v3', None), ('PUT', '/legal-*/_settings', None)):
            self.assertFalse(target.allowed(method, path, raw), (method, path))

    def test_configuration_protects_source_indices(self):
        self.assertIs(config().validate().target, V3)
        for bad in ({'target': {**V3, 'documents': 'legal-docs'}}, {'target': {**V3, 'documents': 'legal-docs-v4'}},
                    {'target': {**V3, 'chunks': 'legal-docs-v3'}}, {'target_url': 'not a url'}):
            with self.assertRaises(ValueError):
                config(**bad).validate()
        # Same cluster is allowed as long as the v3 names differ from the source names.
        self.assertTrue(config(target_url='http://source:9200').validate())


if __name__ == '__main__':
    unittest.main()
