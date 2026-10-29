"""Catalogue fields read from the text when the source lacks them (vbpl_v3.metadata_fill, 29/10/2026)."""

import unittest

from vbpl_v3.metadata_fill import action_of, by_code, signers_of
from vbpl_v3.structure import normalize

# The layout of the new crawl: one item per line.
NEW = normalize('''BỘ TÀI CHÍNH
CỤC THUẾ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 1467/QĐ-CT

Hà Nội, ngày 26 tháng 10 năm 2026

QUYẾT ĐỊNH

Về việc ban hành Quy chế làm việc

Điều 1. Ban hành kèm theo Quyết định này Quy chế làm việc.

Điều 2. Quyết định này có hiệu lực kể từ ngày ký./.

Nơi nhận:
- Như Điều 2;
- Lưu: VT, TCCB (4b).

CỤC TRƯỞNG

Mai Xuân Thành''')

# The layout of older texts: the issuer and the motto in one table row, the signature on one line.
OLD = normalize('''BỘ TÀI CHÍNH TỔNG CỤC HẢI QUAN | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc
Số: 6 01 7 /TB-TCHQ | Hà Nội, ngày 01 tháng 07 năm 2015

THÔNG BÁO

VỀ KẾT QUẢ PHÂN LOẠI ĐỐI VỚI HÀNG HÓA XUẤT KHẨU, NHẬP KHẨU

Thông báo này có hiệu lực kể từ ngày ban hành.

KT. TỔNG CỤC TRƯỞNG PHÓ TỔNG CỤC TRƯỞNG Nguyễn Dương Thái''')

LETTER = normalize('''ỦY BAN NHÂN DÂN
THÀNH PHỐ HỒ CHÍ MINH
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 8110/UBND-KT
V/v triển khai phương án ứng phó

Thành phố Hồ Chí Minh, ngày 26 tháng 10 năm 2026

Kính gửi: Sở Nông nghiệp và Môi trường.

Nơi nhận:
- Như trên;
- Lưu: VT.

TM. ỦY BAN NHÂN DÂN
KT. CHỦ TỊCH
PHÓ CHỦ TỊCH

Bùi Minh Thạnh''')


class Fill(unittest.TestCase):
    def test_new_layout(self):
        got = by_code({}, NEW)
        self.assertEqual((got['document_number'], got['issuance_date'], got['legal_type'], got['issuing_authority'], got['signers']),
                         ('1467/QĐ-CT', '2026-10-26', 'Quyết định', 'Cục thuế', 'Mai Xuân Thành'))

    def test_old_layout(self):
        got = by_code({}, OLD)
        self.assertEqual((got['document_number'], got['issuance_date'], got['legal_type'], got['issuing_authority'], got['signers']),
                         ('6017/TB-TCHQ', '2015-07-01', 'Thông báo', 'Tổng cục hải quan', 'Nguyễn Dương Thái'))

    def test_letter(self):
        got = by_code({}, LETTER)
        self.assertEqual((got['legal_type'], got['issuing_authority'], got['signers'], got['action']),
                         ('Công văn', 'Thành phố Hồ Chí Minh', 'Bùi Minh Thạnh', 'congvan'))

    def test_source_fields_are_kept(self):
        src = {'document_number': '1467/QĐ-CT', 'issuance_date': '2026-10-26', 'legal_type': 'Quyết định', 'issuing_authority': 'Cục Thuế',
               'signers': 'Mai Xuân Thành:7001', 'title': 'Quyết định 1467/QĐ-CT năm 2026 ban hành Quy chế làm việc', 'action': 'other'}
        self.assertEqual(by_code(src, NEW), {})
        self.assertEqual(set(by_code({**src, 'signers': None}, NEW)), {'signers'})

    def test_recipient_lines_are_no_signer(self):
        self.assertIsNone(signers_of(normalize('Điều 1. Thi hành.\n\nNơi nhận:\n- Như Điều 1;\n- Bộ Tài chính;\n- Lưu: VT.')))

    def test_action_of_published_list(self):
        self.assertEqual(action_of('Quyết định', 'Quyết định 715/QĐ-UBND năm 2024 công bố danh mục 02 thủ tục hành chính được sửa đổi, bổ sung'), 'other')
        self.assertEqual(action_of('Quyết định', 'Quyết định 12/2026/QĐ-UBND sửa đổi, bổ sung Quy định kèm theo Quyết định 30/2016/QĐ-UBND'), 'sua-doi')
        self.assertEqual(action_of('Thông tư', 'Thông tư 120/2025/TT-BTC hướng dẫn Nghị định 186/2025/NĐ-CP'), 'huongdan')


if __name__ == '__main__':
    unittest.main()
