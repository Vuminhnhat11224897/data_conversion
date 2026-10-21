"""Check the records of the three target indices against the target data contract (docs/09-hop-dong-du-lieu-v4.md; docs/04 lists
where v3 differs; rule labels use the section numbers of docs/04). Read-only: the target client may write no index. Embeddings are reduced to their length.
Usage: python -m eval.check_contract <v3|v4> [fails.json]. Results for v3: docs/04, 19/10/2026 (232 rules, 19 with failures).
"""
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from vbpl_v3 import config as settings  # noqa: E402
from vbpl_v3.es import Cluster  # noqa: E402

fails = defaultdict(list)  # rule -> ids of failing records
total = Counter()  # rule -> records checked


def rule(name, ok, rid):
    total[name] += 1
    if not ok:
        fails[name].append(rid)


DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TS = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)$')
JOB = re.compile(r'^v3:\d{8}T\d{6}Z$')
isdate = lambda v: isinstance(v, str) and bool(DATE.match(v))
TRACE = ['origin', 'ingest_job_id', 'ingest_revision', 'ingested_at', 'uploaded_by']


def trace(r, sec, rid):
    rule(f'{sec} 4.5 origin legacy|user_upload', r.get('origin') in ('legacy', 'user_upload'), rid)
    rule(f'{sec} 4.5 ingest_job_id v3:<run_id>', bool(JOB.match(str(r.get('ingest_job_id')))), rid)
    rule(f'{sec} 4.5 ingest_revision = 1', r.get('ingest_revision') == 1, rid)
    rule(f'{sec} 4.5 ingested_at ISO+tz', bool(TS.match(str(r.get('ingested_at')))), rid)
    rule(f'{sec} 4.5 uploaded_by = migration-v3', r.get('uploaded_by') == 'migration-v3', rid)


def load(cluster, index):
    rows = []
    for hit in cluster.scan(index, {'match_all': {}}):
        source = hit['_source']
        if isinstance(source.get('embedding'), list):
            source['embedding'] = len(source['embedding'])
        rows.append({'_id': hit['_id'], **source})
    return rows


