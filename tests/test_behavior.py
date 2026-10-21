"""Behavior of the layers after the model (resolver, validation, scope) by family of writing (docs/08 §8.11, 21/10/2026).

A family is one legal fact written in several ways. The layers must give the same impacts for every way. The model's answers are
built from the units the parser makes, as a model reading them would answer: the act on the document the unit names, quoted with
the unit's own words. No document ID appears in the code under test; a real case only lends its wording to a test.
"""

import unittest

from vbpl_v3.convert import one_per_position, rows_into_articles, tidy_positions
from vbpl_v3.extract import table_units, units
from vbpl_v3.governance import acts_on, pieces
from vbpl_v3.relations import document_refs
from vbpl_v3.resolver import resolve_row
from vbpl_v3.structure import parse
from vbpl_v3.text import number_key
from vbpl_v3.validate import distinct, validate

DOC = {'so_hieu': '15/2024/QĐ-UBND', 'loai': 'Quyết định', 'ten': 'QUYẾT ĐỊNH BÃI BỎ MỘT SỐ VĂN BẢN'}
HEAD = 'QUYẾT ĐỊNH:\n'
TAIL = 'Điều 2. Quyết định này có hiệu lực kể từ ngày ký.\nNơi nhận:\n- Như Điều 2;\n- Lưu: VT.\nTM. ỦY BAN NHÂN DÂN\nCHỦ TỊCH\nNguyễn Văn A\n'
A = 'Quyết định số 12/2010/QĐ-UBND ngày 01/01/2010 của Ủy ban nhân dân tỉnh về quản lý phí'
B = 'Quyết định số 34/2012/QĐ-UBND ngày 02/02/2012 của Ủy ban nhân dân tỉnh về giá đất'


def head_document(text):
    """number_key of the first document a line names: the document a model reads as the item's target."""
    found = document_refs(text)
    return number_key(found[0].group()) if found else ''


def answers(text, action, targets=None, part='', positions=None, section='khong_ap_dung'):
    """The rows a model would give for this text: for each unit, the act on each document it names first (or on targets)."""
    parsed, _ = parse(text)
    rows = []
    for _, context, items in units(parsed) + table_units(parsed):
        context = {**context, 'van_ban': DOC, 'phan_dau': ''}
        for unit in items:
            listed = unit.get('danh_sach_kem_theo') or ''
            # An article without clauses may hold its whole sentence in its heading ("Điều 1. Bãi bỏ Quyết định số …"); the model
            # reads the heading with the unit.
            own = unit['noi_dung'] if document_refs(unit['noi_dung']) else context.get('ten_dieu') or ''
            seen = own + '\n' + listed
            if listed:
                named = [head_document(line) for line in listed.split('\n') if line.strip()]
            elif len(document_refs(own)) > 1 and not unit['cau_dan'] and ' Khoản ' not in unit['source_path']:
                named = [number_key(m.group()) for m in document_refs(own)]  # one sentence acting on several documents
            else:
                named = [head_document(own)]
            for target in targets or named:
                if not target:
                    continue
                number = next((m.group() for m in document_refs(seen) if number_key(m.group()) == target), target)
                rows.append({'source_path': unit['source_path'], 'action': action, 'performed': True, 'chu_the': 'van_ban_nay',
                             'van_ban_chua_noi_dung': number, 'target_document': number, 'target_from': 'don_vi',
                             'target_section': section, 'target_text': positions or [], 'target_part': part,
                             'evidence': (unit['noi_dung'] or own)[:200], '_unit': unit, '_context': context})
    return rows


def kept_relations(text, action, **options):
    """The relations kept after validation and after the rows of a list are given to the article acting on it (convert)."""
    kept, _ = validate(answers(text, action, **options), resolve_row)
    return rows_into_articles(kept, parse(text)[0])


def impacts(text, action, **options):
    """{(action, target, vi_tri, chi_tiet_vi_tri)} of the validated relations, after the scope steps of convert."""
    kept = kept_relations(text, action, **options)
    records = [{'_id': f'x_{n}', '_source': {**r, 'scope': r.get('scope') or ''}} for n, r in enumerate(kept)]
    records = one_per_position(tidy_positions(records), 'x')
    return {(r['_source']['action'], number_key(r['_source']['target_doc']), tuple(r['_source'].get('vi_tri') or []),
             r['_source'].get('chi_tiet_vi_tri')) for r in records if r['_source']['resolution_status'] == 'validated'}


