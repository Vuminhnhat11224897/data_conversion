# 13. Phụ lục: định nghĩa, cách lưu, độ dài

Tài liệu này nêu mọi trường hợp công cụ `vbpl_v3` coi là phụ lục. Có hai nghĩa:

1. **Phụ lục trong cấu trúc văn bản:** phần văn bản công cụ tách ra thành phụ lục và lưu thành chunk (mục 1).
2. **Phụ lục ở vị trí của quan hệ:** vị trí của văn bản đích mà công cụ ghi là `Phụ lục` hoặc `Phụ lục <ký hiệu>` (mục 2).

- Code: commit `8b023ca` (27/10/2026). Code tách cấu trúc (`structure.py`, `structure_ai.py`) giống code `2911b77` đã ghi index `-v4`.
- Số đo ở mục 3: đọc `legal-docs-v4` ngày 27/10/2026, 11.000 văn bản.

## 1. Phụ lục trong cấu trúc văn bản

### 1.1. Dấu hiệu mở vùng phụ lục

Công cụ tìm các dấu hiệu dưới đây. **Dấu hiệu sớm nhất** mở vùng phụ lục. Vùng phụ lục kéo dài tới hết văn bản. Thân văn bản kết thúc ở dòng trước vùng này.

| # | Dấu hiệu | Điều kiện | Ví dụ |
| --- | --- | --- | --- |
| 1 | Dòng tiêu đề phụ lục | Dòng bắt đầu bằng `PHỤ LỤC`, `PHU LUC` hoặc `Phụ lục`. Sau đó có thể có `SỐ`/`số` và ký hiệu: số La Mã, số, hoặc số kèm một chữ cái. Dòng phải đạt một trong các điều kiện: cả dòng in hoa; không có chữ sau ký hiệu; chữ sau ký hiệu in hoa; dòng ngắn hơn 60 ký tự. | `PHỤ LỤC II`, `Phụ lục số 01`, `PHỤ LỤC 2a DANH MỤC …` |
| 2 | Tiêu đề in hoa của văn bản kèm theo | Dòng in hoa bắt đầu bằng một trong các từ: `QUY ĐỊNH`, `QUY CHẾ`, `QUY TRÌNH`, `QUY TẮC`, `QUY CHUẨN`, `QUY HOẠCH`, `DANH MỤC`, `DANH SÁCH`, `BẢNG`, `ĐỀ ÁN`, `ĐỀ CƯƠNG`, `CHƯƠNG TRÌNH`, `ĐIỀU LỆ`, `NỘI QUY`, `BIỂU MẪU`, `MẪU SỐ`, `PHỤ BIỂU`, `TIÊU CHÍ`, `KẾ HOẠCH`, `THUYẾT MINH`, `HƯỚNG DẪN`, `TIÊU CHUẨN`. Dòng ngay trên không là `Chương …` hoặc `Mục …`. Trước chữ ký, tiêu đề phải đứng trên một chuỗi Điều mới. Sau chữ ký, tiêu đề đứng một mình cũng đủ. | `QUY CHẾ` + `Điều 1. Phạm vi điều chỉnh` |
| 3 | Ghi chú ban hành kèm theo | Dòng mở bằng `(Ban hành kèm theo`, `(Kèm theo`, `(Phê duyệt` hoặc `(Được ban hành`. Trong 60 ký tự sau đó có `Quyết định`, `Nghị định`, `Nghị quyết`, `Thông tư`, `Chỉ thị`, `Công văn` hoặc `Văn bản`. Ghi chú đứng đầu dòng hoặc sau chữ in hoa. | `(Ban hành kèm theo Quyết định số 12/2025/QĐ-UBND …)` |
| 4 | Chuỗi Điều bắt đầu lại sau chữ ký | Có `Điều 1` mới sau dòng `Nơi nhận:` hoặc sau dòng ký (`TM.`, `KT.`, `T/M`, `K/T`). | Quy chế kèm theo không có tiêu đề |

Không tính là dấu hiệu:

