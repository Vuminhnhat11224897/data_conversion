"""Layers 2-4 (15/10/2026): the model states acts with a quote; code resolves and checks them; nothing unsettled becomes an edge."""

import json
from pathlib import Path
import tempfile
import unittest

from vbpl_v3.extract import extract, shorten_quotes
from vbpl_v3.resolver import appendix_scope, resolve_row
from vbpl_v3.structure import parse
from vbpl_v3.text import number_key
from vbpl_v3.validate import only_in_history, only_noted, validate

META = {'document_number': '15/2020/QĐ-UBND', 'title': 'Quyết định sửa đổi Quy định ban hành kèm theo Quyết định 28/2017/QĐ-UBND',
        'action': 'sua-doi', 'legal_type': 'Quyết định', 'issuing_authority': 'Tỉnh A', 'issuance_date': '2020-05-01', 'legal_sectors': []}


def row(text, act, lead='', heading=''):
    return {'source_path': 'Điều 1 Khoản 1', 'performed': True, 'target_from': 'don_vi', 'target_part': '', **act,
            '_unit': {'source_path': 'Điều 1 Khoản 1', 'cau_dan': lead, 'noi_dung': text},
            '_context': {'chuong': '', 'ten_dieu': heading, 'cau_dan_dieu': '', 'van_ban': {'ten': META['title'], 'so_hieu': META['document_number']}, 'phan_dau': ''}}


def kept(rows):
    return validate(rows, resolve_row)


class ActorAndHolder(unittest.TestCase):
    """P1 (20/10/2026): the model says who acts and which document holds what is changed (124929-like letters, any document)."""

    def test_a_type_word_is_no_part(self):
        # 336452: "Nay bãi bỏ 15 văn bản (Danh mục đính kèm)", each listed decision read with target_part "Quyết định".
        text = 'Nay bãi bỏ 15 văn bản (Danh mục đính kèm) của Ủy ban nhân dân thành phố. Quyết định số 24/2007/QĐ-UBND.'
        act = {'action': 'bai-bo', 'target_document': '24/2007/QĐ-UBND', 'target_section': 'khong_ap_dung', 'target_text': [],
               'target_part': 'Quyết định', 'evidence': 'Nay bãi bỏ 15 văn bản (Danh mục đính kèm)', 'chu_the': 'van_ban_nay',
               'van_ban_chua_noi_dung': '24/2007/QĐ-UBND'}
        relations, _ = kept([row(text, act)])
        self.assertEqual([(r['vi_tri'], r.get('doi_tuong')) for r in relations], [(['toàn bộ'], None)])
        # The same act read from the row of the list: the first cell is the type column, not a procedure's name.
        listed = {**row('Quyết định | 24/2007/QĐ-UBND | 12/3/2007 | Về việc thu phí', {**act, 'target_part': ''}), 'source_path': 'Phụ lục 1 STT 1'}
        resolved = resolve_row(listed)
        self.assertEqual((resolved['vi_tri'], resolved.get('doi_tuong')), (['toàn bộ'], None))

    def test_rows_of_a_plan_are_no_acts(self):
        # 684851: "DANH MỤC VĂN BẢN … CẦN SỬA ĐỔI, BỔ SUNG, BAN HÀNH MỚI", column "Thời hạn thực hiện": documents to draft later.
        text = '4 | Nghị định sửa đổi, bổ sung một số điều của Nghị định số 45/2025/NĐ-CP. | X'
        act = {'action': 'sua-doi', 'target_document': '45/2025/NĐ-CP', 'target_section': 'khong_ro', 'target_text': [],
               'evidence': 'Nghị định sửa đổi, bổ sung một số điều của Nghị định số 45/2025/NĐ-CP', 'chu_the': 'van_ban_nay',
               'van_ban_chua_noi_dung': '45/2025/NĐ-CP'}
        planned = {**row(text, act, lead='TT | Tên văn bản sửa đổi, bổ sung và xây dựng mới | Thời hạn thực hiện',
                         heading='DANH MỤC VĂN BẢN QUY PHẠM PHÁP LUẬT CẦN SỬA ĐỔI, BỔ SUNG, BAN HÀNH MỚI'), 'source_path': 'Phụ lục 1 STT 4'}
        relations, rejected = kept([planned])
        self.assertEqual((relations, [r['reason'] for r in rejected]), ([], ['dong_bang_ke_hoach']))

    def test_proposal_and_task_are_not_acts(self):
        text = 'Giao Bộ Công an chủ trì xây dựng dự thảo Thông tư để sửa đổi, thay thế Thông tư số 36/2010/TT-BCA.'
        act = {'action': 'thay-the', 'target_document': '36/2010/TT-BCA', 'target_section': 'khong_ap_dung', 'target_text': [],
               'evidence': text, 'chu_the': 'giao_nhiem_vu', 'van_ban_chua_noi_dung': '36/2010/TT-BCA'}
        relations, rejected = kept([row(text, act)])
        self.assertEqual((relations, [r['reason'] for r in rejected]), ([], ['chu_the_giao_nhiem_vu']))

    def test_the_holder_of_the_changed_content_is_the_target(self):
        text = ('Bỏ trách nhiệm thực thi của Ngân hàng Nhà nước Việt Nam về việc sửa đổi Nghị định số 160/2006/NĐ-CP nêu tại mục B, phần XVI, '
                'Phương án đơn giản hóa ban hành kèm theo Nghị quyết số 25/NQ-CP ngày 02 tháng 6 năm 2010.')
        act = {'action': 'bai-bo', 'target_document': '160/2006/NĐ-CP', 'target_section': 'kem_theo', 'target_text': [],
               'target_part': 'trách nhiệm thực thi của Ngân hàng Nhà nước Việt Nam', 'evidence': text[:200],
               'chu_the': 'van_ban_nay', 'van_ban_chua_noi_dung': '25/NQ-CP'}
        relations, _ = kept([row(text, act)])
        self.assertEqual([r['target_doc'] for r in relations], ['25/NQ-CP'])
        # A holder the source does not show is not taken.
        relations, _ = kept([row(text, {**act, 'van_ban_chua_noi_dung': '99/NQ-CP'})])
        self.assertEqual([r['target_doc'] for r in relations], ['160/2006/NĐ-CP'])


