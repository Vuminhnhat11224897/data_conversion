"""Report of eval.survey_levels: Phần, Chương, Mục, Tiểu mục above Điều; section levels without Điều; parser cuts."""
import json
import sys
from collections import Counter, defaultdict

rows = [r for r in json.load(open(sys.argv[1])) if 'n_dieu' in r]
N, TOTAL = len(rows), 518261
pct = lambda a, b=None: f'{a} ({100 * a / (b or N):.1f}%) ~{round(a * TOTAL / N):,}'.replace(',', '.') if b is None else f'{a}/{b} ({100 * a / b:.1f}%)'
KINDS = ['phan', 'chuong', 'muc', 'tieu_muc']
art = [r for r in rows if r['n_dieu']]
letters = [r for r in rows if not r['n_dieu']]
print('mẫu', len(rows), '| có Điều', pct(len(art)), '| không chia Điều', pct(len(letters)))

def body(r, k): return r['body'].get(k, 0) > 0
def att(r, k): return any(a['heads'].get(k, 0) > 0 for a in r['attached'])

print('\n== Văn bản có Điều: cấp trên Điều ở phần chính ==')
for k in KINDS:
    print(f'  {k:9}', pct(sum(1 for r in art if body(r, k))))
print('  bất kỳ   ', pct(sum(1 for r in art if any(body(r, k) for k in KINDS))))
combo = Counter('+'.join(k for k in KINDS if body(r, k)) or '(chỉ Điều)' for r in art)
for c, n in combo.most_common(10):
    print('   ', c, n)

print('\n== Văn bản kèm theo có Điều (Quy định, Quy chế…) trong phụ lục ==')
withatt = [r for r in rows if r['attached']]
print('  văn bản có văn bản kèm theo chia Điều', pct(len(withatt)))
for k in KINDS:
    print(f'  {k:9}', pct(sum(1 for r in rows if att(r, k))))

print('\n== Gộp: phần chính hoặc văn bản kèm theo ==')
for k in KINDS:
    print(f'  {k:9}', pct(sum(1 for r in rows if body(r, k) or att(r, k))))
print('  bất kỳ   ', pct(sum(1 for r in rows if any(body(r, k) or att(r, k) for k in KINDS))))

print('\n== Parser có cắt đúng không (phần chính) ==')
for k in KINDS:
    docs = [r for r in art if body(r, k)]
    leak = [r for r in docs if r['leak'].get(k)]
    print(f'  {k:9} văn bản có {len(docs):4} | tiêu đề lọt vào nội dung Điều: {pct(len(leak), len(docs)) if docs else 0}  ví dụ {[r["id"] for r in leak[:4]]}')
for k in ['chuong', 'muc']:
    docs = [r for r in art if body(r, k)]
    miss = [r for r in docs if r['assigned'][k] < r['body'][k]]
    print(f'  {k:9} số tiêu đề > số {k} gán cho Điều: {pct(len(miss), len(docs)) if docs else 0}  ví dụ {[r["id"] for r in miss[:5]]}')
attdocs = [a for r in rows for a in r['attached']]
for k in KINDS:
    has = [a for a in attdocs if a['heads'].get(k)]
    leak = [a for a in has if a['leak'].get(k)]
    print(f'  kèm theo {k:9} {len(has):4} | lọt vào Điều: {pct(len(leak), len(has)) if has else 0}')

print('\n== Văn bản không chia Điều: đề mục ==')
print('  có đề mục (chunk muc)', pct(sum(1 for r in letters if r['sections']), len(letters)), '| toàn kho', pct(sum(1 for r in letters if r['sections'])))
print('  có đề mục con (mục 1, 2 hoặc a, b trong mục lớn)', pct(sum(1 for r in letters if r['nested_sections']), len(letters)), '| toàn kho', pct(sum(1 for r in letters if r['nested_sections'])))

print('\n== Theo loại văn bản (có Điều) ==')
groups = defaultdict(list)
for r in art:
    groups[r['type']].append(r)
for t, rs in sorted(groups.items(), key=lambda x: -len(x[1]))[:10]:
    print(f'  {t:20} {len(rs):5}  ' + '  '.join(f'{k} {100 * sum(1 for r in rs if body(r, k) or att(r, k)) / len(rs):5.1f}%' for k in KINDS))
for k in ['tieu_muc', 'phan']:
    print(k, 'ví dụ', [(r['id'], r['type'], r['body'].get(k)) for r in rows if body(r, k)][:8])