class ListUnderLead(unittest.TestCase):
    """A list item that names a document and no verb takes the act of the lead that opens the list."""

    WHOLE = {('bai-bo', '12/2010/qđ-ubnd', ('toàn bộ',), None), ('bai-bo', '34/2012/qđ-ubnd', ('toàn bộ',), None)}

    def test_one_sentence(self):
        self.assertEqual(impacts(HEAD + f'Điều 1. Bãi bỏ {A}; {B}.\n' + TAIL, 'bai-bo'), self.WHOLE)

    def test_clauses_under_the_article_lead(self):
        text = HEAD + f'Điều 1. Bãi bỏ 02 văn bản quy phạm pháp luật của Ủy ban nhân dân tỉnh, gồm:\n1. {A}.\n2. {B}.\n' + TAIL
        self.assertEqual(impacts(text, 'bai-bo'), self.WHOLE)

    def test_points_under_the_clause_lead(self):
        text = HEAD + f'Điều 1. Bãi bỏ văn bản\n1. Bãi bỏ các quyết định sau:\na) {A};\nb) {B}.\n2. Giao Sở Tư pháp theo dõi.\n' + TAIL
        self.assertEqual(impacts(text, 'bai-bo'), self.WHOLE)

    def test_subject_first(self):
        text = HEAD + f'Điều 1. Các Quyết định sau hết hiệu lực kể từ ngày Quyết định này có hiệu lực:\n1. {A}.\n2. {B}.\n' + TAIL
        self.assertEqual(impacts(text, 'bai-bo'), self.WHOLE)

    def test_list_in_an_attachment(self):
        text = (HEAD + 'Điều 1. Bãi bỏ các văn bản tại Phụ lục I kèm theo Quyết định này.\n' + TAIL +
                'PHỤ LỤC I\nDANH MỤC VĂN BẢN BÃI BỎ\n(Kèm theo Quyết định số 15/2024/QĐ-UBND)\n| STT | Tên văn bản | Ghi chú |\n'
                f'| 1 | {A} | |\n| 2 | {B} | |\n')
        self.assertEqual(impacts(text, 'bai-bo'), self.WHOLE)

    def test_new_wording_is_no_list(self):
        # A lead that names one provision introduces its new wording: the items under it are that wording.
        text = HEAD + f'Điều 1. Sửa đổi khoản 2 Điều 3 Quyết định số 99/2020/QĐ-UBND như sau:\n1. {A}.\n2. {B}.\n' + TAIL
        self.assertEqual(impacts(text, 'bai-bo'), set())


class NotPerformed(unittest.TestCase):
    """The word of an act does not make an act: a proposal, a plan, a history note."""

    def test_history_note(self):
        text = HEAD + 'Điều 1. Sửa đổi khoản 2 Điều 3 Quyết định số 99/2020/QĐ-UBND đã được sửa đổi, bổ sung tại Quyết định số 11/2021/QĐ-UBND.\n' + TAIL
        found = impacts(text, 'sua-doi', targets=['11/2021/qđ-ubnd'], positions=['khoản 2 Điều 3'], section='quyet_dinh')
        self.assertEqual(found, set())

    def test_plan_rows(self):
        text = (HEAD + 'Điều 1. Ban hành kèm theo Quyết định này Kế hoạch rà soát văn bản.\n' + TAIL +
                'PHỤ LỤC\nDANH MỤC VĂN BẢN CẦN SỬA ĐỔI, BỔ SUNG\n| STT | Tên văn bản | Thời hạn thực hiện |\n'
                f'| 1 | Sửa đổi {A} | Quý IV |\n')
        self.assertEqual(impacts(text, 'sua-doi', section='khong_ro'), set())


class VerbOfTheAct(unittest.TestCase):
    """The act stated is the act read: a word of another act's verb ("bỏ" of "hủy bỏ") states no other act."""

    TEXT = (HEAD + 'Điều 1. Hủy bỏ 02 công trình, dự án đã được thông qua tại các Nghị quyết sau:\n'
            '1. Nghị quyết số 20/NQ-HĐND ngày 13/7/2018 của Hội đồng nhân dân tỉnh.\n'
            '2. Nghị quyết số 28/NQ-HĐND ngày 08/12/2019 của Hội đồng nhân dân tỉnh.\n' + TAIL)

    def test_cancel_is_no_repeal(self):
        self.assertEqual(impacts(self.TEXT, 'bai-bo'), set())
        self.assertEqual({(a, t) for a, t, _, _ in impacts(self.TEXT, 'huy-bo')},
                         {('huy-bo', '20/nq-hđnd'), ('huy-bo', '28/nq-hđnd')})


