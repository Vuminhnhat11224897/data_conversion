"""Decisions of 14/10/2026: only direct, stated impacts; one relation per position; sub-points; forms stay in their appendix;
effective dates per provision; consolidated texts relate to what they restate; guidance keeps its stated provisions."""

import json
from pathlib import Path
import tempfile
import unittest

from vbpl_v3.config import Config
from vbpl_v3.convert import level, one_per_position
from vbpl_v3.legal_status import provision_effects, unit_dates
from vbpl_v3.qa import stated, verify
from vbpl_v3.references import guidance
from vbpl_v3.relations import consolidation, detect, scope
from vbpl_v3.structure import build_chunks, parse
from vbpl_v3.temporal import positions
from tests.test_guard import config

META = {'document_number': '30/2018/TT-BTC', 'title': 'Thông tư sửa đổi Thông tư 75/2017/TT-BTC', 'action': 'sua-doi',
        'legal_type': 'Thông tư', 'issuing_authority': 'Bộ Tài chính', 'issuance_date': '2018-03-28', 'legal_sectors': []}


class DirectImpact(unittest.TestCase):
    def test_target_is_the_document_the_unit_names(self):
        # 378946: the clause names TT 55/2016; "được sửa đổi, bổ sung tại … TT 75/2017" is a history note.
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số Điều của Thông tư số 75/2017/TT-BTC như sau:\n'
                          '1. Bỏ gạch đầu dòng thứ ba điểm b Khoản 3 Điều 17 Thông tư số 55/2016/TT-BTC được sửa đổi, '
                          'bổ sung tại Điều 1 Thông tư số 75/2017/TT- BTC.\n'
                          '2. Sửa đổi Khoản 1 Điều 2 như sau:\n'
                          'a) Đối với dự án đã ký hợp đồng được tiếp tục thực hiện, trừ quy định tại điểm b Khoản 2 Điều này.\n'
                          'b) Hợp đồng được áp dụng các quy định tại Điều 1 Thông tư số 75/2017/TT-BTC đã được sửa đổi tại Khoản 1 Điều này.')
        rows = {(r['source_path'], r['action']): r for r in detect(1, META, parsed)}
        repeal = rows[('Điều 1 Khoản 1', 'bai-bo')]
        self.assertEqual((repeal['target_doc'], repeal['scope']), ('55/2016/TT-BTC', 'tiểu điểm 3 điểm b khoản 3 Điều 17'))
        # The points after "như sau:" are new content: the clause is one relation, not two.
        self.assertEqual(rows[('Điều 1 Khoản 2', 'sua-doi')]['scope'], 'khoản 1 Điều 2')
        self.assertFalse([k for k in rows if k[0].startswith('Điều 1 Khoản 2 điểm')])

    def test_positions_below_a_point_and_forms(self):
        self.assertEqual(positions('gạch đầu dòng thứ ba điểm b khoản 3 Điều 17'), ['tiểu điểm 3 điểm b khoản 3 Điều 17'])
        self.assertEqual(positions('tiết thứ 2 của điểm a khoản 1 Điều 5'), ['tiểu điểm 2 điểm a khoản 1 Điều 5'])
        # A dash item of a clause, a sentence or a paragraph stays at the provision that holds it.
        self.assertEqual(positions('gạch đầu dòng thứ hai khoản 3 Điều 5'), ['khoản 3 Điều 5'])
        self.assertEqual(positions('câu thứ nhất điểm a khoản 2 Điều 4'), ['điểm a khoản 2 Điều 4'])
        # An earlier point takes the clause of the later one (282089, 476418).
        self.assertEqual(positions('điểm a và điểm b khoản 2 Điều 11'), ['điểm a khoản 2 Điều 11', 'điểm b khoản 2 Điều 11'])
        # A form stays in its appendix.
        self.assertEqual(positions('Mẫu số 04 Phụ lục I; Mẫu số 05 Phụ lục I'), ['Phụ lục I'])
        self.assertEqual(positions('Mẫu số 01 Phụ lục kèm theo Nghị định số 61/2016/NĐ-CP'), ['Phụ lục'])

    def test_sub_point_chunks(self):
        parsed, _ = parse('Điều 1. Phạm vi\n1. Khoản:\na) Điểm có tiết:\n- tiết một;\n+ ý của tiết một;\n- tiết hai.\nb) Điểm không có tiết.')
        chunks = {c['_id']: c['_source'] for c in build_chunks(9, {'title': 'x'}, parsed)}
        self.assertEqual(chunks['9_d1_k1_pa_t1']['noi_dung'], 'tiết một;\n+ ý của tiết một;')
        self.assertEqual((chunks['9_d1_k1_pa_t2']['chunk_type'], chunks['9_d1_k1_pa_t2']['diem_uid'], chunks['9_d1_k1_pa_t2']['so_tieu_diem']),
                         ('tieu_diem', '9_d1_k1_pa', 2))
        self.assertNotIn('9_d1_k1_pb_t1', chunks)


