"""Documents whose last write stopped part way in the target indices (E1, 03/11–04/11/2026). Read-only.

convert.write_document writes chunks, then relations, then the document record, and removes old records last. Every record carries
the ingest_job_id of the run that wrote it, so a document is complete when all its chunks and relations carry the job of its record:
- chunk_khac_luot, quan_he_khac_luot: chunks or relations of another run than the record (the write stopped before or after the
  record, or old records were not removed yet);
- chunk_khong_van_ban, quan_he_khong_van_ban: records of a document that has no record (a new document whose write stopped);
- van_ban_khong_chunk: a record with no chunk (old code deleted the chunks before writing; every document has at least one).
A write in progress shows the same signs for a few seconds; a document converted with --no-qa keeps relations of an older run.
"""


def document_jobs(target, index):
    """{document _id: ingest_job_id of its record}."""
    return {h['_id']: (h.get('_source') or {}).get('ingest_job_id') for h in target.scan(index, {'match_all': {}}, ['ingest_job_id'], size=10000)}


def group_jobs(target, index, field):
    """{value of field (as text): {ingest_job_id: records}} over the whole index, by a composite aggregation in pages."""
    jobs, after = {}, None
    while True:
        agg = {'composite': {'size': 10000, 'sources': [{'k': {'terms': {'field': field}}}, {'j': {'terms': {'field': 'ingest_job_id'}}}]}}
        if after:
            agg['composite']['after'] = after
        result = target.request('POST', f'/{index}/_search', {'size': 0, 'aggs': {'c': agg}})['aggregations']['c']
        for bucket in result['buckets']:
            jobs.setdefault(str(bucket['key']['k']), {})[bucket['key']['j']] = bucket['doc_count']
        after = result.get('after_key')
        if not result['buckets'] or not after:
            return jobs


def broken(target, config, documents=None):
    """{kind: sorted document ids} for the five kinds of the module doc. documents: {id: job} when the caller already read them."""
    docs = documents if documents is not None else document_jobs(target, config.target['documents'])
    chunks = group_jobs(target, config.target['chunks'], 'doc_id')
    changes = group_jobs(target, config.target['changes'], 'source_id')
    return {'chunk_khac_luot': sorted(d for d, jobs in chunks.items() if d in docs and set(jobs) != {docs[d]}),
            'quan_he_khac_luot': sorted(d for d, jobs in changes.items() if d in docs and set(jobs) != {docs[d]}),
            'chunk_khong_van_ban': sorted(d for d in chunks if d not in docs),
            'quan_he_khong_van_ban': sorted(d for d in changes if d not in docs),
            'van_ban_khong_chunk': sorted(d for d in docs if d not in chunks)}


def to_rewrite(report):
    """Documents that have a record but an incomplete write: converting them again repairs them."""
    return set(report['chunk_khac_luot']) | set(report['quan_he_khac_luot']) | set(report['van_ban_khong_chunk'])


def without_record(report):
    """Documents with chunks or relations but no record: converted again like any document missing from the target."""
    return set(report['chunk_khong_van_ban']) | set(report['quan_he_khong_van_ban'])
