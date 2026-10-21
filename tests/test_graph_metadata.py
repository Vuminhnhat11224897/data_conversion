"""Metadata for the temporal graph: effective dates, new actions, guidance relations and cross references."""

import unittest

from vbpl_v3.references import cross_references, guidance
from vbpl_v3.relations import detect
from vbpl_v3.structure import parse
from vbpl_v3.temporal import effective_date, extension, normalize_scope, phrase_change, positions, stated_positions, suspension
from vbpl_v3.text import action_matches

META = {'document_number': '05/2026/TT-BTC', 'title': 'Thông tư sửa đổi', 'action': 'sua-doi', 'legal_type': 'Thông tư',
        'issuing_authority': 'Bộ Tài chính', 'issuance_date': '2026-03-01', 'legal_sectors': []}


class EffectiveDateCheck(unittest.TestCase):
    def test_effect_clause_forms(self):
        # (date, the day the clause counts from, the stated number of days after it)
        cases = [('Điều 5. Thông tư này có hiệu lực kể từ ngày 15 tháng 9 năm 2013.', 'Thông tư', '2013-09-15', 'ngay_cu_the', None),
                 ('Quyết định này có hiệu lực thi hành từ ngày 01/7/2024.', 'Quyết định', '2024-07-01', 'ngay_cu_the', None),
                 ('Quyết định này có hiệu lực kể từ ngày ký.', 'Quyết định', '2026-03-01', 'ngay_ky', 0),
                 ('Nghị định này có hiệu lực thi hành sau 45 ngày kể từ ngày ký ban hành.', 'Nghị định', '2026-04-15', 'ngay_ky', 45),
                 ('Quyết định này có hiệu lực sau 15 ngày kể từ ngày đăng Công báo.', 'Quyết định', None, 'ngay_dang_cong_bao', 15),
                 ('Nghị quyết này có hiệu lực sau 10 ngày, kể từ ngày thông qua.', 'Nghị quyết', '2026-03-11', 'ngay_thong_qua', 10),
                 ('Thông tư liên tịch này có hiệu lực kể từ ngày 01/02/2008.', 'Thông tư liên tịch', '2008-02-01', 'ngay_cu_the', None),
                 # A provision with its own date does not set the document's date.
                 ('Khoản 3 Điều 2 Thông tư này có hiệu lực từ ngày 01/01/2027.', 'Thông tư', None, 'khong_tim_thay', None),
                 # A letter quoting the law it explains does not take the law's effective date.
                 ('Luật này có hiệu lực từ ngày 01/01/2003, đề nghị các Sở thực hiện.', 'Công văn', None, 'khong_tim_thay', None)]
        for text, kind, value, how, days in cases:
            result = effective_date(text, kind, '2026-03-01')
            self.assertEqual((result['ngay_hieu_luc'], result['ngay_hieu_luc_cach'], result['ngay_hieu_luc_so_ngay']), (value, how, days), text)

    def test_quoted_amendment_and_defaults(self):
        # The effect clause quoted from the amended document is not this document's own.
        text = '1. Điều 9 được sửa đổi như sau:\n“Thông tư này có hiệu lực kể từ ngày 01 tháng 01 năm 2010.”\n2. Thông tư này có hiệu lực kể từ ngày 01 tháng 5 năm 2026.'
        self.assertEqual(effective_date(text, 'Thông tư', '2026-03-01')['ngay_hieu_luc'], '2026-05-01')
        # The issuance date is used without an effect clause only for documents known not to be normative.
        self.assertEqual(effective_date('Kính gửi các Sở.', 'Công văn', '2026-03-01', is_normative=False)['ngay_hieu_luc_cach'], 'mac_dinh_ngay_ban_hanh')
        for normative in (True, None):
            result = effective_date('Không có câu hiệu lực.', 'Quyết định', '2026-03-01', is_normative=normative)
            self.assertEqual((result['ngay_hieu_luc'], result['ngay_hieu_luc_cach']), (None, 'khong_tim_thay'))
        self.assertEqual(effective_date('Thông tư này có hiệu lực từ ngày ký.', 'Văn bản hợp nhất', '2026-03-01')['ngay_hieu_luc_cach'], 'van_ban_hop_nhat')