- Dòng nằm trong ngoặc kép. Ví dụ: nội dung mới của một văn bản sửa đổi có dòng `PHỤ LỤC II`.
- Dòng tiêu đề phụ lục mà chữ sau ký hiệu bắt đầu bằng `kèm theo`, `ban hành kèm theo`, `của`, `tại`, `quy định tại`. Đây là câu nhắc tới phụ lục, không phải tiêu đề. Ví dụ: `Phụ lục kèm theo Quyết định này`.

Dấu hiệu 2, 3, 4 mở một **văn bản kèm theo** (`loai = unlabeled`). Dấu hiệu 1 mở một **phụ lục có nhãn** (`loai = labeled`).

### 1.2. Cắt vùng phụ lục thành từng phần

Mỗi phần là một phụ lục hoặc một văn bản kèm theo. Một phần mới bắt đầu ở:

1. Đầu vùng phụ lục.
2. Mỗi dòng tiêu đề phụ lục (dấu hiệu 1).
3. Mỗi khối tiêu đề có ghi chú ban hành kèm theo, đứng trên một chuỗi Điều mới. Trong vùng phụ lục, tiêu đề in hoa không có ghi chú này **không** mở phần mới. Lý do: biểu mẫu thường có tiêu đề in hoa như `HƯỚNG DẪN GHI CHÉP MẪU`.
4. Mỗi biểu kèm theo cùng văn bản với phần chứa nó. Ví dụ: `Biểu số 1`, `Biểu số 2` cùng ghi `(Kèm theo Thông tư số X)`. Biểu mẫu nêu văn bản khác thì ở lại trong phần chứa nó.

**Tiêu đề của phần** gồm dòng đầu và tối đa 5 dòng tiếp theo. Dòng tiếp theo phải in hoa, hoặc mở bằng `(Ban hành`, `(Kèm theo`, hoặc là ghi chú ban hành kèm theo. Tiêu đề dừng ở dòng kết thúc bằng `)` hoặc ở dòng bảng. Phần mở bằng `Điều 1` không có tiêu đề.

### 1.3. LLM kiểm bố cục

Công cụ hỏi LLM khi kết quả của quy tắc có một trong các tín hiệu sau (`structure_ai.layout_signals`):

| Tín hiệu | Nghĩa |
| --- | --- |
| `tail_dieu` | Có Điều nằm sau phần chữ ký |
| `long_noi_nhan` | Phần nơi nhận dài hơn 2.000 ký tự |
| `segment_in_main` | Thân văn bản có chuỗi Điều kèm theo |
| `unlabeled_without_note` | Có văn bản kèm theo không có ghi chú ban hành kèm theo |
| `empty_labeled_part` | Có phụ lục có nhãn, không có Điều, nội dung dưới 80 ký tự |

LLM đề xuất dòng bắt đầu của từng phần. Công cụ chỉ nhận đề xuất khi mọi điều sau đúng:

- mỗi dòng bắt đầu là dòng tiêu đề, và không trùng nhau;
- đề xuất không gộp một phụ lục có nhãn có nội dung vào phần khác.

Đề xuất không đạt thì công cụ giữ kết quả của quy tắc.

### 1.4. Lưu ở văn bản: `legal-docs-v4` → `phu_luc[]`

| Trường | Nghĩa |
| --- | --- |
| `tieu_de` | Tiêu đề của phần (mục 1.2) |
| `noi_dung` | Toàn văn của phần, sau tiêu đề. Không cắt. |
| `loai` | `labeled`: phần mở bằng dòng tiêu đề phụ lục. `unlabeled`: văn bản kèm theo. |
| `ky_hieu` | Ký hiệu in trên tiêu đề: `II`, `01`, `2a`. Chỉ phần `labeled` có ký hiệu mới có trường này. |
| `has_table` | `true` khi phần có ít nhất 2 dòng bảng (dòng mở bằng `\|`) |
| `n_tables`, `n_table_rows` | Số bảng, số dòng bảng |
| `dieu_luat` | Các Điều của phần, cùng cấu trúc với Điều của thân văn bản |

### 1.5. Lưu thành chunk: `legal-chunk-section-v4`

