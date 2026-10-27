"""Command line: python -m vbpl_v3 {check,init,convert,report,analyze}."""

import argparse
import dataclasses
import json
import os
import statistics
import sys

import requests

from . import config as settings
from .analyze import analyze
from .convert import run, select_ids
from .embedding import chunk_input, cosine, embed, health
from .es import Cluster
from .report import report

MAPPINGS = settings.HOME / 'vbpl_v3' / 'mappings'


def clusters(config):
    # The source never receives writes; the target may write only the three v3 indices.
    return Cluster(config.source_url), Cluster(config.target_url, writable=config.target.values())


def check(config, vectors=0):
    source, target = clusters(config)
    result = {}

    def probe(name, action):
        try:
            result[name] = {'ok': True, 'result': action()}
        except Exception as exc:
            result[name] = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:300]}'}

    probe('source_es', lambda: {'version': source.request('GET', '/')['version']['number'],
                                **{n: source.count(n) for n in config.source.values()}})
    probe('target_es', lambda: {'version': target.request('GET', '/')['version']['number'],
                                **{n: (target.count(n) if target.exists(n) else 'chưa tạo, chạy init') for n in config.target.values()}})

    def llm():
        response = requests.get(settings.required('LITELLM_BASE_URL').rstrip('/') + '/models',
                                 headers={'Authorization': 'Bearer ' + settings.required('LITELLM_API_KEY')}, timeout=(10, 30))
        response.raise_for_status()
        models = [m.get('id') for m in response.json().get('data', [])]
        if settings.required('LITELLM_MODEL') not in models:
            raise ValueError(f'Không thấy model {os.getenv("LITELLM_MODEL")} trong {models}')
        return settings.required('LITELLM_MODEL')
    probe('litellm', llm)
    probe('embedding', lambda: health(config.embedding_url or settings.required('EMBEDDING_URL'), config.embedding_key, config.embedding_model))

    def workdir():
        config.workdir.mkdir(parents=True, exist_ok=True)
        (config.workdir / '.write-test').write_text('ok')
        (config.workdir / '.write-test').unlink()
        return str(config.workdir)
    probe('workdir', workdir)
    if vectors:
        def legacy_vectors():
            # Re-embed stored chunks: high cosine means stored vectors match today's input/model and can be reused.
            body = {'size': vectors, '_source': ['tieu_de', 'noi_dung', 'embedding'], 'query': {'function_score': {
                'query': {'exists': {'field': 'embedding'}}, 'random_score': {'seed': 1, 'field': '_seq_no'}, 'boost_mode': 'replace'}}}
            hits = source.request('POST', f"/{config.source['chunks']}/_search", body)['hits']['hits']
            fresh = embed([chunk_input(h['_source']) for h in hits], config.embedding_url, config.embedding_batch, **config.embedding_options)
            scores = sorted(cosine(h['_source']['embedding'], v) for h, v in zip(hits, fresh))
            return {'chunks': len(scores), 'min': round(scores[0], 4), 'median': round(statistics.median(scores), 4),
                    'reuse_safe': scores[0] > 0.99}
        probe('legacy_vectors', legacy_vectors)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(v['ok'] for v in result.values()) else 1


def additions(wanted, current):
    """Fields (and sub-fields of objects) in the wanted mapping that the live index lacks."""
    missing = {}
    for name, spec in wanted.items():
        if name not in current:
            missing[name] = spec
        elif 'properties' in spec and current[name].get('properties') is not None:
            inner = additions(spec['properties'], current[name]['properties'])
            if inner:
                missing[name] = {'properties': inner}
    return missing


def init(config):
    _, target = clusters(config)
    for role, index in config.target.items():
        body = json.loads((MAPPINGS / f'{role}.json').read_text(encoding='utf-8'))
        if not target.exists(index):
            target.create_index(index, body)
            print(f'{index}: đã tạo')
            continue
        # Existing indices only gain fields; nothing already mapped or stored is changed.
        current = target.request('GET', f'/{index}/_mapping')[index]['mappings'].get('properties', {})
        missing = additions(body['mappings']['properties'], current)
        if missing:
            target.request('PUT', f'/{index}/_mapping', {'properties': missing})
        print(f'{index}: đã có; thêm trường mới: {sorted(missing) or "không"}')
    return 0