class MissedForms(unittest.TestCase):
    """Sentences v4 missed on 14/10/2026: "Bổ sung các …", "Bổ sung cụm từ …", "Bỏ từ …", a list of provisions that end."""

    def test_supplement_and_remove_forms(self):
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN\n'
                          '1. Bổ sung các khoản 9, 10 vào Điều 49 như sau: “9. A. 10. B.”\n'
                          '2. Bổ sung tiết g.10 điểm g khoản 2 Điều 2 như sau: “g.10) C.”\n'
                          '3. Bỏ từ “-huyện:” tại Mẫu số 03/PTY.\n'
                          '4. Thay thế cụm từ “Tổng cục” thành cụm từ “Cục” tại khoản 1 Điều 7 và khoản 1, khoản 2 Điều 9.')
        rows = {r['source_path']: r for r in detect(1, {**META, 'title': 'Thông tư sửa đổi Thông tư 19/2013/TT-NHNN'}, parsed)}
        self.assertEqual((rows['Điều 1 Khoản 1']['action'], positions(rows['Điều 1 Khoản 1']['scope'])), ('bo-sung', ['khoản 9 Điều 49', 'khoản 10 Điều 49']))
        self.assertEqual(rows['Điều 1 Khoản 2']['action'], 'bo-sung')
        self.assertEqual((rows['Điều 1 Khoản 3']['action'], positions(rows['Điều 1 Khoản 3']['scope'])), ('bai-bo', ['Phụ lục']))
        wording = rows['Điều 1 Khoản 4']
        self.assertEqual((wording['cum_tu'][0]['moi'], wording['vi_tri']), ('Cục', ['khoản 1 Điều 7', 'khoản 1 Điều 9', 'khoản 2 Điều 9']))

    def test_list_of_provisions_that_end(self):
        parsed, _ = parse('Điều 1. Phạm vi điều chỉnh\nThông tư này quy định về mua, bán nợ.\n'
                          'Điều 2. Hiệu lực thi hành\n1. Thông tư này có hiệu lực thi hành từ ngày 15 tháng 02 năm 2026.\n'
                          '2. Kể từ ngày Thông tư này có hiệu lực thi hành, các quy định sau đây hết hiệu lực thi hành:\n'
                          'a) Khoản 8, khoản 14 Điều 1 Thông tư 14/2015/TT-NHNN sửa đổi bổ sung một số điều của Thông tư số 19/2013/TT-NHNN;\n'
                          'b) Điểm c khoản 5 Điều 1 Thông tư số 27/2022/TT-NHNN.')
        rows = detect(1, {**META, 'title': 'Thông tư quy định về mua, bán nợ'}, parsed)
        self.assertEqual(sorted((r['source_path'], r['action'], r['target_doc'], tuple(positions(r['scope']))) for r in rows),
                         [('Điều 2 Khoản 2 điểm a', 'bai-bo', '14/2015/TT-NHNN', ('khoản 8 Điều 1', 'khoản 14 Điều 1')),
                          ('Điều 2 Khoản 2 điểm b', 'bai-bo', '27/2022/TT-NHNN', ('điểm c khoản 5 Điều 1',))])

    def test_law_named_without_number(self):
        # 675260: Luật 144/2025/QH15 amends "Luật Quy hoạch đô thị và nông thôn" by name.
        parsed, _ = parse('Căn cứ Hiến pháp;\nĐiều 1. Sửa đổi, bổ sung một số điều của Luật Quy hoạch đô thị và nông thôn\n'
                          '1. Sửa đổi, bổ sung khoản 4 Điều 3 như sau: “4. A.”\nĐiều 2. Hiệu lực thi hành\nLuật này có hiệu lực từ ngày 01 tháng 7 năm 2026.')
        rows = detect(1, {**META, 'title': 'Luật Quy hoạch đô thị và nông thôn sửa đổi 2025', 'legal_type': 'Luật'}, parsed)
        self.assertEqual({(r['action'], r['target_doc'], r['scope']) for r in rows},
                         {('sua-doi', 'Luật Quy hoạch đô thị và nông thôn', 'khoản 4 Điều 3'), ('bo-sung', 'Luật Quy hoạch đô thị và nông thôn', 'khoản 4 Điều 3')})
        # A number in the legal basis wins over the name.
        parsed, _ = parse('Căn cứ Luật Đất đai số 45/2013/QH13 ngày 29 tháng 11 năm 2013;\nĐiều 1. Sửa đổi một số điều của Luật Đất đai\n'
                          '1. Bãi bỏ khoản 2 Điều 5.\nĐiều 2. Hiệu lực\nNghị định này có hiệu lực từ ngày ký.')
        self.assertEqual({r['target_doc'] for r in detect(1, {**META, 'title': 'Nghị định sửa đổi Luật Đất đai', 'legal_type': 'Nghị định'}, parsed)},
                         {'45/2013/QH13'})

    def test_correction_keeps_its_act_and_names(self):
        parsed, _ = parse('QUYẾT ĐỊNH\nĐÍNH CHÍNH QUYẾT ĐỊNH 28/2017/QĐ-UBND\n'
                          'Điều 1. Đính chính Quyết định số 28/2017/QĐ-UBND\n1. Tại khoản 2 Điều 6, bỏ cụm từ “và”.\n2. Sửa tên gọi của Chương III.')
        rows = detect(1, {**META, 'title': 'Quyết định đính chính Quyết định 28/2017/QĐ-UBND'}, parsed)
        self.assertEqual({r['action'] for r in rows}, {'dinh-chinh'})
        self.assertEqual(scope('Sửa tên gọi của Chương III như sau')[0], 'tên Chương III')
        self.assertEqual(positions('Mục 1 Chương IV Quy định kỹ thuật cho 11 công tác'), ['Mục 1 Chương IV'])


