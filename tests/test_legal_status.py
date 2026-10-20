"""Legal standing fields agreed with the graph team: la_vbqppl, cap_hieu_luc (15 groups), stated end, retroactive start."""

import unittest

from vbpl_v3.convert import appendix_label
from vbpl_v3.legal_status import expiry, normative, rank, retroactive
from vbpl_v3.references import amended_targets, link_references
from vbpl_v3.structure import build_chunks, parse, passages


def doc(kind, number, authority, issued='2020-05-01'):
    return {'legal_type': kind, 'document_number': number, 'issuing_authority': authority, 'issuance_date': issued}


class NormativeAndRank(unittest.TestCase):
    def test_normative(self):
        cases = [(doc('Thông tư', '19/2013/TT-NHNN', 'Ngân hàng Nhà nước'), (True, 'theo_loai')),
                 (doc('Công văn', '120/BXD-HĐXD', 'Bộ Xây dựng'), (False, 'theo_loai')),
                 (doc('Quyết định', '12/2020/QĐ-UBND', 'Tỉnh Bắc Kạn'), (True, 'so_hieu_co_nam')),
                 (doc('Quyết định', '1705/QĐ-UBND', 'Tỉnh Lạng Sơn'), (False, 'so_hieu_khong_nam')),
                 (doc('Chỉ thị', '05/2017/CT-UBND', 'Tỉnh A', '2017-03-01'), (False, 'chi_thi_tu_2016')),
                 (doc('Quyết định', '25/2005/QĐ-BTC', 'Bộ Tài chính', '2005-04-01'), (True, 'so_hieu_co_nam')),
                 (doc('Quyết định', '100/2012/QĐ-BTC', 'Bộ Tài chính', '2012-04-01'), (False, 'quyet_dinh_bo_tu_2009')),
                 (doc('Nghị quyết', '20-NQ/TW', 'Ban Chấp hành Trung ương'), (False, 'van_ban_dang')),
                 (doc('Quyết định', '05/QĐ', 'Tỉnh A', '1998-01-01'), (None, 'can_kiem')),
                 (doc('Văn bản hợp nhất', '03/VBHN-BTC', 'Bộ Tài chính'), (False, 'van_ban_hop_nhat')),
                 # A year in the number does not make an individual decision normative.
                 ({**doc('Nghị quyết', '09/2004/NQ-CP', 'Chính phủ'), 'title': 'Nghị quyết về Phiên họp Chính phủ thường kỳ tháng 6'}, (False, 'tieu_de_ca_biet')),
                 ({**doc('Quyết định', '2330/2005/QĐ-CT', 'Tỉnh Bắc Ninh'), 'title': 'Quyết định về việc cử cán bộ đi nghiên cứu sinh'}, (False, 'tieu_de_ca_biet')),
                 ({**doc('Quyết định', '20/2020/QĐ-UBND', 'Tỉnh A'), 'title': 'Quyết định phê duyệt và ban hành Quy chế quản lý'}, (True, 'so_hieu_co_nam')),
                 ({**doc('Quyết định', '33/2008/QĐ-UBND', 'Tỉnh A', '2008-01-01'), 'title': 'Quyết định phê duyệt bảng giá tối thiểu để tính lệ phí trước bạ'}, (True, 'so_hieu_co_nam')),
                 ({**doc('Quyết định', '07/2001/QĐ-BCN', 'Bộ Công nghiệp', '2001-02-14'), 'title': 'Quyết định ban hành tạm thời Định mức tổng hợp và Đơn giá dự toán'}, (True, 'so_hieu_co_nam'))]
        for meta, expected in cases:
            self.assertEqual(normative(meta), expected, meta)

    def test_rank_follows_the_fifteen_groups(self):
        cases = [(doc('Luật', '45/2019/QH14', 'Quốc hội'), (2, 'QUOC_HOI', None)),
                 (doc('Nghị quyết', '35/2018/UBTVQH14', 'Uỷ ban Thường vụ Quốc hội'), (3, 'UBTV_QUOC_HOI', None)),
                 (doc('Nghị định', '15/2020/NĐ-CP', 'Chính phủ'), (5, 'CHINH_PHU', None)),
                 (doc('Quyết định', '12/2020/QĐ-TTg', 'Thủ tướng Chính phủ'), (6, 'THU_TUONG', None)),
                 (doc('Nghị quyết', '02/2020/NQ-HĐTP', 'Hội đồng Thẩm phán Toà án nhân dân tối cao'), (7, 'HDTP_TANDTC', None)),
                 (doc('Thông tư', '19/2013/TT-NHNN', 'Ngân hàng Nhà nước'), (8, 'THONG_TU', None)),
                 (doc('Thông tư liên tịch', '22/2007/TTLT/BTC-BGTVT', 'Bộ Tài chính, Bộ Giao thông vận tải'), (9, 'THONG_TU_LIEN_TICH', None)),
                 (doc('Nghị quyết', '12/2020/NQ-HĐND', 'Tỉnh Bắc Kạn'), (10, 'HDND_TINH', None)),
                 (doc('Quyết định', '12/2020/QĐ-UBND', 'Thành phố Hà Nội'), (11, 'UBND_TINH', None)),
                 (doc('Quyết định', '25/2005/QĐ-BTC', 'Bộ Tài chính', '2005-04-01'), (8, 'THONG_TU', 'hinh_thuc_cu')),
                 (doc('Chỉ thị', '05/2010/CT-UBND', 'Tỉnh A', '2010-03-01'), (11, 'UBND_TINH', 'hinh_thuc_cu')),
                 (doc('Quyết định', '12/2015/QĐ-UBND', 'Quận Phú Nhuận', '2015-03-01'), (None, None, 'cap_huyen'))]
        for meta, expected in cases:
            self.assertEqual(rank(meta, normative(meta)[0]), expected, meta)
        self.assertEqual(rank(doc('Công văn', '1/BXD', 'Bộ Xây dựng'), False), (None, None, None))


