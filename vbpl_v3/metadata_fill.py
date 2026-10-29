"""Catalogue fields the source left empty, read again from the document's own text (29/10/2026).

A field the source has is kept as it is. A field it lacks is read by code from the fixed layout of a Vietnamese document (number line,
place-and-date line, type line, issuer block, signature block), then by the model for what code cannot read: the summary, the
sectors, and any code field the layout did not give. url, pdf_minio_path, pdf_vbpl_id and the signer codes ("Tên:mã") belong to the
crawler, not to the text, and stay as the source has them.
"""

import hashlib
import json
import os
import re

from .llm import validated_json
from .prompts import load
from .structure import NUMBER, SIGNED, TAIL, printed_title, source_lines
from .temporal import DATE, to_date

CODE_FIELDS = ('document_number', 'issuance_date', 'legal_type', 'issuing_authority', 'signers', 'title', 'action')
# The summary comes last: a short field after a long one is not read once the answer is cut.
LLM_FIELDS = ('legal_sectors', 'issuing_authority', 'issuance_date', 'signers', 'document_number', 'legal_type', 'tom_tat')

SECTORS = ['Bộ máy hành chính', 'Thuế - Phí - Lệ Phí', 'Tài chính nhà nước', 'Văn hóa - Xã hội', 'Xuất nhập khẩu', 'Tài nguyên - Môi trường',
           'Xây dựng - Đô thị', 'Thương mại', 'Bất động sản', 'Thể thao - Y tế', 'Giáo dục', 'Giao thông - Vận tải', 'Doanh nghiệp',
           'Lao động - Tiền lương', 'Đầu tư', 'Công nghệ thông tin', 'Lĩnh vực khác', 'Kế toán - Kiểm toán', 'Quyền dân sự',
           'Tiền tệ - Ngân hàng', 'Bảo hiểm', 'Dịch vụ pháp lý', 'Vi phạm hành chính', 'Thủ tục Tố tụng', 'Trách nhiệm hình sự',
           'Sở hữu trí tuệ', 'Chứng khoán', 'Công nghệ- Thực phẩm', 'Xây dựng', 'Công nghiệp', 'Điện - điện tử']
TYPES = ['Quyết định', 'Công văn', 'Nghị quyết', 'Kế hoạch', 'Thông tư', 'Thông báo', 'Chỉ thị', 'Nghị định', 'Văn bản hợp nhất',
         'Thông tư liên tịch', 'Hướng dẫn', 'Công điện', 'Báo cáo', 'Điều ước quốc tế', 'Văn bản khác', 'Sắc lệnh', 'Lệnh', 'Luật',
         'Quy định', 'Pháp lệnh', 'Quy chế', 'Thông tri', 'Bộ luật', 'Hiến pháp', 'Nghị quyết liên tịch', 'Điều lệ']

# The type line under the date line ("QUYẾT ĐỊNH", "NGHỊ QUYẾT LIÊN TỊCH"), longest first.
TYPE_LINE = [(re.compile(r'^' + t.upper().replace(' ', r'\s+') + r'\b'), t) for t in sorted(TYPES, key=len, reverse=True)
             if t not in ('Công văn', 'Văn bản khác', 'Điều ước quốc tế')]
# The body code of a number ("…/QĐ-UBND", "…/2025/NĐ-CP"): its first part names the type.
TYPE_CODE = {'QĐ': 'Quyết định', 'NĐ': 'Nghị định', 'NQ': 'Nghị quyết', 'TT': 'Thông tư', 'TTLT': 'Thông tư liên tịch', 'CT': 'Chỉ thị',
             'KH': 'Kế hoạch', 'TB': 'Thông báo', 'HD': 'Hướng dẫn', 'CĐ': 'Công điện', 'BC': 'Báo cáo', 'VBHN': 'Văn bản hợp nhất',
             'QH': 'Luật', 'L': 'Lệnh', 'PL': 'Pháp lệnh', 'NQLT': 'Nghị quyết liên tịch', 'QC': 'Quy chế', 'TTr': 'Tờ trình'}