class Validation(unittest.TestCase):
    def test_a_decision_and_the_regulation_it_issues(self):
        # Case A: "khoản 7 Điều 3" with no word on which part: the decision and its Quy định both have an Điều 3.
        text = 'Sửa đổi khoản 7 Điều 3 Quyết định số 28/2017/QĐ-UBND như sau: “7. Nội dung mới.”'
        act = {'action': 'sua-doi', 'target_document': '28/2017/QĐ-UBND', 'target_section': 'khong_ro', 'target_text': ['khoản 7 Điều 3'],
               'evidence': 'Sửa đổi khoản 7 Điều 3 Quyết định số 28/2017/QĐ-UBND'}
        (relation,), _ = kept([row(text, act)])
        self.assertEqual((relation['resolution_status'], relation['resolution_reason']), ('unresolved', 'phan_kem_theo_chua_ro'))
        stated = dict(act, target_section='kem_theo', evidence='Sửa đổi khoản 7 Điều 3 của Quy định ban hành kèm theo Quyết định số 28/2017/QĐ-UBND')
        (relation,), _ = kept([row('Sửa đổi khoản 7 Điều 3 của Quy định ban hành kèm theo Quyết định số 28/2017/QĐ-UBND như sau:', stated)])
        self.assertEqual((relation['resolution_status'], relation['vi_tri'], relation['kem_theo']), ('validated', ['khoản 7 Điều 3'], True))

    def test_b_a_catalogue_name_is_no_act(self):
        text = 'Công bố Danh mục văn bản cần đình chỉ thi hành, ngưng hiệu lực, sửa đổi, bổ sung, thay thế, bãi bỏ của Quyết định số 12/2019/QĐ-UBND.'
        act = {'action': 'bai-bo', 'target_document': '12/2019/QĐ-UBND', 'target_section': 'khong_ap_dung', 'target_text': [],
               'evidence': 'Danh mục văn bản cần đình chỉ thi hành, ngưng hiệu lực, sửa đổi, bổ sung, thay thế, bãi bỏ'}
        relations, rejected = kept([row(text, act)])
        self.assertEqual((relations, rejected[0]['reason']), ([], 'ten_danh_muc'))

    def test_amending_laws_in_a_long_history_list_are_no_targets(self):
        # 26/10/2026: the end of a long list after "đã được sửa đổi … theo" lay beyond the 80-character window and became a target.
        text = ('Sửa đổi, bổ sung mục 6.4 Phụ lục số 01 ban hành kèm theo Luật Phí và lệ phí số 97/2015/QH13 đã được sửa đổi, bổ sung một số '
                'điều theo Luật số 09/2017/QH14, Luật số 23/2018/QH14, Luật số 72/2020/QH14, Luật số 16/2023/QH15, Luật số 33/2024/QH15 '
                'và Luật số 89/2025/QH15 như sau:')
        act = {'action': 'sua-doi', 'target_section': 'kem_theo', 'target_text': ['mục 6.4 Phụ lục số 01'],
               'evidence': 'Sửa đổi, bổ sung mục 6.4 Phụ lục số 01 ban hành kèm theo Luật Phí và lệ phí'}
        relations, rejected = kept([row(text, dict(act, target_document='89/2025/QH15'))])
        self.assertEqual((relations, rejected[0]['reason']), ([], 'ghi_chu_lich_su'))
        relations, _ = kept([row(text, dict(act, target_document='97/2015/QH13'))])
        self.assertEqual({r['target_doc'] for r in relations}, {'97/2015/QH13'})
        # A provision in each item of the list keeps the list going; a new act ends it.
        listed = ('Sửa đổi khoản 1 Điều 41 Thông tư số 12/2017/TT-BGTVT (đã được sửa đổi, bổ sung tại khoản 23 Điều 1 Thông tư số '
                  '38/2019/TT-BGTVT và khoản 1 Điều 12 Thông tư số 05/2023/TT-BGTVT) như sau:')
        self.assertTrue(only_in_history(listed, number_key('05/2023/TT-BGTVT')))
        ended = ('Bãi bỏ Quyết định số 12/2020/QĐ-UBND đã được sửa đổi tại Quyết định số 30/2021/QĐ-UBND và bãi bỏ khoản 2 Điều 5 '
                 'Quyết định số 30/2021/QĐ-UBND.')
        self.assertFalse(only_in_history(ended, number_key('30/2021/QĐ-UBND')))

    def test_positions_outside_articles_become_their_appendix(self):
        # 26/10/2026: a part named by name, a Mục or Phần of a plan, a row of a catalogue: the appendix; article positions stay.
        named = {'vi_tri': [], 'doi_tuong': '14 thủ tục hành chính tại Mục I Phụ lục II'}
        appendix_scope(named)
        self.assertEqual((named['vi_tri'], named['doi_tuong']), (['Phụ lục II'], '14 thủ tục hành chính tại Mục I Phụ lục II'))
        mixed = {'vi_tri': ['khoản 2 Điều 5', 'Mục II Phần B Phụ lục I', 'Mục I']}
        appendix_scope(mixed)
        self.assertEqual(mixed['vi_tri'], ['khoản 2 Điều 5', 'Phụ lục I', 'Phụ lục'])
        whole = {'vi_tri': ['toàn bộ']}
        appendix_scope(whole)
        self.assertEqual(whole['vi_tri'], ['toàn bộ'])
        # 27/10/2026: a part no appendix holds keeps its name and no position (676559: "một số điều của các Thông tư …").
        other = {'vi_tri': [], 'doi_tuong': 'một số điều của các Thông tư trong lĩnh vực lâm nghiệp', 'source_path': 'Mục III'}
        appendix_scope(other)
        self.assertEqual((other['vi_tri'], other['doi_tuong']), ([], 'một số điều của các Thông tư trong lĩnh vực lâm nghiệp'))
        procedure = {'vi_tri': [], 'doi_tuong': 'các thủ tục hành chính tương ứng', 'source_path': 'Điều 2'}
        appendix_scope(procedure)
        self.assertEqual(procedure['vi_tri'], ['Phụ lục'])
        # 27/10/2026: body positions of the contract stay; a moved position keeps its words on the edge, and so do wording pairs.
        body = {'vi_tri': ['tên văn bản', 'tên Mục 1', 'Mục 2 Chương III']}
        appendix_scope(body)
        self.assertEqual(body['vi_tri'], ['tên văn bản', 'tên Mục 1', 'Mục 2 Chương III'])
        numbered = {'vi_tri': ['Mục 89']}  # 683435: a Mục on its own is a part of an appendix, also when numbered
        appendix_scope(numbered)
        self.assertEqual((numbered['vi_tri'], numbered['_chi_tiet']), (['Phụ lục'], {'Phụ lục': 'Mục 89'}))
        rows = {'vi_tri': ['Mục I Phụ lục I', 'Mục IV'], '_chi_tiet': {'Mục I Phụ lục I': 'số thứ tự 01'},
                'cum_tu': [{'cum_tu_cu': 'A', 'cum_tu_moi': 'B', 'vi_tri': ['Mục IV']}]}
        appendix_scope(rows)
        self.assertEqual(rows['vi_tri'], ['Phụ lục I', 'Phụ lục'])
        self.assertEqual(rows['_chi_tiet'], {'Phụ lục I': 'Mục I Phụ lục I; số thứ tự 01', 'Phụ lục': 'Mục IV'})
        self.assertEqual(rows['cum_tu'][0]['vi_tri'], ['Phụ lục'])
        appendix_scope(rows)  # a second pass changes nothing
        self.assertEqual((rows['vi_tri'], rows['_chi_tiet']['Phụ lục']), (['Phụ lục I', 'Phụ lục'], 'Mục IV'))

    def test_a_note_cut_out_of_the_quote_still_counts(self):
        # 27/10/2026 (675210): the governing sentence was cut after the note; the unit's own text decides.
        unit = ('Sửa đổi, bổ sung mục 6.4 Phụ lục số 01 ban hành kèm theo Luật Phí và lệ phí số 97/2015/QH13 đã được sửa đổi, bổ sung '
                'một số điều theo Luật số 09/2017/QH14, Luật số 33/2024/QH15, Luật số 35/2024/QH15 và Luật số 89/2025/QH15 như sau:')
        cut = 'Luật số 33/2024/QH15, Luật số 35/2024/QH15 và Luật số 89/2025/QH15 như sau:'
        self.assertTrue(only_noted(unit, cut, number_key('35/2024/QH15')))
        self.assertFalse(only_noted(unit, cut, number_key('97/2015/QH13')))
        # A part of a long list keeps the lead but loses the note: its sentence is still the unit's own text.
        part = 'Sửa đổi, bổ sung mục 6.4 Phụ lục số 01 ban hành kèm theo Luật số 35/2024/QH15 và Luật số 89/2025/QH15 như sau:'
        self.assertFalse(only_noted(unit, part, number_key('35/2024/QH15')))
        self.assertTrue(only_noted(unit, part, number_key('35/2024/QH15'), part=part))
        self.assertFalse(only_noted(unit, part, number_key('97/2015/QH13'), part=part))
        # A lead elsewhere that acts on the document named in the note keeps it.
        item = 'a) Quyết định số 12/2020/QĐ-UBND (đã được sửa đổi bởi Quyết định số 30/2021/QĐ-UBND)'
        self.assertFalse(only_noted(item, 'Bãi bỏ Quyết định số 30/2021/QĐ-UBND và các văn bản sau:', number_key('30/2021/QĐ-UBND')))

    def test_quotes_and_new_wording_and_invented_quotes(self):
        text = 'Khoản 2 được sửa đổi như sau: “2. Bãi bỏ Quyết định số 99/2010/QĐ-UBND.”'
        quoted = {'action': 'bai-bo', 'target_document': '99/2010/QĐ-UBND', 'target_section': 'khong_ap_dung', 'target_text': [],
                  'evidence': 'Bãi bỏ Quyết định số 99/2010/QĐ-UBND'}
        self.assertEqual(kept([row(text, quoted)])[1][0]['reason'], 'trong_noi_dung_moi')
        # The act stands inside the inserted wording, whatever the quote says (21/10/2026: the form of the quote decides nothing).
        invented = dict(quoted, evidence='Bãi bỏ toàn bộ Quyết định số 99/2010/QĐ-UBND kể từ ngày ký')
        self.assertEqual(kept([row(text, invented)])[1][0]['reason'], 'trong_noi_dung_moi')
        # A real act with a quote the model rewrote: the code finds the evidence in the source, verbatim.
        real = 'Bãi bỏ Quyết định số 99/2010/QĐ-UBND ngày 05/3/2010 của Ủy ban nhân dân tỉnh.'
        (relation,), _ = kept([row(real, invented)])
        self.assertEqual((relation['resolution_status'], relation['evidence']), ('validated', real))

    def test_target_and_position_must_be_in_the_source(self):
        text = 'Bãi bỏ khoản 3 Điều 5.'
        act = {'action': 'bai-bo', 'target_document': '28/2017/QĐ-UBND', 'target_section': 'quyet_dinh', 'target_text': ['khoản 3 Điều 5'],
               'evidence': 'Bãi bỏ khoản 3 Điều 5'}
        (relation,), _ = kept([row(text, act, heading='Sửa đổi Quyết định số 28/2017/QĐ-UBND')])
        self.assertEqual(relation['resolution_status'], 'validated')
        (relation,), _ = kept([row(text, dict(act, target_document='30/2018/QĐ-UBND'))])
        self.assertEqual(relation['resolution_reason'], 'van_ban_dich_khong_co_trong_nguon')
        (relation,), _ = kept([row(text, dict(act, target_text=['khoản 4 Điều 5']), heading='Sửa đổi Quyết định số 28/2017/QĐ-UBND')])
        self.assertEqual(relation['resolution_reason'], 'vi_tri_khong_co_trong_nguon')

    def test_whole_document_and_missing_position(self):
        text = 'Quyết định này thay thế Quyết định số 42/2018/QĐ-UBND ngày 08/11/2018.'
        act = {'action': 'thay-the', 'target_document': '42/2018/QĐ-UBND', 'target_section': 'khong_ap_dung', 'target_text': [],
               'evidence': 'thay thế Quyết định số 42/2018/QĐ-UBND'}
        (relation,), _ = kept([row(text, act)])
        self.assertEqual((relation['resolution_status'], relation['vi_tri']), ('validated', ['toàn bộ']))
        # The model names an act the quote does not state: rejected, not renamed by rule (the prompt defines the acts, 19/10/2026).
        misnamed = dict(act, action='sua-doi', target_section='quyet_dinh', evidence='Quyết định này thay thế')
        relations, rejected = kept([row(text, misnamed)])
        self.assertEqual(rejected[0]['reason'], 'chua_co_cau_thuc_hien')
        basis = 'Căn cứ Quyết định số 42/2018/QĐ-UBND ngày 08/11/2018.'
        relations, rejected = kept([row(basis, dict(act, evidence='Quyết định số 42/2018/QĐ-UBND ngày 08/11/2018'))])
        self.assertEqual(rejected[0]['reason'], 'chua_co_cau_thuc_hien')

    def test_act_stated_before_the_listed_item(self):
        # 664270: "Bãi bỏ Quyết định số 71/…; Quyết định số 2687/… và Quyết định số 169/…": the quote may be a later item.
        text = ('Bãi bỏ Quyết định số 71/QĐ-BTP ngày 10 tháng 01 năm 2025 của Bộ trưởng Bộ Tư pháp; Quyết định số 2687/QĐ-BTP ngày 09 tháng 11 '
                'năm 2023 của Bộ trưởng Bộ Tư pháp.')
        act = {'action': 'bai-bo', 'target_document': '2687/QĐ-BTP', 'target_section': 'khong_ap_dung', 'target_text': [],
               'evidence': 'Quyết định số 2687/QĐ-BTP ngày 09 tháng 11 năm 2023 của Bộ trưởng Bộ Tư pháp'}
        (relation,), _ = kept([row(text, act)])
        self.assertEqual((relation['action'], relation['resolution_status']), ('bai-bo', 'validated'))

    def test_expiry_is_a_repeal_and_an_announced_list_is_no_act(self):
        # 634166: "… hết hiệu lực thi hành" stated by the document is bai-bo (prompt definition); the quote carries it.
        text = ('Phụ lục kèm theo Quyết định số 2401/QĐ-UBND ngày 24/10/2022 của Chủ tịch UBND tỉnh hết hiệu lực thi hành kể từ ngày '
                'Quyết định này có hiệu lực thi hành.')
        act = {'action': 'bai-bo', 'target_document': '2401/QĐ-UBND', 'target_section': 'kem_theo', 'target_text': ['Phụ lục'],
               'evidence': text}
        (relation,), _ = kept([row(text, act)])
        self.assertEqual((relation['vi_tri'], relation['resolution_status']), (['Phụ lục'], 'validated'))
        # 542598: publishing a list of abolished procedures names no document; the title's 307 is not the act's target.
        text = 'Công bố kèm theo Quyết định này Danh mục thủ tục hành chính bị bãi bỏ (04 thủ tục cấp tỉnh) lĩnh vực môi trường.'
        act = {'action': 'bai-bo', 'target_document': '307/QĐ-UBND', 'target_section': 'khong_ro', 'target_text': [], 'evidence': text}
        relations, rejected = kept([row(text, act, heading='Sửa đổi Quyết định số 307/QĐ-UBND')])
        self.assertEqual((relations, rejected[0]['reason']), ([], 'cong_bo_danh_muc'))