class NumberAsPrinted(unittest.TestCase):
    """A number is the same number with spaces typed inside it ("32/2012/QĐ- U BND")."""

    def test_row_with_spaces_inside_the_number(self):
        text = (HEAD + 'Điều 1. Nay bãi bỏ 02 văn bản (Danh mục đính kèm) của Ủy ban nhân dân tỉnh.\n' + TAIL +
                'DANH MỤC\nVĂN BẢN BÃI BỎ\n(Kèm theo Quyết định số 15/2024/QĐ-UBND)\n'
                '| STT | Tên loại văn bản | Số, ký hiệu; ngày, tháng, năm ban hành | Tên gọi của văn bản |\n'
                '| 1 | Quyết định | 32/2012/QĐ- U BND ngày 30/7/2012 | Về việc thu phí trông giữ xe |\n'
                '| 2 | Quyết định | 59/2012/QĐ- U BND ngày 20/12/2012 | Về việc sửa đổi Quyết định số 32/2012/QĐ- U BND |\n')
        found = impacts(text, 'bai-bo', targets=['32/2012/QĐ-UBND', '59/2012/QĐ-UBND'])
        self.assertEqual(found, {('bai-bo', '32/2012/qđ-ubnd', ('toàn bộ',), None), ('bai-bo', '59/2012/qđ-ubnd', ('toàn bộ',), None)})


class EvidencePieces(unittest.TestCase):
    def test_pieces_start_at_a_word(self):
        # The model joined the article lead and the item: each piece is a whole stretch of one field, not cut inside a word.
        row = {'_unit': {'noi_dung': 'Quyết định số 3155/QĐ-UBND ngày 26 tháng 10 năm 2009 về việc thành lập Trung tâm Dạy nghề.',
                         'cau_dan': ''}, '_context': {'ten_dieu': 'Bãi bỏ các Quyết định sau:'}, 'source_path': 'Điều 1 Khoản 3'}
        found = pieces('Bãi bỏ các Quyết định sau: Quyết định số 3155/QĐ-UBND ngày 26 tháng 10 năm 2009', row, {'don_vi', 'ten_dieu'})
        self.assertEqual([p['text'] for p in found], ['Bãi bỏ các Quyết định sau:', 'Quyết định số 3155/QĐ-UBND ngày 26 tháng 10 năm 2009'])


class UnnumberedAppendix(unittest.TestCase):
    def test_part_of_an_unnumbered_appendix(self):
        # "Phần I Phụ lục" has no position of the contract: the holder is unknown, the document is still converted.
        from vbpl_v3.relations import appendix_of
        self.assertIsNone(appendix_of('Bãi bỏ các thủ tục hành chính tại Phần I Phụ lục ban hành kèm theo Quyết định số 12/2026/QĐ-UBND'))
        self.assertEqual(appendix_of('tại Phụ lục V ban hành kèm theo Nghị định số 37/2024/NĐ-CP'), 'Phụ lục V')


class QuotedWording(unittest.TestCase):
    def test_act_inside_inserted_wording(self):
        text = HEAD + f'Điều 1. Khoản 2 Điều 3 Quyết định số 99/2020/QĐ-UBND được sửa đổi như sau:\n“2. Bãi bỏ {A}.”\n' + TAIL
        self.assertEqual(impacts(text, 'bai-bo', targets=['12/2010/qđ-ubnd']), set())

    def test_phrases_in_quotes(self):
        text = HEAD + 'Điều 1. Thay cụm từ “Sở Nội vụ” bằng cụm từ “Sở Tư pháp” tại khoản 2 Điều 3 Quyết định số 99/2020/QĐ-UBND.\n' + TAIL
        found = impacts(text, 'thay-cum-tu', positions=['khoản 2 Điều 3'], section='quyet_dinh')
        self.assertEqual({(a, t, v) for a, t, v, _ in found}, {('thay-cum-tu', '99/2020/qđ-ubnd', ('khoản 2 Điều 3',))})


