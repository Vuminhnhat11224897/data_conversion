"""Legal standing of a document: normative or not, its rank (15 groups of the law), its stated end and retroactive start."""

import re

from .structure import NUMBER, unquoted
from .temporal import DATE, own_subject, positions, provision_led, to_date, when
from .text import list_tail

ALWAYS = {'Hiến pháp', 'Bộ luật', 'Luật', 'Pháp lệnh', 'Lệnh', 'Nghị định', 'Thông tư', 'Thông tư liên tịch', 'Sắc lệnh', 'Sắc luật'}
NEVER = {'Công văn', 'Công điện', 'Thông báo', 'Kế hoạch', 'Báo cáo', 'Hướng dẫn', 'Văn bản khác', 'Thông tri',
         'Điều ước quốc tế', 'Công ước', 'Hiệp định', 'Nghị định thư', 'Thoả thuận', 'Điều ước', 'WTO_Văn bản',
         'Văn bản WTO', 'WTO_Cam kết VN', 'Tiêu chuẩn Việt Nam', 'Tiêu chuẩn XDVN', 'Tiêu chuẩn ngành'}
MIXED = {'Quyết định', 'Nghị quyết', 'Chỉ thị'}
PARTY = re.compile(r'Ban Chấp hành Trung ương|Bộ Chính trị|Ban Bí thư|Trung ương Đảng|Ban .* Trung ương$')
CENTRAL_CITIES = ('Hà Nội', 'Hồ Chí Minh', 'Cần Thơ', 'Đà Nẵng', 'Hải Phòng', 'Huế')
MINISTRY = re.compile(r'^(?:Bộ\s|Ngân hàng Nhà nước|Thanh tra Chính phủ|Ủy ban Dân tộc|Uỷ ban Dân tộc|Văn phòng Chính phủ'
                      r'|Tòa án nhân dân tối cao|Toà án nhân dân tối cao|Viện kiểm sát nhân dân tối cao|Kiểm toán Nhà nước)')
LEVELS = {1: 'HIEN_PHAP', 2: 'QUOC_HOI', 3: 'UBTV_QUOC_HOI', 4: 'CHU_TICH_NUOC', 5: 'CHINH_PHU', 6: 'THU_TUONG',
          7: 'HDTP_TANDTC', 8: 'THONG_TU', 9: 'THONG_TU_LIEN_TICH', 10: 'HDND_TINH', 11: 'UBND_TINH',
          12: 'CHU_TICH_UBND_TINH', 13: 'HC_KT_DAC_BIET', 14: 'HDND_XA', 15: 'UBND_XA'}
# Titles of individual (non-normative) decisions and resolutions, which may still carry a year in their number.
INDIVIDUAL = re.compile(r'\b(?:phiên\s+họp|bổ\s+nhiệm|miễn\s+nhiệm|điều\s+động|cử\s+(?:cán\s+bộ|ông|bà|đoàn)|khen\s+thưởng|kỷ\s+luật|'
                        r'phê\s+duyệt|phân\s+bổ|dự\s+toán\s+(?:ngân\s+sách|chi|thu|điều\s+chỉnh)|bổ\s+sung\s+dự\s+toán|chấp\s+thuận|thu\s+hồi\s+đất|thành\s+lập|giải\s+thể|công\s+nhận|xếp\s+hạng|'
                        r'cho\s+phép|đặc\s+xá|phê\s+chuẩn|bầu\s|kế\s+hoạch\s+phát\s+triển|công\s+bố\s+(?:danh\s+mục|thủ\s+tục)|giao\s+(?:chỉ\s+tiêu|kế\s+hoạch))', re.I)
NORMATIVE_TITLE = re.compile(r'\b(?:quy\s+định|hướng\s+dẫn|ban\s+hành\s+(?:\S+\s+){0,2}?(?:Quy\s+chế|Quy\s+trình|Điều\s+lệ)|bảng\s+giá|định\s+mức|đơn\s+giá|giá\s+(?:các\s+loại\s+)?đất|học\s+phí|lệ\s+phí|'
                             r'sửa\s+đổi|bãi\s+bỏ|mức\s+(?:thu|chi|hỗ\s+trợ|phí)|chính\s+sách|chế\s+độ|Quy\s+chế)', re.I)