class EdgeDecision(unittest.TestCase):
    def test_no_position_means_no_edge_whichever_path(self):
        from vbpl_v3.convert import settle
        base = {'source_path': 'Điều 1 Khoản 2', 'scope': 'chưa xác định', 'vi_tri': []}
        # llm mode: a rule relation the QA kept arrives as validated; without a position it waits for review.
        rule = settle({**base, 'extraction': 'rules', 'resolution_status': 'validated', 'resolution_reason': None})
        self.assertEqual((rule['cap_quan_he'], rule['resolution_status'], rule['resolution_reason']),
                         ('chua_xac_dinh', 'unresolved', 'vi_tri_chua_xac_dinh'))
        placed = settle({**base, 'scope': 'khoản 2 Điều 3', 'vi_tri': ['khoản 2 Điều 3']})
        self.assertEqual((placed['cap_quan_he'], placed['resolution_status'], placed['extraction']), ('vi_tri', 'validated', 'rules'))
        held = settle({**base, 'scope': 'khoản 7 Điều 3', 'vi_tri': ['khoản 7 Điều 3'], 'resolution_status': 'unresolved',
                       'resolution_reason': 'phan_kem_theo_chua_ro'})
        self.assertEqual((held['resolution_status'], held['resolution_reason']), ('unresolved', 'phan_kem_theo_chua_ro'))