NUMBER_LINE = re.compile(r'^(?:Luật\s+|Bộ\s+luật\s+|Pháp\s+lệnh\s+|Lệnh\s+)?(?:Số|SỐ|số)\s*[:.]?\s*(' + NUMBER.pattern + ')')
MOTTO = re.compile(r'^(?:CỘNG\s+H(?:OÀ|ÒA|OA)\s+X[AÃ]\s+HỘI\s+CHỦ\s+NGHĨA\s+VIỆT\s+NAM|ĐẢNG\s+CỘNG\s+SẢN\s+VIỆT\s+NAM)')
PLACE_DATE = re.compile(r'^[^\d\n|]{2,40},\s*ngày\s+' + DATE, re.I)
PASSED = re.compile(r'thông\s+qua\s+ngày\s+' + DATE, re.I)

# A line that starts a body in the issuer block; other lines go on the name above them ("BỘ KHOA HỌC VÀ" / "CÔNG NGHỆ").
BODY = re.compile(r'^(?:BỘ|TỔNG\s+CỤC|CỤC|CHI\s+CỤC|SỞ|VỤ|VIỆN|BAN|ỦY\s+BAN|UỶ\s+BAN|UBND|HĐND|HỘI\s+ĐỒNG|VĂN\s+PHÒNG|THANH\s+TRA|CHÍNH\s+PHỦ'
                  r'|THỦ\s+TƯỚNG|QUỐC\s+HỘI|CHỦ\s+TỊCH\s+NƯỚC|BẢO\s+HIỂM|NGÂN\s+HÀNG|KHO\s+BẠC|TÒA\s+ÁN|TOÀ\s+ÁN|KIỂM\s+TOÁN|TRƯỜNG|PHÒNG|TRUNG\s+TÂM'
                  r'|ĐẢNG\s+ỦY|ĐẢNG\s+UỶ|TỈNH\s+ỦY|TỈNH\s+UỶ|THÀNH\s+ỦY|THÀNH\s+UỶ|TỔNG\s+LIÊN\s+ĐOÀN|LIÊN\s+ĐOÀN|HỌC\s+VIỆN|ĐẠI\s+HỌC|TẬP\s+ĐOÀN'
                  r'|TỔNG\s+CÔNG\s+TY|CÔNG\s+TY|ĐÀI|BỆNH\s+VIỆN|CÔNG\s+AN|BỘ\s+CHỈ\s+HUY|BỘ\s+TƯ\s+LỆNH|ĐOÀN|HỘI)\b')
COUNCIL = re.compile(r'^(?:ỦY|UỶ)\s+BAN\s+NHÂN\s+DÂN$|^UBND$|^HỘI\s+ĐỒNG\s+NHÂN\s+DÂN$|^HĐND$')
LOCALITY = re.compile(r'^(TỈNH|THÀNH\s+PHỐ|TP\.?|HUYỆN|QUẬN|THỊ\s+XÃ|XÃ|PHƯỜNG|THỊ\s+TRẤN|ĐẶC\s+KHU)\s+(.+)$')
PLACE_KIND = {'TỈNH': 'Tỉnh', 'THÀNH PHỐ': 'Thành phố', 'TP.': 'Thành phố', 'TP': 'Thành phố', 'HUYỆN': 'Huyện', 'QUẬN': 'Quận',
              'THỊ XÃ': 'Thị xã', 'XÃ': 'Xã', 'PHƯỜNG': 'Phường', 'THỊ TRẤN': 'Thị trấn', 'ĐẶC KHU': 'Đặc khu'}
# Words kept with a capital inside a body's name.
PROPER = ('Việt Nam', 'Chính phủ', 'Quốc hội', 'Trung ương', 'Nhà nước', 'Đảng', 'Mặt trận Tổ quốc', 'Hồ Chí Minh')

# Vietnamese family names: a name standing alone after a non-capital line starts with one.
FAMILY = set('Nguyễn Trần Lê Phạm Hoàng Huỳnh Phan Vũ Võ Đặng Bùi Đỗ Hồ Ngô Dương Lý Đào Đoàn Vương Trịnh Trương Lâm Phùng Mai Tô Hà Tạ '
             'Lương Đinh Thái Châu Cao Quách Kiều La Lưu Hứa Từ Diệp Triệu Chu Lại Tăng Thân Nông Lò Âu Khúc Kim Mạc Giang Lục Ông Nghiêm '
             'Tôn Lã Tống Doãn Quan Bạch Lạc Mẫn Cù Viên Bế Hầu Ninh Phí Sầm Đàm Đồng Thạch Danh Kha Hàn Vi Ma Lô Đường Khổng Thiều '
             'Trình Ung Giáp Lữ Lường Phó Nhữ Đới Đậu Đái Chế Thiệu Mông Y Ksor Rơ Siu Nay Rcom Kpă Huỳnh Võ Văn Lục'.split())