| Phần | Chunk | ID |
| --- | --- | --- |
| Có Điều (quy chế, quy định kèm theo) | Tách như thân văn bản: Điều, khoản, điểm, tiểu điểm, chunk `_full` | `<doc>_pl<i>_d<k>`, `<doc>_pl<i>_d<k>_k<m>`, `<doc>_pl<i>_d<k>_k<m>_p<x>` |
| Không có Điều (bảng, danh mục, biểu mẫu, văn bản thường) | **Một chunk** `chunk_type = phu_luc`, chứa toàn bộ `noi_dung`. Không chia đoạn. | `<doc>_pl<i>` |

Mọi chunk của phần phụ lục có thêm 3 trường: `in_phu_luc = true`, `phu_luc_tieu_de` (500 ký tự đầu của tiêu đề), `has_table`.

### 1.6. Ba cách đánh số phụ lục

Một phụ lục có thể mang 3 số khác nhau. Bên đọc không được trộn các số này.

| Nơi dùng | Dạng | Số lấy từ | Ví dụ: 680964 (2226/QĐ-UBND), phần thứ hai in là "PHỤ LỤC II" |
| --- | --- | --- | --- |
| ID chunk | `<doc>_pl<i>` | Thứ tự phần, đếm từ 0 | `680964_pl1` |
| `source_path` khi văn bản nguồn tác động từ trong phụ lục của nó | `Phụ lục <i+1> …` | Thứ tự phần, đếm từ 1 | `Phụ lục 2 Điều 3`, `Phụ lục 2 Mục II STT 5` |
| `vi_tri` của văn bản đích (mục 2) | `Phụ lục <ký hiệu>` | Ký hiệu câu nguồn nêu | `Phụ lục II` (khi một văn bản khác tác động lên phụ lục này) |
| `phu_luc[i].ky_hieu` ở `legal-docs-v4` | Ký hiệu in trên tiêu đề | Tiêu đề của phần | `phu_luc[1].ky_hieu = "II"` |

Để nối `vi_tri = ["Phụ lục II"]` với chunk của văn bản đích, tìm phần có `phu_luc[i].ky_hieu = "II"` rồi dùng `<doc>_pl<i>`. `Phụ lục` không ký hiệu không chỉ tới một phần cụ thể (docs/11, Việc 3).

## 2. Phụ lục ở vị trí của quan hệ (quy ước phụ lục)

Code: `resolver.appendix_scope`, `resolver.body_place`, `resolver.appendix_like`. Chạy ở chế độ `llm`, hai lần: cuối bước gộp và trong `convert.tidy_positions`. Bộ chấm (`eval/score.place`) dùng cùng phép thử.

### 2.1. Quan hệ có `vi_tri`

**Giữ nguyên.** Đây là vị trí của thân văn bản:

| Dạng | Ví dụ |
| --- | --- |
| Có chữ `điểm`, `khoản`, `Điều` hoặc `Chương` | `khoản 2 Điều 5`, `Mục 1 Chương II`, `tên Điều 5`, `tên Chương II`, `Điều 3 Phụ lục II` |
| `tên văn bản` | `tên văn bản` |
| `tên Mục <số>` | `tên Mục 1` |
| `toàn bộ` | `toàn bộ` |

**Thành phụ lục.** Đây là mọi vị trí còn lại:

| Vị trí gốc | Ghi thành |
| --- | --- |
| `Mục I`, `Mục IV` (số La Mã, đứng một mình) | `Phụ lục` |
| `Mục 2`, `Mục 89` (số, không nêu Chương) | `Phụ lục` |
| `Phần A`, `Mục II Phần B` | `Phụ lục` |
| `Mục I Phụ lục I`, `Mục II Phần B Phụ lục I` | `Phụ lục I` |
| `Phụ lục số 01`, `Phụ lục 01 STT 5` | `Phụ lục 01` |
| Dòng danh mục: `số thứ tự 01, 02 Mục II Phụ lục` | `Phụ lục` |

- Câu nguồn nêu đúng một ký hiệu phụ lục (số La Mã, số, chữ cái) thì công cụ ghi `Phụ lục <ký hiệu>`. Câu không nêu ký hiệu, hoặc nêu nhiều ký hiệu, thì công cụ ghi `Phụ lục`.
- Công cụ ghi chữ vị trí gốc vào `chi_tiet_vi_tri` của cạnh tới phụ lục. Ví dụ: `Mục IV Phụ lục I; số thứ tự 01`. Nhiều vị trí gốc về cùng một phụ lục thì gộp thành một cạnh, chữ nối bằng `; `.
- Cặp cụm từ (`cum_tu[].vi_tri`) theo cùng quy ước.