class Extraction(unittest.TestCase):
    def test_one_call_per_article_with_its_context(self):
        parsed, _ = parse('Điều 1. Sửa đổi, bổ sung một số điều của Quy định ban hành kèm theo Quyết định số 28/2017/QĐ-UBND\n'
                          '1. Sửa đổi khoản 7 Điều 3 như sau: “7. ' + 'Nội dung mới rất dài. ' * 30 + '”\n2. Bãi bỏ Điều 9.\n'
                          'Điều 2. Hiệu lực\nQuyết định này có hiệu lực kể từ ngày ký.')
        sent = []

        def caller(prompt, text, folder, **options):
            payload = json.loads(text)
            sent.append(payload)
            units = [{'source_path': u['source_path'], 'acts': []} for u in payload['don_vi']]
            units[0]['acts'] = [{'action': 'sua-doi', 'performed': True, 'target_document': '28/2017/QĐ-UBND', 'target_from': 'ten_dieu',
                                 'target_section': 'kem_theo', 'target_text': ['khoản 7 Điều 3'], 'target_part': '',
                                 'evidence': 'Sửa đổi khoản 7 Điều 3'}]
            return json.dumps({'units': units}), {}
        with tempfile.TemporaryDirectory() as folder:
            rows, _ = extract(1, META, parsed, Path(folder), caller=caller)
            extract(1, META, parsed, Path(folder), caller=caller)  # cached: no second call
        self.assertEqual(len([p for p in sent if p['don_vi'][0]['source_path'] != 'Phần đầu']), 1)
        article = next(p for p in sent if p['don_vi'][0]['source_path'] != 'Phần đầu')
        self.assertIn('Quyết định số 28/2017/QĐ-UBND', article['ten_dieu'])
        self.assertTrue(article['don_vi'][0]['noi_dung'].endswith('…”'))
        relation = resolve_row(rows[0])
        self.assertEqual((relation['vi_tri'], relation['kem_theo'], relation['target_doc']), (['khoản 7 Điều 3'], True, '28/2017/QĐ-UBND'))

    def test_quotes_are_shortened(self):
        self.assertEqual(shorten_quotes('A “ngắn” B'), 'A “ngắn” B')
        self.assertTrue(shorten_quotes('“' + 'x' * 400 + '”').endswith('…”'))