NOT_NAME = {'Như', 'Lưu', 'Các', 'Bộ', 'Sở', 'Ban', 'Văn', 'Cục', 'Vụ', 'Ủy', 'Uỷ', 'Hội', 'Tổng', 'Cổng', 'Trung', 'Phòng', 'Thường',
            'Đảng', 'Chính', 'Viện', 'Tòa', 'Toà', 'Kho', 'Công', 'Báo', 'Đài', 'Trường', 'Chi', 'Thành', 'Tỉnh', 'Huyện', 'Quận', 'Xã',
            'Phường', 'Kính', 'Nơi', 'Ngân', 'Bảo', 'Thanh', 'Kiểm', 'Mặt', 'Liên', 'Đoàn', 'Học', 'Đại', 'Bệnh', 'Tập', 'Lãnh', 'Thủ'}


def name_word(word):
    # Two letters at least: "S Ố", "G T R Ì N H" are spaced capitals, "Chương I" a heading.
    return len(word) >= 2 and word[:1].isupper() and word[1:].islower() and word.isalpha()


def trailing_name(cell):
    """The name that ends a cell, after its title in capitals ("KT. BỘ TRƯỞNG THỨ TRƯỞNG Nguyễn Văn A") or alone ("Vũ Hải Quân"):
    (name, has_title), or None."""
    words = cell.split()
    n = 0
    while n < len(words) and n < 6 and name_word(words[-1 - n]):
        n += 1
    if n < 2:
        return None
    name, title = words[-n:], ' '.join(words[:-n])
    if title and not title.isupper():
        return None
    if not title and name[0] in NOT_NAME:
        return None
    return ' '.join(name), bool(title)


ACTIONS = [('hopnhat', r'^Văn bản hợp nhất$'), ('congvan', r'^Công văn$')]
TITLE_ACTIONS = [('huongdan', r'\b(?:hướng\s+dẫn|quy\s+định\s+chi\s+tiết)\b'), ('sua-doi', r'\bsửa\s+đổi\b'), ('bo-sung', r'\bbổ\s+sung\b'),
                 ('bai-bo', r'\bb[ãả]i\s+bỏ\b'), ('thay-the', r'\bthay\s+thế\b'), ('huy-bo', r'\bh(?:ủy|uỷ)\s+bỏ\b')]


def head_lines(text, n=60):
    """The cells of the first lines: an issuer and the motto side by side in one table row are two cells."""
    cells = []
    for line in source_lines(text)[:n]:
        parts = [' '.join(c.split()) for c in line.split('|')] if '|' in line else [' '.join(line.split())]
        cells += [c for c in parts if c] or ['']
    return cells


def number_of(lines):
    for line in lines:
        # "Số: 6 01 7 /TB-TCHQ", "Số: 1258 / QĐ-UBND": spaces the PDF text put inside the number.
        line = re.sub(r'(?<=\d)\s+(?=[\d/])|(?<=/)\s+', '', line) if line.startswith(('Số', 'SỐ', 'số')) else line
        m = NUMBER_LINE.match(line)
        if m:
            return re.sub(r'\s+', '', m[1])
        if line.startswith('Số') and re.search(r'\d+-[A-ZĐ]', line):  # old form "Số 499-QĐ/TW"
            m = re.search(r'\d{1,6}-[A-ZĐ][\w/-]*', line)
            if m:
                return m.group()
    return None


def date_of(lines, text):
    for line in lines:
        m = PLACE_DATE.match(line) or (re.match(r'^ngày\s+' + DATE, line, re.I) if len(line) < 40 else None)
        if m:
            return to_date(*m.groups()[-3:])
    m = PASSED.search(text)  # a law passed by the National Assembly carries its date in the passing sentence
    return to_date(*m.groups()) if m else None


