"""The source site's notice is no content (E5) and does not hide an English text (E16), 03/11/2026."""
import unittest

from vbpl_v3.structure import normalize, paywalled
from vbpl_v3.text import language

NOTICE = 'Bạn phải đăng nhập hoặc đăng ký Thành Viên TVPL Pro để sử dụng được đầy đủ các tiện ích gia tăng liên quan đến nội dung TCVN.'
CONTACT = 'Mọi chi tiết xin liên hệ: ĐT: (028) 3930 3279 DĐ: 0906 22 99 66'


class PaywallCheck(unittest.TestCase):
    def test_notice_and_hidden_marks_removed(self):
        text = f'QUY CHUẨN\n\n1. Phạm vi\n\n...\n\n{NOTICE}\n\n...\n\n{NOTICE}\n\n{CONTACT}'
        clean = normalize(text)
        self.assertEqual(clean, 'QUY CHUẨN\n\n1. Phạm vi')
        self.assertTrue(paywalled(text))

    def test_form_dots_kept_without_notice(self):
        text = 'Số: ........\n\n...\n\nĐiều 1. Nội dung'
        self.assertEqual(normalize(text), text)
        self.assertFalse(paywalled(text))

    def test_english_text_found_once_notice_removed(self):
        english = ' '.join(['The enterprise shall submit the invoices as prescribed by law to the tax authority.'] * 20)
        text = '\n\n'.join([english, NOTICE] * 15)
        self.assertEqual(language(normalize(text)), 'en')


if __name__ == '__main__':
    unittest.main()