YEAR_NUMBER = re.compile(r'^\s*\d+[a-zđ]?\s*/\s*(?:19|20)\d{2}\s*/', re.I)


def issuer(authority):
    """Coarse issuer class from the stored issuing_authority."""
    a = (authority or '').strip()
    if PARTY.search(a):
        return 'dang'
    if a == 'Quốc hội':
        return 'quoc_hoi'
    if 'Thường vụ Quốc hội' in a:
        return 'ubtvqh'
    if a.startswith('Chủ tịch nước'):
        return 'chu_tich_nuoc'
    if a.startswith('Hội đồng Thẩm phán'):
        return 'hdtp'
    if a in ('Chính phủ', 'Hội đồng Chính phủ', 'Hội đồng Bộ trưởng'):
        return 'chinh_phu'
    if a == 'Thủ tướng Chính phủ':
        return 'thu_tuong'
    if re.match(r'(?:Tỉnh\s|Thành phố\s(?:' + '|'.join(CENTRAL_CITIES) + r')$)', a):
        return 'tinh'
    if re.match(r'(?:Huyện|Quận|Thị xã|Thành phố)\s', a):
        return 'huyen'
    if re.match(r'(?:Xã|Phường|Thị trấn)\s', a):
        return 'xa'
    if 'đặc khu' in a.casefold():
        return 'dac_khu'
    if MINISTRY.match(a):
        return 'bo'
    return 'khac'


def normative(meta):
    """(la_vbqppl, la_vbqppl_cach); la_vbqppl is None when the rules cannot decide."""
    kind, number, issued = meta.get('legal_type'), meta.get('document_number') or '', meta.get('issuance_date') or ''
    who = issuer(meta.get('issuing_authority'))
    if kind == 'Văn bản hợp nhất':
        return False, 'van_ban_hop_nhat'
    if who == 'dang':
        return False, 'van_ban_dang'
    if kind in ALWAYS:
        return True, 'theo_loai'
    if kind in NEVER:
        return False, 'theo_loai'
    if kind not in MIXED:
        return None, 'can_kiem'
    if kind == 'Chỉ thị' and issued >= '2016-07-01':
        return False, 'chi_thi_tu_2016'
    if who in ('bo',) and kind in ('Quyết định', 'Chỉ thị') and issued >= '2009-01-01':
        return False, 'quyet_dinh_bo_tu_2009'
    if who == 'khac':
        return False, 'co_quan_khong_ban_hanh_vbqppl'
    title = meta.get('title') or ''
    if kind in ('Quyết định', 'Nghị quyết') and INDIVIDUAL.search(title) and not NORMATIVE_TITLE.search(title):
        return False, 'tieu_de_ca_biet'
    if YEAR_NUMBER.match(number):
        return True, 'so_hieu_co_nam'
    if issued >= '2005-01-01':
        return False, 'so_hieu_khong_nam'
    return None, 'can_kiem'


def rank(meta, is_normative):
    """(cap_hieu_luc, cap_hieu_luc_nhan, cap_hieu_luc_ghi_chu) following the 15 groups of the law; legacy forms keep their issuer's rank."""
    if not is_normative:
        return None, None, None
    kind, number, issued = meta.get('legal_type'), meta.get('document_number') or '', meta.get('issuance_date') or ''
    authority = meta.get('issuing_authority') or ''
    who = issuer(authority)
    legacy = None
    level = None
    if kind == 'Hiến pháp':
        level = 1
    elif kind in ('Luật', 'Bộ luật', 'Sắc luật') or (kind == 'Nghị quyết' and who == 'quoc_hoi'):
        level = 2
    elif kind == 'Pháp lệnh' or (kind == 'Nghị quyết' and who == 'ubtvqh'):
        level = 3
    elif kind in ('Lệnh', 'Sắc lệnh') or (kind == 'Quyết định' and who == 'chu_tich_nuoc'):
        level, legacy = 4, ('hinh_thuc_cu' if kind == 'Sắc lệnh' else None)
    elif kind == 'Nghị định' or (kind in ('Nghị quyết', 'Quyết định') and who == 'chinh_phu'):
        level, legacy = 5, ('hinh_thuc_cu' if authority != 'Chính phủ' or kind == 'Quyết định' else None)
    elif kind in ('Quyết định', 'Chỉ thị') and who == 'thu_tuong':
        level, legacy = 6, ('hinh_thuc_cu' if kind == 'Chỉ thị' else None)
    elif kind == 'Nghị quyết' and who == 'hdtp':
        level = 7
    elif kind == 'Thông tư':
        level = 8
    elif kind in ('Quyết định', 'Chỉ thị') and who == 'bo':
        level, legacy = 8, 'hinh_thuc_cu'
    elif kind == 'Thông tư liên tịch':
        level = 9
    elif who == 'tinh' and kind == 'Nghị quyết':
        level = 10
    elif who == 'tinh' and kind == 'Quyết định':
        level = 12 if re.search(r'QĐ-CT\b', number) else 11
    elif who == 'tinh' and kind == 'Chỉ thị':
        level, legacy = 11, 'hinh_thuc_cu'
    elif who == 'dac_khu':
        level = 13
    elif who == 'xa':
        level = 14 if kind == 'Nghị quyết' else 15 if kind == 'Quyết định' else None
    elif who == 'huyen':
        return None, None, 'cap_huyen'
    if level is None:
        return None, None, 'khong_xac_dinh'
    return level, LEVELS[level], legacy


