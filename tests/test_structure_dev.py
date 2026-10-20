"""Structure errors the dev labelers found (15/10/2026), as general rules."""

import unittest

from vbpl_v3.structure import parse


def clauses(parsed, number):
    article = next(a for a in parsed['dieu_luat'] if a['ky_hieu'] == number)
    return [(k['ky_hieu'], [p['ky_hieu'] for p in k['diem']]) for k in article['khoan']]


class FootnoteLabels(unittest.TestCase):
    """A consolidated text glues the number of its footnote to the label: "4.[2]", "4.8 ", "46.", "d4)", "đ)5", "Điều 32."."""

    TEXT = ('Số: 12/VBHN-NHNN\nTHÔNG TƯ\nĐiều 1. Phạm vi\n1. Một.\n2. Hai:\na) A;\nb) B;\nc) C;\nd4) (được bãi bỏ)\nđ)5 Đ.\n'
            '3. Ba.\n4.[2] Bốn.\n5.8 Năm.\n66. Sáu.\nĐiều 2. Đối tượng\n1. Một.\n2.[11] Hai.\nĐiều 32. Hiệu lực\n1. Một.\n2. Hai.\n'
            'XÁC THỰC VĂN BẢN HỢP NHẤT\n2 Điều này được sửa đổi theo Thông tư số 1/2020/TT-NHNN.')

    def test_glued_labels_follow_the_running_numbering(self):
        parsed, _ = parse(self.TEXT)
        self.assertEqual([a['ky_hieu'] for a in parsed['dieu_luat']], ['1', '2', '3'])
        self.assertEqual(clauses(parsed, '1'), [('1', []), ('2', ['a', 'b', 'c', 'd', 'đ']), ('3', []), ('4', []), ('5', []), ('6', [])])
        self.assertEqual(clauses(parsed, '2'), [('1', []), ('2', [])])
        # The closing block of a consolidated text belongs to no article.
        self.assertNotIn('XÁC THỰC', parsed['dieu_luat'][-1]['noi_dung'])

    def test_a_real_clause_46_is_not_cut(self):
        # Outside a consolidated text, and where 46 is not the expected label, nothing is rewritten.
        text = 'NGHỊ ĐỊNH\nĐiều 1. Phạm vi\n' + ''.join(f'{n}. Khoản {n}.\n' for n in range(1, 47)) + 'Điều 2. Hiệu lực\nCó hiệu lực.'
        parsed, _ = parse(text)
        self.assertEqual(len(clauses(parsed, '1')), 46)


class OpeningsAndClosings(unittest.TestCase):
    def test_a_letter_opening_is_not_its_first_section(self):
        text = ('BỘ TÀI CHÍNH | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nSố: 123/BTC-CST\nV/v hướng dẫn thuế\nKính gửi: Cục Thuế tỉnh A.\n'
                'Bộ Tài chính hướng dẫn như sau:\nI. Phạm vi áp dụng\nNội dung một.\nII. Thủ tục\nNội dung hai.\nNơi nhận:\n- Như trên;')
        parsed, _ = parse(text)
        self.assertEqual([m['so_muc'] for m in parsed['noi_dung_sections']], ['I', 'II'])
        self.assertTrue(parsed['noi_dung_sections'][0]['noi_dung'].startswith('Phạm vi áp dụng'))
        self.assertIn('Kính gửi', parsed['intro'])
        self.assertNotIn('Phạm vi áp dụng', parsed['intro'])

    def test_closing_sentence_of_a_resolution(self):
        text = ('NGHỊ QUYẾT\nĐiều 1. Phạm vi\nNội dung.\nĐiều 2. Tổ chức thực hiện\n1. Giao Ủy ban nhân dân tỉnh.\n'
                '2. Giao Thường trực Hội đồng nhân dân tỉnh giám sát.\n'
                'Nghị quyết này đã được Hội đồng nhân dân tỉnh A khóa XIX, kỳ họp thứ nhất thông qua ngày 10 tháng 7 năm 2021.\n'
                'Nơi nhận:\n- Như Điều 2;\nCHỦ TỊCH')
        parsed, _ = parse(text)
        self.assertNotIn('thông qua', parsed['dieu_luat'][-1]['khoan'][-1]['noi_dung'])
        self.assertNotIn('Nghị quyết này đã được', ' '.join(parsed['noi_nhan']))

    def test_a_signature_without_recipients_is_no_recipient(self):
        text = ('QUYẾT ĐỊNH\nĐiều 1. Công bố kèm theo quyết định này 03 thủ tục hành chính.\nĐiều 2. Quyết định này có hiệu lực thi hành kể từ ngày ký.\n'
                'Chánh văn phòng Ủy ban nhân dân tỉnh chịu trách nhiệm thi hành Quyết định này./.\nCHỦ TỊCH Phùng Quang Hùng')
        self.assertEqual(parse(text)[0]['noi_nhan'], [])
        parsed, _ = parse(text.replace('CHỦ TỊCH', 'Nơi nhận:\n- Như Điều 2;\n- Lưu: VT.\nKT. CHỦ TỊCH'))
        self.assertEqual(parsed['noi_nhan'], ['Như Điều 2', 'Lưu: VT'])

    def test_old_and_misspelt_article_labels(self):
        parsed, _ = parse('SẮC LỆNH\nĐiều thứ 1: Một.\nĐiều thứ 2: Hai.\nĐiêu 3: Ba.\nHồ Chí Minh')
        self.assertEqual([a['ky_hieu'] for a in parsed['dieu_luat']], ['1', '2', '3'])

    def test_stray_space_before_the_dot(self):
        parsed, _ = parse('NGHỊ ĐỊNH\nĐiều 1. Lập kế hoạch\n1. Căn cứ.\n2 . Trên cơ sở các căn cứ.\n3. Hồ sơ.\nĐiều 2. Hiệu lực\nCó hiệu lực.')
        self.assertEqual([k for k, _ in clauses(parsed, '1')], ['1', '2', '3'])