class DevRoundOne(unittest.TestCase):
    """Errors seen on the dev set (15/10/2026), as general rules."""

    def test_quote_running_into_new_wording(self):
        text = 'Sửa đổi khoản 4 Điều 3 như sau:\n“4. Đối với đất nông nghiệp là đất vườn.”'
        act = {'action': 'sua-doi', 'target_document': '14/2014/QĐ-UBND', 'target_section': 'kem_theo', 'target_text': ['khoản 4 Điều 3'],
               'evidence': 'Sửa đổi khoản 4 Điều 3 như sau:\n\n“4. Đối với đất nông nghiệp'}
        (relation,), _ = kept([row(text, act, heading='Sửa đổi Quy định ban hành kèm theo Quyết định số 14/2014/QĐ-UBND')])
        self.assertEqual((relation['resolution_status'], relation['vi_tri']), ('validated', ['khoản 4 Điều 3']))

    def test_position_read_from_the_quote(self):
        text = 'Khoản 3 Điều 5 được sửa đổi, bổ sung như sau: “3. Mới.”'
        act = {'action': 'sua-doi', 'target_document': '38/2017/QĐ-UBND', 'target_section': 'quyet_dinh', 'target_text': [],
               'evidence': 'Khoản 3 Điều 5 được sửa đổi, bổ sung như sau:'}
        relations, _ = kept([row(text, act, heading='Sửa đổi Quyết định số 38/2017/QĐ-UBND')])
        # "được sửa đổi, bổ sung" is two acts (settled 14/10/2026); the model gave one, the other is added.
        self.assertEqual(sorted((r['action'], tuple(r['vi_tri'])) for r in relations),
                         [('bo-sung', ('khoản 3 Điều 5',)), ('sua-doi', ('khoản 3 Điều 5',))])

    def test_no_document_itself_and_citations(self):
        text = 'Triển khai thực hiện theo hướng dẫn tại Quyết định số 15/2020/QĐ-UBND này. Bãi bỏ các quy định trái với Quyết định này.'
        own = {'action': 'huong-dan', 'target_document': '15/2020/QĐ-UBND', 'target_section': 'khong_ap_dung', 'target_text': [],
               'evidence': 'thực hiện theo hướng dẫn tại Quyết định số 15/2020/QĐ-UBND'}
        self.assertEqual(kept([row(text, own)])[1][0]['reason'], 'chinh_van_ban_nguon')
        none = {'action': 'bai-bo', 'target_document': 'các quy định trái với Quyết định này', 'target_section': 'khong_ap_dung',
                'target_text': [], 'evidence': 'Bãi bỏ các quy định trái với Quyết định này'}
        self.assertEqual(kept([row(text, none)])[1][0]['reason'], 'khong_co_van_ban_dich')
        cited = {'action': 'huong-dan', 'target_document': '96/2020/NĐ-CP', 'target_section': 'khong_ap_dung', 'target_text': [],
                 'evidence': 'thực hiện theo hướng dẫn tại Nghị định số 96/2020/NĐ-CP'}
        self.assertEqual(kept([row('Xử phạt thực hiện theo hướng dẫn tại Nghị định số 96/2020/NĐ-CP.', cited)])[1][0]['reason'],
                         'dan_chieu_khong_phai_huong_dan')
        guides = dict(cited, evidence='Thông tư này hướng dẫn Nghị định số 96/2020/NĐ-CP')
        (relation,), _ = kept([row('Thông tư này hướng dẫn Nghị định số 96/2020/NĐ-CP về xử phạt.', guides)])
        self.assertEqual((relation['resolution_status'], relation['scope']), ('validated', 'toàn bộ'))
