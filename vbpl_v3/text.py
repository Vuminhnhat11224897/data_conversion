"""Text keys and evidence matching used by relation detection and QA."""

import re
import unicodedata

ACTIONS = [('bai-bo', r'b[ãả]i\s*bỏ|(?<!\w)bỏ(?=\s+(?:dấu\s+)?(?:gạch\s+đầu\s+dòng|gạch\s+ngang|tiết|điểm|khoản|điều|đoạn|câu|mục|phụ\s+lục|chương|cụm\s+từ|từ\s+ngữ|từ)\b)'
                       # A list lead that ends provisions: "các quy định sau đây hết hiệu lực thi hành: a) …"
                       r'|(?:các\s+)?(?:quy\s+định|văn\s+bản|điều\s+khoản|Thông\s+tư(?:\s+liên\s+tịch)?|Nghị\s+định|Quyết\s+định|Nghị\s+quyết|Chỉ\s+thị)'
                       r'\s+sau\s+(?:đây\s+)?hết\s+hiệu\s*lực'), ('huy-bo', r'h(?:uỷ|ủy|uy|uỹ|ũy)\s*bỏ'), ('thay-the', r'thay\s*thế'),
           # "điều chỉnh, bổ sung khoản 6 Điều 1 … lại thành": the pair is "sửa đổi, bổ sung" in other words.
           ('sua-doi', r'sửa\s*đổi|điều\s+chỉnh(?=\s*,?\s*(?:và\s+)?bổ\s*sung\b)'), ('bo-sung', r'bổ\s*sung'),
           ('dinh-chi', r'(?:tạm\s+)?đình\s*chỉ\s+(?:việc\s+)?(?:thi\s*hành|thực\s*hiện)'),
           ('thay-cum-tu', r'thay\s+(?:thế\s+)?(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ|từ)(?!\s+(?:ngày|năm|tháng|khi)\b)'
                           # "Sửa đổi cụm từ “ngày làm việc” thành “ngày”": the same replacement of wording.
                           r'|(?:sửa\s*đổi|thay\s+đổi|điều\s+chỉnh)\s+(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ)\b'),
           ('dinh-chinh', r'đính\s*chính'),
           ('ngung-hieu-luc', r'(?:tạm\s+)?ng(?:ư|ừ)ng\s+(?:thi\s+hành\s+)?hiệu\s*lực'),
           # "gia hạn nộp thuế" extends a deadline, not a document: only its validity or application counts.
           ('gia-han', r'(?:gia\s+hạn|kéo\s+dài)\s+(?:thời\s+(?:hạn|gian)\s+)?(?:hiệu\s*lực|áp\s+dụng)')]
# Words before an action that make it a power, a proposal or a catalogue heading, not the act itself.
NOT_PERFORMED = r'(?:kiến\s+nghị|đề\s+nghị|yêu\s+cầu|có\s+quyền|thẩm\s+quyền)\b'


def number_key(value):
    value = unicodedata.normalize('NFC', value or '').replace('Ð', 'Đ').replace('ð', 'đ')  # Icelandic eth typed for Đ
    value = ''.join(c for c in value if not c.isspace() and c not in '​‌‍⁠﻿')
    return re.sub(r'^0+(?=\d+/)', '', value.replace('–', '-').replace('—', '-')).casefold()