EFFECT_VERB = r'(?:có\s+hiệu\s+lực(?:\s+thi\s+hành)?|(?:được\s+)?(?:áp\s+dụng|thực\s+hiện|thi\s+hành))'
ARTICLE_LINE = re.compile(r'^\s*Điều\s+(\d+[a-zđ]?)\b')


def visible_lines(text):
    """(article, line) for each line outside quotations, quoted spans removed, with the article it sits in."""
    lines, article = text.split('\n'), None
    for line, visible in zip(lines, unquoted(lines)):
        if not visible:
            continue
        heading = ARTICLE_LINE.match(line)
        article = heading[1] if heading else article
        yield article, re.sub(r'“[^”]*”|"[^"]*"', ' ', line).split('“')[0]


def expiry(text, issued, legal_type=None):
    """{ngay_het_hieu_luc, ngay_het_hieu_luc_cach, ngay_het_hieu_luc_trich}: only an end the document states for itself,
    with its effect verb right after "<own type> này" ("Nghị quyết này có hiệu lực từ … đến hết ngày …")."""
    own = own_subject(legal_type) + r'(?:\s+[^\s.;:,]+){0,2}?\s+này'
    for _, line in visible_lines(text):
        if any(provision_led(line, m.start()) for m in re.finditer(own, line, re.I)):
            continue  # "Điều 2 của Luật này có hiệu lực đến hết ngày …" ends one provision, not the document
        for match in re.finditer(own + r'\s+(?:hết\s+hiệu\s+lực(?:\s+thi\s+hành)?\s+(?:kể\s+)?(?:từ|vào)\s+ngày\s+' + DATE + r')', line, re.I):
            return {'ngay_het_hieu_luc': to_date(*match.groups()), 'ngay_het_hieu_luc_cach': 'ngay_cu_the', 'ngay_het_hieu_luc_trich': match.group().strip()[:300]}
        for match in re.finditer(own + r'\s+' + EFFECT_VERB + r'(?P<rest>[^.;\n]{0,200})', line, re.I):
            rest = match['rest']
            day = re.search(r'(?:đến|tới)\s+(?:hết\s+)?ngày\s+' + DATE, rest, re.I)
            if day:
                return {'ngay_het_hieu_luc': to_date(*day.groups()), 'ngay_het_hieu_luc_cach': 'ngay_cu_the', 'ngay_het_hieu_luc_trich': match.group().strip()[:300]}
            year = re.search(r'(?:đến|tới)\s+(?:hết\s+)?năm\s+(?:ngân\s+sách\s+)?((?:19|20)\d{2})', rest, re.I) \
                or re.search(r'(?:cho|trong)\s+(?:giai\s+đoạn|thời\s+kỳ)[^.;\n]{0,40}?(?:19|20)\d{2}\s*[-–]\s*((?:19|20)\d{2})', rest, re.I)
            if year:
                return {'ngay_het_hieu_luc': f'{year[1]}-12-31', 'ngay_het_hieu_luc_cach': 'het_nam', 'ngay_het_hieu_luc_trich': match.group().strip()[:300]}
    return {'ngay_het_hieu_luc': None, 'ngay_het_hieu_luc_cach': 'khong_ghi', 'ngay_het_hieu_luc_trich': None}