def type_of(lines, number):
    head = ' '.join(lines)
    # A consolidated text names the type of the text it restates on its type line; a letter has a "V/v" line and no type line.
    if re.search(r'VĂN\s+BẢN\s+HỢP\s+NHẤT', head) or re.search(r'/VBHN-', number or ''):
        return 'Văn bản hợp nhất'
    for line in lines:
        if re.search(r'(?<!\w)(?:V/v|V/V)\b', line):
            return 'Công văn'  # the "V/v" line comes before any type line: a letter (a decision prints it under "QUYẾT ĐỊNH")
        if MOTTO.match(line) or NUMBER_LINE.match(line) or line.startswith('Số'):
            continue
        for pattern, name in TYPE_LINE:
            if pattern.match(line) and line.isupper():
                return name
    if number:
        code = re.split(r'[-/]', re.sub(r'^\d+/(?:\d{4}/)?', '', number))[0]
        if code in TYPE_CODE:
            return TYPE_CODE[code]
        return 'Công văn'  # a number with only the issuer's code ("123/UBND-KT") and no type line is a letter
    return None


# Where a body starts inside one line of the issuer block ("BỘ TÀI CHÍNH TỔNG CỤC HẢI QUAN"); BỘ only starts a line (ĐƯỜNG BỘ).
INNER = re.compile(r'(?<!\S)(?=(?:TỔNG\s+CỤC|(?<!TỔNG )(?<!CHI )CỤC|CHI\s+CỤC|SỞ|(?<!DỊCH )(?<!NHIỆM )(?<!THƯỜNG )VỤ|(?<!ỦY )(?<!UỶ )BAN(?!\s+(?:CHẤP|THƯỜNG))'
                   r'|VIỆN|(?<!VĂN )PHÒNG(?!\s+CHÍNH)|VĂN\s+PHÒNG|TRUNG\s+TÂM|BẢO\s+HIỂM\s+XÃ\s+HỘI|ỦY\s+BAN|UỶ\s+BAN|UBND|HỘI\s+ĐỒNG)\s)')
LOCAL_COUNCIL = re.compile(r'^(?:(?:ỦY|UỶ)\s+BAN\s+NHÂN\s+DÂN|UBND|HỘI\s+ĐỒNG\s+NHÂN\s+DÂN|HĐND)\s+(.+)$')


def name_case(words):
    """'KHOA HỌC VÀ CÔNG NGHỆ' -> 'Khoa học và Công nghệ': a capital at the start and after "và", ",", "-"; proper words kept."""
    out = re.sub(r'(^|\bvà\s+|,\s*|-\s*)(\w)', lambda m: m[1] + m[2].upper(), words.lower())
    for word in PROPER:
        out = re.sub(r'\b' + re.escape(word.lower()) + r'\b', word, out, flags=re.I)
    return out


def place(name):
    return ' '.join(w if w.isdigit() else w[:1].upper() + w[1:].lower() for w in name.split())


def body_name(text):
    """One body in the source's form: "Tỉnh Cao Bằng", "Bộ Tài chính", "Cục Thuế Thành phố Hà Nội"."""
    text = re.sub(r'\s+', ' ', text).strip(' ,.-')
    m = LOCAL_COUNCIL.match(text)
    if m:
        text = m[1]
    m = LOCALITY.match(text)
    if m:
        return f"{PLACE_KIND.get(re.sub(r'\s+', ' ', m[1]), m[1].title())} {place(m[2])}"
    m = re.match(r'^(.*?)\s+(TỈNH|THÀNH\s+PHỐ|TP\.?|HUYỆN|QUẬN)\s+(.+)$', text)
    if m and not COUNCIL.match(m[1]):
        head = name_case(m[1])
        return f"{head} {PLACE_KIND[re.sub(r'\s+', ' ', m[2])]} {place(m[3])}"
    if COUNCIL.match(text):
        return None
    return name_case(text)