class ObjectOfTheAct(unittest.TestCase):
    """An item acts on the document it names first; provisions and documents in that document's name are its name."""

    def test_name_of_the_listed_document(self):
        item = 'Quyết định số 12/2010/QĐ-UBND ngày 01/01/2010 về việc sửa đổi khoản 2 Điều 3 của Quyết định số 05/2008/QĐ-UBND'
        text = HEAD + f'Điều 1. Bãi bỏ các văn bản sau:\n1. {item}.\n2. {B}.\n' + TAIL
        # The model may also give the act on the document inside the name, and a position read from the name.
        found = impacts(text, 'bai-bo', positions=['khoản 2 Điều 3'])
        self.assertEqual(found, ListUnderLead.WHOLE)
        found = impacts(text, 'bai-bo', targets=['05/2008/qđ-ubnd'])
        self.assertEqual(found, set())

    def test_provision_named_as_the_item(self):
        text = HEAD + f'Điều 1. Bãi bỏ các quy định sau:\n1. Khoản 2 Điều 3 {A}.\n2. Điều 5 {B}.\n' + TAIL
        found = impacts(text, 'bai-bo', section='quyet_dinh')
        self.assertEqual({(a, t, v) for a, t, v, _ in found},
                         {('bai-bo', '12/2010/qđ-ubnd', ('khoản 2 Điều 3',)), ('bai-bo', '34/2012/qđ-ubnd', ('Điều 5',))})

    def test_whole_named_documents_keep_their_scope(self):
        # Items whose names describe what the document did: each listed document ends as a whole, never "in part".
        text = (HEAD + 'Điều 1. Thu hồi và hủy bỏ hiệu lực các Quyết định công nhận phòng thí nghiệm sau:\n'
                '1. Quyết định số 109/QĐ-BXD ngày 01/02/2012 công nhận phòng thí nghiệm LAS-XD 101.\n'
                '2. Quyết định số 123/QĐ-BXD ngày 03/02/2012 công nhận phòng thí nghiệm LAS-XD 102.\n' + TAIL)
        found = impacts(text, 'huy-bo', part='phòng thí nghiệm LAS-XD')
        self.assertEqual(found, {('huy-bo', '109/qđ-bxd', ('toàn bộ',), None), ('huy-bo', '123/qđ-bxd', ('toàn bộ',), None)})


class ListedTogether(unittest.TestCase):
    """Documents joined in one item ("X ngày … và Y ngày …") are all objects of the item; the article acting on the list acts on each."""

    TEXT = (HEAD + 'Điều 1. Thu hồi và hủy bỏ hiệu lực các Quyết định công nhận phòng thí nghiệm của các phòng thí nghiệm sau '
            '(có danh sách kèm theo).\n' + TAIL +
            'DANH SÁCH\n(Kèm theo Quyết định số 15/2024/QĐ-UBND)\n'
            '| STT | Tên phòng thí nghiệm | Thu hồi, hủy bỏ Quyết định số: |\n'
            '| 1 | Phòng thí nghiệm A | 1307/QĐ-BXD ngày 29/10/2008 và 91/QĐ-BXD ngày 05/3/2009 |\n'
            '| 2 | Phòng thí nghiệm B | 621/QĐ-BXD ngày 24/12/2010 |\n')

    def test_joined_documents_of_a_row(self):
        found = impacts(self.TEXT, 'huy-bo', targets=['1307/QĐ-BXD', '91/QĐ-BXD', '621/QĐ-BXD'])
        self.assertEqual(found, {('huy-bo', '1307/qđ-bxd', ('toàn bộ',), None), ('huy-bo', '91/qđ-bxd', ('toàn bộ',), None),
                                 ('huy-bo', '621/qđ-bxd', ('toàn bộ',), None)})
        kept = kept_relations(self.TEXT, 'huy-bo', targets=['1307/QĐ-BXD', '91/QĐ-BXD', '621/QĐ-BXD'])
        self.assertEqual({r['source_path'] for r in kept if r['resolution_status'] == 'validated'}, {'Điều 1'})

    def test_joined_or_named(self):
        self.assertTrue(acts_on('1307/QĐ-BXD ngày 29/10/2008 và 91/QĐ-BXD ngày 05/3/2009', '91/QĐ-BXD'))
        self.assertTrue(acts_on(f'{A}; {B}', '34/2012/QĐ-UBND'))
        self.assertFalse(acts_on('Quyết định số 12/2010/QĐ-UBND ngày 01/01/2010 về việc sửa đổi Quyết định số 05/2008/QĐ-UBND', '05/2008/QĐ-UBND'))
        self.assertFalse(acts_on('12/2010/QĐ-UBND | Thay thế Quyết định số 05/2008/QĐ-UBND', '05/2008/QĐ-UBND'))

    def test_this_document_holds_no_changed_content(self):
        # The model may say the listed content is held by this document ("Kèm theo Quyết định số 15/2024/QĐ-UBND"): no edge to itself.
        rows = [{**r, 'van_ban_chua_noi_dung': DOC['so_hieu']} for r in answers(self.TEXT, 'huy-bo', targets=['621/QĐ-BXD'])]
        kept, _ = validate(rows, resolve_row)
        self.assertEqual({number_key(r['target_doc']) for r in kept if r['resolution_status'] == 'validated'}, {'621/qđ-bxd'})