def provision_effects(text, issued, legal_type=None):
    """Effective dates the document gives some of its own provisions, apart from its own date:
    "Khoản 3 Điều 2 Nghị định này có hiệu lực từ ngày …", "…, trừ quy định tại Điều 5 có hiệu lực từ ngày …".
    Returns [{vi_tri, ngay_hieu_luc, ngay_hieu_luc_cach, ngay_hieu_luc_so_ngay, ngay_hieu_luc_trich}]."""
    if legal_type == 'Văn bản hợp nhất':
        return []
    own = own_subject(legal_type) + r'(?:\s+[^\s.;:,]+){0,2}?\s+này'
    found = []
    for article, line in visible_lines(text):
        # "có hiệu lực", or "được áp dụng / thực hiện" followed by a start day.
        for match in re.finditer(r'\bcó\s+hiệu\s+lực(?:\s+thi\s+hành)?|\bđược\s+(?:áp\s+dụng|thực\s+hiện)(?=\s+(?:kể\s+)?từ\s+ngày)', line, re.I):
            # A list split by ';' ("Khoản 9 và khoản 11 Điều 3; Điều 5; điểm g khoản 2 Điều 11; … có hiệu lực từ …") is one subject.
            before = list_tail(line[:match.start()])
            cut = list(re.finditer(r'\b(?:trừ|riêng|đối\s+với)\b', before, re.I))
            if cut:
                before = before[cut[-1].end():]
            before = re.sub(r'^\s*(?:\d+[a-zđ]?\.\s+)?(?:(?:các\s+)?(?:quy\s+định|nội\s+dung)\s+)?(?:(?:tại|ở)\s+)?', '', before, flags=re.I)
            before = re.sub(r'\s*(?:của\s+)?' + own + r'\s*$', '', before, flags=re.I).strip(' ,')
            named = re.search(r'\b(?:tại|ở)\s+((?:các\s+)?(?:điểm|khoản|điều|chương|mục)\b.*)$', before, re.I)
            if named and not re.match(r'(?:các\s+)?(?:điểm|khoản|điều|chương|mục)\b', before, re.I):
                before = named[1]  # "Quy định thuế suất 5% … tại khoản 3 Điều 1": the provision is the one named after "tại"
            if not re.match(r'(?:các\s+)?(?:điểm|khoản|điều|chương|mục)\b', before, re.I) or NUMBER.search(before):
                continue  # the document itself, or a provision of another document
            places = [f'Điều {article}'] if re.fullmatch(r'Điều\s+này', before, re.I) and article else positions(before)
            if not places:
                continue
            value, how, offset = when(line[match.end():match.end() + 160], issued, line)
            if how == 'khong_doc_duoc' or (value and issued and value < issued):
                continue  # "có hiệu lực đến hết ngày …" is an end; a day before signing is retroactivity (retroactive())
            found.append({'vi_tri': places, 'ngay_hieu_luc': value, 'ngay_hieu_luc_cach': how, 'ngay_hieu_luc_so_ngay': offset,
                          'ngay_hieu_luc_trich': line[max(0, match.start() - 200):match.end() + 100].strip()[:300]})
    return found


def unit_of(source):
    """(article, clause, point, sub_point, chapter) of a main-text chunk; None for appendix and attached-document chunks."""
    if not source.get('ky_hieu_dieu') or source.get('in_phu_luc') or source.get('segment'):
        return None
    return (source['ky_hieu_dieu'], source.get('ky_hieu_khoan'), source.get('so_diem'),
            str(source['so_tieu_diem']) if source.get('so_tieu_diem') else None, source.get('chuong') or '')


def unit_of_path(path):
    """'Điều 1 Khoản 8 điểm a' -> ('1', '8', 'a', None, ''); paths outside the main articles give None."""
    match = re.fullmatch(r'Điều\s+(\S+)(?:\s+Khoản\s+(\S+))?(?:\s+điểm\s+(\S+))?', path or '')
    return (match[1], match[2], match[3], None, '') if match else None


