"""Four grounded candidate detectors and conservative target resolution."""

from collections import defaultdict
from datetime import date
import re

from .text import action_matches, authority_key, catalog_authority_key, list_tail, number_key
from .structure import NUMBER, refs
from .temporal import DATE, IN_APPENDIX, SECTION, SUB_POINT, SUSPENSIONS, extension, levels, ordinal, phrase_change, positions, stated_positions, suspension


FORM_LIST=re.compile(r'(?:mẫu|biểu|quy\s*trình)\s*(?:biểu\s*)?(?:số\s*)?(?:[\w./-]+\s*(?:,|và)\s*)*$',re.I)



# Words that name a part of a document, not the document as a whole: "khoản 2 Điều 5", "Phụ lục II", "số thứ tự 1 Mục II", "Chương III".
PART_NAMED=r'\b(?:điều|khoản|điểm|chương|mục|phần|phụ\s+lục|số\s+thứ\s+tự|stt|tiết|bảng|biểu|mẫu|danh\s+mục|nội\s+dung\s+(?:công\s+bố|quy\s+định))\b'


def row_holders(text):
    """The appendices that hold the numbered rows a text names ("số thứ tự 1, 2 Mục IV Phần A Phụ lục I, số thứ tự 2 Mục I Phụ lục II
    kèm theo …" -> "Phụ lục I; Phụ lục II"): a row has no node, its appendix does (C4). None when the text names no row."""
    if not re.search(r'\b(?:số\s+thứ\s+tự|stt)\b',text or '',re.I):
        return None
    labels=[m[1] for m in re.finditer(r'\bphụ\s+lục\s+(?:số\s+)?([IVXLCDM]+|\d+[A-Za-z]?)\b',text,re.I)]
    if labels:
        return '; '.join(dict.fromkeys(f'Phụ lục {x}' for x in labels))
    return 'Phụ lục' if re.search(r'\bphụ\s+lục\b',text,re.I) else None

def document_refs(text):
    """Document numbers in text, without form numbers ("mẫu số 01/THKH, 01A/KK-HĐ" are forms, not documents)."""
    # A run of form codes can be long ("mẫu biểu số 05/KK-TNCN, 05-1/BK-TNCN, …, 02/KK-TNCN"): look back far enough.
    return [m for m in NUMBER.finditer(text) if not FORM_LIST.search(text[max(0,m.start()-400):m.start()])
            and not re.search(r'\w-$',text[max(0,m.start()-2):m.start()])]  # "02-1/BK-BH" is one form code, not "1/BK-BH"


def lead_context(parent):
    """(clause, article) named once in a lead sentence ("… tại các điểm, khoản của khoản 3 Điều 2 như sau:")."""
    lead=frame(parent or '')
    pairs=re.findall(r'\bkhoản\s+(\d+[a-zđ]?)\s+(?:của\s+)?điều\s+(\d+[a-zđ]?)\b',lead,re.I)
    if len(set(pairs))==1:return pairs[0]
    articles=re.findall(r'\bđiều\s+(\d+[a-zđ]?)\b',lead,re.I)
    return (None,articles[0]) if len(set(articles))==1 else None


def strip_quotes(text):
    """Remove quoted text, nested quotes included; an unclosed quote runs to the end."""
    out,depth,straight=[],0,False
    for char in text:
        if char=='“':depth+=1;continue
        if char=='”' and depth:depth-=1;continue
        if char=='"' and not depth:straight=not straight;continue
        if not depth and not straight:out.append(char)
    return ''.join(out)


def frame(text):
    # Only the declaration before replacement content can describe the change.
    text=re.split(r'như sau\s*[:.]',text,maxsplit=1,flags=re.I)[0]
    # "Tại Điều 1 đính chính thành: Thông tư số …": what follows is the corrected wording.
    text=re.sub(r'(đính\s*chính\s+(?:lại\s+)?thành)\s*:.*',r'\1',text,flags=re.I|re.S)
    text=strip_quotes(text)
    # The source's own appendix, where the new wording sits ("… tại Mẫu số 01 Phụ lục I kèm theo Nghị định này", "(Phụ lục 1 kèm theo)").
    text=re.sub(r'\((?:[^()]*?\b)?phụ\s+lục[^()]*kèm\s+theo[^()]*\)','',text,flags=re.I)
    text=re.sub(r'(?:\s*,?\s*(?:tại|ở|theo)\s+)?(?:(?:các\s+)?mẫu\s+(?:số\s+)?[\w./-]+(?:\s*(?:,|và)\s*[\w./-]+)*\s+)?(?:tại\s+)?phụ\s+lục\s*[\w.]*\s+(?:ban\s+hành\s+)?kèm\s+theo\s+(?:Nghị\s+định|Quyết\s+định|Thông\s+tư(?:\s+liên\s+tịch)?|Nghị\s+quyết|Chỉ\s+thị|Luật|văn\s+bản)\s+này','',text,flags=re.I)
    # History notes "(đã được bổ sung theo ... Điều 1 của Thông tư ...)" name neither the change nor its location.
    text=re.sub(r'\s*\((?:đã\s+)?được\s+(?:sửa\s+đổi|bổ\s+sung|thay\s+thế|bãi\s+bỏ)[^()]*\)','',text,flags=re.I)
    # The same note without brackets, to the end of its clause: "… Thông tư số 55/2016/TT-BTC được sửa đổi, bổ sung tại Điều 1
    # Thông tư số 75/2017/TT-BTC.", "… Điều 1 Thông tư số 75/2017/TT-BTC đã được sửa đổi tại Khoản 1 Điều này."
    text=re.sub(r',?\s+(?:đã\s+)?được\s+(?:sửa\s+đổi|bổ\s+sung|thay\s+thế)(?:\s*,\s*bổ\s+sung)?\s+(?:tại|bởi|theo)\s+[^.;:]*','',text,flags=re.I)
    return re.split(r'[“"]',text,maxsplit=1)[0][:440]


DIRECT=re.compile(r'(?:điểm\s+[a-zđ]\w?\s+)?(?:khoản\s+\d+[a-zđ]?\s+)?điều\s+\d+[a-zđ]?\s+(?:của\s+)?(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Nghị\s+định|'
                  r'Nghị\s+quyết(?:\s+liên\s+tịch)?|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định|Chỉ\s+thị)\s+(?:số\s*)?('+NUMBER.pattern+')',re.I)