class StatedDates(unittest.TestCase):
    def test_expiry_only_from_the_document_itself(self):
        self.assertEqual(expiry('Nghị quyết này có hiệu lực từ ngày 01/01/2022 đến hết ngày 31/12/2025.', '2021-12-10', 'Nghị quyết')['ngay_het_hieu_luc'], '2025-12-31')
        self.assertEqual(expiry('Quyết định này được áp dụng cho giai đoạn 2021 - 2025.', '2021-01-10', 'Quyết định'),
                         {'ngay_het_hieu_luc': '2025-12-31', 'ngay_het_hieu_luc_cach': 'het_nam',
                          'ngay_het_hieu_luc_trich': 'Quyết định này được áp dụng cho giai đoạn 2021 - 2025'})
        # Another document's end, a quoted one, or the period of a plan issued by the decision is not this document's end.
        text = ('Quyết định số 12/2015/QĐ-UBND hết hiệu lực kể từ ngày 01/01/2020.\n“Thông tư này có hiệu lực đến hết ngày 31/12/2019.”\n'
                'Điều 1. Ban hành kèm theo Quyết định này Kế hoạch thực hiện Đề án giai đoạn 2022-2025.')
        self.assertEqual(expiry(text, '2019-12-01', 'Quyết định')['ngay_het_hieu_luc'], None)

    def test_retroactive_start(self):
        effect = {'ngay_hieu_luc': '2024-12-10', 'ngay_hieu_luc_cach': 'ngay_ky'}
        result = retroactive('Mức hỗ trợ quy định tại Nghị quyết này được áp dụng từ ngày 01/01/2024.', '2024-12-10', effect, 'Nghị quyết')
        self.assertEqual((result['hoi_to'], result['ngay_hoi_to'], result['hoi_to_vi_tri']), (True, '2024-01-01', []))
        self.assertFalse(retroactive('Quyết định này có hiệu lực kể từ ngày ký.', '2024-12-10', effect, 'Quyết định')['hoi_to'])
        early = {'ngay_hieu_luc': '2024-07-01', 'ngay_hieu_luc_cach': 'ngay_cu_the', 'ngay_hieu_luc_trich': 'có hiệu lực từ ngày 01/7/2024'}
        self.assertEqual(retroactive('', '2024-07-15', early, 'Quyết định')['ngay_hoi_to'], '2024-07-01')
        # Only the listed provisions reach back; a letter about a law, or a consolidated text, is not retroactive.
        part = retroactive('Quy định tại khoản 8 Điều 1 và khoản 3 Điều 2 Nghị định này được áp dụng từ ngày 01 tháng 01 năm 2019.', '2023-10-19', effect, 'Nghị định')
        self.assertEqual(part['hoi_to_vi_tri'], ['khoản 8 Điều 1', 'khoản 3 Điều 2'])
        self.assertFalse(retroactive('Mọi khoản của Luật này đều được áp dụng từ ngày 01/01/2003.', '2003-08-06', effect, 'Công văn')['hoi_to'])
        self.assertFalse(retroactive('Nghị quyết này được thực hiện từ ngày 01/7/2021.', '2023-08-02', effect, 'Văn bản hợp nhất')['hoi_to'])
        from vbpl_v3.convert import within
        self.assertTrue(within('Điều 1 Khoản 8 điểm a', ['khoản 8 Điều 1']))
        self.assertFalse(within('Điều 1 Khoản 2', ['khoản 8 Điều 1']))
        self.assertTrue(within('Điều 4', []))