def authority_of(lines):
    """The lowest body of the issuer block (the cells above the national motto), in the source's form."""
    block = []
    for line in lines:
        if MOTTO.match(line) or NUMBER_LINE.match(line) or PLACE_DATE.match(line) or line.startswith('Số'):
            break
        line = line.strip(' -–—_*=.')  # "QUỐC HỘI ********", "BỘ TÀI CHÍNH -------"
        if not line:
            continue
        block.append(line)
    if not block or len(block) > 8 or not all(x.isupper() for x in block):
        return None
    bodies = []
    for line in block:
        pieces = [x for x in INNER.split(line) if x.strip()]
        for piece in pieces:
            if bodies and COUNCIL.match(bodies[-1]) and LOCALITY.match(piece):
                bodies[-1] += ' ' + piece  # "ỦY BAN NHÂN DÂN / TỈNH CAO BẰNG"
            elif BODY.match(piece) or LOCALITY.match(piece) or not bodies:
                bodies.append(piece)
            else:
                bodies[-1] += ' ' + piece
    name = body_name(bodies[-1])
    # "ỦY BAN NHÂN DÂN THÀNH PHỐ HỒ CHÍ MINH / SỞ GIÁO DỤC VÀ ĐÀO TẠO": the source names the department with its city.
    if name and len(bodies) > 1 and not LOCALITY.search(bodies[-1]) and not re.search(r'\s(?:TỈNH|THÀNH\s+PHỐ|TP\.?)\s', bodies[-1]):
        parent = LOCAL_COUNCIL.match(bodies[-2])
        if parent and re.match(r'^(?:SỞ|BAN|VĂN\s+PHÒNG|THANH\s+TRA)\b', bodies[-1]):
            local = body_name(parent[1])
            if local and re.match(r'^(?:Tỉnh|Thành phố)\s', local):
                name += ' ' + local
    return name


POST = re.compile(r'(?:CHỦ\s+TỊCH|TRƯỞNG|THỦ\s+TƯỚNG|GIÁM\s+ĐỐC|THỐNG\s+ĐỐC|BÍ\s+THƯ|CHÁNH\s+ÁN|TỔNG\s+KIỂM\s+TOÁN|PHÓ\s+\w+)\s*$')


def signature_lines(text):
    """(lines, marked): the lines from the first recipient list or signing mark (at most 40), or every line when there is none."""
    lines = [' '.join(x.split()) for x in source_lines(text)]
    marks = [i for i, x in enumerate(lines) if re.match(r'^Nơi\s+nhận\s*:', x, re.I) or TAIL.match(x) or SIGNED.search(x)
             or re.match(r'^(?:TL\.|TUQ\.|Q\.)\s', x)]
    # A consolidated text is signed under its verification block, after the restated text and its forms.
    verified = next((i for i, x in enumerate(lines) if re.match(r'^XÁC\s+THỰC\s+VĂN\s+BẢN\s+HỢP\s+NHẤT', x)), None)
    if verified is not None:
        return lines[verified:verified + 40], True
    return (lines[marks[0]:marks[0] + 40], True) if marks else (lines, False)


def signers_of(text):
    """Names in the signature block, in order, without the crawler's codes. A name counts after a title in capitals on its line
    or the line above ("KT. BỘ TRƯỞNG THỨ TRƯỞNG Nguyễn Văn A", "BỘ TRƯỞNG / Vũ Hải Quân"), or as a family name and two more words
    in the block. With no block (a law, an old text), only a name after the signer's post counts ("THỦ TƯỚNG Phan Văn Khải")."""
    lines, marked = signature_lines(text)
    names = []
    for i, line in enumerate(lines):
        for cell in [c.strip() for c in line.split('|')]:
            found = None if cell.startswith(('-', '+', '•', '*')) else trailing_name(cell)  # "- PCT Âu Anh Tuấn" is a recipient
            if not found:
                continue
            name, titled = found
            title = cell[:len(cell) - len(name)].strip()
            if not marked:
                ok = titled and POST.search(title)
            else:
                above = next((lines[j].split('|')[-1].strip() for j in range(i - 1, -1, -1) if lines[j].strip()), '')
                ok = titled or (above.isupper() and POST.search(above)) or (name.split()[0] in FAMILY and len(name.split()) >= 3)
            if ok and name not in names:
                names.append(name)
    return ', '.join(names) if names else None


def title_of(lines, legal_type, number, day):
    """The source's title form: "<loại> <số> năm <năm> <trích yếu>" ("Quyết định 147/QĐ-UBND năm 2026 phê duyệt …")."""
    subject = printed_title('\n'.join(lines))
    if not subject or not legal_type:
        return None
    subject = re.sub(r'^(?:' + re.escape(legal_type.upper()) + r')\s*', '', subject).strip(' .:')
    if not subject:
        return None
    subject = subject if not subject.isupper() else subject.lower()
    subject = subject[:1].lower() + subject[1:]
    year = f' năm {day[:4]}' if day and number and not re.search(r'/\d{4}/', number) else ''
    return ' '.join(x for x in (legal_type, number, (year + ' ' + subject).strip()) if x)