def main(argv=None):
    cli = argparse.ArgumentParser(prog='python -m vbpl_v3', description=__doc__)
    cli.add_argument('--env', help='File cấu hình (mặc định data_vbpl_v3/.env)')
    commands = cli.add_subparsers(dest='command', required=True)
    probe = commands.add_parser('check', help='Kiểm tra kết nối, chỉ đọc')
    probe.add_argument('--vectors', type=int, default=0, help='Tạo lại vector N chunk nguồn để kiểm tra có dùng lại vector cũ được không')
    commands.add_parser('init', help='Tạo 3 index v3 nếu chưa có; index đã có chỉ được thêm trường mới')
    convert = commands.add_parser('convert', help='Chuyển văn bản sang v3')
    convert.add_argument('--run', required=True, help='Tên lượt; nhật ký ở work/<run>, chạy lại cùng tên thì làm tiếp')
    pick = convert.add_mutually_exclusive_group()
    pick.add_argument('--sample', type=int, help='Lấy ngẫu nhiên N văn bản (tối đa 10.000)')
    pick.add_argument('--ids', help='File danh sách ID (mỗi dòng một ID hoặc mảng JSON)')
    pick.add_argument('--all', action='store_true', help='Toàn bộ văn bản khớp bộ lọc')
    convert.add_argument('--seed', type=int, default=20261009)
    convert.add_argument('--from-date', help='Lọc issuance_date từ YYYY-MM-DD')
    convert.add_argument('--to-date', help='Lọc issuance_date đến YYYY-MM-DD')
    convert.add_argument('--legal-type', help='Lọc theo legal_type')
    convert.add_argument('--limit', type=int, help='Chỉ chạy N văn bản chưa xong trong lượt này')
    # LLM calls stay under LLM_CONCURRENCY_DAY/NIGHT whatever this is; 10 lets the night capacity be used.
    convert.add_argument('--workers', type=int, default=10, help='Số văn bản chạy song song (mặc định 10). Số lời gọi LLM cùng lúc do LLM_CONCURRENCY_DAY/NIGHT giới hạn')
    convert.add_argument('--no-qa', action='store_true', help='Bỏ QA và không ghi quan hệ')
    convert.add_argument('--extractor', choices=['rules', 'llm'], help='Cách dò quan hệ; mặc định theo RELATION_EXTRACTOR (llm, chốt 20/10/2026)')
    convert.add_argument('--dry-run', action='store_true', help='Chạy đủ các bước nhưng không ghi ES; kết quả ở work/<run>/dry-run')
    convert.add_argument('--redo', action='store_true', help='Chạy lại cả văn bản đã xong trong lượt này (ví dụ sau khi thêm trường mới)')
    summary = commands.add_parser('report', help='So nguồn với v3 cho các văn bản đã chuyển, chỉ đọc')
    summary.add_argument('--run', required=True)
    survey = commands.add_parser('analyze', help='Đo độ phủ metadata cho đồ thị trên văn bản nguồn; chỉ đọc, không gọi AI')
    survey.add_argument('--name', required=True, help='Kết quả ở work/analyze-<name>/')
    survey_pick = survey.add_mutually_exclusive_group(required=True)
    survey_pick.add_argument('--sample', type=int)
    survey_pick.add_argument('--ids')
    survey.add_argument('--seed', type=int, default=20261012)
    survey.add_argument('--legal-type')
    survey.add_argument('--action', help='Lọc theo action của văn bản nguồn, ví dụ huongdan')
    survey.add_argument('--workers', type=int, default=8)
    args = cli.parse_args(argv)
    settings.load(args.env)
    config = settings.Config.from_env()
    if args.command == 'check':
        return check(config, args.vectors)
    if args.command == 'init':
        return init(config)
    source, target = clusters(config)
    if args.command == 'convert':
        if not 1 <= args.workers <= 32:
            cli.error('--workers phải trong khoảng 1..32')
        if not (config.workdir / args.run / 'ids.json').exists() and not (args.sample or args.ids or args.all):
            cli.error('Lượt mới cần --sample, --ids hoặc --all')
        settings.required('EMBEDDING_URL')
        if args.extractor:
            config = dataclasses.replace(config, extractor=args.extractor)
        return run(config, source, target, args)
    if args.command == 'analyze':
        args.all, args.from_date, args.to_date = False, None, None
        ids = select_ids(config, source, args)
        result = analyze(config, source, ids, config.workdir / f'analyze-{args.name}', args.workers)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    print(report(config, source, target, config.workdir / args.run))
    return 0


if __name__ == '__main__':
    sys.exit(main())
