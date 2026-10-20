# Tiêu chí gán nhãn chuẩn (gold) cho quan hệ

Bạn đọc một văn bản pháp luật Việt Nam và ghi **mọi tác động trực tiếp** văn bản này thực hiện lên văn bản khác.
Bạn không thấy kết quả của công cụ. Làm độc lập.

## Dữ liệu vào

Mỗi văn bản có: số hiệu, loại, cơ quan, ngày ban hành, tên, `phan_dau` (phần trước Điều 1), `loi_dan`,
`don_vi` (các đơn vị có từ chỉ hành động: `source_path`, `ten_dieu` là Chương + tên Điều, `cau_dan` là câu dẫn của khoản chứa điểm,
`noi_dung`), và `toan_van` nếu văn bản ngắn. Đơn vị không có trong `don_vi` thường không có tác động.
Nếu `toan_van` cho thấy một hành động ở phần **không có** trong `don_vi` (parser làm mất hoặc gộp sai), vẫn ghi quan hệ đó:
`source_path` theo toàn văn (ví dụ `Điều 1`), và ghi lỗi cấu trúc `thieu_noi_dung` hoặc `gop_sai`. Đích không phải văn bản có số hiệu
hoặc tên luật (ví dụ tiêu chuẩn TCVN) thì không ghi quan hệ, chỉ ghi ở `ghi_chu`.

## Tác động trực tiếp

Chính câu của đơn vị (cùng câu dẫn, tên Điều, tên Chương) thực hiện hành động lên một văn bản khác. KHÔNG ghi:
- kể lại lịch sử, ghi chú "đã được sửa đổi tại …", trích dẫn, căn cứ ban hành;
- nội dung mới trong ngoặc kép;
- thẩm quyền, đề nghị, giao nhiệm vụ ("có quyền đình chỉ", "đề nghị bãi bỏ", "giao Sở … rà soát");
- **tên của một danh mục, bảng, mục** chứa từ hành động: "Danh mục văn bản cần đình chỉ, sửa đổi, bổ sung, bãi bỏ" là tên, không phải hành động;
- công bố thủ tục hành chính, công bố danh mục: chỉ ghi khi văn bản tự nói thay thế, bãi bỏ, sửa đổi một văn bản khác hoặc một phần của nó.

## Mỗi quan hệ

| Trường | Giá trị |
| --- | --- |
| `source_path` | Chép đúng `source_path` của đơn vị chứa câu. Câu ở tên văn bản, phần đầu, lời dẫn: `Phần đầu`. |
| `action` | `sua-doi`, `bo-sung`, `bai-bo` (bãi bỏ, bỏ, "… hết hiệu lực" do văn bản này tuyên bố), `thay-the`, `thay-cum-tu` (thay cụm từ X bằng Y), `huy-bo`, `dinh-chi`, `ngung-hieu-luc`, `dinh-chinh`, `gia-han`, `huong-dan`, `quy-dinh-chi-tiet`, `hop-nhat`. "Sửa đổi, bổ sung X" cho 2 quan hệ: `sua-doi` và `bo-sung`. |
| `target_document` | Số hiệu văn bản đích như câu nêu (`28/2017/QĐ-UBND`). Câu không nêu thì lấy từ câu dẫn, tên Điều, tên Chương, tên văn bản. Luật chỉ nêu bằng tên: ghi số hiệu nếu văn bản nêu số hiệu của luật đó ở bất kỳ đâu (phần đầu, căn cứ), nếu không thì `Luật <tên>`. |
| `target_section` | `quyet_dinh`: vị trí thuộc chính văn bản đích. `kem_theo`: vị trí thuộc Quy định, Quy chế… ban hành kèm theo văn bản đích, và câu nói rõ như vậy. `khong_ro`: văn bản đích có phần kèm theo nhưng câu không nói vị trí thuộc phần nào. `khong_ap_dung`: tác động lên cả văn bản hoặc không có vị trí. |
| `vi_tri` | Mảng vị trí, mỗi vị trí một phần tử, đủ cấp: `Điều 5`, `khoản 2 Điều 5`, `điểm a khoản 2 Điều 5`, `tiểu điểm 3 điểm b khoản 2 Điều 5` (gạch đầu dòng của điểm), `tên Điều 5`, `Chương III`, `Mục 2 Chương III`, `Phụ lục II`, `Mục D.2 Phụ lục I`, `toàn bộ`. Đoạn, câu, gạch đầu dòng của khoản hoặc Điều, tiết, mục La Mã trong Điều: dừng ở khoản hoặc Điều chứa nó. Mẫu biểu: phụ lục chứa nó. Dòng "số thứ tự" của danh mục: phụ lục chứa danh mục, hoặc để rỗng và ghi `doi_tuong`. Văn bản không chia Điều: `Mục II`. Rỗng khi tác động lên cả văn bản ("sửa đổi một số điều", hướng dẫn chung) hoặc chỉ nêu phần bằng tên. |
| `doi_tuong` | Tên phần bị tác động khi câu chỉ nêu bằng tên ("Danh mục hàng hóa …", "đơn giá …", "phần căn cứ"). Không có thì `null`. |
| `evidence` | Chép **nguyên văn** câu (hoặc đoạn câu) thực hiện hành động, từ `noi_dung`, `cau_dan`, `ten_dieu`, `phan_dau` hoặc `loi_dan`. |