def direct_target(unit):
    """The document whose provision the unit itself names ("Bỏ … Điều 17 Thông tư số 55/2016/TT-BTC"), or None.
    A history note naming the document that amended it earlier is not the target."""
    match=DIRECT.search(frame(unit))
    return re.sub(r'\s+','',match[1]) if match else None


NAMED_LAW=re.compile(r'\b(Bộ\s+luật|Luật|Pháp\s+lệnh)\s+(?!này\b|số\b)([A-ZĐÀ-Ỹ][^.;:()“”"\n]*?)'
                     r'(?=\s+và\s+(?:các\s+)?(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\b|\s+(?:số|năm|ngày|đã|được|như\s+sau|tại|theo)\b|\s*[.;:(“"]|\s*$)')


def named_law(text,parsed):
    """A law or ordinance the text names without a number ("… một số điều của Luật Quy hoạch đô thị và nông thôn"):
    its number from the legal basis when listed there, else its name ("Luật Quy hoạch đô thị và nông thôn")."""
    from .references import basis_targets  # references imports this module
    # The name runs to the end of the heading: it may hold "và" and commas ("Luật Thi đua, Khen thưởng").
    match=NAMED_LAW.search(frame(text))
    if not match:
        return None
    name=re.sub(r'\s+',' ',match[2]).strip()
    number,_=basis_targets(parsed.get('can_cu')).get(name.casefold(),(None,None))
    return number or re.sub(r'\s+',' ',match[1])+' '+name


DOCUMENT_TYPE=(r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh|Nghị\s+định|Nghị\s+quyết(?:\s+liên\s+tịch)?|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định|Chỉ\s+thị'
               r'|Công\s+văn|Văn\s+bản)')
LIST_GAP=re.compile(r'(?:\s*ngày\s+[\d\s/.\-]+(?:tháng\s+\d+\s+năm\s+\d+)?)?(?:\s+(?:của|do)\s+[^;.\d]{0,120}?)?\s*(?:,\s*và|,|;|và)\s*'
                    r'(?:các\s+)?(?:Quyết\s+định|Nghị\s+định|Thông\s+tư(?:\s+liên\s+tịch)?|Nghị\s+quyết|Chỉ\s+thị|Công\s+văn|Văn\s+bản|Luật|Pháp\s+lệnh)?\s*(?:số\s*)?',re.I)


def listed_after(declaration,found):
    """Documents named right after the first one in the same list, with only dates, issuers and "và" between them."""
    extra=[]
    for previous,current in zip(found,found[1:]):
        if not LIST_GAP.fullmatch(declaration[previous.end():current.start()]):
            break
        extra.append(current)
    return extra


def acting_points(points):
    """Do the points of a clause each perform an act ("a) Sửa đổi điểm a …; b) Bãi bỏ …")? New content quoted under a lead
    is a list of rules, of which only a few happen to mention a verb: a majority of points must carry their own act."""
    acting=sum(1 for p in points if action_matches(frame(p['noi_dung'])))
    return acting*2>len(points) and any(opens_with_act(p['noi_dung']) for p in points)


def opens_with_act(text):
    """The unit opens with its own act ("Sửa đổi …", "Bãi bỏ …", "Thay thế cụm từ …"), not new content that merely mentions one."""
    found=action_matches(frame(text).lstrip()[:60])
    return bool(found) and found[0][0]<=12


def listing(lead):
    """A lead that performs an act on a list that follows ("Bãi bỏ các quy định sau:", "các quy định sau đây hết hiệu lực:"),
    not one that introduces new content ("Điều 5 được sửa đổi như sau:")."""
    return bool(action_matches(frame(lead))) and not re.search(r'như\s+sau\s*[:.]',lead or '',re.I)


def sub_point(text):
    """'gạch đầu dòng thứ ba điểm b' -> 3: the dash item of a point that the text names, or None."""
    match=SUB_POINT.search(text)
    return ordinal(match[1]) if match and re.match(r'điểm\b',text[match.end():],re.I) else None


def bullet_units(text):
    """A unit listing two or more "- ..." items declares one change per item: (lead, items)."""
    lines=text.split('\n')
    starts=[i for i,line in enumerate(lines) if re.match(r'^\s*[-+•–]\s*\S',line)]
    if len(starts)<2:return text,[]
    items=['\n'.join(lines[i:j]).strip() for i,j in zip(starts,starts[1:]+[len(lines)])]
    return '\n'.join(lines[:starts[0]]).strip(),items


