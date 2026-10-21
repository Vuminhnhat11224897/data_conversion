"""Settings come only from data_vbpl_v3/.env (or the process environment, e.g. docker --env-file)."""

from dataclasses import dataclass
import os
from pathlib import Path
import re

from dotenv import load_dotenv

HOME = Path(__file__).resolve().parent.parent
# Source index names that must never receive a v3 write, on any cluster.
PROTECTED = {'legal-docs', 'legal-chunk-section-v2', 'legal-changed-v2'}
ROLES = ('documents', 'chunks', 'changes')
# Target index suffixes: v3 is the contract; v4 is a staging copy for reviewing changes before v3 is rewritten.
STAGES = {'v3', 'v4'}


def load(env_file=None):
    load_dotenv(env_file or HOME / '.env')


def required(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise ValueError(f'Chưa điền {name} trong data_vbpl_v3/.env')
    return value


def number(name, default, low, high):
    value = int(os.getenv(name, str(default)))
    if not low <= value <= high:
        raise ValueError(f'{name} phải trong khoảng {low}..{high}')
    return value


@dataclass
class Config:
    source_url: str
    source: dict
    target_url: str
    target: dict
    embedding_url: str
    embedding_batch: int
    embedding_reuse: bool
    workdir: Path
    qa_max_tokens: int
    qa_scope_max_tokens: int
    extractor: str = 'llm'
    start_year: int = 1980

    @classmethod
    def from_env(cls):
        workdir = Path(os.getenv('V3_WORKDIR', 'work'))
        return cls(
            source_url=required('SOURCE_ES_URL').rstrip('/'),
            source={'documents': os.getenv('SOURCE_DOCUMENT_INDEX', 'legal-docs'),
                    'chunks': os.getenv('SOURCE_CHUNK_INDEX', 'legal-chunk-section-v2'),
                    'changes': os.getenv('SOURCE_CHANGE_INDEX', 'legal-changed-v2')},
            target_url=required('TARGET_ES_URL').rstrip('/'),
            target={'documents': os.getenv('TARGET_DOCUMENT_INDEX', 'legal-docs-v3'),
                    'chunks': os.getenv('TARGET_CHUNK_INDEX', 'legal-chunk-section-v3'),
                    'changes': os.getenv('TARGET_CHANGE_INDEX', 'legal-changed-v3')},
            embedding_url=os.getenv('EMBEDDING_URL', '').strip().rstrip('/'),
            embedding_batch=number('EMBEDDING_BATCH', 64, 1, 512),
            embedding_reuse=os.getenv('EMBEDDING_REUSE', 'yes') == 'yes',
            workdir=workdir if workdir.is_absolute() else HOME / workdir,
            qa_max_tokens=number('QA_MAX_TOKENS', 512, 128, 4096),
            qa_scope_max_tokens=number('QA_SCOPE_MAX_TOKENS', 1024, 256, 4096),
            # rules: regex detector + model QA (until 15/10/2026). llm: 4 layers, model extraction checked by rules (extract, resolver, validate).
            extractor=os.getenv('RELATION_EXTRACTOR', 'llm'),
            start_year=number('START_YEAR', 1980, 1000, 2999),
        ).validate()

    def validate(self):
        if self.extractor not in ('rules', 'llm'):
            raise ValueError('RELATION_EXTRACTOR phải là rules hoặc llm')
        for url in (self.source_url, self.target_url):
            if not re.fullmatch(r'https?://[^/\s]+', url):
                raise ValueError('SOURCE_ES_URL và TARGET_ES_URL phải có dạng http(s)://host:port')
        targets = set(self.target.values())
        if any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) for name in [*self.source.values(), *targets]):
            raise ValueError('Tên index chỉ gồm chữ thường, số và dấu gạch ngang')
        # -v4 is the staging copy: review a change there before rewriting -v3. The three names share one suffix.
        suffixes = {name.rsplit('-', 1)[-1] for name in targets}
        if len(targets) != 3 or len(suffixes) != 1 or suffixes - STAGES or targets & PROTECTED:
            raise ValueError('Ba index đích phải khác nhau, cùng kết thúc bằng -v3 (hoặc cùng -v4 để chạy thử) và không trùng index nguồn')
        if self.source_url == self.target_url and targets & set(self.source.values()):
            raise ValueError('Index đích trùng index nguồn trên cùng cụm')
        return self