class ActionCheck(unittest.TestCase):
    def test_positions_and_scope_normalization(self):
        self.assertEqual(positions('tên Chương II; Điều 1; các khoản 1, 7, 8a Điều 3; điểm b, c khoản 2 Điều 108, Điều 82'),
                         ['tên Chương II', 'Điều 1', 'khoản 1 Điều 3', 'khoản 7 Điều 3', 'khoản 8a Điều 3',
                          'điểm b khoản 2 Điều 108', 'điểm c khoản 2 Điều 108', 'Điều 82'])
        self.assertEqual([normalize_scope(x) for x in ('toan-bo', 'toàn văn', 'Toàn bộ', 'khoản 2 Điều 3')],
                         ['toàn bộ', 'toàn bộ', 'toàn bộ', 'khoản 2 Điều 3'])

    def test_wording_replacement_and_suspension(self):
        self.assertEqual(action_matches('Thay thế cụm từ bằng cụm từ tại Điều 4')[0][2], 'thay-cum-tu')
        self.assertEqual(action_matches('Thay thế Điều 5')[0][2], 'thay-the')
        self.assertEqual(action_matches('Kiến nghị Thủ tướng đình chỉ việc thi hành Nghị quyết'), [])
        pairs, places = phrase_change('Thay thế cụm từ “tái cơ cấu” và cụm từ “cơ cấu lại lần đầu” bằng cụm từ “cơ cấu lại” tại điểm b khoản 5 Điều 11, khoản 2b Điều 46.')
        here = ['điểm b khoản 5 Điều 11', 'khoản 2b Điều 46']
        self.assertEqual(pairs, [{'cu': 'tái cơ cấu', 'moi': 'cơ cấu lại', 'vi_tri': here}, {'cu': 'cơ cấu lại lần đầu', 'moi': 'cơ cấu lại', 'vi_tri': here}])
        # Each replacement keeps its own locations.
        split, both = phrase_change('Thay thế cụm từ “cấp huyện” bằng cụm từ “cấp xã” tại Điều 32; thay thế từ “huyện” bằng từ “xã” tại Điều 4.')
        self.assertEqual([(x['cu'], x['vi_tri']) for x in split], [('cấp huyện', ['Điều 32']), ('huyện', ['Điều 4'])])
        self.assertEqual(both, ['Điều 32', 'Điều 4'])
        self.assertEqual(places, ['điểm b khoản 5 Điều 11', 'khoản 2b Điều 46'])
        self.assertEqual(suspension('Tạm đình chỉ thi hành Quyết định số 12/2020/QĐ-UBND kể từ ngày 01/02/2026 đến hết ngày 30/6/2026.'),
                         {'dinh_chi_tu_ngay': '2026-02-01', 'dinh_chi_den_ngay': '2026-06-30', 'dinh_chi_den_khi': None})

    def test_detected_relations_carry_locations_and_period(self):
        parsed, _ = parse('Điều 1. Sửa đổi Thông tư số 19/2013/TT-NHNN\n'
                          '1. Thay thế cụm từ “tổ chức tín dụng” bằng cụm từ “tổ chức tín dụng Việt Nam” tại các khoản 5, 8 Điều 3; Điều 12.\n'
                          '2. Bãi bỏ khoản 2 Điều 7.\n'
                          'Điều 2. Đình chỉ thi hành Quyết định số 99/2025/QĐ-BTC cho đến khi có kết luận thanh tra.')
        rows = {(r['action'], r['target_doc']): r for r in detect(1, META, parsed)}
        wording = rows[('thay-cum-tu', '19/2013/TT-NHNN')]
        self.assertEqual((wording['vi_tri'], wording['cum_tu'][0]['moi']), (['khoản 5 Điều 3', 'khoản 8 Điều 3', 'Điều 12'], 'tổ chức tín dụng Việt Nam'))
        self.assertEqual(rows[('bai-bo', '19/2013/TT-NHNN')]['scope'], 'khoản 2 Điều 7')
        self.assertEqual(rows[('dinh-chi', '99/2025/QĐ-BTC')]['dinh_chi_den_khi'], 'có kết luận thanh tra')