def declared_scope(unit, parent='', action=None):
    """Resolve an explicit target location, inheriting only its parent article.

    Do not infer a whole provision when changing words or sentences within it.
    Insertion anchors ("vào sau điểm đ") are not the provision being added.
    """
    declaration=frame(unit)
    if not action_matches(declaration):return None
    if re.search(r'\b(?:cụm từ|từ ngữ|câu|đoạn(?!\s+đầu))\b',declaration,re.I):return None
    # Independent actions in one declaration can affect different provisions.
    # "…; bổ sung khoản 1a …", "… và bổ sung …" start another act; the verb pair "sửa đổi, bổ sung" is one act on one place.
    parts=re.split(r'(?:\s*;\s*(?:và\s+)?|(?<!sửa\sđổi)(?<!điều\schỉnh),\s*(?:và\s+)?|\s+và\s+)(?=(?:bổ sung|sửa đổi|bãi bỏ|thay thế|bỏ)\b)',declaration,flags=re.I)
    # Provisions named after the document the act is on describe that document ("thay thế Quyết định số 42/2018/QĐ-UBND …
    # sửa đổi Điểm a, Khoản 2 Điều 3 …" is the replaced decision's name), not where it changes.
    def own(part):
        acts=action_matches(part)
        after=[m for m in document_refs(part) if acts and m.start()>=acts[0][1]]
        return part[:after[0].start()] if after else part
    parts=[own(part) for part in parts]
    stated='; '.join(parts)
    parent_articles=re.findall(r'\bđiều\s+(\d+[a-zđ]?)\b',frame(parent),re.I)
    inherited=parent_articles[0] if len(set(parent_articles))==1 else None
    parent_clauses=re.findall(r'\bkhoản\s+(\d+[a-zđ]?)\b',frame(parent),re.I)
    inherited_clause=parent_clauses[0] if len(set(parent_clauses))==1 else None
    unit_articles=re.findall(r'\bđiều\s+(\d+[a-zđ]?)\b',stated,re.I)
    if len(set(unit_articles))==1:inherited=unit_articles[0]
    # "Sửa đổi điểm b và bổ sung điểm đ khoản 2 Điều 4": a part without its own clause takes the one named once after it.
    unit_clauses=re.findall(r'\bkhoản\s+(\d+[a-zđ]?)\b',stated,re.I)
    if len(set(unit_clauses))==1 and not inherited_clause:inherited_clause=unit_clauses[0]
    values=[]
    for part in parts:
        actions={a for _,_,a in action_matches(part)}
        if action and action not in actions:continue
        part=re.sub(r'\s+vào\s+(?:sau|trước)\s+(?:điểm\s+[a-zđ]\w*|khoản\s+\d+[a-zđ]?|điều\s+\d+[a-zđ]?)','',part,flags=re.I)
        name=NAMED.search(part)
        if name:
            values.append(named(name));continue
        article=re.search(r'\bđiều\s+(\d+[a-zđ]?)\b',part,re.I)
        article_number=article[1] if article else inherited
        point_label=r'(?:\d+(?:\.\d+)+|[a-zđ]\d*)(?![\wÀ-ỹ])'  # "điểm d, khoản 1": "khoản" is not a point label
        points=re.search(r'\bđiểm\s+('+point_label+r'(?:(?:\s*,\s*|\s+và\s+)(?:điểm\s+)?'+point_label+r')*)\b',part,re.I)
        clauses=re.search(r'\bkhoản\s+(\d+[a-zđ]?(?:(?:\s*,\s*|\s+và\s+)(?:khoản\s+)?\d+[a-zđ]?)*)\b',part,re.I)
        clause_number=clauses[1] if clauses else inherited_clause
        sub=sub_point(part)
        if points and clause_number and article_number and sub and not re.search(r'[,\s]và\s|,',points[1]):
            value=f'tiểu điểm {sub} điểm {points[1]} khoản {clause_number} Điều {article_number}'
        elif points and clause_number and article_number:
            value=f'điểm {points[1]} khoản {clause_number} Điều {article_number}'
        elif clauses and article_number:
            prefix='đoạn đầu ' if re.search(r'đoạn\s+đầu\s+khoản',part,re.I) else ''
            value=f'{prefix}khoản {clauses[1]} Điều {article_number}'
        elif article and not points:
            value,unresolved=scope(part)
            if unresolved:return None
        else:return None
        # "Bãi bỏ khoản 6, khoản 7 Điều 4; khoản 2 Điều 6", "Sửa đổi, bổ sung Điều 36 và Điều 37": keep every position, not only the first.
        # The list read item by item is the more exact when it differs: "khoản 1 và điểm c, điểm đ khoản 3 Điều 15" is not "điểm c,
        # điểm đ khoản 1"; the value above only stays when it names more (levels the list takes from the lead, H3 21/10/2026).
        listed=positions(re.sub(r'^.*?\b(?:bãi\s+bỏ|bỏ|sửa\s+đổi(?:,\s*bổ\s+sung)?|bổ\s+sung|thay\s+thế|hủy\s+bỏ|huỷ\s+bỏ)\s+','',part,count=1,flags=re.I),
                         (inherited_clause,inherited))
        if listed and not set(listed)<set(positions(value)):
            value='; '.join(listed)
        values.append(value)
    return '; '.join(dict.fromkeys(values)) if values else None


NAMED=re.compile(r'\btên\s+(?:gọi\s+)?(?:của\s+)?(?:(?P<muc>mục\s+\d+)\s+)?(?:(?P<chuong>chương\s+[IVXLCDM\d]+)|(?P<dieu>điều\s+\d+[a-zđ]?)|(?P<phuluc>phụ\s+lục\s+[IVXLCDM\d]+))'
                 r'|\btên\s+(?P<muc_only>mục\s+\d+)',re.I)


def named(match):
    """'tên Mục 2 Chương II', 'tên Điều 42': the heading of a provision or section is itself a position."""
    parts=[match['muc'] or match['muc_only'],match['chuong'] or match['dieu'] or match['phuluc']]
    words=[re.sub(r'^(\w)',lambda m:m[1].upper(),' '.join(x.split())) for x in parts if x]
    return 'tên '+' '.join(words)


def scope(text):
    name=NAMED.search(text)
    if name:return named(name),False
    whole=re.search(r'một\s+số\s+(?:điều|nội\s+dung)',text,re.I)
    if re.search(r'một\s+số\s+(?:từ\s*,\s*)?(?:cụm\s+)?từ(?:\s+ngữ)?\b',text,re.I):return 'một số cụm từ',False
    forms=re.search(r'(?:các\s+)?mẫu\s*(?:biểu\s*)?(?:số\s*)?([\w./-]+(?:\s*(?:,|và)\s*(?:mẫu\s*(?:số\s*)?)?[\w./-]+)*)',text,re.I)
    if forms and re.search(r'\d',forms[1]):
        # A form has no node of its own: keep the appendix the sentence puts it in, for positions() to use.
        appendix=re.match(r'\s*(?:(?:tại|thuộc|của|trong|ở)\s+)?(phụ\s+lục\s+(?:số\s+)?(?:[IVXLCDM]+|\d+[A-Za-z]?)\b)',text[forms.end():forms.end()+80],re.I)
        tail=' '+appendix[1] if appendix else ''
        return '; '.join('Mẫu số '+f+tail for f in re.split(r'\s*(?:,|và)\s*(?:mẫu\s*(?:số\s*)?)?',forms[1],flags=re.I) if f),False
    if re.search(r'(?:sửa\s+đổi\s+tên|tên\s+gọi)(?!\s+(?:của\s+)?(?:điều|chương|mục|phụ\s+lục))',text,re.I) and not NAMED.search(text):return 'tên văn bản',False
    fee=re.search(r'(?:bãi bỏ|hủy bỏ|huỷ bỏ|thay thế)\s+toàn bộ\s+((?:lệ phí|phí)\b[^.\n;]*)',text,re.I)
    if fee:return fee[1].strip(),False
    # "đoạn 3, điểm a, khoản 2, Điều 4" is one position, "điểm a khoản 2 Điều 4"; "Mục I, Phần I Phụ lục" is "Mục I Phần I Phụ lục".
    text=levels(text)
    patterns=[r'tiểu\s+điểm\s+\d+\s+điểm\s+[a-zđ]\w?\s+khoản\s+\d+[a-zđ]?\s+điều\s+\d+[a-zđ]?',
        r'điểm\s+\d+(?:\.\d+)+\s+khoản\s+\d+\s+điều\s+\d+',
        # "toàn bộ nội dung số thứ tự 51", "toàn bộ Điều 5": a part, not the whole document.
        r'toàn (?:bộ|văn)(?!\s+(?:nội\s+dung|các|điều|khoản|điểm|chương|mục|phần|phụ\s+lục|số\s+thứ\s+tự|danh\s+mục|thủ\s+tục)\b)',
        r'(?:số )?thứ tự\s+[\d, và]+',IN_APPENDIX.pattern,r'phụ lục\s+[IVXLCDM\d]+',
        r'phụ lục(?=\s+(?:được\s+)?(?:ban hành\s+)?kèm theo)',
        r'điểm\s+[a-zđ](?:\s*[, và]+\s*(?:điểm\s+)?[a-zđ])*\s+khoản\s+\d+[a-zđ]?\s+điều\s+\d+[a-zđ]?',
        r'khoản\s+\d+[a-zđ]?(?:\s*[, và]+\s*(?:khoản\s+)?\d+[a-zđ]?)*\s+điều\s+\d+[a-zđ]?',
        r'điều\s+\d+[a-zđ]?(?:\s*[, và]+\s*\d+[a-zđ]?)*',r'khoản\s+\d+[a-zđ]?(?:\s*[, và]+\s*\d+[a-zđ]?)*',
        r'mục\s+'+SECTION+r'(?:\s+(?:của\s+)?chương\s+[IVXLCDM\d]+)?',r'chương\s+[IVXLCDM\d]+',
        ]
    for pattern in patterns:
        match=re.search(pattern,text,re.I)
        if match:
            value=match.group().strip()
            if value.casefold()=='phụ lục':value='Phụ lục'  # the target's single, unnumbered appendix
            return ('toàn bộ' if value.casefold()=='toàn văn' else value),False
    if whole:return 'một số điều',False
    return 'chưa xác định',True