class NumberWithSpaceBeforeSlash(unittest.TestCase):
    def test_row_names_its_document(self):
        text = (HEAD + 'Điều 1. Huỷ bỏ 02 văn bản do Ủy ban nhân dân tỉnh ban hành. (Có Danh sách kèm theo).\n' + TAIL +
                'DANH SÁCH\n(Kèm theo Quyết định số 15/2024/QĐ-UBND)\n| STT | Tên gọi, trích yếu, ngày ban hành văn bản |\n'
                '| 1. | Quyết định số 96 /QĐ-UBND ngày 17/12/2007 của Chủ tịch UBND tỉnh về mức trợ cấp |\n'
                f'| 2. | {B} |\n')
        kept = kept_relations(text, 'huy-bo', targets=['96/QĐ-UBND', '34/2012/QĐ-UBND'])
        self.assertEqual({(r['source_path'], number_key(r['target_doc'])) for r in kept if r['resolution_status'] == 'validated'},
                         {('Điều 1', '96/qđ-ubnd'), ('Điều 1', '34/2012/qđ-ubnd')})


class RowsIntoArticles(unittest.TestCase):
    """A row details the act of the article that acts on its list; a record kept for review never hides a checked one."""

    def record(self, path, status):
        return {'source_path': path, 'action': 'huy-bo', 'target_doc': '621/QĐ-BXD', 'resolution_status': status,
                'source_in_phu_luc': path.startswith('Phụ lục')}

    def merged(self, *records):
        return [(r['source_path'], r['resolution_status']) for r in rows_into_articles(list(records), {'phu_luc': [], 'dieu_luat': []})]

    def test_checked_row_shows_the_article_act(self):
        self.assertEqual(self.merged(self.record('Điều 1', 'unresolved'), self.record('Phụ lục 1 STT 2', 'validated')), [('Điều 1', 'validated')])

    def test_checked_article_keeps_its_act(self):
        self.assertEqual(self.merged(self.record('Điều 1', 'validated'), self.record('Phụ lục 1 STT 2', 'validated')), [('Điều 1', 'validated')])

    def test_one_reading_per_unit_keeps_the_checked_one(self):
        records = [self.record('Điều 1', 'unresolved'), self.record('Điều 1', 'validated')]
        self.assertEqual([r['resolution_status'] for r in distinct(records)], ['validated'])

    def test_both_kept_for_review(self):
        self.assertEqual(self.merged(self.record('Điều 1', 'unresolved'), self.record('Phụ lục 1 STT 2', 'unresolved')), [('Điều 1', 'unresolved')])


class ScopeAndNode(unittest.TestCase):
    """A part without its own node keeps its limit when the edge goes to the node that holds it."""

    def test_form_in_an_appendix(self):
        text = HEAD + 'Điều 1. Sửa đổi Mẫu số 01 Phụ lục I ban hành kèm theo Quyết định số 99/2020/QĐ-UBND.\n' + TAIL
        found = impacts(text, 'sua-doi', positions=['Mẫu số 01 Phụ lục I'], section='kem_theo')
        self.assertEqual(found, {('sua-doi', '99/2020/qđ-ubnd', ('Phụ lục I',), 'Mẫu số 01')})

    def test_paragraph_of_a_clause(self):
        text = HEAD + 'Điều 1. Sửa đổi đoạn 2 khoản 3 Điều 5 Quyết định số 99/2020/QĐ-UBND.\n' + TAIL
        found = impacts(text, 'sua-doi', positions=['đoạn 2 khoản 3 Điều 5'], section='quyet_dinh')
        self.assertEqual(found, {('sua-doi', '99/2020/qđ-ubnd', ('khoản 3 Điều 5',), 'đoạn 2')})

    def test_new_unit_added(self):
        text = HEAD + 'Điều 1. Bổ sung Điều 5a vào sau Điều 5 Quyết định số 99/2020/QĐ-UBND.\n' + TAIL
        found = impacts(text, 'bo-sung', positions=['Điều 5a'], section='quyet_dinh')
        self.assertEqual({(a, t, v) for a, t, v, _ in found}, {('bo-sung', '99/2020/qđ-ubnd', ('Điều 5a',))})


if __name__ == '__main__':
    unittest.main()