### 2.2. Quan hệ không có `vi_tri`, có phần nêu bằng tên (`doi_tuong`)

Phần nêu bằng tên thành phụ lục **chỉ khi** có ít nhất một dấu hiệu dưới đây. Khi đó `doi_tuong` giữ chữ gốc.

| Dấu hiệu | Ví dụ |
| --- | --- |
| Chữ `phụ lục` | "nội dung tại Phụ lục 1" |
| `danh mục` | `694022_0`: "danh mục và nội dung 02 thủ tục hành chính có số thứ tự 11, 17 mục I, phần A, Phụ lục 1" → `Phụ lục 1` |
| `thủ tục`, `TTHC` | `685249_0`: "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ" → `Phụ lục` |
| `biểu mẫu`, `mẫu …`, `mẫu số …` | "Mẫu số 01", "mẫu tờ khai" |
| `phương án` | "phương án đơn giản hóa thủ tục …" |
| `quy trình nội bộ` | "02 quy trình nội bộ giải quyết thủ tục hành chính" |
| `Mục <số hoặc La Mã>`, `Phần <số, La Mã hoặc chữ>` | "tại Mục I Phần A" |
| `số thứ tự`, `STT` | "có số thứ tự 11, 17" |
| `doi_tuong_loai = thu_tuc_hanh_chinh` | Phần mà công cụ xếp là thủ tục hành chính |
| `source_path` có ` STT ` hoặc mở bằng `Phụ lục` | Quan hệ đọc từ dòng bảng, hoặc từ phụ lục của văn bản nguồn |

### 2.3. Không phải phụ lục

Phần nêu bằng tên không có dấu hiệu ở mục 2.2 thì giữ tên. Quan hệ không có `vi_tri`. `cap_quan_he` là `van_ban_kem_theo` khi phần nằm trong văn bản kèm theo; trường hợp khác là `noi_dung`. Ví dụ:

- `676559_0`: "một số điều của các Thông tư trong lĩnh vực lâm nghiệp";
- "phần căn cứ";
- "đơn giá ban hành kèm theo Quyết định X".

## 3. Độ dài

Đo ngày 27/10/2026 trên `legal-docs-v4`. Độ dài là độ dài của `phu_luc[].noi_dung`, không tính tiêu đề. Từ là chuỗi tách bằng khoảng trắng.

### 3.1. Số lượng

| Chỉ số | Giá trị |
| --- | --- |
| Văn bản có phụ lục | 6.051/11.000 (55%) |
| Số phần phụ lục | 11.788 |
| Phụ lục có nhãn (`labeled`) | 8.259 (70%); 6.687 phần có `ky_hieu` |
| Văn bản kèm theo (`unlabeled`) | 3.529 (30%) |
| Phần có Điều (tách thành Điều, khoản) | 1.591 (13,5%) |
| Phần không có Điều (một chunk `phu_luc`) | 10.197 (86,5%) |
| Phần có bảng | 8.815 (75%) |
| Số phần trong một văn bản | Trung vị 1, p95 5, tối đa 180 (`694210`, 279/QĐ-BNNMT) |

### 3.2. Độ dài theo ký tự

| Nhóm | Số phần | Nhỏ nhất | p5 | p25 | Trung vị | p75 | p95 | p99 | Lớn nhất |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tất cả | 11.788 | 0 | 484 | 2.019 | 5.686 | 15.312 | 54.173 | 212.860 | 1.712.716 |
| Không có Điều (chunk `phu_luc`) | 10.197 | 0 | 396 | 1.789 | 4.515 | 12.454 | 49.319 | 212.091 | 1.712.716 |
| Có Điều | 1.591 | 728 | 2.704 | 9.902 | 16.557 | 28.532 | 79.458 | 215.932 | 437.946 |
| Có nhãn (`labeled`) | 8.259 | 0 | 322 | 1.624 | 4.242 | 11.371 | 46.538 | 162.739 | 1.712.716 |
| Văn bản kèm theo (`unlabeled`) | 3.529 | 0 | 1.150 | 4.471 | 11.746 | 23.865 | 70.782 | 258.751 | 775.262 |
| Không có Điều, có bảng | 8.385 | 38 | 636 | 2.004 | 4.968 | 13.208 | 53.471 | 240.254 | 1.712.716 |
| Không có Điều, không có bảng | 1.812 | 0 | 0 | 1.086 | 2.599 | 8.527 | 33.163 | 62.729 | 267.163 |