class CorrectionHaltExtensionCheck(unittest.TestCase):
    """dinh-chinh, ngung-hieu-luc and gia-han, with sentences from 1321/QĐ-UBND, 03/2023/TT-NHNN and 986/TTg-KTN."""

    def test_action_words(self):
        cases = [('Đính chính lỗi kỹ thuật trình bày Quyết định số 28/2017/QĐ-UBND', ['dinh-chinh']),
                 ('Ngưng hiệu lực thi hành từ ngày 24 tháng 4 năm 2023 đối với khoản 11 Điều 4', ['ngung-hieu-luc']),
                 ('Đồng ý gia hạn hiệu lực của Quyết định 10/2009/QĐ-TTg', ['gia-han']),
                 # A tax deadline, a proposal and a catalogue heading are not the act.
                 ('Nghị định về gia hạn thời hạn nộp thuế', []),
                 ('Bộ Công Thương đề nghị gia hạn hiệu lực Quyết định số 10/2009/QĐ-TTg', []),
                 ('Danh mục văn bản hết hiệu lực, ngưng hiệu lực toàn bộ của tỉnh', [])]
        for text, actions in cases:
            self.assertEqual([a for _, _, a in action_matches(text)], actions, text)

    def test_extension_end(self):
        cases = [('gia hạn hiệu lực đến hết tháng 12 năm 2016.', ('2016-12-31', None)),
                 ('gia hạn hiệu lực đến hết tháng 2 năm 2024.', ('2024-02-29', None)),
                 ('gia hạn hiệu lực đến hết ngày 30/6/2025.', ('2025-06-30', None)),
                 ('gia hạn hiệu lực đến hết năm 2025.', ('2025-12-31', None)),
                 ('gia hạn hiệu lực cho đến khi có văn bản thay thế.', (None, 'có văn bản thay thế')),
                 ('gia hạn hiệu lực thêm 06 tháng.', (None, 'thêm 06 tháng'))]
        for text, expected in cases:
            result = extension(text)
            self.assertEqual((result['gia_han_den_ngay'], result['gia_han_den_khi']), expected, text)

    def test_correction_lists_every_place(self):
        self.assertEqual(stated_positions('Tại điểm b khoản 7 Điều 3 và khoản 2 Điều 6, bỏ dấu ba chấm.'),
                         ['điểm b khoản 7 Điều 3', 'khoản 2 Điều 6'])
        self.assertEqual(stated_positions('Đính chính cụm từ thành tại khoản 1 Điều 17 và khoản 3 Điều 19; cụm từ thành tại khoản 4 Điều 8.'),
                         ['khoản 1 Điều 17', 'khoản 3 Điều 19', 'khoản 4 Điều 8'])
        self.assertEqual(stated_positions('Tại khoản 2, 3, 4 Điều 7 đính chính thành'), ['khoản 2 Điều 7', 'khoản 3 Điều 7', 'khoản 4 Điều 7'])

    def test_detected_correction(self):
        parsed, _ = parse('Điều 1. Đính chính Quyết định số 28/2017/QĐ-UBND, cụ thể:\n'
                          '1. Bỏ căn cứ pháp lý thứ 8 tại phần căn cứ.\n'
                          '2. Đính chính lỗi chính tả cụm từ “đầu đủ” thành “đầy đủ” tại khoản 1 Điều 17 và khoản 3 Điều 19.\n'
                          '3. Tại khoản 2, 3 Điều 20 đính chính thành: Thông tư số 61/2013/TT-BGTVT sửa đổi, bổ sung Điều 5.\n'
                          'Điều 2. Quyết định này có hiệu lực kể từ ngày ký./.')
        meta = {**META, 'title': 'Quyết định đính chính Quyết định 28/2017/QĐ-UBND', 'legal_type': 'Quyết định'}
        rows = {r['source_path']: r for r in detect(1, meta, parsed)}
        self.assertEqual({r['action'] for r in rows.values()}, {'dinh-chinh'})  # the corrected wording's "sửa đổi, bổ sung" is content
        self.assertEqual((rows['Điều 1 Khoản 1']['doi_tuong'], rows['Điều 1 Khoản 1']['kem_theo']), ('phần căn cứ', False))
        self.assertEqual(rows['Điều 1 Khoản 2']['vi_tri'], ['khoản 1 Điều 17', 'khoản 3 Điều 19'])
        self.assertEqual(rows['Điều 1 Khoản 3']['vi_tri'], ['khoản 2 Điều 20', 'khoản 3 Điều 20'])

    def test_detected_halt_keeps_intro_relation(self):
        parsed, _ = parse('THÔNG TƯ\nQUY ĐỊNH NGƯNG HIỆU LỰC THI HÀNH KHOẢN 11 ĐIỀU 4 THÔNG TƯ 16/2021/TT-NHNN\n'
                          'Căn cứ Luật Ngân hàng Nhà nước Việt Nam;\n'
                          'Thống đốc ban hành Thông tư quy định ngưng hiệu lực thi hành khoản 11 Điều 4 Thông tư số 16/2021/TT-NHNN.\n'
                          'Điều 1. Ngưng hiệu lực thi hành từ ngày 24 tháng 4 năm 2023 đến hết ngày 31 tháng 12 năm 2023 '
                          'đối với quy định tại khoản 11 Điều 4 Thông tư số 16/2021/TT-NHNN.\n'
                          'Điều 2. Thông tư này có hiệu lực từ ngày 24 tháng 4 năm 2023.')
        meta = {**META, 'title': 'Thông tư quy định ngưng hiệu lực thi hành khoản 11 Điều 4 Thông tư 16/2021/TT-NHNN'}
        rows = detect(1, meta, parsed)
        # The intro keeps its own relation beside the article's.
        self.assertEqual([(r['_id'], r['action'], r['source_path'], r['scope']) for r in rows],
                         [('1_0', 'ngung-hieu-luc', 'Điều 1', 'khoản 11 Điều 4'), ('intro_1_0', 'ngung-hieu-luc', 'intro', 'khoản 11 Điều 4')])
        self.assertEqual({k: rows[0][k] for k in ('dinh_chi_tu_ngay', 'dinh_chi_den_ngay', 'dinh_chi_den_khi')},
                         {'dinh_chi_tu_ngay': '2023-04-24', 'dinh_chi_den_ngay': '2023-12-31', 'dinh_chi_den_khi': None})

    def test_detected_extension_in_letter(self):
        parsed, _ = parse('Số: 986/TTg-KTN\nV/v gia hạn hiệu lực Quyết định 10/2009/QĐ-TTg\nKính gửi: Bộ Công Thương.\n'
                          'Xét đề nghị của Bộ Công Thương về việc gia hạn hiệu lực của Quyết định số 10/2009/QĐ-TTg, '
                          'Thủ tướng Chính phủ có ý kiến như sau:\n'
                          '1. Đồng ý gia hạn hiệu lực của Quyết định 10/2009/QĐ-TTg đến hết tháng 12 năm 2016.\n'
                          '2. Bộ Công Thương hoàn thiện Đề án trong tháng 12 năm 2016./.\nNơi nhận: - Như trên;')
        meta = {**META, 'title': 'Công văn 986/TTg-KTN gia hạn hiệu lực Quyết định 10/2009/QĐ-TTg', 'legal_type': 'Công văn'}
        rows = detect(1, meta, parsed)
        self.assertEqual([(r['_id'], r['action'], r['source_path'], r['target_doc'], r['scope'], r['gia_han_den_ngay']) for r in rows],
                         [('1_0', 'gia-han', 'Mục 1', '10/2009/QĐ-TTg', 'toàn bộ', '2016-12-31')])