NAMED_CONTENT=re.compile(r'(?:thay\s+thế|b[ãả]i\s+bỏ|h(?:uỷ|ủy|uy)\s+bỏ|sửa\s+đổi(?:,\s*bổ\s+sung)?|bổ\s+sung)\s+(?:toàn\s+bộ\s+)?(?:nội\s+dung\s+)?(?P<obj>(?:[^.;]|(?<=[\dA-Z])\.(?=\d)){3,200}?)\s*'
    r'(?P<link>(?:(?:đã\s+)?được\s+(?:[^.;]{0,60}?\s)?)?ban\s+hành\s+kèm\s+theo|công\s+bố\s+tại|(?:đã\s+|được\s+)?ban\s+hành\s+tại|quy\s+định\s+tại|tại)\s+'
    r'(?:các\s+)?(?:Quyết\s+định|Văn\s+bản|văn\s+bản|Thông\s+tư(?:\s+liên\s+tịch)?|Nghị\s+định|Chỉ\s+thị|Nghị\s+quyết)\s*(?:số\s*)?$',re.I)


def named_content(scope_text):
    """'thay thế đơn giá khảo sát ban hành kèm theo Quyết định số' -> ('đơn giá khảo sát', True): a part named, not numbered."""
    numbers=document_refs(scope_text)
    match=NAMED_CONTENT.search((scope_text[:numbers[0].start()] if numbers else scope_text).strip())
    if not match or re.search(r'\b(?:điều|khoản|điểm)\s+\d',match['obj'],re.I):return None,False
    obj=re.sub(r'\s+(?:đã\s+)?được\s*$','',' '.join(match['obj'].split()))
    return obj,'kèm theo' in match['link']


CATALOGUE=re.compile(r'\b(danh\s+mục\s+[^.;:()\n]{3,150}?)\s+(?:được\s+)?(?:ban\s+hành\s+|công\s+bố\s+)?kèm\s+theo\b',re.I)


def appendix_of(text):
    """The appendix a text names, with its section when given: "… Mục I, Phần I Phụ lục công bố kèm theo …" -> "Mục I Phần I Phụ lục",
    "… tại Phụ lục V ban hành kèm theo Nghị định số 37/2024/NĐ-CP" -> "Phụ lục V". None when it names none, or several."""
    text=levels(frame(text or ''))
    chain=IN_APPENDIX.search(text)
    if chain:
        return positions(chain.group())[0]
    labels=set(re.findall(r'phụ\s+lục\s+(?:số\s+)?([IVXLCDM]+|\d+[A-Za-z]?)\b',text,re.I))
    return f'Phụ lục {labels.pop()}' if len(labels)==1 else None


def document_part(text):
    """A part a correction names without a number: the document's legal bases or its recipients."""
    if re.search(r'căn\s+cứ\s+(?:pháp\s+lý|ban\s+hành)|phần\s+căn\s+cứ',text,re.I):return 'phần căn cứ'
    if re.search(r'\bnơi\s+nhận\b',text,re.I):return 'phần Nơi nhận'
    return None


PLACE=re.compile(r'\b(?:tại|ở)\s+(?:(?:các\s+)?số\s+)?(?:thứ\s+tự|điểm|khoản|điều|mục|phụ\s+lục|chương)\b',re.I)


# Letters (no Điều) are read only for these actions; the others keep article-only detection until measured on letters.
LETTER_ACTIONS={'dinh-chinh','ngung-hieu-luc','gia-han'}