class LetterOutline(unittest.TestCase):
    """A letter with several numbering styles goes to the model, which returns line ids only."""

    TEXT = ('BỘ TÀI CHÍNH | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nSố: 12/BTC-TCT\nKính gửi: Cục Thuế các tỉnh.\n'
            'Bộ Tài chính hướng dẫn như sau:\nI- PHẠM VI ÁP DỤNG\n1. Cơ quan đại diện.\n2. Tổ chức quốc tế.\n'
            'II- THỦ TỤC\n1. Hồ sơ.\n2. Thời hạn.\nTrong quá trình thực hiện, nếu có vướng mắc đề nghị phản ánh.\nNơi nhận:\n- Như trên;')

    def run_outline(self, answer):
        import json
        import tempfile
        from pathlib import Path
        from vbpl_v3.structure import source_lines
        from vbpl_v3.structure_ai import refine
        lines = source_lines(self.TEXT)
        calls = []

        def caller(prompt, text, folder, **options):
            calls.append(json.loads(text))
            return json.dumps(answer(lines)), {}
        with tempfile.TemporaryDirectory() as folder:
            parsed, stats = refine(self.TEXT, Path(folder), title='Công văn hướng dẫn thuế', caller=caller)
        return parsed, stats, calls

    def test_valid_outline_is_applied(self):
        def answer(lines):
            at = lambda prefix: next(i for i, line in enumerate(lines) if line.startswith(prefix))
            return {'mo_dau_ket_thuc': at('Bộ Tài chính hướng dẫn'), 'ket_thuc_bat_dau': at('Trong quá trình'),
                    'muc': [{'dong': at('I-'), 'nhan': 'I', 'cap': 1}, {'dong': at('II-'), 'nhan': 'II', 'cap': 1}]}
        parsed, stats, calls = self.run_outline(answer)
        self.assertTrue(stats['structure_ai']['outline']['applied'])
        self.assertEqual([m['so_muc'] for m in parsed['noi_dung_sections']], ['I', 'II'])
        self.assertTrue(parsed['noi_dung_sections'][0]['noi_dung'].startswith('PHẠM VI ÁP DỤNG'))
        self.assertNotIn('vướng mắc', parsed['noi_dung_sections'][1]['noi_dung'])
        self.assertIn('Kính gửi', parsed['intro'] + parsed['phan_dau'])

    def test_a_label_not_on_its_line_is_refused(self):
        def answer(lines):
            return {'mo_dau_ket_thuc': 0, 'ket_thuc_bat_dau': -1, 'muc': [{'dong': 1, 'nhan': 'I', 'cap': 1}, {'dong': 2, 'nhan': 'II', 'cap': 1}]}
        parsed, stats, calls = self.run_outline(answer)
        self.assertFalse(stats['structure_ai']['outline']['applied'])
        self.assertTrue(any('Outline model failed' in w for w in stats['structure_ai']['warnings']))

    def test_one_section_is_no_change_and_no_retry(self):
        parsed, stats, calls = self.run_outline(lambda lines: {'mo_dau_ket_thuc': -1, 'ket_thuc_bat_dau': -1, 'muc': []})
        self.assertFalse(stats['structure_ai']['outline']['applied'])
        self.assertEqual(sum(1 for c in calls if 'dong' in c), 1)


if __name__ == '__main__':
    unittest.main()
