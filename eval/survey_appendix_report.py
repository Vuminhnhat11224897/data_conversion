"""Report of eval.survey_appendix: appendix kinds per document and per character."""
import json
import statistics
import sys
from collections import Counter, defaultdict

rows = json.load(open(sys.argv[1]))
ok = [r for r in rows if 'appendices' in r]
n = len(ok)
pct = lambda a, b: f'{100 * a / b:.1f}%' if b else '-'
print('sample', len(rows), 'parsed', n, 'empty', sum(1 for r in rows if r.get('empty')), 'errors', sum(1 for r in rows if r.get('error')))

KINDS = ['danh_muc', 'bieu_mau', 'bang_khac', 'quy_dinh_co_dieu', 'van_ban_khac']
has = lambda r, k: any(a['kind'] == k for a in r['appendices'])
print('\n== documents ==')
print('có phụ lục', pct(sum(1 for r in ok if r['appendices']), n))
for k in KINDS:
    print(f'  có phụ lục {k}', pct(sum(1 for r in ok if has(r, k)), n))
print('có bảng (bất kỳ đâu)', pct(sum(1 for r in ok if r['table_chars']), n))
print('có bảng trong thân văn bản', pct(sum(1 for r in ok if r['body_table_rows'] >= 2), n))
print('danh mục (phụ lục hoặc tiêu đề DANH MỤC trong thân)', pct(sum(1 for r in ok if has(r, 'danh_muc') or r['body_catalogue']), n),
      '| chỉ trong thân', pct(sum(1 for r in ok if r['body_catalogue'] and not has(r, 'danh_muc')), n))
print('biểu mẫu (phụ lục hoặc tiêu đề Mẫu số trong thân)', pct(sum(1 for r in ok if has(r, 'bieu_mau') or r['body_form']), n),
      '| chỉ trong thân', pct(sum(1 for r in ok if r['body_form'] and not has(r, 'bieu_mau')), n))
print('bảng/danh mục/biểu mẫu (bất kỳ)', pct(sum(1 for r in ok if r['table_chars'] or r['body_catalogue'] or r['body_form']
                                                 or any(a['kind'] in ('danh_muc', 'bieu_mau', 'bang_khac') for a in r['appendices'])), n))

print('\n== volume (characters) ==')
total = sum(r['chars'] for r in ok)
print('tổng ký tự', total)
print('phụ lục', pct(sum(a['chars'] for r in ok for a in r['appendices']), total))
for k in KINDS:
    print(f'  {k}', pct(sum(a['chars'] for r in ok for a in r['appendices'] if a['kind'] == k), total))
print('dòng bảng (mọi nơi)', pct(sum(r['table_chars'] for r in ok), total))

print('\n== appendices ==')
apps = [a for r in ok for a in r['appendices']]
print('số phụ lục', len(apps), 'TB/văn bản có phụ lục', round(len(apps) / max(1, sum(1 for r in ok if r['appendices'])), 2))
for k in KINDS:
    sizes = [a['chars'] for a in apps if a['kind'] == k]
    if sizes:
        print(f'  {k:18} {len(sizes):5} {pct(len(sizes), len(apps)):>6}  có bảng {pct(sum(1 for a in apps if a["kind"] == k and a["table"]), len(sizes)):>6}'
              f'  trung vị {int(statistics.median(sizes)):6} ký tự  >1000 ký tự {pct(sum(1 for s in sizes if s > 1000), len(sizes)):>6}  max {max(sizes)}')
one = [a for a in apps if a['kind'] != 'quy_dinh_co_dieu']
print('lưu 1 chunk (không Điều)', pct(len(one), len(apps)), '| trong đó >1000 ký tự', pct(sum(1 for a in one if a['chars'] > 1000), len(one)))

print('\n== by legal type (top 10) ==')
groups = defaultdict(list)
for r in ok:
    groups[r['type']].append(r)
for t, rs in sorted(groups.items(), key=lambda x: -len(x[1]))[:10]:
    print(f'  {t:14} {len(rs):5} ({pct(len(rs), n):>6})  có phụ lục {pct(sum(1 for r in rs if r["appendices"]), len(rs)):>6}'
          f'  danh mục {pct(sum(1 for r in rs if has(r, "danh_muc") or r["body_catalogue"]), len(rs)):>6}'
          f'  biểu mẫu {pct(sum(1 for r in rs if has(r, "bieu_mau") or r["body_form"]), len(rs)):>6}'
          f'  bảng {pct(sum(1 for r in rs if r["table_chars"]), len(rs)):>6}')
vb = [r for r in ok if r['vbhn']]
print('VBHN', len(vb), 'có phụ lục', pct(sum(1 for r in vb if r['appendices']), len(vb)))