def authority_key(value):
    value = unicodedata.normalize('NFD', (value or '').casefold()).replace('đ', 'd')
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r'\bubnd\b', 'uy ban nhan dan', value)
    value = re.sub(r'\bhdnd\b', 'hoi dong nhan dan', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return ', '.join(sorted(part.strip() for part in value.split(',')))


def catalog_authority_key(value):
    value = authority_key(value)
    return re.sub(r'^(?:(?:chu tich )?(?:uy ban nhan dan|hoi dong nhan dan) )(?=(?:tinh|thanh pho|huyen|quan|thi xa|xa|phuong|thi tran) )', '', value)


def action_matches(text):
    matches = []
    for action, pattern in ACTIONS:
        for match in re.finditer(pattern, text, re.I):
            if action == 'bo-sung' and not (re.search(r'(?:sửa\s*đổi|điều\s+chỉnh)\s*,?\s*(?:và\s+)?$', text[max(0, match.start() - 20):match.start()], re.I)
                                            or re.match(r'\s*(?:một số|(?:các\s+|thêm\s+)?(?:điều|khoản|điểm|tiết|mục|chương|phụ\s+lục|mẫu)\s+[\w.]|'
                                                        r'(?:các\s+|thêm\s+)?(?:cụm\s+từ|từ\s+ngữ|từ|câu|đoạn)\b|nội dung|tên gọi|vào\s+(?:sau|trước|cuối|đầu)?)',
                                                        text[match.end():], re.I)):
                continue
            if action == 'sua-doi' and re.match(r'\s+(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ)\b', text[match.end():], re.I):
                continue  # "sửa đổi cụm từ X thành Y" replaces wording (thay-cum-tu)
            if action == 'thay-the' and re.match(r'\s+(?:các\s+)?(?:cụm\s+từ|từ\s+ngữ|từ)(?!\s+(?:ngày|năm|tháng|khi)\b)', text[match.end():], re.I):
                continue  # "thay thế cụm từ X bằng Y" replaces wording, not the document or provision
            if action == 'bai-bo' and match.group().casefold().startswith('bỏ') and \
                    re.search(r'(?:h(?:uỷ|ủy|uy|uỹ|ũy)|loại|từ)\s*$', text[max(0, match.start() - 8):match.start()], re.I):
                continue  # "hủy bỏ khoản 2" is an annulment; "từ bỏ" is not a repeal
            if action in ('dinh-chi', 'ngung-hieu-luc', 'gia-han') and re.search(NOT_PERFORMED, text[max(0, match.start() - 40):match.start()], re.I):
                continue  # a power to suspend, or a proposal to extend, not the act
            if action == 'ngung-hieu-luc' and re.search(r'(?:hết\s+hiệu\s*lực|danh\s+mục|văn\s+bản\s+cần)[^.;]{0,40}$', text[max(0, match.start() - 60):match.start()], re.I):
                continue  # "Danh mục văn bản hết hiệu lực, ngưng hiệu lực": a status in a catalogue heading
            if re.search(r'\bkhông\s+(?:bị\s+|được\s+)?(?:(?:sửa\s*đổi|điều\s+chỉnh)\s*,?\s*)?$', text[max(0, match.start() - 30):match.start()], re.I):
                continue  # "Các nội dung khác không điều chỉnh, bổ sung … giữ nguyên": a denial, not the act
            matches.append((match.start(), match.end(), action))
            break
    return sorted(matches)


def norm(text):
    text = re.sub(r'(?<=\w)-[ \t]*\n[ \t]*(?=\w)', '-', text)
    return ' '.join(unicodedata.normalize('NFC', text).split())


def quote_in_text(quote, text):
    if not isinstance(quote, str) or not quote.strip():
        return False
    if norm(quote).casefold() in norm(text).casefold():
        return True
    parts = [norm(line).casefold() for line in quote.splitlines() if line.strip()]
    if len(parts) < 2:
        return False

    def column(part, line):
        match = re.search(r'\s+'.join(map(re.escape, part.split())), line)
        return match.start() if match else None

    # Match nearby lines in one PDF column.
    for page in text.split('\f'):
        lines = [unicodedata.normalize('NFC', line).casefold() for line in page.splitlines()]
        for index, line in enumerate(lines):
            start = column(parts[0], line)
            if start is None:
                continue
            last = index
            for part in parts[1:]:
                for next_line in range(last + 1, min(last + 9, len(lines))):
                    offset = column(part, lines[next_line])
                    if offset is not None and abs(offset - start) <= 8:
                        last = next_line
                        break
                else:
                    break
            else:
                return True
    return False


# A clause that states something of its own ends a list: what comes before it is another sentence, not an earlier item.
PREDICATE = re.compile(r'\b(?:có\s+hiệu\s*lực|hết\s+hiệu\s*lực|được\s+áp\s+dụng|áp\s+dụng\s+(?:từ|đến)|chịu\s+trách\s+nhiệm|giao\s|thay\s*thế|'
                       r'sửa\s*đổi|bổ\s*sung|b[ãả]i\s*bỏ|h(?:uỷ|ủy|uy)\s*bỏ|ban\s+hành|quy\s+định\s+(?:về|chi\s+tiết)|như\s+sau)\b', re.I)


def list_tail(text):
    """The part of text that a statement closing it is about: the last sentence, with the earlier items of a list split by ';'.
    "… tại Phụ lục I kèm theo Quyết định số 560/QĐ-UBND; Phụ lục kèm theo Quyết định số 2401/QĐ-UBND; số thứ tự 1 … Quyết định số
    1659/QĐ-UBND" (then "hết hiệu lực") keeps all three items; an item that states something of its own ("Quyết định này có hiệu lực
    từ ngày ký;") ends the list."""
    sentence = re.split(r'[.:]\s|\n', text)[-1]
    items = re.split(r';\s*', sentence)
    kept = [items[-1]]
    for item in reversed(items[:-1]):
        if not item.strip() or PREDICATE.search(item):
            break
        kept.insert(0, item)
    return '; '.join(kept)


VIETNAMESE = re.compile(r'[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]', re.I)


def language(text):
    """'vi', or 'en' for a text with almost no Vietnamese letters (an English translation stored as the full text: its "Article 1.-"
    are not parsed as articles, so its relations cannot be read)."""
    letters = sum(c.isalpha() for c in (text or '')[:20000])
    marked = len(VIETNAMESE.findall((text or '')[:20000]))
    return 'en' if letters > 500 and marked / letters < 0.02 else 'vi'