"Điều 36 và Điều 37" cho một quan hệ với `vi_tri` có 2 phần tử. Không gộp các hành động khác nhau.

Tên văn bản hoặc lời dẫn tự thực hiện hành động ("Quyết định bãi bỏ Quyết định số 32/2012/QĐ-UBND", "Bộ trưởng … ban hành Thông tư sửa đổi Thông tư số …"):
ghi một quan hệ riêng với `source_path` = `Phần đầu`, kể cả khi một Điều cũng thực hiện cùng hành động (đã chốt: tên và lời dẫn giữ quan hệ riêng).
Tên chỉ mô tả nội dung ("Quyết định về quản lý …") thì không ghi.

## Quy ước bổ sung (20/10/2026)

- Tên văn bản hoặc lời dẫn chỉ có quan hệ `Phần đầu` khi chính câu đó nêu văn bản đích (số hiệu hoặc tên luật). Không lấy số hiệu từ thân văn bản cho tên văn bản.
- Câu chung "các quy định, thủ tục … trái với văn bản này được sửa đổi, thay thế, bãi bỏ" không nêu phần nào bị tác động: không phải quan hệ, kể cả khi câu nêu số hiệu các văn bản. Ghi ở `ghi_chu`.

- Phụ lục viết thành đoạn văn (không chia Điều, không phải bảng): `source_path` là `Phụ lục <so> Mục <m>` theo đề mục đánh số của phụ lục (`1.`, `2.` hoặc `I.`, `II.`), hoặc `Phụ lục <so>` khi không có đề mục.
- "Đồng ý với đề nghị của …", "chấp thuận …": là quan hệ khi chính câu nêu văn bản đích và nêu rõ sửa, bỏ, thay nội dung nào ở vị trí nào. Đồng ý một đề xuất sẽ được thực hiện bằng văn bản khác sau này không phải quan hệ.
- Văn bản không phải Hiến pháp, Bộ luật, Luật, Pháp lệnh hoặc Nghị quyết của Quốc hội, Ủy ban Thường vụ Quốc hội không sửa đổi, bổ sung, bãi bỏ, thay thế được Luật, Pháp lệnh. Câu "sửa đổi Điều 12 Luật X" trong văn bản đó là đề xuất hoặc nhiệm vụ: không phải quan hệ.

## Phụ lục và dòng bảng (từ 19/10/2026)

Gói có `phu_luc`: các phụ lục và văn bản kèm theo theo thứ tự, `so` đếm từ 1. Đọc bảng trong `toan_van`.

`source_path` là nơi **chữ chỉ hành động** lên văn bản đích được viết:

| Chữ chỉ hành động nằm ở | `source_path` | Ví dụ |
| --- | --- | --- |
| Chính dòng bảng (cột ghi chú, chú thích trong dòng) | `Phụ lục <so> STT <k>`. Bảng nằm dưới đề mục có ký hiệu (A, B, I, II, 1): `Phụ lục <so> Mục <ký hiệu> STT <k>`. | Dòng 1 dưới "A. DANH MỤC … ĐƯỢC SỬA ĐỔI, BỔ SUNG" ghi "(Sửa đổi, bổ sung TTHC được công bố tại Quyết định số 2074/QĐ-UBND …)" → `Phụ lục 1 Mục A STT 1` |
| Một Điều (khoản) nêu hành động lên các văn bản liệt kê ở phụ lục | Điều (khoản) đó. Mỗi văn bản trong danh sách là một quan hệ. | "Điều 1. Bãi bỏ các văn bản tại Phụ lục II" và Phụ lục II liệt kê 25 quyết định → 25 quan hệ `Điều 1` |
| Chỉ tên phụ lục hoặc đề mục của bảng, và đó là danh sách thủ tục hành chính được sửa đổi, bổ sung, thay thế, bãi bỏ, hủy bỏ mà dòng nêu Quyết định đã công bố thủ tục đó | `Phụ lục <so> STT <k>` như dòng 1 | Phụ lục "DANH MỤC TTHC BỊ HỦY BỎ", dòng 1 ghi "… công bố tại Quyết định số 1692/QĐ-UBND" |

**Không phải hành động (sửa ngày 19/10/2026):** quyết định **công bố danh mục văn bản hết hiệu lực, ngưng hiệu lực** (kết quả rà soát, hệ thống hóa văn bản) chỉ công bố tình trạng của văn bản. Các văn bản đó hết hiệu lực do văn bản khác. Không ghi quan hệ cho các dòng của danh mục này, trừ khi chính văn bản nói "bãi bỏ", "hủy bỏ", "thay thế" văn bản trong danh mục, hoặc tự tuyên bố văn bản đó hết hiệu lực từ ngày văn bản này có hiệu lực.

- `<k>` là số ở cột "TT"/"STT" của dòng. Dòng không có số: đếm dòng dữ liệu từ 1 trong bảng đó.
- Văn bản ở cột "Căn cứ pháp lý" không phải đích.
- "Công bố kèm theo Quyết định này Danh mục thủ tục hành chính được sửa đổi, bổ sung, bãi bỏ" ở Điều 1 không là hành động. Hành động nằm ở dòng bảng khi dòng nêu rõ văn bản đích.
- Một dòng nêu "sửa đổi, bổ sung" lên 2 văn bản cho 4 quan hệ.
- Vị trí đích: theo câu ("số thứ tự 1 Mục II Phụ lục II kèm theo Quyết định X" → `Phụ lục II`). Câu chỉ nêu thủ tục bằng tên: `vi_tri` rỗng, `doi_tuong` là tên thủ tục.

## Lỗi cấu trúc

Nếu thấy đơn vị bị tách hoặc gộp sai (khoản bị chia đôi, điểm của khoản này nằm ở khoản khác, nội dung mới trong ngoặc kép bị nhận thành Điều của văn bản), ghi vào `loi_cau_truc`.

## Kết quả

Một file JSON là mảng, mỗi văn bản một phần tử, cùng thứ tự với file vào:

```json
{"doc_id": "...", "relations": [{"source_path": "Điều 1 Khoản 2", "action": "sua-doi", "target_document": "28/2017/QĐ-UBND",
  "target_section": "kem_theo", "vi_tri": ["khoản 7 Điều 3"], "doi_tuong": null, "evidence": "..."}],
 "loi_cau_truc": [{"source_path": "...", "loai": "tach_sai|gop_sai|nhan_sai_dieu|thieu_noi_dung", "ghi_chu": "..."}],
 "ghi_chu": "ngắn"}
```

Không đoán. Văn bản bị cắt hoặc thiếu chữ để kết luận thì ghi rõ ở `ghi_chu` và chỉ ghi các quan hệ chắc chắn.