class RoundOneReview(unittest.TestCase):
    """Errors found by the review of 14/10/2026 on 503 documents."""
    META = {**META, 'title': 'Nghị định sửa đổi Nghị định 108/2013/NĐ-CP', 'legal_type': 'Nghị định'}

    def found(self, clause, meta=None):
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 108/2013/NĐ-CP\n1. ' + clause)
        return sorted({(c['action'], c['target_doc'], tuple(positions(c['scope']))) for c in detect(9, meta or self.META, parsed)})

    def test_positions(self):
        # 328155: each act keeps its own point; the clause and Điều named once apply to both.
        self.assertEqual(self.found('Sửa đổi điểm b và bổ sung điểm đ khoản 2 Điều 4 như sau: “b) A; đ) B.”'),
                         [('bo-sung', '108/2013/NĐ-CP', ('điểm đ khoản 2 Điều 4',)), ('sua-doi', '108/2013/NĐ-CP', ('điểm b khoản 2 Điều 4',))])
        # 602450: "… tại Mẫu số 01 Phụ lục I kèm theo Nghị định này" is where the new form sits, not the target.
        self.assertEqual({x[2] for x in self.found('Sửa đổi, bổ sung Phụ lục III ban hành kèm theo Nghị định số 01/2012/NĐ-CP tại Mẫu số 01 Phụ lục I kèm theo Nghị định này;')},
                         {('Phụ lục III',)})
        # 585073: every group of a semicolon list.
        self.assertEqual(self.found('Bãi bỏ khoản 6 và khoản 7 Điều 4; khoản 2 Điều 6; khoản 2 Điều 7 của Nghị định số 108/2013/NĐ-CP.')[0][2],
                         ('khoản 6 Điều 4', 'khoản 7 Điều 4', 'khoản 2 Điều 6', 'khoản 2 Điều 7'))
        # 106471: "khoản" after a comma is not a point label.
        self.assertEqual(self.found('Bổ sung thêm điểm d, khoản 1, điều 1 như sau: d) X.')[0][2], ('điểm d khoản 1 Điều 1',))
        # 282089: nested quotes in the new content do not leak into the declaration.
        self.assertEqual({x[2] for x in self.found('Sửa đổi, bổ sung khoản 5 Điều 16\n\n“5. A “Mẫu số 04/CNV-TNCN” và B.\n\na) câu.”')}, {('khoản 5 Điều 16',)})

    def test_units_and_targets(self):
        # 662238: an article without clauses whose body is one act: the body's act, not every verb of the heading.
        parsed, _ = parse('Điều 36. Bổ sung, thay thế, bãi bỏ một số từ, cụm từ của Thông tư số 31/2024/TT-BTNMT\n'
                          'Thay thế cụm từ “Bộ A” bằng cụm từ “Bộ B” tại khoản 1, khoản 3 Điều 41.\n'
                          'Điều 37. Hiệu lực thi hành\nThông tư này có hiệu lực từ ngày ký.')
        rows = [r for r in detect(9, {**META, 'title': 'Thông tư sửa đổi các Thông tư'}, parsed) if r['source_path'] == 'Điều 36']
        self.assertEqual([(r['action'], r['vi_tri']) for r in rows], [('thay-cum-tu', ['khoản 1 Điều 41', 'khoản 3 Điều 41'])])
        # 568719: points of new content that only mention an act are not units.
        self.assertEqual(self.found('Sửa đổi, bổ sung Điều 12 như sau:\na) Chủ tịch Hội đồng: là Phó Chủ tịch tỉnh;\nb) Thành viên được sửa đổi khi cần.'),
                         [('bo-sung', '108/2013/NĐ-CP', ('Điều 12',)), ('sua-doi', '108/2013/NĐ-CP', ('Điều 12',))])
        # 164086: every document of a "thay thế A và B" list.
        parsed, _ = parse('Điều 1. Ban hành quy trình\nNội dung.\nĐiều 2.\nQuyết định này có hiệu lực kể từ ngày ký, thay thế Quyết định số 436/QĐ-TCHQ '
                          'ngày 09/3/2009 và Quyết định số 1376/QĐ-TCHQ ngày 13/7/2009 của Tổng cục trưởng Tổng cục Hải quan.')
        self.assertEqual(sorted(r['target_doc'] for r in detect(9, {**META, 'title': 'Quyết định về thủ tục hải quan'}, parsed)),
                         ['1376/QĐ-TCHQ', '436/QĐ-TCHQ'])