class ReferenceCheck(unittest.TestCase):
    def test_guidance_from_title_and_basis(self):
        hit = {'_id': '500', '_source': {'document_number': '06/2021/NĐ-CP', 'issuance_date': '2021-01-26', 'issuing_authority': 'Chính phủ'}}
        meta = {**META, 'title': 'Thông tư 10/2026/TT-BXD hướng dẫn Nghị định 06/2021/NĐ-CP do Bộ trưởng Bộ Xây dựng ban hành',
                'document_number': '10/2026/TT-BXD'}
        rows = guidance('900', meta, {'phan_dau': 'THÔNG TƯ\nHƯỚNG DẪN NGHỊ ĐỊNH 06/2021/NĐ-CP', 'can_cu': []}, lambda numbers: [hit], lambda name, day: None)
        self.assertEqual([(r['action'], r['target_doc'], r['target_matched_id']) for r in rows], [('huong-dan', '06/2021/NĐ-CP', 500)])
        law = {'_id': '77', '_source': {}}
        meta = {**META, 'title': 'Nghị định quy định chi tiết một số điều của Luật Đất đai'}
        rows = guidance('901', meta, {'phan_dau': 'NGHỊ ĐỊNH\nQUY ĐỊNH CHI TIẾT MỘT SỐ ĐIỀU CỦA LUẬT ĐẤT ĐAI',
                                      'can_cu': ['Căn cứ Luật Đất đai ngày 29 tháng 11 năm 2013;']}, lambda n: [],
                        lambda name, day: law if (name, day) == ('Đất đai', '2013-11-29') else None)
        self.assertEqual([(r['action'], r['scope'], r['target_doc'], r['target_matched_id']) for r in rows],
                         [('quy-dinh-chi-tiet', 'một số điều', 'Luật Đất đai', 77)])
        # An amending title's "hướng dẫn" describes the amended document, not this one.
        meta = {**META, 'title': 'Thông tư sửa đổi Thông tư 05/2019/TT-BTC hướng dẫn Nghị định 34/2016/NĐ-CP'}
        head = 'THÔNG TƯ\nSỬA ĐỔI THÔNG TƯ 05/2019/TT-BTC HƯỚNG DẪN NGHỊ ĐỊNH 34/2016/NĐ-CP'
        self.assertEqual(guidance('902', meta, {'phan_dau': head, 'can_cu': []}, lambda n: [hit], lambda name, day: None), [])
        # Q11 (20/10/2026): a stored title that states guidance the printed title does not ("Công văn … hướng dẫn chính sách thuế",
        # 144450, a reply to a company) gives no relation.
        meta = {**META, 'title': 'Công văn 2470/TCT-CC hướng dẫn chính sách thuế đối với Nhà thầu nước ngoài', 'legal_type': 'Quyết định'}
        self.assertEqual(guidance('903', meta, {'phan_dau': 'Số: 2470/TCT-CC V/v chính sách thuế | Hà Nội', 'can_cu': []},
                                  lambda n: [hit], lambda name, day: None), [])

    def test_cross_references(self):
        chunk = {'noi_dung': 'Thực hiện theo quy định tại khoản 2 Điều này và Điều 5 Luật này; '
                             'hồ sơ theo điểm a khoản 1 Điều 7 Nghị định số 15/2018/NĐ-CP.', 'ky_hieu_dieu': '12'}
        self.assertEqual([(r['loai'], r['vi_tri'], r['van_ban']) for r in cross_references(chunk)],
                         [('noi_bo', 'Điều 5', None), ('noi_bo', 'khoản 2 Điều 12', None),
                          ('ngoai', 'điểm a khoản 1 Điều 7', '15/2018/NĐ-CP')])


