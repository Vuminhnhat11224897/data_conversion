"""Parser and relation regressions copied from the main pipeline; v3 keeps its own copy of the rules."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vbpl_v3.relations import detect, lookup_numbers, resolve
from vbpl_v3.structure import build_chunks, parse, printed_title, sentence_case
from vbpl_v3.structure_ai import refine


class ParserRegressions(unittest.TestCase):
    def test_attached_documents_are_titled_appendices(self):
        decision='QUYẾT ĐỊNH:\nĐiều 1. Ban hành kèm theo Quyết định này Quy định quản lý chi phí.\nĐiều 2. Quyết định này có hiệu lực kể từ ngày ký.\nĐiều 3. Các đơn vị chịu trách nhiệm thi hành Quyết định này./.\n'
        rules='Chương I\nQUY ĐỊNH CHUNG\nĐiều 1. Phạm vi điều chỉnh\nNội dung phạm vi.\nĐiều 2. Đối tượng áp dụng\n1. Cơ quan nhà nước.\n2. Tổ chức, cá nhân.\n'
        # Attached rules between the recipients and a labeled appendix must not fall into the tail.
        parsed,stats=parse(decision+'Nơi nhận:\n- Như Điều 3;\n- Lưu: VT.\nKT. CHỦ TỊCH\nPHÓ CHỦ TỊCH\nNguyễn Văn A\nQUY ĐỊNH\nVỀ QUẢN LÝ CHI PHÍ\n(Ban hành kèm theo Quyết định số 29/2010/QĐ-UBND)\n'+rules+'PHỤ LỤC SỐ 1\nBiểu mẫu\n| A | B |\n| 1 | 2 |')
        self.assertEqual([(p['tieu_de'],p['loai'],len(p['dieu_luat'])) for p in parsed['phu_luc']],
                         [('QUY ĐỊNH VỀ QUẢN LÝ CHI PHÍ (Ban hành kèm theo Quyết định số 29/2010/QĐ-UBND)','unlabeled',2),('PHỤ LỤC SỐ 1','labeled',0)])
        self.assertEqual(parsed['noi_nhan'],['Như Điều 3','Lưu: VT'])
        self.assertEqual((stats['n_dieu'],stats['tail_dieu'],stats['grade']),(3,0,'full'))
        keyed={c['_id']:c['_source'] for c in build_chunks(1,{'title':'Quyết định'},parsed)}
        self.assertEqual(keyed['1_pl0_d2_k1']['phu_luc_tieu_de'],parsed['phu_luc'][0]['tieu_de'])
        self.assertIn('1_pl1',keyed)
        # Same document without a recognised signature, title separated from Chương I by a preamble: not a segment.
        parsed,stats=parse(decision+'Nguyễn Văn A (Đã ký)\nĐIỀU LỆ\nHỘI NGHỀ NGHIỆP\nLời mở đầu giới thiệu quá trình hình thành của hội.\n'+rules)
        self.assertNotIn('ĐIỀU LỆ',parsed['dieu_luat'][-1]['noi_dung'])
        self.assertEqual([a.get('van_ban_kem_theo',0) for a in parsed['dieu_luat']],[0,0,0])
        self.assertEqual((parsed['phu_luc'][0]['tieu_de'],len(parsed['phu_luc'][0]['dieu_luat'])),('ĐIỀU LỆ HỘI NGHỀ NGHIỆP',2))
        # A title outside the known names (OCR "QUY CHỂ") is found from its issuance note; "QUY ĐỊNH CHUNG" stays a chapter name.
        parsed,_=parse(decision+'Nơi nhận:\n- Như Điều 3;\nQUY CHỂ\n(Ban hành kèm theo Quyết định số 09/2013/QĐ-UBND)\n'+rules)
        self.assertEqual([(p['tieu_de'],len(p['dieu_luat'])) for p in parsed['phu_luc']],[('QUY CHỂ (Ban hành kèm theo Quyết định số 09/2013/QĐ-UBND)',2)])
        # Each titled attached document is its own part.
        second='QUY CHẾ PHỐI HỢP\n(Ban hành kèm theo Quyết định số 29/2010/QĐ-UBND)\nĐiều 1. Nguyên tắc\nNội dung.\nĐiều 2. Trách nhiệm\nNội dung.'
        parsed,_=parse(decision+'Nơi nhận:\n- Như Điều 3;\nQUY ĐỊNH\n(Ban hành kèm theo Quyết định số 29/2010/QĐ-UBND)\n'+rules+second)
        self.assertEqual([(p['tieu_de'][:16],len(p['dieu_luat'])) for p in parsed['phu_luc']],[('QUY ĐỊNH (Ban hà',2),('QUY CHẾ PHỐI HỢP',2)])
        # A parenthetical reference inside an article is not an attached document.
        parsed,_=parse('Điều 1. Bãi bỏ\nQuy chế quản lý (ban hành kèm theo Quyết định số 05/2010/QĐ-UBND) hết hiệu lực.\nĐiều 2. Thi hành\nNơi nhận:\n- Đơn vị;')
        self.assertEqual(parsed['phu_luc'],[])
        # A quote never closed (OCR dropped its pair) no longer hides the articles after it.
        parsed,stats=parse(decision+'Nơi nhận:\n- Như Điều 3;\n- Báo "Nhân dân;\nĐiều 1. Phạm vi\nNội dung.\nĐiều 2. Đối tượng\nNội dung.')
        self.assertEqual((stats['tail_dieu'],[len(p['dieu_luat']) for p in parsed['phu_luc']]),(0,[2]))
        # Articles still hidden in the tail by a closed quote are reported instead of counted as covered.
        _,stats=parse(decision+'Nơi nhận:\n- Như Điều 3;\n- Báo "Nhân dân;\nĐiều 1. Phạm vi\nNội dung.\nĐiều 2. Đối tượng\nNội dung."')
        self.assertEqual((stats['tail_dieu'],stats['grade']),(2,'partial'))

    def test_hybrid_article_titles_and_layout_are_validated(self):
        text=('QUYẾT ĐỊNH:\nĐiều 1. Phạm vi điều chỉnh\nQuyết định này quy định việc kiểm thử.\n'
              'Điều 2. Giao Sở Tài chính thực hiện các nhiệm vụ sau:\n1. Hướng dẫn đơn vị.\n2. Kiểm tra thực hiện.\n'
              'Điều 3. Bãi bỏ Quyết định số 12/2010/QĐ-UBND.\nNơi nhận:\n- Như Điều 3;\nKT. CHỦ TỊCH\nNguyễn Văn A')
        # Rule: text after "Điều 3." with no body is the article's content; relation detection still reads it.
        parsed,_=parse(text)
        self.assertEqual((parsed['dieu_luat'][2]['tieu_de'],parsed['dieu_luat'][2]['noi_dung']),('','Bãi bỏ Quyết định số 12/2010/QĐ-UBND.'))
        meta={'title':'Quyết định','action':'other','legal_type':'Quyết định','issuing_authority':'Tỉnh A','issuance_date':'2026-01-01'}
        self.assertEqual({(r['target_doc'],r['action']) for r in detect(1,meta,parsed)},{('12/2010/QĐ-UBND','bai-bo')})
        asked=[]
        def caller(prompt,payload,folder,**options):
            asked.append(json.loads(payload))
            lines=[x['line'] for x in asked[-1]['dieu_can_xac_dinh']]
            return json.dumps({'articles':[{'line':line,'has_title':False} for line in lines]}),{}
        with tempfile.TemporaryDirectory() as folder:
            parsed,stats=refine(text,Path(folder),caller=caller)
        # Only the subject-led heading is asked; the short name "Phạm vi điều chỉnh" is settled by rules.
        self.assertEqual([[x['dong'][0]['text'][:7] for x in a['dieu_can_xac_dinh']] for a in asked],[['Điều 2.']])
        article=parsed['dieu_luat'][1]
        self.assertEqual(article['tieu_de'],'')
        self.assertTrue(article['mo_dau'].startswith('Giao Sở Tài chính'))
        self.assertEqual([k['ky_hieu'] for k in article['khoan']],['1','2'])
        self.assertEqual(parsed['dieu_luat'][0]['tieu_de'],'Phạm vi điều chỉnh')
        self.assertEqual((stats['structure_ai']['status'],stats['structure_ai']['untitled_lines']),('checked',[3]))
        chunks={c['_id']:c['_source'] for c in build_chunks(1,{'title':'Quyết định'},parsed)}
        self.assertEqual(chunks['1_d2_k1']['tieu_de'],'')
        # Answers for lines that were not asked are rejected; after retries the rule decision is kept with a warning.
        with tempfile.TemporaryDirectory() as folder, patch('vbpl_v3.llm.time.sleep'):
            parsed,stats=refine(text,Path(folder),caller=lambda *a,**k:(json.dumps({'articles':[{'line':1,'has_title':False}]}),{}))
        self.assertEqual(parsed['dieu_luat'][1]['tieu_de'],'Giao Sở Tài chính thực hiện các nhiệm vụ sau:')
        self.assertEqual(stats['structure_ai']['status'],'needs_review')
        # A layout proposal must start parts on title lines after the main articles; otherwise rules are kept.
        toc=text.replace('Nguyễn Văn A','Nguyễn Văn A\nMỤC LỤC\nPhụ lục 1: Mẫu\nPhụ lục 2: Bảng\nQUY CHẾ\n(Ban hành kèm theo Quyết định số 1/QĐ-UBND)\nĐiều 1. Phạm vi\nNội dung.\nĐiều 2. Đối tượng\nNội dung.\nPHỤ LỤC 1\nMẪU\nNội dung mẫu dài hơn tám mươi ký tự để không bị coi là phần rỗng của mục lục văn bản này.')
        def layout(prompt,payload,folder,**options):
            if 'khung' in json.loads(payload):
                return json.dumps({'parts':[{'start_line':2}]}),{}
            return caller(prompt,payload,folder)
        with tempfile.TemporaryDirectory() as folder, patch('vbpl_v3.llm.time.sleep'):
            parsed,stats=refine(toc,Path(folder),caller=layout)
        self.assertIn('empty_labeled_part',stats['structure_ai']['layout']['signals'])
        self.assertFalse(stats['structure_ai']['layout']['applied'])
        self.assertEqual(stats['n_dieu'],3)
        def good(prompt,payload,folder,**options):
            if 'khung' in json.loads(payload):
                lines={x['text']:x['id'] for x in json.loads(payload)['khung'] if x['id'] is not None}
                return json.dumps({'parts':[{'start_line':lines['QUY CHẾ']},{'start_line':lines['PHỤ LỤC 1']}]}),{}
            return caller(prompt,payload,folder)
        with tempfile.TemporaryDirectory() as folder:
            parsed,stats=refine(toc,Path(folder),caller=good)
        self.assertTrue(stats['structure_ai']['layout']['applied'])
        self.assertEqual([(p['tieu_de'][:7],len(p['dieu_luat'])) for p in parsed['phu_luc']],[('QUY CHẾ',2),('PHỤ LỤC',0)])
        # The model may drop empty table-of-contents labels, never a labeled appendix with real content.
        long=toc.replace('Nội dung mẫu dài','Nội dung mẫu dài '+'rất '*300)
        def merge(prompt,payload,folder,**options):
            if 'khung' in json.loads(payload):
                lines={x['text']:x['id'] for x in json.loads(payload)['khung'] if x['id'] is not None}
                return json.dumps({'parts':[{'start_line':lines['QUY CHẾ']}]}),{}
            return caller(prompt,payload,folder)
        with tempfile.TemporaryDirectory() as folder:
            parsed,stats=refine(long,Path(folder),caller=merge)
        self.assertFalse(stats['structure_ai']['layout']['applied'])
        self.assertIn('labeled appendix',stats['structure_ai']['layout']['reason'])

    def test_each_listed_document_is_its_own_relation(self):
        meta={'title':'Quyết định về đơn giá','action':'other','legal_type':'Quyết định','issuing_authority':'Tỉnh A','issuance_date':'2026-01-01'}
        parsed,_=parse('Điều 1. Ban hành đơn giá.\nĐiều 2. Quyết định này có hiệu lực từ ngày ký và thay thế các Quyết định sau:\n'
                       '- Quyết định số 12/2010/QĐ-UBND ngày 01/01/2010 của UBND tỉnh;\n- Quyết định số 15/2011/QĐ-UBND ngày 02/02/2011 của UBND tỉnh.\n'
                       'Điều 3. Quyết định này có hiệu lực thi hành kể từ ngày ký.\n- Sửa đổi thủ tục số 3 của Quyết định số 20/2019/QĐ-UBND;\n'
                       '- Bãi bỏ Quyết định số 21/2020/QĐ-UBND.')
        rows={(r['source_path'],r['target_doc'],r['action']) for r in detect(900000001,meta,parsed)}
        self.assertEqual(rows,{('Điều 2','12/2010/QĐ-UBND','thay-the'),('Điều 2','15/2011/QĐ-UBND','thay-the'),
                               ('Điều 3','20/2019/QĐ-UBND','sua-doi'),('Điều 3','21/2020/QĐ-UBND','bai-bo')})

    def test_cited_year_finds_decision_registered_without_year(self):
        self.assertEqual(lookup_numbers(['1941/2008/QĐ-UBND','19/2012/QĐ-UBND','5/QĐ-UBND']),
                         ['1941/2008/QĐ-UBND','19/2012/QĐ-UBND','5/QĐ-UBND','1941/QĐ-UBND','19/QĐ-UBND'])
        hit=lambda i,number,authority,day:{'_id':i,'_source':{'document_number':number,'issuing_authority':authority,'issuance_date':day}}
        base={'target_doc':'1941/2008/QĐ-UBND','action':'bai-bo','source_id':423648,'source_issuance_date':'2019-06-25',
              'source_issuing_authority':'Tỉnh Điện Biên','_evidence':'Bãi bỏ Quyết định số 1941/2008/QĐ-UBND.'}
        hits=[hit('247805','1941/QĐ-UBND','Tỉnh Điện Biên','2008-12-12'),hit('9','1941/QĐ-UBND','Tỉnh Điện Biên','2015-01-05'),
              hit('10','1941/QĐ-UBND','Tỉnh Lai Châu','2008-03-01')]
        self.assertEqual(resolve(dict(base),hits)['target_matched_id'],247805)
        # Another province's same-year decision never qualifies, even when it is the only one.
        self.assertIsNone(resolve(dict(base),hits[2:])['target_matched_id'])
        # An exact registration wins over the year-less variant.
        self.assertEqual(resolve(dict(base),hits+[hit('77','1941/2008/QĐ-UBND','Tỉnh Điện Biên','2008-12-12')])['target_matched_id'],77)

    def test_final_article_with_closing_marker_is_retained(self):
        parsed,stats=parse('Điều 1. Nội dung\nNội dung một.\nĐiều 2. Hiệu lực\nCó hiệu lực hôm nay.\nĐiều 3. Các đơn vị chịu trách nhiệm thi hành./.\nKT. CHỦ TỊCH\nNguyễn Văn An')
        self.assertEqual(stats['n_dieu'],3)
        # The sentence after "Điều 3." is the article's content, not its name.
        self.assertEqual(parsed['dieu_luat'][-1]['tieu_de'],'')
        self.assertIn('./.',parsed['dieu_luat'][-1]['noi_dung'])
        self.assertNotIn('Nguyễn Văn An',parsed['dieu_luat'][-1]['noi_dung'])

    def test_inline_appendix_reference_and_mixed_quotes_do_not_cut_body(self):
        parsed,stats=parse('Điều 1. Biển báo\nTheo mẫu tại\nPhụ lục I kèm theo Thông tư này.\nBiển báo "vành đai biên giới”.\nĐiều 2. Thi hành\nĐơn vị thực hiện.\nKT. BỘ TRƯỞNG\nNguyễn Văn An\nPHỤ LỤC I\nMẪU GIẤY\nNội dung mẫu.')
        self.assertEqual(stats['n_dieu'],2)
        self.assertEqual(stats['n_phu_luc'],1)
        self.assertIn('Phụ lục I kèm theo',parsed['dieu_luat'][0]['noi_dung'])


if __name__ == '__main__':
    unittest.main()


class PrintedTitle(unittest.TestCase):
    """Q11 (20/10/2026): relations are read from the title printed in the document, never from the stored `title`."""

    def test_title_block_stops_at_the_issuer(self):
        # 628298: the stored title adds "29/2020/QĐ-UBND và 11/2021/QĐ-UBND"; the printed one names no number.
        head = ('ỦY BAN NHÂN DÂN TỈNH BÌNH ĐỊNH | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nSố: 59/2024/QĐ-UBND | Bình Định, ngày 17 tháng 10 năm 2024\n'
                'QUYẾT ĐỊNH\nBÃI BỎ CÁC QUYẾT ĐỊNH CỦA ỦY BAN NHÂN DÂN TỈNH BÌNH ĐỊNH\nỦY BAN NHÂN DÂN TỈNH BÌNH ĐỊNH')
        self.assertEqual(printed_title(head), 'QUYẾT ĐỊNH BÃI BỎ CÁC QUYẾT ĐỊNH CỦA ỦY BAN NHÂN DÂN TỈNH BÌNH ĐỊNH')

    def test_letter_subject_and_markup(self):
        self.assertEqual(printed_title('Số: 2470/TCT-CC V/v Hướng dẫn chính sách thuế đối với Nhà thầu nước ngoài | Hà Nội, ngày 12'),
                         'Hướng dẫn chính sách thuế đối với Nhà thầu nước ngoài')
        # 37831: markup left in the source, and a line ending in "CỦA" that goes on with the issuer's name.
        head = ('QUYẾT ĐỊNH\nVỀ VIỆC SỬA ĐỔI MỨC THU QUỐC DOANH BAN HÀNHxml:namespace prefix = u1 / KÈM THEO QUYẾT ĐỊNH SỐ 188-CT CỦA\n'
                'CHỦ TỊCH HỘI ĐỒNG BỘ TRƯỞNG\nĐể thực hiện Nghị quyết của Quốc hội;')
        self.assertEqual(printed_title(head), 'QUYẾT ĐỊNH VỀ VIỆC SỬA ĐỔI MỨC THU QUỐC DOANH BAN HÀNH KÈM THEO QUYẾT ĐỊNH SỐ 188-CT CỦA '
                                              'CHỦ TỊCH HỘI ĐỒNG BỘ TRƯỞNG')
        self.assertEqual(printed_title('Số: 12/QĐ-UB | Hà Nội'), '')

    def test_sentence_case_keeps_numbers_and_law_names(self):
        self.assertEqual(sentence_case('HƯỚNG DẪN THỰC HIỆN NGHỊ ĐỊNH SỐ 31/CP NGÀY 18/5/1996'), 'Hướng dẫn thực hiện Nghị định số 31/CP ngày 18/5/1996')
        self.assertEqual(sentence_case('QUY ĐỊNH CHI TIẾT MỘT SỐ ĐIỀU CỦA LUẬT ĐẤT ĐAI'), 'Quy định chi tiết một số điều của Luật Đất đai')
        self.assertEqual(sentence_case('Hướng dẫn chính sách thuế'), 'Hướng dẫn chính sách thuế')


class AppendixStorage(unittest.TestCase):
    """Nhánh exp/phu-luc-chia-doan (27/10/2026): biểu mẫu không giữ Điều; phụ lục và đề mục dài có đoạn tìm kiếm."""
    DECISION = ('QUYẾT ĐỊNH:\nĐiều 1. Ban hành kèm theo Quyết định này Quy chế và các mẫu.\nĐiều 2. Quyết định này có hiệu lực kể từ ngày ký.\n'
                'Nơi nhận:\n- Như Điều 2;\n- Lưu: VT.\nTM. ỦY BAN NHÂN DÂN\nCHỦ TỊCH\nNguyễn Văn A\n')

    def test_sample_decision_in_appendix_is_flat(self):
        # 676317_pl20 (PHỤ LỤC SỐ 18): a sample licence decision with blanks and its own recipients.
        form = ('PHỤ LỤC SỐ 18\nĐiều 1. Cho phép\n1. Tên doanh nghiệp: ……………\n2. Trụ sở chính: ………………\n'
                'Điều 2. Quyết định này được lập thành 06 bản.\nNơi nhận:\n- DN/NHTM;\n- Lưu: VP.\nTHỐNG ĐỐC\n')
        rules = ('QUY CHẾ\nLÀM VIỆC CỦA BAN CHỈ ĐẠO\n(Ban hành kèm theo Quyết định số 12/2025/QĐ-UBND)\nĐiều 1. Phạm vi điều chỉnh\nNội dung phạm vi.\n'
                 'Điều 2. Đối tượng áp dụng\nCác cơ quan.\n')
        parsed, _ = parse(self.DECISION + rules + form)
        self.assertEqual([len(p['dieu_luat']) for p in parsed['phu_luc']], [2, 0])
        keyed = {c['_id']: c['_source'] for c in build_chunks(1, {'title': 'Quyết định'}, parsed)}
        self.assertEqual((keyed['1_pl0_d1']['loai_phan'], keyed['1_pl0_d1']['phu_luc_uid']), ('kem_theo', '1_pl0'))
        self.assertEqual((keyed['1_pl1']['chunk_type'], keyed['1_pl1']['loai_phan']), ('phu_luc', 'phu_luc'))
        self.assertIn('Điều 1. Cho phép', keyed['1_pl1']['noi_dung'])

    def test_form_line_is_no_appendix_heading(self):
        # 680444: "Phụ lục (Ban hành kèm theo .................(1))" is a line of a form, not a new part.
        parsed, _ = parse(self.DECISION + 'PHỤ LỤC I\nMẪU QUY CHẾ\nPhụ lục (Ban hành kèm theo .................(1))\nNội dung mẫu.\n')
        self.assertEqual([p['tieu_de'] for p in parsed['phu_luc']], ['PHỤ LỤC I MẪU QUY CHẾ'])

    def test_long_table_has_passages_with_column_names(self):
        rows = '\n'.join(f'| {n} | Quyết định số {n}/2020/QĐ-UBND về việc quy định giá dịch vụ số {n} trên địa bàn tỉnh |' for n in range(1, 41))
        parsed, _ = parse(self.DECISION + 'PHỤ LỤC II\nDANH MỤC VĂN BẢN BỊ BÃI BỎ\n| STT | Tên văn bản |\n||||\n' + rows)
        chunks = build_chunks(1, {'title': 'Quyết định'}, parsed, passage_words=60)
        keyed = {c['_id']: c['_source'] for c in chunks}
        self.assertTrue(keyed['1_pl0']['is_full'])
        passages = [c['_source'] for c in chunks if c['_source']['chunk_type'] == 'phu_luc_doan']
        self.assertEqual([p['so_doan'] for p in passages], list(range(1, len(passages) + 1)))
        self.assertGreater(len(passages), 3)
        # Every passage names the appendix and the columns; rows are never cut.
        self.assertTrue(all(p['tieu_de'] == 'PHỤ LỤC II DANH MỤC VĂN BẢN BỊ BÃI BỎ' and p['noi_dung'].startswith('| STT | Tên văn bản |')
                            for p in passages))
        body = [line for p in passages for line in p['noi_dung'].splitlines() if not line.startswith('| STT') and line != '||||']
        self.assertEqual(body, rows.splitlines())
        self.assertEqual({p['phu_luc_uid'] for p in passages}, {'1_pl0'})

    def test_long_section_has_passages(self):
        body = ' '.join(['Các sở, ngành triển khai thực hiện nhiệm vụ được giao.'] * 40)
        parsed, _ = parse('Kính gửi: Các sở.\nI. Phòng, chống dịch bệnh\n' + body + '\nII. Tổ chức thực hiện\nCác đơn vị báo cáo.')
        keyed = {c['_id']: c['_source'] for c in build_chunks(1, {'title': 'Công văn'}, parsed, passage_words=100)}
        self.assertTrue(keyed['1_mI']['is_full'])
        self.assertEqual((keyed['1_mI_doan2']['chunk_type'], keyed['1_mI_doan2']['muc_uid'], keyed['1_mI_doan2']['tieu_de']),
                         ('muc_doan', '1_mI', 'Phòng, chống dịch bệnh'))
        self.assertNotIn('1_mII_doan1', keyed)