class QuotedReferencesAndPassages(unittest.TestCase):
    def test_this_document_inside_quoted_new_text_is_the_amended_one(self):
        meta = {'document_number': '08/2016/TT-NHNN', 'title': 'Thông tư sửa đổi Thông tư 19/2013/TT-NHNN', 'action': 'sua-doi',
                'legal_type': 'Thông tư', 'issuing_authority': 'Ngân hàng Nhà nước', 'issuance_date': '2016-06-16', 'legal_sectors': []}
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 19/2013/TT-NHNN\n'
                          '1. Bổ sung Điều 15a vào sau Điều 15 như sau:\n“Điều 15a. Gia hạn\n'
                          '1. Theo quy định tại Điều 17b Thông tư này và khoản 2 Điều này.\n2. Nội dung.”\n'
                          '2. Theo quy định tại Điều 3 Thông tư này, đơn vị báo cáo.')
        chunks = build_chunks(314836, meta, parsed)
        candidates = [{'source_path': 'Điều 1 Khoản 1', 'target_doc': '19/2013/TT-NHNN', 'target_matched_id': 206663}]
        link_references(chunks, 314836, meta, parsed, lambda n: [], lambda n, d: None, amended_targets(candidates))
        refs = {c['_id']: c['_source'].get('dan_chieu') for c in chunks}
        self.assertEqual([(r['loai'], r['vi_tri'], r['target_id']) for r in refs['314836_d1_k1']],
                         [('van_ban_bi_sua', 'Điều 17b', 206663), ('van_ban_bi_sua', 'khoản 2 Điều 15a', 206663)])
        # Outside the quotation, "Thông tư này" is the amending circular itself.
        self.assertEqual([(r['loai'], r['target_id']) for r in refs['314836_d1_k2']], [('noi_bo', 314836)])

    def test_long_unstructured_text_is_split_into_passages(self):
        body = 'Kính gửi các Sở.\n' + '\n'.join('Đoạn số %d nêu yêu cầu thực hiện ' % i + 'nhiệm vụ ' * 30 for i in range(12))
        chunks = build_chunks(9, {'title': 'Công văn'}, parse(body)[0])
        kinds = [(c['_id'], c['_source']['chunk_type']) for c in chunks]
        self.assertEqual(kinds[0], ('9_nd_full', 'noi_dung_full'))
        self.assertTrue(all(len(c['_source']['noi_dung'].split()) <= 200 for c in chunks[1:]))
        self.assertEqual(' '.join(' '.join(c['_source']['noi_dung'].split()) for c in chunks[1:]), ' '.join(chunks[0]['_source']['noi_dung'].split()))
        self.assertEqual(passages('ngắn'), ['ngắn'])

    def test_appendix_label(self):
        self.assertEqual(appendix_label({'loai': 'labeled', 'tieu_de': 'PHỤ LỤC SỐ 01 BÁO CÁO'}), '01')
        self.assertEqual(appendix_label({'loai': 'labeled', 'tieu_de': 'PHỤ LỤC II DANH MỤC'}), 'II')
        self.assertIsNone(appendix_label({'loai': 'unlabeled', 'tieu_de': 'QUY CHẾ …'}))


if __name__ == '__main__':
    unittest.main()