if __name__ == '__main__':
    unittest.main()


class ReviewedRelationErrors(unittest.TestCase):
    """Errors found by reviewing legal-changed-v3 for TT 19/2013 and its amending circulars."""

    TEXT = ('Thông tư sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN.\n'
            'Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN như sau:\n'
            'Điều 1 được sửa đổi, bổ sung như sau:\n“Điều 1. Phạm vi điều chỉnh\nThông tư này quy định việc mua nợ.”\n'
            '2. Bổ sung khoản 10, khoản 11 vào Điều 3 như sau:\n“10. Nợ xấu.\n11. Trái phiếu.”\n'
            '3. Sửa đổi, bổ sung tên Mục 2 Chương II như sau:\n“Mục 2. PHÁT HÀNH TRÁI PHIẾU”\n'
            '4. Điều 34 được sửa đổi, bổ sung như sau:\n“Điều 34. Nguyên tắc bán nợ\na) Nguyên tắc bán nợ xấu của Công ty;\nb) Thu hồi tối đa khoản nợ.”\n'
            '5. Bổ sung Điều 47a vào sau Điều 47 như sau:\n“Điều 47a. Trích lập dự phòng\nNội dung.”\n'
            'Điều 2. Thay thế một số cụm từ của Thông tư số 19/2013/TT-NHNN\n'
            '1. Thay thế cụm từ “nợ” bằng cụm từ “nợ xấu” tại các khoản 3, 4a, 7 và tên Điều 50.\n'
            '2. Thay thế cụm từ “bán” bằng cụm từ “bán nợ” tại Điều 12.')

    def rows(self):
        parsed, _ = parse(self.TEXT)
        return parsed, detect(288269, {**META, 'title': 'Thông tư sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN'}, parsed)

    def test_lost_first_clause_label_is_clause_one(self):
        parsed, _ = self.rows()
        article = parsed['dieu_luat'][0]
        self.assertEqual(([k['ky_hieu'] for k in article['khoan']], article.get('mo_dau', '')), (['1', '2', '3', '4', '5'], ''))

    def test_positions_of_each_change(self):
        _, rows = self.rows()
        found = {(r['source_path'], r['action'], r['scope']) for r in rows}
        self.assertIn(('Điều 1 Khoản 5', 'bo-sung', 'Điều 47a'), found)
        self.assertIn(('Điều 1 Khoản 3', 'sua-doi', 'tên Mục 2 Chương II'), found)
        self.assertIn(('Điều 1 Khoản 4', 'sua-doi', 'Điều 34'), found)
        # Points of the new Điều 34 are its content, not changes of their own.
        self.assertFalse([r for r in rows if r['source_path'].startswith('Điều 1 Khoản 4 điểm')])
        self.assertEqual(positions('khoản 10, khoản 11 Điều 3'), ['khoản 10 Điều 3', 'khoản 11 Điều 3'])
        wording = next(r for r in rows if r['action'] == 'thay-cum-tu')
        self.assertEqual(wording['vi_tri'], ['khoản 3 Điều 50', 'khoản 4a Điều 50', 'khoản 7 Điều 50', 'tên Điều 50'])
        self.assertEqual(positions('điểm d, khoản 1, điều 1'), ['điểm d khoản 1 Điều 1'])

    def test_document_level_relations_are_classified(self):
        from vbpl_v3.convert import level
        intro = next(r for r in self.rows()[1] if r['source_path'] == 'intro')
        self.assertEqual(intro['scope'], 'một số điều')
        self.assertEqual(level({**intro, 'vi_tri': []}), 'van_ban')
        self.assertEqual(level({'source_path': 'Điều 1 Khoản 2', 'scope': 'khoản 10 Điều 3', 'vi_tri': ['khoản 10 Điều 3']}), 'vi_tri')
        self.assertEqual(level({'source_path': 'Điều 1 Khoản 9', 'scope': 'chưa xác định', 'vi_tri': []}), 'chua_xac_dinh')

    def test_named_parts_without_numbers(self):
        from vbpl_v3.convert import level
        from vbpl_v3.relations import named_content
        self.assertEqual(named_content('Đơn giá này thay thế đơn giá khảo sát xây dựng ban hành kèm theo Quyết định số '), ('đơn giá khảo sát xây dựng', True))
        self.assertEqual(named_content('có hiệu lực và thay thế nội dung bảng giá ca máy công bố tại Văn bản '), ('bảng giá ca máy', False))
        self.assertEqual(named_content('Bãi bỏ khoản 2 Điều 5 của Quyết định số '), (None, False))
        self.assertEqual(level({'source_path': 'Điều 2', 'scope': 'đơn giá', 'vi_tri': [], 'doi_tuong': 'đơn giá', 'kem_theo': True}), 'van_ban_kem_theo')

    def test_single_unnumbered_appendix_is_a_position(self):
        from vbpl_v3.relations import scope
        self.assertEqual(scope('Thay thế Phụ lục ban hành kèm theo Thông tư '), ('Phụ lục', False))
        self.assertEqual(positions('Phụ lục'), ['Phụ lục'])

    def test_mistyped_citation_day_with_numbered_year(self):
        from vbpl_v3.relations import resolve
        hit = lambda i, number, authority, day: {'_id': i, '_source': {'document_number': number, 'issuing_authority': authority, 'issuance_date': day}}
        base = {'target_doc': '45/2008/QĐ-UBND', 'action': 'thay-the', 'source_id': 1, 'source_issuance_date': '2009-12-31',
                'source_issuing_authority': 'Tỉnh Tiền Giang', '_evidence': 'thay thế Quyết định số 45/2008/QĐ-UBND ngày 19/12/2008 của UBND tỉnh.'}
        hits = [hit('86855', '45/2008/QĐ-UBND', 'Tỉnh Tiền Giang', '2008-12-22'), hit('98267', '45/2008/QĐ-UBND', 'Tỉnh Đồng Nai', '2008-08-04')]
        row = resolve(dict(base), hits)
        self.assertEqual((row['target_matched_id'], row.get('target_match_note')), (86855, 'lech_ngay_trich_dan'))
        # Another province's same-number decision is never taken, even when the day is the only mismatch.
        self.assertIsNone(resolve(dict(base), hits[1:])['target_matched_id'])
        # A number without its year needs the exact cited day.
        self.assertIsNone(resolve({**base, 'target_doc': '45/QĐ-UBND', '_evidence': 'Quyết định số 45/QĐ-UBND ngày 19/12/2008'},
                                  [hit('5', '45/QĐ-UBND', 'Tỉnh Tiền Giang', '2008-12-22')])['target_matched_id'])