class RoundThreeReview(unittest.TestCase):
    """Errors found by the third review (300 new documents)."""

    def found(self, text, title='Thông tư sửa đổi Thông tư 19/2013/TT-NHNN'):
        parsed, _ = parse(text)
        return sorted({(c['source_path'], c['action'], c['target_doc'], tuple(positions(c['scope']))) for c in detect(9, {**META, 'title': title}, parsed)})

    def test_two_acts_in_one_sentence_and_whole_chapters(self):
        self.assertEqual(self.found('Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN\n'
                                    '1. Sửa đổi khoản 1 Điều 39; bổ sung khoản 1a, 1b vào sau khoản 1 Điều 39 như sau: “1. A”\n2. Bãi bỏ Chương III.'),
                         [('Điều 1 Khoản 1', 'bo-sung', '19/2013/TT-NHNN', ('khoản 1a Điều 39', 'khoản 1b Điều 39')),
                          ('Điều 1 Khoản 1', 'sua-doi', '19/2013/TT-NHNN', ('khoản 1 Điều 39',)),
                          ('Điều 1 Khoản 2', 'bai-bo', '19/2013/TT-NHNN', ('Chương III',))])

    def test_documents_that_end(self):
        effect = 'Điều 1. Phạm vi\nNội dung.\nĐiều 2. Hiệu lực thi hành\n1. Thông tư này có hiệu lực từ ngày 01/7/2025.\n'
        self.assertEqual(self.found(effect + '2. Thông tư số 52/2018/TT-NHNN và Thông tư số 23/2021/TT-NHNN hết hiệu lực kể từ ngày Thông tư này có hiệu lực thi hành.',
                                    'Thông tư quy định về xếp hạng'),
                         [('Điều 2 Khoản 2', 'bai-bo', '23/2021/TT-NHNN', ('toàn bộ',)), ('Điều 2 Khoản 2', 'bai-bo', '52/2018/TT-NHNN', ('toàn bộ',))])
        self.assertEqual(self.found(effect + '2. Các Thông tư sau đây hết hiệu lực thi hành kể từ ngày Thông tư này có hiệu lực:\n'
                                    'a) Thông tư số 25/2018/TT-BCT ngày 12/9/2018;\nb) Thông tư số 16/2014/TT-BCT.', 'Thông tư quy định giá điện'),
                         [('Điều 2 Khoản 2 điểm a', 'bai-bo', '25/2018/TT-BCT', ('toàn bộ',)), ('Điều 2 Khoản 2 điểm b', 'bai-bo', '16/2014/TT-BCT', ('toàn bộ',))])

    def test_new_content_after_a_cut_lead(self):
        # 675260: the source cuts the text right after "như sau:"; the points below are still new content.
        rows = self.found('Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN\n'
                          '1. Sửa đổi, bổ sung các khoản 2, 3 Điều 29 như sau:\n\n...\n\nHãy đăng nhập để xem tiếp\n'
                          'a) Xác định yêu cầu, nội dung theo quy hoạch;\nb) Đánh giá điều kiện tự nhiên.')
        self.assertFalse([r for r in rows if ' điểm ' in r[0]])