def detect(doc_id,meta,parsed):
    if meta.get('legal_type')=='Văn bản hợp nhất':return []
    candidates=[];title_actions=action_matches(meta.get('title',''))
    correction=any(a=='dinh-chinh' for _,_,a in title_actions)
    def add(target,action,path,text,scope_text,mode='',extra_scope=None,in_appendix=False,unit_text=None,parent_text='',stated=False):
        value,unresolved=scope(scope_text)
        explicit=declared_scope(scope_text,parent_text,action)
        if explicit:value,unresolved=explicit,False
        if extra_scope:value,unresolved=extra_scope,False
        if not target:return
        # A number loses its spaces ("75/2017/TT- BTC"); a law named by name keeps them.
        target=re.sub(r'\s+','' if NUMBER.fullmatch(target.strip()) or not re.match(r'(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s',target) else ' ',target.strip()).replace('Ð','Đ')
        extra={}
        unit=unit_text if unit_text is not None else text
        if re.match(r'(?:số\s+)?thứ\s+tự\b',value or '',re.I):
            # A numbered row of a list has no node: the position is the appendix (or its section) that holds it,
            # else the list named ("Danh mục hàng hóa … ban hành kèm theo Quyết định số …").
            holder=appendix_of(scope_text) or appendix_of(parent_text)
            catalogue=None if holder else CATALOGUE.search(frame(scope_text)+'\n'+frame(parent_text))
            if holder:value=holder
            elif catalogue:
                value=' '.join(catalogue[1].split());extra.update(doi_tuong=value,kem_theo=True)
        elif re.fullmatch(r'mục\s+'+SECTION,value or '',re.I) and not re.search(r'\bchương\s+[IVXLCDM\d]',frame(parent_text),re.I):
            # "Bổ sung Mục 6" under "Sửa đổi, bổ sung Phụ lục III …": the section belongs to the appendix the lead names.
            holder=appendix_of(parent_text)
            if holder and holder.startswith('Phụ lục'):value=f'{value} {holder}'
        if unresolved and action in ('thay-the','bai-bo','huy-bo','sua-doi','bo-sung'):
            obj,attached=named_content(scope_text)
            if obj:value,unresolved=obj,False;extra.update(doi_tuong=obj,kem_theo=attached)
        context=lead_context(parent_text)
        if action=='thay-cum-tu':
            # Wording replacements list their own locations; the first number in the list is not the scope.
            pairs,places=phrase_change(unit,context)
            if places:value,unresolved='; '.join(places),False
            extra.update(cum_tu=pairs,vi_tri=places)
        elif action=='dinh-chinh':
            # A correction lists every place it fixes ("Tại điểm b khoản 7 Điều 3 và khoản 2 Điều 6, bỏ …").
            places=stated_positions(frame(unit),context)
            if places:
                value,unresolved='; '.join(places),False;extra['vi_tri']=places
            elif unresolved and document_part(frame(unit)):
                part=document_part(frame(unit))
                value,unresolved=part,False;extra.update(doi_tuong=part,kem_theo=False)
        elif context and (unresolved or (re.match(r'(?:đoạn đầu\s+)?(?:điểm|khoản)\b',value,re.I) and not re.search(r'\bđiều\s+\d',value,re.I))):
            # "tại khoản 1", "Bổ sung các điểm đ và e vào khoản 2": the lead sentence names the Điều (and khoản).
            plain=re.sub(r'“[^”]*”|"[^"]*"',' ',frame(unit))
            into=re.search(r'(?:bổ\s+sung|thêm)\s+(?:các\s+)?((?:điểm|khoản)\s+.+?)\s+vào\s+(?:sau\s+\S+\s+\S+\s+(?:của\s+)?)?((?:khoản|điều)\s+\S+)',plain,re.I)
            where=re.search(r'\b(?:tại|ở)\s+(.+)$',plain,re.I|re.S)
            places=positions(f'{into[1]} {into[2]}' if into else (where[1] if where else value),context)
            if places:value,unresolved='; '.join(places),False
        if action in SUSPENSIONS:
            extra.update(suspension(unit))
        elif action=='gia-han':
            extra.update(extension(unit))
        if action in ('bai-bo','huy-bo','thay-the','dinh-chi','ngung-hieu-luc','gia-han') and re.search(
                r'(?:bãi bỏ|hủy bỏ|huỷ bỏ|thay thế|đình\s*chỉ(?:\s+việc)?\s+(?:thi\s*hành|thực\s*hiện)'
                r'|ng(?:ư|ừ)ng\s+(?:thi\s+hành\s+)?hiệu\s*lực(?:\s+thi\s+hành)?(?:\s+(?:của|đối\s+với))?'
                r'|(?:gia\s+hạn|kéo\s+dài)\s+(?:thời\s+(?:hạn|gian)\s+)?(?:hiệu\s*lực|áp\s+dụng)(?:\s+thi\s+hành)?(?:\s+của)?)\s+(?:toàn bộ\s+)?'
                r'(?:Quyết định|Nghị quyết|Nghị định|Thông tư(?: liên tịch)?|Luật|Bộ luật|Pháp lệnh|Chỉ thị)(?:\s+[^.;,\d]{0,80}?)?\s+(?:số\s*)?$',scope_text,re.I):
            value,unresolved='toàn bộ',False
        candidates.append({'target_doc':target,'action':action,'source_path':path,'scope':value,
            'unresolved':unresolved,'source_in_phu_luc':in_appendix,'_mode':mode,'_evidence':text[:4000],
            '_unit_evidence':(unit_text if unit_text is not None else text)[:4000],
            '_parent_evidence':parent_text[:2000],'_stated':stated,**extra})
    articles=[(a,'',False) for a in parsed['dieu_luat']]
    articles += [(a,f'Phụ lục {i+1} ',True) for i,p in enumerate(parsed['phu_luc']) for a in p['dieu_luat']]
    for article,prefix,in_appendix in articles:
        if article.get('van_ban_kem_theo'):prefix+=f'Văn bản kèm theo {article["van_ban_kem_theo"]} '
        path=prefix+'Điều '+article['ky_hieu']
        title,body=article['tieu_de'],article['noi_dung']
        if not title and not article['khoan']:
            # An untitled article opens with its content sentence, which plays the heading's role here;
            # with Khoản, that sentence already leads mo_dau.
            title,_,body=body.partition('\n')
        head=title+' '+article.get('mo_dau','')
        effect=bool(re.search(r'hiệu\s*lực|thi\s+hành|chuyển\s+tiếp',title,re.I))
        chapter=article.get('chuong','')
        head_refs=document_refs(head);chapter_refs=refs(chapter)
        matches=action_matches(head)
        target=None;mode='' if title_actions else 'hidden'
        if title_actions:
            target=head_refs[0].group() if head_refs else (chapter_refs[0] if chapter_refs else named_law(head,parsed))
        else:
            for start,end,action in matches:
                if any(m.start()<start for m in head_refs):continue
                if re.search(r'(?:đã|đang|sẽ)\s+(?:được|bị)\s*$',head[max(0,start-40):start],re.I):continue
                following=[m for m in head_refs if m.start()>end]
                if following:target=following[0].group();break
                if chapter_refs:target=chapter_refs[0];break
                law=named_law(head[end:],parsed)
                if law:target=law;break
        if target and target in head:
            target_position=head.find(target)
            matches=[m for m in matches if m[1]<=target_position]
        default=(matches or title_actions)
        if target and default:
            if article['khoan']:
                # "Điều 3. Ngưng hiệu lực … tại Phụ lục V …: 1. Cá trích xương … tại số thứ tự 36 mục 1. 2. …": clauses with no act
                # of their own, each naming a place, are the items the heading acts on; each states its own impact.
                items=sum(1 for c in article['khoan'] if not c['diem'] and not action_matches(frame(c['noi_dung'])))>=2
                for clause in article['khoan']:
                    clause_path=path+' Khoản '+clause['ky_hieu']
                    # "Điều 34 được sửa đổi như sau: a) ... b) ...": points without their own change are the new content.
                    # "Bãi bỏ các quy định sau: a) …; b) …": each point names its own place and takes the lead's act.
                    listed=clause['diem'] and listing(clause.get('mo_dau',''))
                    own=clause['diem'] and not listed and acting_points(clause['diem'])
                    units=[(clause_path+' điểm '+p['ky_hieu'],p['noi_dung']) for p in clause['diem']] if own or listed else [(clause_path,clause['noi_dung'])]
                    for unit_path,unit in units:
                        declaration=frame(unit)
                        if listed:
                            # Words after the item's document number describe that document ("Thông tư 14/2015 sửa đổi …"), not this act.
                            named=document_refs(declaration)
                            actions=action_matches(declaration[:named[0].start()] if named else declaration) or action_matches(frame(clause['mo_dau'])) or default[:1]
                        else:
                            actions=action_matches(declaration) or default[:1]
                        if correction:
                            # In a correction, "bỏ dấu / bỏ cụm từ" is part of correcting, not a repeal.
                            actions=[a for a in actions if not (a[2]=='bai-bo' and declaration[a[0]:a[1]].casefold().startswith('bỏ'))] or default[:1]
                        if listed:
                            unit=frame(clause['mo_dau'])+' '+unit
                        # The unit's own sentence may name the document it changes directly; that one is the target.
                        named=document_refs(frame(unit)) if listed else []
                        unit_target=direct_target(unit) or (re.sub(r'\s+','',named[0].group()) if named else None) or target
                        item=items and not own and not listed and not action_matches(declaration) and len(unit)<300 and bool(PLACE.search(unit))
                        for _,_,action in actions:
                            # A point inherits the Điều/Khoản named in its clause lead ("... khoản 6, khoản 7a Điều 3 như sau: a) ...").
                            add(unit_target,action,unit_path,chapter+'\n'+head+'\n'+(clause.get('mo_dau','')+'\n'+unit if own else unit),declaration,mode,in_appendix=in_appendix,unit_text=unit,
                                parent_text=(clause.get('mo_dau','') if own and re.search(r'\bđiều\s+\d',frame(clause.get('mo_dau','')),re.I) else head),stated=item)
            elif opens_with_act(body):
                # "Điều 36. Bổ sung, thay thế, bãi bỏ một số cụm từ …" whose body is one act ("Thay thế cụm từ … tại khoản 1 Điều 41"):
                # the body's own act and place, not every verb of the heading.
                declaration=frame(body)
                for _,_,action in action_matches(declaration):
                    add(direct_target(body) or target,action,path,chapter+'\n'+head+'\n'+body,declaration,mode,in_appendix=in_appendix,unit_text=body,parent_text=head)
            else:
                source=head+'\n'+body;declaration=frame(source)
                before=declaration.split(target,1)[0]
                named=document_refs(declaration)
                first=next((i for i,m in enumerate(named) if re.sub(r'\s+','',m.group())==target),None)
                extras=listed_after(declaration,named[first:]) if first is not None else []
                for _,_,action in (matches or default):
                    add(target,action,path,chapter+'\n'+source,before,mode,in_appendix=in_appendix,unit_text=source,parent_text=head)
                    for extra in extras:  # "thay thế Quyết định số A … và Quyết định số B …"
                        add(extra.group(),action,path,chapter+'\n'+source,before,mode,in_appendix=in_appendix,unit_text=source,parent_text=head)
        # The article on effect may perform an act in its own sentence ("Thông tư này có hiệu lực … và thay thế Thông tư liên tịch số …").
        elif title_actions or matches or article['khoan'] or effect or any(action_matches(frame(item)) for item in bullet_units(body)[1]):
            units=[(path,article.get('mo_dau',''))];lists=[]
            if not article['khoan']:units.append((path,head+'\n'+body))
            for clause in article['khoan']:
                kpath=path+' Khoản '+clause['ky_hieu']
                if clause['diem'] and listing(clause.get('mo_dau','')):
                    lists.extend((kpath+' điểm '+p['ky_hieu'],p['noi_dung'],clause['mo_dau']) for p in clause['diem'])
                elif clause['diem'] and acting_points(clause['diem']):
                    units.append((kpath,clause.get('mo_dau','')))
                    units.extend((kpath+' điểm '+p['ky_hieu'],p['noi_dung']) for p in clause['diem'])
                else:units.append((kpath,clause['noi_dung']))
            expanded=list(lists)
            for unit_path,text in units:
                lead,items=bullet_units(text)
                # Each listed item names its own target; it inherits the action of its lead sentence.
                expanded+=[(unit_path,lead,'')]+[(unit_path,item,lead) for item in items] if items else [(unit_path,text,'')]
            for unit_path,text,lead in expanded:
                declaration=frame(text);found=document_refs(declaration);match=found[0] if found else None
                if match:
                    # In the article on effect, only the sentence naming the document acts on it ("Bãi bỏ các quy định trái …. Quyết định số …").
                    direct=action_matches(re.split(r'(?<=[.;])\s',declaration[:match.start()])[-1] if effect else declaration[:match.start()])
                    inherited=action_matches(frame(lead)) or matches or title_actions[:1]
                    for _,_,action in (direct or inherited):
                        context=head+'\n'+(lead+'\n' if lead else '')+text if matches or lead else text
                        # An item of "Bãi bỏ các văn bản sau:" / "Các Thông tư sau đây hết hiệu lực:" that names no provision is a whole document.
                        document_list=not direct and (matches or lead) and action in ('bai-bo','huy-bo','thay-the') and (
                            re.search(r'(?:bãi bỏ|hủy bỏ|huỷ bỏ|thay thế)\s+các\s+(?:văn bản|Quyết định|Thông tư|Nghị định|Nghị quyết)\b',head+' '+lead,re.I)
                            or (re.search(r'sau\s+(?:đây\s+)?hết\s+hiệu\s*lực',lead,re.I) and not re.search(r'\b(?:điều|khoản|điểm|chương|phụ\s+lục)\s+\S',declaration[:match.start()],re.I)))
                        add(match.group(),action,unit_path,context,declaration[:match.start()],extra_scope='toàn bộ' if document_list else None,in_appendix=in_appendix,unit_text=text,parent_text=head)
                        # "thay thế Quyết định số A ngày … và Quyết định số B …": each document of the list is a relation.
                        for extra in listed_after(declaration,found):
                            add(extra.group(),action,unit_path,context,declaration[:match.start()],extra_scope='toàn bộ' if document_list else None,in_appendix=in_appendix,unit_text=text,parent_text=head)
        units=[(path,head+' '+body)] if not article['khoan'] else [(path,head)]+[(path+' Khoản '+k['ky_hieu'],k['noi_dung']) for k in article['khoan']]
        for unit_path,text in units:
            for match in re.finditer(r'hết\s*hiệu\s*lực(?:\s*thi\s*hành)?(?:\s*kể)?\s*từ\s*ngày',text,re.I):
                after=text[match.end():match.end()+60]
                # "… hết hiệu lực kể từ ngày Thông tư này có hiệu lực", or from a stated day in the article on effect.
                if not (re.search(r'này\s+có\s+hiệu\s+lực',after,re.I) or (effect and re.match(r'\s*'+DATE,after))):continue
                if re.search(r'\b(?:đã|bị)\s*$',text[max(0,match.start()-12):match.start()],re.I):continue  # a past fact, not this act
                # The subject of "… hết hiệu lực": the sentence before it, without history notes ("… đã được sửa đổi, bổ sung
                # một số điều theo Luật số 21/2017/QH14 và Luật số 23/2018/QH14": both amending laws are part of the note).
                # A list of items split by ';' ("… Phụ lục I kèm theo Quyết định số 560/…; Phụ lục kèm theo Quyết định số 2401/…") is one subject.
                before=list_tail(text[max(0,match.start()-1500):match.start()])
                before=re.sub(r',?\s*(?:đã\s+)?được\s+(?:sửa\s*đổi(?:,?\s*bổ\s*sung)?|bổ\s*sung|thay\s+thế).{0,80}?(?:theo|tại|bởi).{0,120}?(?=[,;]|$)','',before,flags=re.I)
                # The documents that end are the first one named and those listed with it: after ',', 'và', or in a new item after ';'.
                # A number inside the name of one of them ("Thông tư số 143/2020/TT-BQP … hướng dẫn thực hiện … Nghị định số
                # 146/2018/NĐ-CP") is not.
                named,end=[],0
                for i,m in enumerate(document_refs(before)):
                    if i==0 or ';' in before[end:m.start()] or re.search(r'(?:,|;|\bvà)\s*(?:(?:các\s+)?'+DOCUMENT_TYPE+r'\s*)?(?:số\s*)?$',before[:m.start()],re.I):
                        named.append((before[end:m.start()],m))
                    end=m.end()
                # Each document ends as far as the words before its own number say: "số thứ tự 1 Mục II Phụ lục II kèm theo Quyết định
                # số 1659/…" ends that part of 1659, not 1659 as a whole. Only an item that names no part ends a document as a whole.
                for k,(segment,m) in enumerate(named):
                    part=segment.split(';')[-1]
                    partial=re.search(PART_NAMED,part,re.I)
                    add(re.sub(r'\s+','',m.group()),'bai-bo',unit_path,text,part if partial else before,'het_hieu_luc',
                        row_holders(part) if partial else 'toàn bộ',in_appendix,stated=True)
    declared={a for _,_,a in title_actions}&LETTER_ACTIONS
    if not parsed['dieu_luat'] and declared:
        # A letter whose title declares the act performs it in a numbered paragraph ("1. Đồng ý gia hạn hiệu lực của Quyết định …").
        sections=parsed.get('noi_dung_sections') or [{'so_muc':None,'noi_dung':parsed.get('noi_dung','')}]
        for section in sections:
            # The first paragraph carries the letter's preamble, which ends "… có ý kiến như sau:".
            text=re.split(r'như\s+sau\s*:',section['noi_dung'],flags=re.I)[-1].strip()
            declaration=frame(text)
            for _,end,action in action_matches(declaration):
                found=[m for m in document_refs(declaration) if m.start()>=end]
                if action in declared and found:
                    path=f'Mục {section["so_muc"]}' if section['so_muc'] else 'Nội dung'
                    add(found[0].group(),action,path,section['noi_dung'],declaration[:found[0].start()],unit_text=text)
    intro=parsed.get('intro','')
    for start,end,action in action_matches(intro):
        if NUMBER.search(intro[:start]) or re.search(r'(?:đã|đang|sẽ)\s+(?:được|bị)\s*$',intro[max(0,start-40):start],re.I):continue
        match=NUMBER.search(intro,end)
        if match and 'BC-' not in match.group():
            add(match.group(),action,'intro',intro,intro[end:match.start()],'intro')
    # The intro keeps its own relations beside the articles' relations to the same target.
    seen=set();result=[]
    for candidate in candidates:
        key=tuple(candidate[k] for k in ('target_doc','action','source_path','scope'))
        if key not in seen:
            seen.add(key);result.append(candidate)
    result.sort(key=lambda x:(x['_mode'],x['source_path'],x['target_doc'],x['action'],x['scope']))
    counts=defaultdict(int)
    for candidate in result:
        mode=candidate.pop('_mode');i=counts[mode];counts[mode]+=1
        prefix={'hidden':'hidden_','het_hieu_luc':'hhl_','intro':'intro_'}.get(mode,'')
        candidate['_id']=f'{prefix}{doc_id}_{i}'
        stamp(candidate,doc_id,meta)
        if mode:candidate['detection_mode']=mode
    return result