class PilotTwoRelationErrors(unittest.TestCase):
    """Errors found by auditing the 200-document pilot."""

    def rows(self, text, title='Quyết định'):
        parsed, _ = parse(text)
        return detect(1, {**META, 'title': title}, parsed)

    def test_form_codes_are_not_target_documents(self):
        rows = self.rows('Điều 1. Sửa đổi mẫu biểu\n1. Thay thế mẫu số 01/THKH và 01A/KK-HĐ ban hành kèm theo Thông tư số 156/2013/TT-BTC bằng mẫu số 01/CNKD.\n'
                         '2. Thay thế mẫu số 02-1/BK-BH ban hành kèm theo Thông tư số 156/2013/TT-BTC bằng mẫu số 01-1/BK-BHXSĐC.')
        self.assertEqual({(r['target_doc'], r['scope']) for r in rows},
                         {('156/2013/TT-BTC', 'Mẫu số 01/THKH; Mẫu số 01A/KK-HĐ'), ('156/2013/TT-BTC', 'Mẫu số 02-1/BK-BH')})

    def test_both_spellings_of_annulment_and_whole_document_actions(self):
        self.assertEqual(action_matches('Hủy bỏ Quyết định số 12/2020/QĐ-UBND')[0][2], 'huy-bo')
        rows = self.rows('Điều 1. Đình chỉ thực hiện Quyết định số 2048/QĐ-UBND ngày 19/11/2012 của Ủy ban nhân dân tỉnh.')
        self.assertEqual([(r['action'], r['scope']) for r in rows], [('dinh-chi', 'toàn bộ')])
        rows = self.rows('Điều 1. Hiệu lực thi hành\n1. Luật này có hiệu lực từ ngày 01/01/2009.\n2. Luật này thay thế Luật thuế thu nhập doanh nghiệp số 09/2003/QH11.', 'Luật')
        self.assertEqual([(r['action'], r['scope']) for r in rows], [('thay-the', 'toàn bộ')])

    def test_lead_sentence_supplies_clause_and_article(self):
        rows = self.rows('Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 01/2012/NĐ-CP\n'
                         '1. Sửa đổi khoản 1 Điều 2 như sau: “1. Nội dung.”\n'
                         '2. Bổ sung, thay thế một số cụm từ tại các điểm, khoản của khoản 3 Điều 2 như sau:\n'
                         'a) Thay thế cụm từ “cơ quan” bằng cụm từ “đơn vị” tại điểm a, điểm d;\n'
                         'b) Thay thế cụm từ “báo cáo” bằng cụm từ “thông báo” tại điểm b.', 'Nghị định sửa đổi Nghị định 01/2012/NĐ-CP')
        wording = {r['source_path']: r['vi_tri'] for r in rows if r['action'] == 'thay-cum-tu'}
        self.assertEqual(wording['Điều 1 Khoản 2 điểm a'], ['điểm a khoản 3 Điều 2', 'điểm d khoản 3 Điều 2'])
        self.assertEqual(wording['Điều 1 Khoản 2 điểm b'], ['điểm b khoản 3 Điều 2'])

    def test_named_part_with_its_issuer(self):
        rows = self.rows('Điều 1. Hủy bỏ Kế hoạch tuyển dụng công chức năm 2024 đã được Chủ tịch UBND tỉnh ban hành kèm theo Quyết định số 444/QĐ-UBND ngày 10/4/2024.')
        self.assertEqual([(r['action'], r.get('doi_tuong'), r.get('kem_theo')) for r in rows], [('huy-bo', 'Kế hoạch tuyển dụng công chức năm 2024', True)])

    def test_bare_clause_takes_the_article_of_its_lead(self):
        rows = self.rows('Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 146/2018/NĐ-CP\n'
                         '1. Sửa đổi khoản 1 Điều 3 như sau: “1. Nội dung.”\n'
                         '2. Sửa đổi, bổ sung một số khoản của Điều 21 như sau:\n'
                         'a) Sửa đổi, bổ sung khoản 1 như sau: “1. Nội dung.”\n'
                         'b) Bổ sung các điểm đ và e vào khoản 2 như sau: “đ) Nội dung; e) Nội dung.”', 'Nghị định sửa đổi Nghị định 146/2018/NĐ-CP')
        found = {(r['source_path'], tuple(positions(r['scope']))) for r in rows}
        self.assertIn(('Điều 1 Khoản 2 điểm a', ('khoản 1 Điều 21',)), found)
        self.assertIn(('Điều 1 Khoản 2 điểm b', ('điểm đ khoản 2 Điều 21', 'điểm e khoản 2 Điều 21')), found)