class RoundFourReview(unittest.TestCase):
    """Errors found by the fourth review (300 new documents)."""

    found = RoundThreeReview.found

    def test_every_listed_position_is_a_relation(self):
        # 588810, 691249: "Điều 36 và Điều 37", "điểm b khoản 1, điểm b khoản 2 Điều 26" name two places each.
        rows = self.found('Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN\n'
                          '1. Sửa đổi, bổ sung Điều 36 và Điều 37 như sau: “Điều 36. A”\n2. Bãi bỏ điểm b khoản 1, điểm b khoản 2 Điều 26.')
        self.assertEqual(rows, [('Điều 1 Khoản 1', 'bo-sung', '19/2013/TT-NHNN', ('Điều 36', 'Điều 37')),
                                ('Điều 1 Khoản 1', 'sua-doi', '19/2013/TT-NHNN', ('Điều 36', 'Điều 37')),
                                ('Điều 1 Khoản 2', 'bai-bo', '19/2013/TT-NHNN', ('điểm b khoản 1 Điều 26', 'điểm b khoản 2 Điều 26'))])

    def test_positions_written_with_commas(self):
        # 250467, 303413, 695107, 691249, 404462: levels with commas, parts without a node, sections of an appendix.
        self.assertEqual(positions('đoạn 3, điểm a, khoản 2, Điều 4'), ['điểm a khoản 2 Điều 4'])
        self.assertEqual(positions('điểm b tiết 3.5, mục III, Điều 1'), ['Điều 1'])
        self.assertEqual(positions('Mục I, Phần I Phụ lục công bố kèm theo Quyết định số'), ['Mục I Phần I Phụ lục'])
        self.assertEqual(positions('Mục D.2 của Phụ lục I'), ['Mục D.2 Phụ lục I'])
        self.assertEqual(positions('Chương II, Phụ lục I'), ['Chương II', 'Phụ lục I'])
        self.assertEqual(scope('Sửa đổi đoạn 3, điểm a, khoản 2, Điều 4'), ('điểm a khoản 2 Điều 4', False))
        self.assertEqual(scope('Sửa đổi, bổ sung toàn bộ nội dung số thứ tự 51')[0], 'số thứ tự 51')

    def test_positions_of_mixed_levels(self):
        # 21/10/2026: lists that mix levels; a group with no article takes the next one; words after "Điều N" name the document.
        self.assertEqual(positions('điểm a, điểm b khoản 3; điểm a khoản 5 và điểm a khoản 6 Điều 3'),
                         ['điểm a khoản 3 Điều 3', 'điểm b khoản 3 Điều 3', 'điểm a khoản 5 Điều 3', 'điểm a khoản 6 Điều 3'])
        self.assertEqual(positions('quy định tại khoản 2 Điều 3, điểm b khoản 1 Điều 19 Quy định về quản lý'),
                         ['khoản 2 Điều 3', 'điểm b khoản 1 Điều 19'])
        rows = self.found('Điều 1. Sửa đổi, bổ sung một số điều của Quy định ban hành kèm theo Quyết định số 22/2021/QĐ-UBND\n'
                          '1. Sửa đổi, bổ sung khoản 1 và điểm c, điểm đ khoản 3 Điều 15 như sau: “1. A”')
        self.assertEqual({r[3] for r in rows}, {('khoản 1 Điều 15', 'điểm c khoản 3 Điều 15', 'điểm đ khoản 3 Điều 15')})
        rows = self.found('Điều 1. Sửa đổi, bổ sung Phụ lục III ban hành kèm theo Nghị quyết số 37/2016/NQ-HĐND như sau:\n'
                          '1. Sửa đổi Mục 2 như sau: “2. A”\n2. Bổ sung Mục 6. Phí thẩm định như sau: “6. B”', 'Nghị quyết sửa đổi Phụ lục III')
        self.assertIn(('Điều 1 Khoản 2', 'bo-sung', '37/2016/NQ-HĐND', ('Mục 6 Phụ lục III',)), rows)

    def test_provisions_in_the_name_of_the_replaced_document(self):
        # 442079: "… sửa đổi Điểm a, Khoản 2 Điều 3 …" is the name of QĐ 42/2018, which is replaced as a whole.
        rows = self.found('Điều 1. Phạm vi\nNội dung.\nĐiều 2. Tổ chức thực hiện\n1. Giao Sở Nội vụ.\n'
                          '2. Quyết định này có hiệu lực kể từ ngày 20/4/2020 và thay thế Quyết định số 42/2018/QĐ-UBND ngày 08/11/2018 '
                          'của UBND tỉnh sửa đổi Điểm a, Khoản 2 Điều 3 Quy định ban hành kèm theo Quyết định số 10/2016/QĐ-UBND.',
                          'Quyết định về chức năng của Sở Ngoại vụ')
        self.assertEqual(rows, [('Điều 2 Khoản 2', 'thay-the', '42/2018/QĐ-UBND', ('toàn bộ',))])

    def test_the_article_on_effect_acts_in_its_own_sentence(self):
        # 147773: "có hiệu lực … và thay thế Thông tư liên tịch số 34/2007/…" in an article without clauses.
        body = 'Điều 1. Phạm vi\nNội dung.\nĐiều 2. Hiệu lực thi hành\n'
        self.assertEqual(self.found(body + 'Thông tư này có hiệu lực kể từ ngày 27 tháng 10 năm 2012 và thay thế Thông tư liên tịch số '
                                    '34/2007/TTLT-BTC-BLĐTBXH ngày 09 tháng 4 năm 2007.', 'Thông tư hướng dẫn chế độ'),
                         [('Điều 2', 'thay-the', '34/2007/TTLT-BTC-BLĐTBXH', ('toàn bộ',))])
        # A repeal sentence without a number does not reach the next sentence's document.
        self.assertEqual(self.found(body + 'Thông tư này có hiệu lực kể từ ngày ký. Bãi bỏ các quy định trái với Thông tư này. '
                                    'Thông tư số 12/2010/TT-BTC tiếp tục áp dụng.', 'Thông tư hướng dẫn chế độ'), [])

    def test_documents_that_end_on_a_stated_day(self):
        # 674713: a day instead of "kể từ ngày Thông tư này có hiệu lực"; the amended document named inside the second one's name
        # is not ending. 672601: neither is the decree named in the guiding circular's name. 535782: nor the amending laws of a note.
        effect = 'Điều 1. Phạm vi\nNội dung.\nĐiều 2. Hiệu lực thi hành\n1. Thông tư này có hiệu lực từ ngày 01/11/2025.\n'
        self.assertEqual(self.found(effect + '2. Thông tư số 52/2018/TT-NHNN ngày 31 tháng 12 năm 2018 quy định xếp hạng tổ chức tín dụng và '
                                    'Thông tư số 23/2021/TT-NHNN về việc sửa đổi, bổ sung một số điều của Thông tư số 52/2018/TT-NHNN '
                                    'hết hiệu lực thi hành kể từ ngày 01 tháng 11 năm 2025, trừ quy định tại khoản 3 Điều này.', 'Thông tư quy định xếp hạng'),
                         [('Điều 2 Khoản 2', 'bai-bo', '23/2021/TT-NHNN', ('toàn bộ',)), ('Điều 2 Khoản 2', 'bai-bo', '52/2018/TT-NHNN', ('toàn bộ',))])
        self.assertEqual(self.found(effect + '2. Thông tư số 143/2020/TT-BQP ngày 08 tháng 12 năm 2020 hướng dẫn thực hiện một số điều của '
                                    'Nghị định số 146/2018/NĐ-CP hết hiệu lực kể từ ngày Thông tư này có hiệu lực thi hành.', 'Thông tư hướng dẫn'),
                         [('Điều 2 Khoản 2', 'bai-bo', '143/2020/TT-BQP', ('toàn bộ',))])
        self.assertEqual(self.found(effect + '2. Luật Viễn thông số 41/2009/QH12 đã được sửa đổi, bổ sung một số điều theo Luật số 21/2017/QH14 '
                                    'và Luật số 23/2018/QH14 hết hiệu lực kể từ ngày Luật này có hiệu lực thi hành.', 'Luật Viễn thông'),
                         [('Điều 2 Khoản 2', 'bai-bo', '41/2009/QH12', ('toàn bộ',))])

    def test_items_of_a_list_the_heading_acts_on(self):
        # 682620: each clause names one row of Phụ lục V; the heading performs the halt. Rows have no node: the appendix holds them.
        parsed, _ = parse('Điều 1. Phạm vi\nNội dung.\nĐiều 2. Ngưng hiệu lực thi hành quy định về kích thước tối thiểu tại Phụ lục V '
                          'ban hành kèm theo Nghị định số 37/2024/NĐ-CP cho đến khi có quy định mới\n'
                          '1. Cá chày đất tại số thứ tự 11 mục 1.\n2. Cá trích xương tại số thứ tự 36 mục 1.')
        rows = [c for c in detect(9, {**META, 'title': 'Nghị định về thủy sản'}, parsed) if c['source_path'].startswith('Điều 2')]
        self.assertEqual([(c['source_path'], c['action'], c['scope'], c['_stated']) for c in rows],
                         [('Điều 2 Khoản 1', 'ngung-hieu-luc', 'Phụ lục V', True), ('Điều 2 Khoản 2', 'ngung-hieu-luc', 'Phụ lục V', True)])

    def test_parts_named_by_name(self):
        # 13696: "các Thông tư liên tịch số A …, số B … của liên Bộ Tài chính, Công nghiệp, Tổng cục Hải quan, Quyết định số C".
        parsed, _ = parse('Điều 1. Bãi bỏ chính sách thuế theo tỷ lệ nội địa hoá quy định tại các Thông tư liên tịch số 176/1998/TTLT-BTC-BCN-TCHQ '
                          'ngày 25/12/1998, số 120/2000/TTLT-BTC-BCN-TCHQ ngày 25/12/2000 của liên Bộ Tài chính, Công nghiệp, Tổng cục Hải quan, '
                          'Quyết định số 1944/1998/QĐ-BTC ngày 25/12/1998 của Bộ trưởng Bộ Tài chính.\nĐiều 2. Hiệu lực\nQuyết định này có hiệu lực.')
        rows = detect(9, {**META, 'title': 'Quyết định bãi bỏ chính sách thuế theo tỷ lệ nội địa hoá'}, parsed)
        self.assertEqual(sorted((c['target_doc'], c.get('doi_tuong')) for c in rows),
                         sorted((n, 'chính sách thuế theo tỷ lệ nội địa hoá') for n in ('176/1998/TTLT-BTC-BCN-TCHQ', '120/2000/TTLT-BTC-BCN-TCHQ', '1944/1998/QĐ-BTC')))

    def test_adjust_and_supplement_and_its_denial(self):
        # 686881: "điều chỉnh, bổ sung … lại thành" is the pair "sửa đổi, bổ sung"; "không điều chỉnh, bổ sung … giữ nguyên" is no act.
        rows = self.found('Điều 1. Phê duyệt điều chỉnh, bổ sung nội dung khoản 6 Điều 1 Quyết định số 972/QĐ-UBND ngày 01/4/2025 lại thành: “6. A”\n'
                          'Điều 2. Các nội dung khác không điều chỉnh, bổ sung tại Quyết định số 972/QĐ-UBND giữ nguyên không thay đổi.',
                          'Quyết định điều chỉnh Kế hoạch')
        self.assertEqual(rows, [('Điều 1', 'bo-sung', '972/QĐ-UBND', ('khoản 6 Điều 1',)), ('Điều 1', 'sua-doi', '972/QĐ-UBND', ('khoản 6 Điều 1',))])

    def test_guided_provision_before_the_number(self):
        # 217132: "… hướng dẫn thực hiện xóa nợ … của Điều 55 Nghị định số 83/2013/NĐ-CP".
        parsed, _ = parse('THÔNG TƯ\nHƯỚNG DẪN THỰC HIỆN XÓA NỢ TIỀN THUẾ\nBộ trưởng Bộ Tài chính ban hành Thông tư hướng dẫn thực hiện xóa nợ tiền thuế phát sinh trước ngày 01 tháng 7 năm 2007 '
                          'của Điều 55 Nghị định số 83/2013/NĐ-CP ngày 22 tháng 7 năm 2013 nêu trên.\nĐiều 1. Phạm vi\nNội dung.\nĐiều 2. Hiệu lực\nA.')
        rows = guidance(9, {**META, 'title': 'Thông tư hướng dẫn thực hiện xóa nợ tiền thuế'}, parsed, lambda numbers: [], lambda name, day: None)
        self.assertEqual([(r['source_path'], r['target_doc'], r['scope']) for r in rows], [('Lời dẫn', '83/2013/NĐ-CP', 'Điều 55')])