def stamp(candidate,doc_id,meta):
    """The source fields every relation carries."""
    candidate.update(source_id=int(doc_id),source_document_number=meta.get('document_number'),source_title=meta['title'],
        source_action=meta['action'],source_issuing_authority=meta['issuing_authority'],source_issuance_date=meta.get('issuance_date'),
        source_legal_type=meta['legal_type'],source_legal_sectors=', '.join(meta.get('legal_sectors',[])),source_url=meta.get('url'))
    return candidate


def consolidation(doc_id,meta,parsed):
    """A consolidated text (Văn bản hợp nhất) restates the base document its opening names first:
    "Nghị quyết số 131/2020/QH14 …, được sửa đổi, bổ sung bởi: Nghị quyết số 96/2023/QH15 …" gives one hop-nhat relation to 131/2020/QH14."""
    if meta.get('legal_type')!='Văn bản hợp nhất':return []
    opening=parsed.get('phan_dau') or ''
    own=number_key(meta.get('document_number'))
    def in_title(m):
        line=opening[opening.rfind('\n',0,m.start())+1:opening.find('\n',m.end()) if opening.find('\n',m.end())>=0 else len(opening)]
        return line.upper()==line
    numbers=list(dict.fromkeys(re.sub(r'\s+','',m.group()) for m in document_refs(opening) if number_key(m.group())!=own and not in_title(m)))
    # The text restates its base document, the first one named. The amending ones listed after "được sửa đổi, bổ sung bởi"
    # and documents the base one cites are notes, not what is restated.
    numbers=numbers[:1]
    rows=[]
    for number in numbers:
        rows.append({'_id':f'hn_{doc_id}_{len(rows)}','target_doc':number,'action':'hop-nhat','source_path':'Phần đầu','scope':'toàn bộ',
            'unresolved':False,'source_in_phu_luc':False,'detection_mode':'hop_nhat','_evidence':opening[:4000],
            'source_id':int(doc_id),'source_document_number':meta.get('document_number'),'source_title':meta.get('title'),
            'source_action':meta.get('action'),'source_issuing_authority':meta.get('issuing_authority'),
            'source_issuance_date':meta.get('issuance_date'),'source_legal_type':meta.get('legal_type'),
            'source_legal_sectors':', '.join(meta.get('legal_sectors') or []),'source_url':meta.get('url')})
    return rows