def action_of(legal_type, title):
    """The source's label of what the document does, from its type and title. A verb after "được"/"bị" describes what is published
    ("công bố thủ tục hành chính được sửa đổi"), and a document that publishes a list does not act itself: both are "other"."""
    for action, pattern in ACTIONS:
        if re.match(pattern, legal_type or ''):
            return action
    subject = re.sub(r'^\S+(?:\s+\S+)?\s+\S*\d\S*(?:\s+năm\s+\d{4})?\s*', '', title or '')  # after "<loại> <số> năm <năm>"
    if re.match(r'(?:về\s+việc\s+|v/v\s+)?công\s+bố\b', subject, re.I):
        return 'other'
    for action, pattern in TITLE_ACTIONS:
        for m in re.finditer(pattern, subject, re.I):
            if not re.search(r'\b(?:được|bị|đã)\s+(?:\S+\s*,\s*)*$', subject[:m.start()], re.I):
                return action
    return 'other' if legal_type else None


def by_code(src, text):
    """{field: value} for the code fields src lacks, read from the text; fields the text does not give are left out."""
    missing = [f for f in CODE_FIELDS if not src.get(f)]
    if not missing:
        return {}
    lines = head_lines(text)
    found = {}
    number = src.get('document_number') or number_of(lines)
    if 'document_number' in missing and number:
        found['document_number'] = number
    day = src.get('issuance_date') or date_of(lines, text)
    if 'issuance_date' in missing and day:
        found['issuance_date'] = day
    legal_type = src.get('legal_type') or type_of(lines, number)
    if 'legal_type' in missing and legal_type:
        found['legal_type'] = legal_type
    if 'issuing_authority' in missing:
        found['issuing_authority'] = authority_of(lines)
    if 'signers' in missing:
        found['signers'] = signers_of(text)
    title = src.get('title') or title_of(lines, legal_type, number, day)
    if 'title' in missing and title:
        found['title'] = title
    if 'action' in missing:
        found['action'] = action_of(legal_type, title)
    return {k: v for k, v in found.items() if v}


FIELD_SCHEMA = {
    # maxLength: without it the model may repeat one sentence until the answer is cut (29/10/2026, 11 of 40 documents).
    'tom_tat': {'type': 'string', 'maxLength': 700,
                'description': 'Tóm tắt 1–2 câu, tối đa 60 từ, không lặp ý, như người biên tập cơ sở dữ liệu văn bản pháp luật: văn bản làm '
                               'gì (ban hành, phê duyệt, hướng dẫn, sửa đổi, giao nhiệm vụ…), về việc gì, cho ai hoặc ở đâu. Không chép căn '
                               'cứ, không nhận xét. Mở đầu bằng tên loại của chính văn bản và chữ "này", ví dụ "Quyết định này …".'},
    'legal_sectors': {'type': 'array', 'items': {'type': 'string', 'enum': SECTORS},
                      'description': '1–3 lĩnh vực theo nội dung chính của văn bản (không theo cơ quan ban hành), quan trọng nhất trước. '
                                     '"Bộ máy hành chính" cho văn bản về tổ chức, nhân sự, chức năng nhiệm vụ của cơ quan nhà nước.'},
    'issuing_authority': {'type': 'string', 'description': 'Cơ quan ban hành thấp nhất ở khối tên cơ quan đầu văn bản (hoặc khối xác thực '
                                                           'cuối văn bản hợp nhất), viết như "Bộ Tài chính", "Cục Thuế", "Tỉnh Cao Bằng" '
                                                           '(Ủy ban/Hội đồng nhân dân tỉnh X ghi "Tỉnh X"), "Thủ tướng Chính phủ". Rỗng nếu nguồn không có.'},
    'issuance_date': {'type': 'string', 'description': 'Ngày ký/ban hành dạng YYYY-MM-DD, chép từ dòng "…, ngày … tháng … năm …"; rỗng nếu nguồn không có.'},
    'signers': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Họ tên người ký ở khối chữ ký, chép nguyên văn; mảng rỗng nếu không có.'},
    'document_number': {'type': 'string', 'description': 'Số, ký hiệu ở dòng "Số: …", chép nguyên văn; rỗng nếu không có.'},
    'legal_type': {'type': 'string', 'enum': TYPES, 'description': 'Loại văn bản.'},
}