class PairedActions(unittest.TestCase):
    def test_amend_and_supplement_stand_together(self):
        # The model accepts "sửa đổi" but rejects "bổ sung" for "Khoản 5 Điều 4 được sửa đổi, bổ sung": both are kept (D2).
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 85/2014/TT-BGTVT\n'
                          '1. Khoản 5 Điều 4 được sửa đổi, bổ sung như sau: “5. Nội dung.”')
        candidates = detect(1, {**META, 'title': 'Thông tư sửa đổi Thông tư 85/2014/TT-BGTVT'}, parsed)
        self.assertEqual(sorted(c['action'] for c in candidates), ['bo-sung', 'sua-doi'])

        def caller(prompt, text, folder, **options):
            valid = json.loads(text)['action'] == 'sua-doi'
            return json.dumps({'valid': valid, 'reason': 'thử'}), {}
        with tempfile.TemporaryDirectory() as folder:
            rows, errors = verify(candidates, Path(folder), lambda numbers: [], {}, config(), caller=caller)
        self.assertEqual(errors, [])
        self.assertEqual(sorted((r['_source']['action'], r['_source']['scope']) for r in rows),
                         [('bo-sung', 'khoản 5 Điều 4'), ('sua-doi', 'khoản 5 Điều 4')])


    def test_a_unit_that_opens_with_the_act_needs_no_model(self):
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số Điều của Thông tư số 75/2017/TT-BTC như sau:\n'
                          '1. Bỏ gạch đầu dòng thứ ba điểm b Khoản 3 Điều 17 Thông tư số 55/2016/TT-BTC.\n'
                          '2. Sửa đổi, bổ sung khoản 5 Điều 4 như sau: “5. Nội dung.”\n'
                          '3. Các đơn vị đã thực hiện theo khoản 2 Điều 3 Thông tư số 75/2017/TT-BTC được sửa đổi.')
        found = {(c['source_path'], c['action']): stated(c) for c in detect(1, META, parsed)}
        self.assertEqual(found, {('Điều 1 Khoản 1', 'bai-bo'): True, ('Điều 1 Khoản 2', 'sua-doi'): True,
                                 ('Điều 1 Khoản 2', 'bo-sung'): True, ('Điều 1 Khoản 3', 'sua-doi'): False})