def year_variant(number):
    """'1941/2008/QĐ-UBND' -> ('1941/QĐ-UBND', '2008'): older decisions are often registered without the year cited for them."""
    m=re.fullmatch(r'\s*(\d+)\s*/\s*((?:19|20)\d{2})\s*/\s*(\S.*)',number or '')
    if m:return m[1]+'/'+m[3],m[2]
    # Titles append the year to old numbers: "05/CP-1995" is "05/CP" issued in 1995.
    m=re.fullmatch(r'\s*(\d+\s*/\s*\S+?)-((?:19|20)\d{2})\s*',number or '')
    return (m[1],m[2]) if m else (None,None)


def lookup_numbers(numbers):
    """Numbers to fetch for resolve(): each cited number plus its year-less registration variant."""
    return list(dict.fromkeys([*numbers,*(v for v in (year_variant(n)[0] for n in numbers) if v)]))


def resolve(candidate,hits):
    exact=[h for h in hits if number_key(h['_source'].get('document_number'))==number_key(candidate['target_doc'])]
    short,year=year_variant(candidate['target_doc'])
    variant=not exact and bool(short)
    if variant:
        # Only the year-less number issued in the cited year qualifies; the authority check below is then mandatory.
        exact=[h for h in hits if number_key(h['_source'].get('document_number'))==number_key(short) and str(h['_source'].get('issuance_date') or '').startswith(year)]
    hits=exact
    candidate['target_candidates_count']=len(hits)
    eligible=[h for h in hits if h['_id'].isdigit() and int(h['_id'])!=candidate['source_id'] and
              h['_source'].get('issuance_date') and candidate.get('source_issuance_date') and h['_source']['issuance_date']<=candidate['source_issuance_date']]
    evidence=candidate.get('_evidence','')
    cited=next((m for m in NUMBER.finditer(evidence) if number_key(m.group())==number_key(candidate['target_doc'])),None)
    citation=evidence[cited.end():cited.end()+240] if cited else ''
    cited_date=candidate.get('target_issuance_date')
    match=re.search(r'ngày\s+(\d{1,2})(?:\s+tháng\s+|[/-])(\d{1,2})(?:\s+năm\s+|[/-])(\d{4})',citation,re.I)
    if match:
        try:cited_date=date(int(match[3]),int(match[2]),int(match[1])).isoformat()
        except ValueError:pass
    if cited_date:
        candidate['target_issuance_date']=cited_date
        dated=[h for h in eligible if h['_source']['issuance_date']==cited_date]
        if not dated and re.match(r'\s*\d+\s*/\s*(?:19|20)\d{2}\s*/',candidate['target_doc']):
            # A number carrying its year names one document per issuer; the cited day is sometimes mistyped
            # (cited 19/12/2008, registered 22/12/2008). Accept only a single same-year match, same issuer for local numbers.
            pool=[h for h in eligible if h['_source']['issuance_date'][:4]==cited_date[:4]]
            if re.search(r'(?:UBND|HĐND|UB)\b',candidate['target_doc']):
                issuer=authority_key(candidate.get('target_issuing_authority') or candidate.get('source_issuing_authority'))
                pool=[h for h in pool if authority_key(h['_source'].get('issuing_authority'))==issuer]
            if len(pool)==1:
                dated=pool;candidate['target_match_note']='lech_ngay_trich_dan'
        eligible=dated
    authority=candidate.get('target_issuing_authority')
    if not authority and re.search(r'\bcủa\b',citation,re.I):
        # "của Ủy ban nhân dân tỉnh X" names the authority stored as "Tỉnh X".
        tail=catalog_authority_key(re.split(r'\bcủa\b',citation,maxsplit=1,flags=re.I)[-1])
        matches={h['_source'].get('issuing_authority') for h in hits if catalog_authority_key(h['_source'].get('issuing_authority'))
                 and tail.startswith(catalog_authority_key(h['_source'].get('issuing_authority')))}
        if len(matches)==1:authority=matches.pop()
    if authority:
        candidate['target_issuing_authority']=authority
        eligible=[h for h in eligible if authority_key(h['_source'].get('issuing_authority'))==authority_key(authority)]
    elif re.search(r'(?:UBND|HĐND|UB)\b',candidate['target_doc']):
        # Provinces reuse the same local numbers, even on the same day: without a named authority, a local
        # decision cited by a province is that province's own; another province's namesake is never linked.
        eligible=[h for h in eligible if authority_key(h['_source'].get('issuing_authority'))==authority_key(candidate.get('source_issuing_authority'))]
    if len(eligible)>1:
        same=[h for h in eligible if authority_key(h['_source'].get('issuing_authority'))==authority_key(candidate.get('source_issuing_authority'))]
        if same:eligible=same
        else:eligible=[]
    if len(eligible)>1:
        nearest=max(h['_source']['issuance_date'] for h in eligible)
        eligible=[h for h in eligible if h['_source']['issuance_date']==nearest]
    candidate['target_matched_id']=int(eligible[0]['_id']) if len(eligible)==1 else None
    return candidate
