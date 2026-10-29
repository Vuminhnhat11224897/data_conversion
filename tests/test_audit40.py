"""Errors found by the audit of 40 documents in -v4 (29/10/2026), each with the cases next to it that must not change."""

import unittest

from vbpl_v3.convert import appendix_label
from vbpl_v3.governance import performer
from vbpl_v3.references import cross_references
from vbpl_v3.structure import appendix_header, parse
from vbpl_v3.validate import VERBS


def implicit(text):
    return [r['vi_tri'] for r in cross_references({'noi_dung': text}) if r['loai'] == 'noi_bo_ngam']


class ImplicitReference(unittest.TestCase):
    def test_number_of_another_document_is_not_cut(self):
        self.assertEqual(implicit('đáp ứng quy định tại điểm a khoản 1 Điều 149 Luật Kinh doanh bảo hiểm'), [])
        self.assertEqual(implicit('theo Điều 218 Bộ luật Tố tụng hình sự'), [])
        self.assertEqual(implicit('tại điều 37 Luật Thể dục, thể thao'), [])

    def test_own_positions_stay(self):
        self.assertEqual(implicit('theo quy định tại khoản 2 Điều 14; hồ sơ nêu tại Điều 15a.'), ['khoản 2 Điều 14', 'Điều 15a'])
        self.assertEqual(implicit('như Điều 6.'), ['Điều 6'])


class AppendixLabel(unittest.TestCase):
    def label(self, title):
        return appendix_label({'loai': 'labeled', 'tieu_de': title})

    def test_word_after_heading_is_no_label(self):
        for title in ('PHỤ LỤC DANH SÁCH CÁC LĨNH VỰC', 'PHỤ LỤC MẪU KÊ KHAI', 'PHỤ LỤC CÁC NHIỆM VỤ', 'PHỤ LỤC MA TRẬN',
                      'PHỤ LỤC LỊCH CHUYỂN TRƯỜNG', 'PHỤ LỤC VỀ GIẤY PHÉP'):
            self.assertIsNone(self.label(title), title)

    def test_labels_stay(self):
        for title, label in (('PHỤ LỤC II DANH MỤC', 'II'), ('PHỤ LỤC SỐ 01 BÁO CÁO', '01'), ('PHỤ LỤC XII', 'XII'),
                             ('PHỤ LỤC IA MẪU BÁO CÁO', 'IA'), ('PHỤ LỤC Vb ĐIỀU CHỈNH', 'Vb'), ('PHỤ LỤC I4 DANH MỤC', 'I4'),
                             ('PHỤ LỤC 2a', '2a'), ('PHỤ LỤC VII: Danh mục', 'VII')):
            self.assertEqual(self.label(title), label, title)

    def test_cited_appendix_in_a_cell_is_no_heading(self):
        self.assertFalse(appendix_header('Phụ lục I.1; các bộ, ngành là cơ quan chủ trì.'))
        self.assertTrue(appendix_header('Phụ lục I'))
        self.assertTrue(appendix_header('PHỤ LỤC I.1'))


class RecipientsAndSignature(unittest.TestCase):
    BODY = 'QUYẾT ĐỊNH:\nĐiều 1. Quyết định này có hiệu lực kể từ ngày ký./.\n\nNơi nhận:\n- Như Điều 1;\n'

    def recipients(self, tail):
        return parse(self.BODY + tail)[0]['noi_nhan']

    def test_signature_without_kt_tm(self):
        self.assertEqual(self.recipients('- Lưu: VT, TCCB.\n\nBỘ TRƯỞNG\n\nVũ Hải Quân'), ['Như Điều 1', 'Lưu: VT, TCCB'])
        self.assertEqual(self.recipients('- Lưu: VT, VP (2b).\n\nTL. CỤC TRƯỞNG\nCHÁNH VĂN PHÒNG\n\nNguyễn Văn A'),
                         ['Như Điều 1', 'Lưu: VT, VP (2b)'])

    def test_recipient_on_two_lines_stays(self):
        self.assertEqual(self.recipients('- VPCP: BTCN, các Vụ, Cục:\nKTTH, PL, TH;\n- Lưu: VT.\nKT. BỘ TRƯỞNG\nTHỨ TRƯỞNG\nNguyễn Văn A'),
                         ['Như Điều 1', 'VPCP: BTCN, các Vụ, Cục:\nKTTH, PL, TH', 'Lưu: VT'])


class BareListLead(unittest.TestCase):
    TEXT = ('Quyết định này bãi bỏ:\n\na) Quyết định số 30/2016/QĐ-UBND ngày 29 tháng 6 năm 2016 của Ủy ban nhân dân tỉnh;\n\n'
            'b) Quyết định số 15/2018/QĐ-UBND ngày 18 tháng 7 năm 2018 của Ủy ban nhân dân tỉnh.')

    def tie(self, text, target):
        row = {'source_path': 'Điều 7 Khoản 2', '_unit': {'noi_dung': text, 'cau_dan': ''}, '_context': {'ten_dieu': 'Hiệu lực thi hành'}}
        return performer(row, VERBS['bai-bo'], target)[3]

    def test_act_before_colon_ties_each_item(self):
        self.assertTrue(self.tie(self.TEXT, '30/2016/QĐ-UBND'))
        self.assertTrue(self.tie(self.TEXT, '15/2018/QĐ-UBND'))

    def test_lead_naming_a_provision_stays_untied(self):
        text = 'Bãi bỏ khoản 2 Điều 3:\n\na) Quyết định số 30/2016/QĐ-UBND.'
        self.assertFalse(self.tie(text, '30/2016/QĐ-UBND'))


if __name__ == '__main__':
    unittest.main()