FIELD_NAMES = re.compile(r'\s*\b(?:' + '|'.join(FIELD_SCHEMA) + r')\b\s*[:"].*$', re.S)


def tidy_summary(value):
    """The summary without what the model put after it: a field name ("…thành phố.legal_sectors: ["), a word count ("(58 từ)"), a
    sentence cut by the length limit. None when no whole sentence is left."""
    text = FIELD_NAMES.sub('', ' '.join((value or '').split()))
    text = re.sub(r'\s*\(\s*\d+\s*từ\s*\)\s*$', '', text).strip()
    if text and text[-1] not in '.;!?)"”':
        stop = max(text.rfind('. '), text.rfind('.'))
        text = text[:stop + 1] if stop > 40 else ''
    return text or None


def excerpt(text, title):
    """What the model reads: the opening, the start of the body and the signature block."""
    lines = source_lines(text)
    body = '\n'.join(lines)
    block, marked = signature_lines(text)
    tail = '\n'.join(block[:25] if marked else block[-25:])
    return json.dumps({'ten_van_ban': title or '', 'dau_van_ban': body[:6000], 'khoi_chu_ky': tail[:1500]}, ensure_ascii=False)


def grounded(value, text):
    flat = ' '.join(text.split()).casefold()
    return ' '.join(value.split()).casefold() in flat


def by_model(src, text, folder, caller=None, check=None):
    """{field: value} for the model fields src (with the code fields already filled) still lacks."""
    missing = [f for f in LLM_FIELDS if not src.get(f)]
    if not missing:
        return {}
    schema = {'type': 'object', 'additionalProperties': False, 'required': missing, 'properties': {f: FIELD_SCHEMA[f] for f in missing}}
    prompt = load('boc_metadata')
    raw = excerpt(text, src.get('title'))

    def valid(answer):
        if 'tom_tat' in missing and not tidy_summary(answer.get('tom_tat')):
            raise ValueError('tom_tat rỗng hoặc không có câu trọn vẹn')
        if 'legal_sectors' in missing and not (1 <= len(answer.get('legal_sectors') or []) <= 3 and set(answer['legal_sectors']) <= set(SECTORS)):
            raise ValueError('legal_sectors phải có 1–3 lĩnh vực trong danh mục')
        day = answer.get('issuance_date') or ''
        if day and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            raise ValueError('issuance_date phải dạng YYYY-MM-DD')
        for name in answer.get('signers') or []:
            if not grounded(name, text):
                raise ValueError(f'người ký "{name}" không có trong nguồn')
        if answer.get('document_number') and not grounded(answer['document_number'], text):
            raise ValueError('số hiệu không có trong nguồn')
    target = folder / 'metadata' / hashlib.sha256((prompt + raw + json.dumps(schema) + os.getenv('LITELLM_MODEL', '')).encode()).hexdigest()[:24]
    target.mkdir(parents=True, exist_ok=True)
    answer = validated_json(prompt, raw, target, 'metadata.json', valid, schema=schema, max_tokens=800, timeout=240, caller=caller, check=check)
    out = {}
    for field in missing:
        value = answer.get(field)
        if field == 'signers':
            value = ', '.join(value or []) or None
        if field == 'tom_tat':
            value = tidy_summary(value)
        if field == 'issuance_date' and value and not to_date(value[8:10], value[5:7], value[:4]):
            value = None
        if isinstance(value, str):
            value = value.strip() or None
        if value:
            out[field] = value
    return out


def fill(src, text, folder=None, caller=None, check=None, model=True):
    """src with the empty catalogue fields read from the text: by code, then by the model. A model failure keeps the code result."""
    filled = by_code(src, text)
    merged = {**src, **filled}
    if model and folder is not None:
        try:
            filled.update(by_model(merged, text, folder, caller=caller, check=check))
        except Exception as exc:  # the conversion goes on without the fields the model could not give
            filled['_loi'] = f'{type(exc).__name__}: {str(exc)[:200]}'
    return filled