class OnePerPosition(unittest.TestCase):
    def test_each_position_is_one_relation(self):
        row = {'action': 'thay-cum-tu', 'source_path': 'Điều 1 Khoản 2', 'scope': 'khoản 5 Điều 3; Điều 12',
               'vi_tri': ['khoản 5 Điều 3', 'Điều 12'],
               'cum_tu': [{'cu': 'a', 'moi': 'b', 'vi_tri': ['khoản 5 Điều 3']}, {'cu': 'c', 'moi': 'd', 'vi_tri': []}]}
        split = one_per_position([{'_id': '7_4', '_source': row}, {'_id': 'hd_7_0', '_source': {'scope': 'toàn bộ', 'vi_tri': ['toàn bộ']}}], 7)
        self.assertEqual([(r['_id'], r['_source']['vi_tri']) for r in split],
                         [('7_0', ['khoản 5 Điều 3']), ('7_1', ['Điều 12']), ('hd_7_0', ['toàn bộ'])])
        # A pair keeps its own position; a pair whose position was not found keeps the relation's.
        self.assertEqual([p['cu'] for p in split[0]['_source']['cum_tu']], ['a', 'c'])
        self.assertEqual([p['cu'] for p in split[1]['_source']['cum_tu']], ['c'])
        # Both keep the source sentence's scope.
        self.assertEqual({r['_source']['scope'] for r in split[:2]}, {'khoản 5 Điều 3; Điều 12'})

    def test_level_follows_the_positions_wherever_the_sentence_stands(self):
        self.assertEqual(level({'source_path': 'intro', 'detection_mode': 'intro', 'scope': 'Điều 6', 'vi_tri': ['Điều 6']}), 'vi_tri')
        self.assertEqual(level({'source_path': 'Tiêu đề', 'scope': 'toàn bộ', 'vi_tri': ['toàn bộ']}), 'van_ban')
        self.assertEqual(level({'source_path': 'intro', 'scope': 'một số điều', 'vi_tri': []}), 'van_ban')
        self.assertEqual(level({'source_path': 'Điều 1', 'scope': 'phần căn cứ', 'vi_tri': [], 'doi_tuong': 'phần căn cứ', 'kem_theo': False}), 'noi_dung')
        self.assertEqual(level({'source_path': 'Điều 1', 'scope': 'chưa xác định', 'vi_tri': []}), 'chua_xac_dinh')
        # A form named with its appendix: the appendix is the position (192512).
        self.assertEqual(level({'source_path': 'Điều 6', 'scope': 'x', 'vi_tri': ['Phụ lục 03'], 'doi_tuong': 'mẫu Bản cáo bạch', 'kem_theo': True}), 'vi_tri')