def covers(place, unit):
    """How closely a position names a unit: 0 = not at all, higher = more specific."""
    if unit is None:
        return 0
    article, clause, point, sub, chapter = unit
    if place == 'toàn bộ':
        return 1
    m = re.fullmatch(r'Chương\s+(\S+)', place)
    if m:
        return 2 if re.match(rf'Chương\s+{re.escape(m[1])}\b', chapter) else 0
    m = re.fullmatch(r'(?:tiểu điểm (\S+) )?(?:điểm (\S+) )?(?:khoản (\S+) )?Điều (\S+)', place)
    if not m or m[4] != article:
        return 0
    wanted = [m[3], m[2], m[1]]
    have = [clause, point, sub]
    for depth, (want, value) in enumerate(zip(wanted, have)):
        if want is None:
            return 3 + depth
        if want != value:
            return 0
    return 6


def unit_dates(unit, document, provisions):
    """Effective and retroactive day of one unit: its own stated date when the document gives one, else the document's."""
    best, own = 0, None
    for row in provisions:
        score = max((covers(p, unit) for p in row['vi_tri']), default=0)
        if score > best:
            best, own = score, row
    source = own or document
    dates = {'ngay_hieu_luc': source['ngay_hieu_luc'], 'ngay_hieu_luc_cach': source['ngay_hieu_luc_cach'],
             'ngay_hieu_luc_so_ngay': source.get('ngay_hieu_luc_so_ngay'), 'ngay_hieu_luc_rieng': own is not None}
    if document.get('hoi_to') and (not document.get('hoi_to_vi_tri') or any(covers(p, unit) for p in document['hoi_to_vi_tri'])):
        dates['ngay_hoi_to'] = document['ngay_hoi_to']
    return dates


def retroactive(text, issued, effective, legal_type=None):
    """{hoi_to, ngay_hoi_to, ngay_hoi_to_trich, hoi_to_vi_tri}: the document applies from a day before it was signed.
    hoi_to_vi_tri lists the provisions that do ("khoản 8 Điều 1"); empty means the whole document."""
    none = {'hoi_to': False, 'ngay_hoi_to': None, 'ngay_hoi_to_trich': None, 'hoi_to_vi_tri': []}
    if not issued or legal_type == 'Văn bản hợp nhất':
        return none
    if effective.get('ngay_hieu_luc') and effective.get('ngay_hieu_luc_cach') == 'ngay_cu_the' and effective['ngay_hieu_luc'] < issued:
        return {'hoi_to': True, 'ngay_hoi_to': effective['ngay_hieu_luc'], 'ngay_hoi_to_trich': effective.get('ngay_hieu_luc_trich'), 'hoi_to_vi_tri': []}
    own = own_subject(legal_type) + r'(?:\s+[^\s.;:,]+){0,2}?\s+này'
    itself = re.compile(rf'(?P<own>{own})|(?P<part>\b(?:Điều|Khoản|Chương|Mục)\s+này)'
                        r'|(?P<attached>(?:Quy\s+định|Quy\s+chế|Định\s+mức|Đơn\s+giá|Bảng\s+giá|Bộ\s+định\s+mức)(?:\s+[^\s.;:,]+){0,6}?\s+này)', re.I)
    for article, line in visible_lines(text):
        for sentence in re.finditer(r'[^.;\n]{0,300}', line):
            s = sentence.group()
            subject = itself.search(s)
            match = re.search(r'(?:được\s+)?(?:áp\s+dụng|thực\s+hiện|tính)\s+(?:kể\s+)?từ\s+ngày\s+' + DATE, s, re.I) if subject else None
            day = to_date(*match.groups()) if match and match.start() > subject.start() else None
            if not day or day >= issued:
                continue
            where = re.search(r'\b(?:tại|ở)\s+(.+?)(?:\s+của)?\s*$', s[:subject.start()], re.I)
            scope = positions(where[1]) if where and subject['own'] else []
            if subject['part'] and subject['part'].lower().startswith('điều') and article:
                scope = [f'Điều {article}']
            return {'hoi_to': True, 'ngay_hoi_to': day, 'ngay_hoi_to_trich': s.strip()[:300], 'hoi_to_vi_tri': scope}
    return none