### 3.3. Độ dài theo từ

| Nhóm | Nhỏ nhất | p5 | p25 | Trung vị | p75 | p95 | p99 | Lớn nhất |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tất cả | 0 | 120 | 464 | 1.316 | 3.474 | 12.126 | 51.873 | 392.507 |
| Không có Điều (chunk `phu_luc`) | 0 | 99 | 411 | 1.091 | 2.909 | 11.139 | 51.867 | 392.507 |
| Có Điều | 122 | 560 | 2.142 | 3.583 | 6.181 | 17.223 | 51.045 | 95.986 |
| Có nhãn (`labeled`) | 0 | 80 | 375 | 999 | 2.648 | 10.499 | 39.607 | 392.507 |
| Văn bản kèm theo (`unlabeled`) | 0 | 254 | 1.029 | 2.616 | 5.261 | 16.551 | 65.264 | 179.220 |

### 3.4. Hai đầu của khoảng

**Ngắn nhất.** 205 phần rỗng (0 ký tự): 196 phần có nhãn, 9 văn bản kèm theo. 222 phần ngắn hơn 80 ký tự. Phần rỗng chỉ có dòng tiêu đề. Có hai loại:

- toàn văn nguồn không có nội dung dưới tiêu đề. Ví dụ: `681010_pl4` (4822/QĐ-BNNMT, `PHỤ LỤC 1`); `678905_pl1` (45/VBHN-BCT, `PHỤ LỤC 2 (được bãi bỏ)`);
- dòng tiêu đề là chữ trong một biểu mẫu, ví dụ `Phụ lục (Ban hành kèm theo .................(1))`. Đây là lỗi tách cấu trúc.

**Dài nhất.** Cả 6 phần dài nhất là phụ lục có nhãn, có bảng, không có Điều. Mỗi phần là **một chunk**:

| Chunk | Văn bản | Ký tự | Từ | Tiêu đề |
| --- | --- | --- | --- | --- |
| `685877_pl2` | 47/NQ-HĐND | 1.712.716 | 392.507 | PHỤ LỤC III GIÁ DỊCH VỤ KỸ THUẬT VÀ XÉT NGHIỆM |
| `685237_pl2` | 43/NQ-HĐND | 1.554.665 | 345.731 | PHỤ LỤC III GIÁ DỊCH VỤ KỸ THUẬT VÀ XÉT NGHIỆM |
| `689638_pl11` | 54/NQ-HĐND | 959.745 | 215.560 | PHỤ LỤC III GIÁ DỊCH VỤ KỸ THUẬT, XÉT NGHIỆM |
| `695432_pl2` | 374/QĐ-BYT | 921.204 | 191.711 | PHỤ LỤC DANH MỤC KỸ THUẬT |
| `686999_pl2` | 94/2025/QĐ-UBND | 876.104 | 199.838 | Phụ lục II NỘI DUNG QUY TRÌNH SẢN XUẤT MỘT SỐ CÂY TRỒNG |
| `565484_pl1` | 99/2025/TT-BTC | 794.241 | 176.227 | PHỤ LỤC II HỆ THỐNG TÀI KHOẢN KẾ TOÁN DOANH NGHIỆP |

### 3.5. Hệ quả cho vector

- 9.123/10.197 chunk `phu_luc` (89,5%) dài hơn 200 từ.
- Lệnh `convert` cắt đầu vào embedding ở 256 token, khoảng 200 từ. Vì vậy vector của các chunk này chỉ đại diện cho đoạn đầu.
- Ngày 26/10/2026, vector của `-v4` được tạo lại với toàn bộ đầu vào. Lượt `convert` mới vẫn ghi vector cắt ở 256 token.
- Đề xuất chia đoạn con cho chunk `phu_luc` dài: docs/10, mục S1 và S2. Chưa làm.