class EffectPerProvision(unittest.TestCase):
    TEXT = ('Điều 4. Hiệu lực thi hành\n'
            '1. Nghị định này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2024, trừ quy định tại khoản 2 Điều 2 có hiệu lực từ ngày 01 tháng 01 năm 2025.\n'
            '2. Điểm b khoản 1 Điều 3 Nghị định này có hiệu lực sau 45 ngày kể từ ngày ký.\n'
            '3. Khoản 5 Điều 12 Nghị định số 15/2018/NĐ-CP có hiệu lực đến hết năm 2025.')

    def test_stated_dates(self):
        rows = provision_effects(self.TEXT, '2024-05-01', 'Nghị định')
        self.assertEqual([(r['vi_tri'], r['ngay_hieu_luc'], r['ngay_hieu_luc_cach'], r['ngay_hieu_luc_so_ngay']) for r in rows],
                         [(['khoản 2 Điều 2'], '2025-01-01', 'ngay_cu_the', None), (['điểm b khoản 1 Điều 3'], '2024-06-15', 'ngay_ky', 45)])

    def test_units_take_the_closest_stated_date(self):
        rows = provision_effects(self.TEXT, '2024-05-01', 'Nghị định')
        document = {'ngay_hieu_luc': '2024-07-01', 'ngay_hieu_luc_cach': 'ngay_cu_the', 'ngay_hieu_luc_so_ngay': None,
                    'hoi_to': True, 'ngay_hoi_to': '2024-01-01', 'hoi_to_vi_tri': ['khoản 1 Điều 2']}
        cases = [(('2', '2', 'a', None, ''), '2025-01-01', True), (('2', '1', None, None, ''), '2024-07-01', False),
                 (('3', '1', 'b', '2', ''), '2024-06-15', True), (('3', '1', None, None, ''), '2024-07-01', False)]
        for unit, day, own in cases:
            dates = unit_dates(unit, document, rows)
            self.assertEqual((dates['ngay_hieu_luc'], dates['ngay_hieu_luc_rieng']), (day, own), unit)
        self.assertEqual(unit_dates(('2', '1', None, None, ''), document, rows).get('ngay_hoi_to'), '2024-01-01')
        self.assertNotIn('ngay_hoi_to', unit_dates(('2', '2', None, None, ''), document, rows))


class ConsolidationAndGuidance(unittest.TestCase):
    def test_consolidated_text_relates_to_what_it_restates(self):
        parsed, _ = parse('VĂN PHÒNG QUỐC HỘI\nSố: 35/VBHN-VPQH\nNGHỊ QUYẾT\n'
                          'Nghị quyết số 131/2020/QH14 ngày 16 tháng 11 năm 2020 của Quốc hội, được sửa đổi, bổ sung bởi:\n'
                          'Nghị quyết số 96/2023/QH15 ngày 23 tháng 6 năm 2023 của Quốc hội.\n'
                          'Căn cứ Hiến pháp;\nĐiều 1. Phạm vi\nNội dung.')
        meta = {**META, 'document_number': '35/VBHN-VPQH', 'legal_type': 'Văn bản hợp nhất'}
        rows = consolidation(589448, meta, parsed)
        self.assertEqual([(r['_id'], r['action'], r['target_doc'], r['source_path'], r['scope']) for r in rows],
                         [('hn_589448_0', 'hop-nhat', '131/2020/QH14', 'Phần đầu', 'toàn bộ')])  # the base only, not the amending note
        self.assertEqual(detect(589448, meta, parsed), [])  # its notes restate other acts; it performs none

    def test_guidance_keeps_the_provisions_it_names(self):
        head = 'NGHỊ ĐỊNH\nQUY ĐỊNH CHI TIẾT KHOẢN 3 ĐIỀU 25 VÀ ĐIỀU 30 CỦA LUẬT ĐẤT ĐAI SỐ 31/2024/QH15'
        rows = guidance(1, META, {'phan_dau': head, 'intro': '', 'can_cu': []}, lambda numbers: [], lambda name, day: None)
        self.assertEqual([(r['action'], r['target_doc'], r['scope']) for r in rows],
                         [('quy-dinh-chi-tiet', '31/2024/QH15', 'khoản 3 Điều 25; Điều 30')])


class StagingTarget(unittest.TestCase):
    def test_v4_staging_names(self):
        v4 = {'documents': 'legal-docs-v4', 'chunks': 'legal-chunk-section-v4', 'changes': 'legal-changed-v4'}
        self.assertTrue(config(target=v4).validate())
        with self.assertRaises(ValueError):  # one suffix for all three
            config(target={**v4, 'changes': 'legal-changed-v3'}).validate()
        with self.assertRaises(ValueError):
            config(target={**v4, 'changes': 'legal-changed-v5'}).validate()
        self.assertIsInstance(config(), Config)


if __name__ == '__main__':
    unittest.main()