def run(doc_rows, chunks, rels):
    docs = {d['_id']: d for d in doc_rows}
    # ---------------- 4.6 documents ----------------
    DOC_FIELDS = ['document_number', 'title', 'legal_type', 'legal_sectors', 'issuing_authority', 'issuance_date', 'signers', 'tom_tat',
                  'action', 'url', 'pdf_minio_path', 'pdf_vbpl_id', 'embedding', 'full_content', 'content_sha256', 'text_source', 'can_cu',
                  'can_cu_refs', 'intro', 'noi_nhan', 'phu_luc', 'has_tail', 'n_dieu', 'grade', 'la_vbqppl', 'la_vbqppl_cach', 'cap_hieu_luc',
                  'cap_hieu_luc_nhan', 'cap_hieu_luc_ghi_chu', 'ngay_hieu_luc', 'ngay_hieu_luc_cach', 'ngay_hieu_luc_so_ngay',
                  'ngay_hieu_luc_trich', 'hieu_luc_rieng', 'ngay_het_hieu_luc', 'ngay_het_hieu_luc_cach', 'ngay_het_hieu_luc_trich', 'hoi_to',
                  'ngay_hoi_to', 'ngay_hoi_to_trich', 'hoi_to_vi_tri'] + TRACE
    DOC_ALWAYS = [f for f in DOC_FIELDS if f not in ('legal_sectors', 'signers', 'pdf_minio_path', 'pdf_vbpl_id')]
    LEVELS = {1: 'HIEN_PHAP', 2: 'QUOC_HOI', 3: 'UBTV_QUOC_HOI', 4: 'CHU_TICH_NUOC', 5: 'CHINH_PHU', 6: 'THU_TUONG', 7: 'HDTP_TANDTC',
              8: 'THONG_TU', 9: 'THONG_TU_LIEN_TICH', 10: 'HDND_TINH', 11: 'UBND_TINH', 12: 'CHU_TICH_UBND_TINH', 13: 'HC_KT_DAC_BIET',
              14: 'HDND_XA', 15: 'UBND_XA'}
    EFF_CACH = {'ngay_cu_the', 'ngay_ky', 'ngay_thong_qua', 'ngay_dang_cong_bao', 'mac_dinh_ngay_ban_hanh', 'khong_doc_duoc',
                'khong_tim_thay', 'van_ban_hop_nhat'}
    extra_doc = Counter()
    for i, d in docs.items():
        S = '4.6'
        for f in DOC_ALWAYS:
            rule(f'{S} có trường "{f}" (mọi văn bản)', f in d, i)
        for f in d:
            if f not in DOC_FIELDS and f != '_id':
                extra_doc[f] += 1
        rule(f'{S}.2 _id chỉ chữ số', i.isdigit(), i)
        for f in ('document_number', 'title', 'legal_type', 'issuing_authority', 'tom_tat', 'action'):
            rule(f'{S}.2 {f} khác rỗng', bool((d.get(f) or '').strip()), i)
        rule(f'{S}.2 issuance_date là Ngày', isdate(d.get('issuance_date')), i)
        if 'legal_sectors' in d:
            rule(f'{S}.2 legal_sectors mảng, phần tử khác rỗng', isinstance(d['legal_sectors'], list) and all(s.strip() for s in d['legal_sectors']), i)
        u = d.get('url') or ''
        rule(f'{S}.2 url theo origin', u.startswith('https://thuvienphapluat.vn/') if d.get('origin') == 'legacy' else u == f'upload://{i}', i)
        if 'pdf_minio_path' in d:
            p = d['pdf_minio_path'] or ''
            rule(f'{S}.2 pdf_minio_path đúng dạng', (p.startswith('tvpl-pdf/') and p.endswith(f'_{i}.pdf')) or bool(re.match(r'^legal-upload/pdf/[0-9a-f]{64}\.pdf$', p)), i)
        if 'pdf_vbpl_id' in d:
            rule(f'{S}.2 pdf_vbpl_id chỉ chữ số', str(d['pdf_vbpl_id']).isdigit(), i)
        rule(f'{S}.2 embedding 1.024 chiều', d.get('embedding') == 1024, i)
        fc = d.get('full_content') or ''
        rule(f'{S}.3 full_content khác rỗng', bool(fc.strip()), i)
        rule(f'{S}.3 full_content NFC', unicodedata.is_normalized('NFC', fc), i)
        rule(f'{S}.3 content_sha256 = sha256(full_content)', d.get('content_sha256') == hashlib.sha256(fc.encode()).hexdigest(), i)
        if d.get('origin') == 'legacy':
            rule(f'{S}.3 legacy → text_source = source_full_content', d.get('text_source') == 'source_full_content', i)
        rule(f'{S}.3 can_cu: mỗi dòng bắt đầu "Căn cứ"', isinstance(d.get('can_cu'), list) and all(re.match(r'^\s*Căn\s+cứ', c, re.I) for c in d['can_cu']), i)
        rule(f'{S}.3 can_cu_refs là mảng', isinstance(d.get('can_cu_refs'), list), i)
        rule(f'{S}.3 noi_nhan là mảng', isinstance(d.get('noi_nhan'), list), i)
        rule(f'{S}.3 noi_nhan không có dòng chữ ký', not any(re.search(r'\b(?:KT\.|TM\.|Q\.|CHỦ TỊCH|BỘ TRƯỞNG|THỦ TƯỚNG|GIÁM ĐỐC)\b', x) for x in d.get('noi_nhan') or []), i)
        rule(f'{S}.3 grade full|partial|minimal', d.get('grade') in ('full', 'partial', 'minimal'), i)
        rule(f'{S}.3 n_dieu số nguyên', isinstance(d.get('n_dieu'), int), i)
        rule(f'{S}.3 has_tail boolean', isinstance(d.get('has_tail'), bool), i)
        for k, p in enumerate(d.get('phu_luc') or []):
            pid = f'{i}_pl{k}'
            rule(f'{S}.4 phu_luc.loai labeled|unlabeled', p.get('loai') in ('labeled', 'unlabeled'), pid)
            if p.get('loai') == 'unlabeled':
                rule(f'{S}.4 unlabeled → ky_hieu null', p.get('ky_hieu') is None, pid)
            rule(f'{S}.4 phu_luc.tieu_de khác rỗng', bool((p.get('tieu_de') or '').strip()), pid)
            rows = sum(1 for line in (p.get('noi_dung') or '').split('\n') if line.lstrip().startswith('|'))
            rule(f'{S}.4 n_table_rows = số dòng "|"', p.get('n_table_rows') == rows, pid)
            rule(f'{S}.4 has_table ⇔ n_table_rows ≥ 2', p.get('has_table') == ((p.get('n_table_rows') or 0) >= 2), pid)
            rule(f'{S}.4 có n_tables, dieu_luat', 'n_tables' in p and isinstance(p.get('dieu_luat'), list), pid)
            for a in p.get('dieu_luat') or []:
                aid = f'{pid}_d{a.get("ky_hieu")}'
                rule(f'{S}.5 dieu_luat có so_dieu, ky_hieu, tieu_de, noi_dung, so_van_ban_refs, khoan',
                     all(f in a for f in ('so_dieu', 'ky_hieu', 'tieu_de', 'noi_dung', 'so_van_ban_refs', 'khoan')), aid)
                rule(f'{S}.5 ky_hieu bắt đầu bằng so_dieu', str(a.get('ky_hieu', '')).startswith(str(a.get('so_dieu'))), aid)
                if a.get('khoan'):
                    rule(f'{S}.5 có mo_dau khi khoan khác rỗng', 'mo_dau' in a, aid)
                for kh in a.get('khoan') or []:
                    rule(f'{S}.5 khoan có so_khoan, ky_hieu, noi_dung, so_van_ban_refs, diem',
                         all(f in kh for f in ('so_khoan', 'ky_hieu', 'noi_dung', 'so_van_ban_refs', 'diem')), aid)
                    for dm in kh.get('diem') or []:
                        if 'tieu_diem' in dm:
                            rule(f'{S}.5 tieu_diem → có mo_dau', 'mo_dau' in dm, aid)
        # 4.6.6
        c = d.get('la_vbqppl_cach')
        rule(f'{S}.6 la_vbqppl null ⇔ cach = can_kiem', (d.get('la_vbqppl') is None) == (c == 'can_kiem'), i)
        if d.get('la_vbqppl') is not True:
            rule(f'{S}.6 la_vbqppl ≠ true → cap_hieu_luc null', d.get('cap_hieu_luc') is None, i)
        cap = d.get('cap_hieu_luc')
        rule(f'{S}.6 cap_hieu_luc_nhan khớp cap_hieu_luc', d.get('cap_hieu_luc_nhan') == LEVELS.get(cap) if cap is not None else d.get('cap_hieu_luc_nhan') is None, i)
        g = d.get('cap_hieu_luc_ghi_chu')
        rule(f'{S}.6 cap_hieu_luc_ghi_chu đúng enum', g in (None, 'hinh_thuc_cu', 'cap_huyen', 'khong_xac_dinh'), i)
        if g in ('cap_huyen', 'khong_xac_dinh'):
            rule(f'{S}.6 cap_huyen|khong_xac_dinh → cap null', cap is None, i)
        # 4.6.7
        rule(f'{S}.7 ngay_hieu_luc Ngày|null', d.get('ngay_hieu_luc') is None or isdate(d.get('ngay_hieu_luc')), i)
        hc = d.get('ngay_hieu_luc_cach')
        rule(f'{S}.7 ngay_hieu_luc_cach đúng enum', hc in EFF_CACH, i)
        rule(f'{S}.7 ngay_hieu_luc_trich null ⇔ cach ∈ {{mac_dinh, khong_tim_thay, hop_nhat}}',
             (d.get('ngay_hieu_luc_trich') is None) == (hc in ('mac_dinh_ngay_ban_hanh', 'khong_tim_thay', 'van_ban_hop_nhat')), i)
        if hc == 'ngay_cu_the':
            rule(f'{S}.7 ngay_cu_the → so_ngay null', d.get('ngay_hieu_luc_so_ngay') is None, i)
        if hc == 'mac_dinh_ngay_ban_hanh':
            rule(f'{S}.7 mac_dinh_ngay_ban_hanh chỉ khi la_vbqppl = false', d.get('la_vbqppl') is False, i)
            rule(f'{S}.7 mac_dinh → ngay_hieu_luc = issuance_date', d.get('ngay_hieu_luc') == d.get('issuance_date'), i)
        eh = d.get('ngay_het_hieu_luc_cach')
        rule(f'{S}.7 ngay_het_hieu_luc_cach đúng enum', eh in ('ngay_cu_the', 'het_nam', 'khong_ghi'), i)
        rule(f'{S}.7 ngay_het_hieu_luc null ⇔ khong_ghi', (d.get('ngay_het_hieu_luc') is None) == (eh == 'khong_ghi'), i)
        rule(f'{S}.7 ngay_het_hieu_luc_trich null ⇔ khong_ghi', (d.get('ngay_het_hieu_luc_trich') is None) == (eh == 'khong_ghi'), i)
        rule(f'{S}.7 hoi_to ⇔ ngay_hoi_to ≠ null', bool(d.get('hoi_to')) == (d.get('ngay_hoi_to') is not None), i)
        rule(f'{S}.7 ngay_hoi_to_trich null ⇔ hoi_to = false', (d.get('ngay_hoi_to_trich') is None) == (not d.get('hoi_to')), i)
        if d.get('ngay_hoi_to'):
            rule(f'{S}.7 ngay_hoi_to trước issuance_date', d['ngay_hoi_to'] < d.get('issuance_date', ''), i)
        trace(d, S, i)

    # ---------------- 4.7 chunks ----------------
    ART = {'dieu', 'dieu_full', 'dieu_mo_dau', 'khoan', 'khoan_full', 'khoan_mo_dau', 'diem'}
    TYPES = ART | {'tieu_diem', 'phu_luc', 'muc', 'noi_dung', 'noi_dung_full'}
    X = r'\d+[a-zđ]?'
    PRE = r'(?:_pl\d+)?(?:_s\d+)?'
    PAT = {'dieu': rf'_d{X}', 'dieu_full': rf'_d{X}_full', 'dieu_mo_dau': rf'_d{X}_md', 'khoan': rf'_d{X}_k{X}',
           'khoan_full': rf'_d{X}_k{X}_full', 'khoan_mo_dau': rf'_d{X}_k{X}_md', 'diem': rf'_d{X}_k{X}_p[\wđ.]+',
           'tieu_diem': rf'_d{X}_k{X}_p[\wđ.]+_t\d+'}
    DOC_COPY = ['document_number', 'title', 'action', 'legal_type', 'issuing_authority', 'issuance_date', 'url', 'signers']
    CHUNK_FIELDS = set(['doc_id', 'chunk_type', 'tieu_de', 'noi_dung', 'so_van_ban_refs', 'embedding', 'legal_sectors', 'dieu_uid', 'segment',
                        'so_dieu', 'ky_hieu_dieu', 'chuong', 'muc_lon', 'khoan_uid', 'so_khoan', 'ky_hieu_khoan', 'so_diem', 'diem_uid',
                        'so_tieu_diem', 'is_full', 'in_phu_luc', 'phu_luc_tieu_de', 'has_table', 'so_muc', 'so_doan', 'dan_chieu',
                        'ngay_hieu_luc', 'ngay_hieu_luc_cach', 'ngay_hieu_luc_so_ngay', 'ngay_hieu_luc_rieng', 'ngay_hoi_to'] + DOC_COPY + TRACE)
    extra_chunk = Counter()
    by_doc = defaultdict(list)
    for c in chunks:
        i, t, did = c['_id'], c.get('chunk_type'), c.get('doc_id')
        S = '4.7'
        by_doc[did].append(c)
        for f in c:
            if f not in CHUNK_FIELDS and f != '_id':
                extra_chunk[f] += 1
        rule('4.2 chunk doc_id có trong legal-docs-v3', did in docs, i)
        d = docs.get(did, {})
        rule(f'{S}.3 _id bắt đầu bằng <doc_id>_', i.startswith(f'{did}_'), i)
        rule(f'{S}.2 chunk_type thuộc 11 giá trị', t in TYPES, i)
        base = re.sub(r'_\d+$', '', i) if not re.search(r'_nd\d+$|_pl\d+$|_m[^_]+$', i) else i
        if t in PAT:
            rule(f'{S}.2 _id khớp mẫu của chunk_type', bool(re.fullmatch(re.escape(str(did)) + PRE + PAT[t] + r'(?:_\d+)?', i)), i)
        elif t == 'phu_luc':
            rule(f'{S}.2 _id khớp mẫu của chunk_type', bool(re.fullmatch(rf'{did}_pl\d+(?:_\d+)?', i)), i)
        elif t == 'muc':
            rule(f'{S}.2 _id khớp mẫu của chunk_type', i.startswith(f'{did}_') and '_m' in i, i)
        elif t == 'noi_dung':
            rule(f'{S}.2 _id khớp mẫu của chunk_type', bool(re.fullmatch(rf'{did}_nd\d*', i)), i)
        elif t == 'noi_dung_full':
            rule(f'{S}.2 _id khớp mẫu của chunk_type', i == f'{did}_nd_full', i)
        rule(f'{S}.3 có tieu_de, noi_dung', 'tieu_de' in c and 'noi_dung' in c, i)
        rule(f'{S}.3 tieu_de + noi_dung khác rỗng', bool(((c.get('tieu_de') or '') + (c.get('noi_dung') or '')).strip()), i)
        if t in ('muc', 'noi_dung', 'noi_dung_full'):
            rule(f'{S}.3 muc/noi_dung → tieu_de rỗng', not (c.get('tieu_de') or '').strip(), i)
        rule(f'{S}.3 so_van_ban_refs là mảng', isinstance(c.get('so_van_ban_refs'), list), i)
        if i.endswith('_md'):
            rule(f'{S}.3 chunk _md → so_van_ban_refs rỗng', c.get('so_van_ban_refs') == [], i)
        rule(f'{S}.3 embedding 1.024 chiều', c.get('embedding') == 1024, i)
        for f in DOC_COPY:
            if f in d:
                rule(f'{S}.3 {f} bằng văn bản', c.get(f) == d[f], i)
        if 'legal_sectors' in d:
            rule(f'{S}.3 legal_sectors = chuỗi nối ", "', c.get('legal_sectors') == ', '.join(d['legal_sectors']), i)
        if t in ART:
            m = re.match(re.escape(str(did)) + PRE + rf'_d{X}', i)
            rule(f'{S}.3 dieu_uid = phần đầu _id đến _d<x>', bool(m) and c.get('dieu_uid') == m.group(), i)
            sm = re.search(r'_s(\d+)_d', i)
            rule(f'{S}.3 segment khớp _s<s>', c.get('segment') == (int(sm.group(1)) if sm else 0), i)
            rule(f'{S}.3 có so_dieu, ky_hieu_dieu', isinstance(c.get('so_dieu'), int) and 'ky_hieu_dieu' in c, i)
            rule(f'{S}.3 dieu_uid kết thúc _d<ky_hieu_dieu>', str(c.get('dieu_uid', '')).endswith(f'_d{c.get("ky_hieu_dieu")}'), i)
        if t in ('khoan', 'khoan_full', 'khoan_mo_dau', 'diem'):
            m = re.match(re.escape(str(did)) + PRE + rf'_d{X}_k{X}', i)
            rule(f'{S}.3 khoan_uid = phần đầu _id đến _k<y>', bool(m) and c.get('khoan_uid') == m.group(), i)
            rule(f'{S}.3 có so_khoan, ky_hieu_khoan', isinstance(c.get('so_khoan'), int) and 'ky_hieu_khoan' in c, i)
        if t in ('diem', 'tieu_diem'):
            rule(f'{S}.3 diem/tieu_diem có so_diem', 'so_diem' in c, i)
            rule(f'{S}.3 diem/tieu_diem có diem_uid', 'diem_uid' in c, i)
            if t == 'diem':
                rule(f'{S}.3 diem_uid = _id của chunk diem', c.get('diem_uid') == base, i)
        if t == 'tieu_diem':
            rule(f'{S}.3 tieu_diem có so_tieu_diem', isinstance(c.get('so_tieu_diem'), int), i)
        if t in ('dieu', 'dieu_full', 'khoan', 'khoan_full', 'noi_dung_full'):
            rule(f'{S}.3 is_full = true ở dieu/dieu_full/khoan/khoan_full/noi_dung_full', c.get('is_full') is True, i)
        else:
            rule(f'{S}.3 is_full chỉ ở 5 loại', 'is_full' not in c, i)
        pm = re.match(rf'{did}_pl(\d+)', i)
        rule(f'{S}.3 in_phu_luc ⇔ _id có _pl<i>', (c.get('in_phu_luc') is True) == bool(pm) and c.get('in_phu_luc') in (True, None), i)
        if pm and 'phu_luc' in d:
            k = int(pm.group(1))
            pls = d['phu_luc']
            rule(f'{S}.3 _pl<i> có phần tử phu_luc[i]', k < len(pls), i)
            if k < len(pls):
                rule(f'{S}.3 phu_luc_tieu_de = 500 ký tự đầu phu_luc[i].tieu_de', c.get('phu_luc_tieu_de') == pls[k]['tieu_de'][:500], i)
                rule(f'{S}.3 has_table = phu_luc[i].has_table', c.get('has_table') == pls[k].get('has_table'), i)
        if t == 'muc':
            rule(f'{S}.3 muc có so_muc', 'so_muc' in c, i)
        nm = re.fullmatch(rf'{did}_nd(\d+)', i)
        if nm:
            rule(f'{S}.3 so_doan = k', c.get('so_doan') == int(nm.group(1)), i)
        for dc in c.get('dan_chieu') or []:
            rule(f'{S}.4 dan_chieu.loai đúng enum', dc.get('loai') in ('noi_bo', 'noi_bo_ngam', 'ngoai', 'van_ban_bi_sua'), i)
            if dc.get('loai') in ('noi_bo', 'noi_bo_ngam'):
                rule(f'{S}.4 noi_bo → van_ban null, target_id = doc_id', dc.get('van_ban') is None and str(dc.get('target_id')) == str(did), i)
        if 'dan_chieu' in c:
            rule(f'{S}.3 dan_chieu khác rỗng khi có', bool(c['dan_chieu']), i)
        for f in ('ngay_hieu_luc', 'ngay_hieu_luc_cach', 'ngay_hieu_luc_so_ngay', 'ngay_hieu_luc_rieng'):
            rule(f'{S}.3 có "{f}" (mọi chunk)', f in c, i)
        trace(c, S, i)
        rule(f'{S}.3 5 trường truy vết bằng văn bản', all(c.get(f) == d.get(f) for f in TRACE), i)
    for did in docs:
        rule('4.2 mọi văn bản có ít nhất một chunk', bool(by_doc.get(did)), did)
        ids = {c['_id'] for c in by_doc.get(did, [])}
        for k, p in enumerate(docs[did].get('phu_luc') or []):
            if not p.get('dieu_luat'):
                rule('4.6.4 phu_luc không chia Điều có chunk <doc>_pl<i>', f'{did}_pl{k}' in ids, f'{did}_pl{k}')
        nd = [c for c in by_doc.get(did, []) if re.fullmatch(rf'{did}_nd\d+', c['_id'])]
        if nd:
            rule('4.7.3 có đoạn → đúng một noi_dung_full', sum(c.get('chunk_type') == 'noi_dung_full' for c in by_doc[did]) == 1, did)
            rule('4.7.3 so_doan liên tục từ 1', sorted(c.get('so_doan') for c in nd) == list(range(1, len(nd) + 1)), did)

    # ---------------- 4.8 relations ----------------
    ACTIONS = {'bo-sung', 'sua-doi', 'thay-cum-tu', 'bai-bo', 'thay-the', 'dinh-chinh', 'huong-dan', 'hop-nhat', 'quy-dinh-chi-tiet', 'huy-bo',
               'dinh-chi', 'ngung-hieu-luc', 'gia-han'}
    EFFECT = {'bai-bo': 've_sau', 'huy-bo': 'tu_dau', 'sua-doi': 've_sau', 'bo-sung': 've_sau', 'thay-the': 've_sau', 'thay-cum-tu': 've_sau',
              'dinh-chi': 'tam_ngung', 'huong-dan': 'khong_ap_dung', 'quy-dinh-chi-tiet': 'khong_ap_dung', 'dinh-chinh': 'tu_dau',
              'ngung-hieu-luc': 'tam_ngung', 'gia-han': 've_sau', 'hop-nhat': 'khong_ap_dung'}
    PREFIX = {'': None, 'hidden_': 'hidden', 'intro_': 'intro', 'hhl_': 'het_hieu_luc', 'hd_': 'title_guidance', 'hn_': 'hop_nhat'}
    Y = r'\d+[a-zđ]?'
    Z = r'(?:[a-zđ]\d*|\d+(?:\.\d+)+)'
    C = r'(?:[IVXLC]+|\d+)'
    SYM = r'[\w.\-]+'
    VI_TRI = re.compile('^(?:' + '|'.join([
        rf'Điều {Y}', rf'khoản {Y} Điều {Y}', rf'điểm {Z} khoản {Y} Điều {Y}', rf'tiểu điểm \d+ điểm {Z} khoản {Y} Điều {Y}',
        rf'tên Điều {Y}', rf'tên Chương {C}', rf'tên Mục \d+(?: Chương {C})?', rf'Chương {C}', rf'Mục \d+(?: Chương {C})?',
        r'Phụ lục', rf'Phụ lục {SYM}', rf'Mục {SYM} Phụ lục(?: {SYM})?', rf'Mục {SYM} Phần {SYM} Phụ lục(?: {SYM})?', 'tên văn bản', 'toàn bộ']) + ')$')
    SP = re.compile(rf'^(?:(?:Phụ lục \d+ )?(?:Văn bản kèm theo \d+ )?Điều {Y}(?: Khoản {Y}(?: điểm [\wđ.]+)?)?|intro|Tiêu đề|Lời dẫn|Phần đầu|Mục .+|Nội dung'
                    r'|Phụ lục \d+(?: Mục \S+)?(?: STT \S+)?)$')
    REL_FIELDS = set(['source_id', 'source_document_number', 'source_title', 'source_action', 'source_issuing_authority', 'source_issuance_date',
                      'source_legal_type', 'source_url', 'source_legal_sectors', 'source_path', 'source_in_phu_luc', 'source_ngay_hieu_luc',
                      'source_ngay_hoi_to', 'target_doc', 'target_matched_id', 'target_candidates_count', 'target_issuance_date',
                      'target_issuing_authority', 'target_match_note', 'action', 'scope', 'vi_tri', 'cap_quan_he', 'hieu_luc_tac_dong',
                      'unresolved', 'doi_tuong', 'doi_tuong_loai', 'ma_thu_tuc', 'chi_tiet_vi_tri', 'kem_theo', 'cum_tu', 'dinh_chi_tu_ngay', 'dinh_chi_den_ngay', 'dinh_chi_den_khi',
                      'gia_han_den_ngay', 'gia_han_den_khi', 'detection_mode', 'resolution_status', 'resolution_reason', 'extraction', 'evidence',
                      'target_section', 'scope_resolution_method', 'scope_grounding_checked', 'scope_grounding_correct',
                      'scope_grounding_suggestion', 'llm_refined', 'llm_hallucination_rejected'] + TRACE)
    REL_ALWAYS = ['source_id', 'source_document_number', 'source_title', 'source_action', 'source_issuing_authority', 'source_issuance_date',
                  'source_legal_type', 'source_url', 'source_legal_sectors', 'source_path', 'source_in_phu_luc', 'source_ngay_hieu_luc',
                  'target_doc', 'target_matched_id', 'target_candidates_count', 'action', 'scope', 'vi_tri', 'cap_quan_he', 'hieu_luc_tac_dong',
                  'unresolved', 'resolution_status', 'extraction', 'doi_tuong_loai'] + TRACE
    extra_rel = Counter()
    numbering = defaultdict(list)
    for r in rels:
        i = r['_id']
        S = '4.8'
        for f in REL_ALWAYS:
            rule(f'{S} có trường "{f}" (luôn)', f in r, i)
        for f in r:
            if f not in REL_FIELDS and f != '_id':
                extra_rel[f] += 1
        m = re.fullmatch(r'(hidden_|intro_|hhl_|hd_|hn_)?(\d+)_(\d+)', i)
        rule(f'{S}.2 _id dạng <tiền tố><source_id>_<n>', bool(m), i)
        if m:
            pre = m.group(1) or ''
            rule(f'{S}.2 tiền tố khớp detection_mode', r.get('detection_mode') == PREFIX[pre], i)
            rule(f'{S}.2 _id chứa source_id', str(r.get('source_id')) == m.group(2), i)
            numbering[(pre, m.group(2))].append(int(m.group(3)))
        a = r.get('action')
        rule(f'{S}.5 action thuộc 13 giá trị', a in ACTIONS, i)
        rule(f'{S}.2 title_guidance ⇔ huong-dan|quy-dinh-chi-tiet', (r.get('detection_mode') == 'title_guidance') == (a in ('huong-dan', 'quy-dinh-chi-tiet')), i)
        rule(f'{S}.2 hop_nhat ⇔ action hop-nhat', (r.get('detection_mode') == 'hop_nhat') == (a == 'hop-nhat'), i)
        sid = str(r.get('source_id'))
        rule(f'{S}.3 source_id số nguyên', isinstance(r.get('source_id'), int), i)
        rule('4.2 source_id có trong legal-docs-v3', sid in docs, i)
        d = docs.get(sid, {})
        for f in ('document_number', 'title', 'action', 'issuing_authority', 'issuance_date', 'legal_type', 'url'):
            if f in d:
                rule(f'{S}.3 source_{f} bằng văn bản nguồn', r.get(f'source_{f}') == d[f], i)
        if 'legal_sectors' in d:
            rule(f'{S}.3 source_legal_sectors = chuỗi nối ", "', r.get('source_legal_sectors') == ', '.join(d['legal_sectors']), i)
        sp = r.get('source_path') or ''
        rule(f'{S}.3/4.4 source_path đúng dạng', bool(SP.match(sp)), i)
        rule(f'{S}.3 source_in_phu_luc ⇔ source_path bắt đầu "Phụ lục"', r.get('source_in_phu_luc') == sp.startswith('Phụ lục'), i)
        rule(f'{S}.3 source_ngay_hieu_luc Ngày|null', r.get('source_ngay_hieu_luc') is None or isdate(r.get('source_ngay_hieu_luc')), i)
        rule(f'{S}.3 source_ngay_hoi_to ⇔ ve_truoc', ('source_ngay_hoi_to' in r) == (r.get('hieu_luc_tac_dong') == 've_truoc'), i)
        td = r.get('target_doc') or ''
        rule(f'{S}.4 target_doc không có khoảng trắng (trừ tên luật)', ' ' not in td or bool(re.match(r'^(?:Bộ luật|Luật|Pháp lệnh|Hiến pháp)\s', td)), i)
        tm = r.get('target_matched_id')
        rule(f'{S}.4 target_matched_id integer|null', tm is None or isinstance(tm, int), i)
        if tm is not None:
            rule(f'{S}.4 target_matched_id ≠ source_id', tm != r.get('source_id'), i)
            rule(f'{S}.4 target_candidates_count ≥ 1 khi đã nối', (r.get('target_candidates_count') or 0) >= 1, i)
            if r.get('target_issuance_date') and r.get('source_issuance_date'):
                rule(f'{S}.4 ngày đích không sau ngày nguồn', r['target_issuance_date'] <= r['source_issuance_date'], i)
        if 'target_match_note' in r:
            rule(f'{S}.4 target_match_note = lech_ngay_trich_dan', r['target_match_note'] == 'lech_ngay_trich_dan', i)
        rule(f'{S}.5 scope khác rỗng', bool((r.get('scope') or '').strip()), i)
        v = r.get('vi_tri')
        rule(f'{S}.5 vi_tri là mảng', isinstance(v, list), i)
        v = v if isinstance(v, list) else []
        rule(f'{S}.5 vi_tri không quá một phần tử', len(v) <= 1, i)
        for p in v:
            rule('4.3 vi_tri đúng định dạng', bool(VI_TRI.match(p)), i)
        if r.get('scope') == 'toàn bộ':
            rule(f'{S}.5 scope toàn bộ → vi_tri ["toàn bộ"]', v == ['toàn bộ'], i)
        exp = EFFECT.get(a)
        h = r.get('hieu_luc_tac_dong')
        rule(f'{S}.5 hieu_luc_tac_dong khớp action', h == exp or (h == 've_truoc' and exp == 've_sau'), i)
        rule(f'{S}.5 unresolved boolean', isinstance(r.get('unresolved'), bool), i)
        if r.get('scope') == 'chưa xác định':
            rule(f'{S}.5 scope chưa xác định → unresolved', r.get('unresolved') is True, i)
        if 'kem_theo' in r or 'doi_tuong' in r:
            rule(f'{S}.5 kem_theo đi cùng doi_tuong', ('kem_theo' in r) == ('doi_tuong' in r), i)
        rule(f'{S}.5 cum_tu ⇔ thay-cum-tu', ('cum_tu' in r) == (a == 'thay-cum-tu'), i)
        rule(f'{S}.5 doi_tuong_loai là van_ban hoặc thu_tuc_hanh_chinh', r.get('doi_tuong_loai') in ('van_ban', 'thu_tuc_hanh_chinh'), i)
        if 'chi_tiet_vi_tri' in r:
            rule(f'{S}.5 chi_tiet_vi_tri chỉ có khi vi_tri có một vị trí', len(v) == 1 and v != ['toàn bộ'], i)
        if 'ma_thu_tuc' in r:
            rule(f'{S}.5 ma_thu_tuc chỉ có khi thu_tuc_hanh_chinh', r.get('doi_tuong_loai') == 'thu_tuc_hanh_chinh', i)
        for ct in r.get('cum_tu') or []:
            rule(f'{S}.5 cum_tu cu, moi khác rỗng', bool(ct.get('cu')) and bool(ct.get('moi')), i)
            rule(f'{S}.5 cum_tu[].vi_tri = vi_tri', ct.get('vi_tri') == v, i)
        if a in ('dinh-chi', 'ngung-hieu-luc'):
            rule(f'{S}.5 dinh-chi có dinh_chi_*', all(f in r for f in ('dinh_chi_tu_ngay', 'dinh_chi_den_ngay', 'dinh_chi_den_khi')), i)
        if a == 'gia-han':
            rule(f'{S}.5 gia-han có gia_han_*', all(f in r for f in ('gia_han_den_ngay', 'gia_han_den_khi')), i)
        # 4.8.6
        if 'scope_resolution_method' in r:
            rule(f'{S}.6 scope_resolution_method → grounding_correct true', r.get('scope_grounding_correct') is True, i)
        if 'scope_grounding_checked' in r:
            rule(f'{S}.6 scope_grounding_checked chỉ true', r['scope_grounding_checked'] is True, i)
        if r.get('scope_grounding_correct') is False:
            rule(f'{S}.6 grounding_correct false → unresolved', r.get('unresolved') is True, i)
        if 'llm_refined' in r:
            rule(f'{S}.6 llm_refined → correct true, unresolved false', r['llm_refined'] is True and r.get('scope_grounding_correct') is True and r.get('unresolved') is False, i)
        if 'llm_hallucination_rejected' in r:
            rule(f'{S}.6 llm_hallucination_rejected → correct false', r.get('scope_grounding_correct') is False, i)
        # 4.8.7
        dm = r.get('detection_mode')
        if len(v) == 1 and v[0] != 'toàn bộ':
            want = 'vi_tri'
        elif 'doi_tuong' in r and r.get('kem_theo') is True:
            want = 'van_ban_kem_theo'
        elif 'doi_tuong' in r and r.get('kem_theo') is False:
            want = 'noi_dung'
        elif v == ['toàn bộ'] or dm in ('intro', 'title_guidance', 'het_hieu_luc', 'hop_nhat') or sp in ('intro', 'Tiêu đề', 'Lời dẫn', 'Phần đầu') \
                or r.get('scope') in ('một số điều', 'một số cụm từ'):
            want = 'van_ban'
        else:
            want = 'chua_xac_dinh'
        rule(f'{S}.7 cap_quan_he theo thứ tự xét', r.get('cap_quan_he') == want, i)
        trace(r, S, i)
        rule(f'{S} 5 trường truy vết bằng văn bản nguồn', all(r.get(f) == d.get(f) for f in TRACE), i)
    for key, ns in numbering.items():
        rule('4.8.2 n đếm từ 0, không khuyết', sorted(ns) == list(range(len(ns))), f'{key[0]}{key[1]}')
    return extra_doc, extra_chunk, extra_rel


def main(argv):
    if not argv or argv[0] not in settings.STAGES:
        print(__doc__)
        return 2
    settings.load()
    cluster = Cluster(settings.Config.from_env().target_url)
    names = [f'legal-docs-{argv[0]}', f'legal-chunk-section-{argv[0]}', f'legal-changed-{argv[0]}']
    doc_rows, chunks, rels = (load(cluster, name) for name in names)
    extras = run(doc_rows, chunks, rels)
    print(f'Văn bản {len(doc_rows)}, chunk {len(chunks)}, quan hệ {len(rels)}')
    bad = [name for name in sorted(total) if fails[name]]
    print(f'Quy tắc đã kiểm: {len(total)}. Quy tắc có lỗi: {len(bad)}')
    for name in bad:
        print(f'{len(fails[name]):>6}/{total[name]:<6} {name}   vd: {", ".join(sorted(set(fails[name]))[:4])}')
    print('Trường ngoài hợp đồng:', {label: dict(c) for label, c in zip(('văn bản', 'chunk', 'quan hệ'), extras) if c} or 'không')
    if len(argv) > 1:
        with open(argv[1], 'w', encoding='utf-8') as out:
            json.dump({name: sorted(set(ids)) for name, ids in fails.items()}, out, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
