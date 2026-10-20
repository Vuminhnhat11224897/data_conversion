# 3. Hợp đồng dữ liệu v2 (nguồn)

Tài liệu này mô tả 3 index v2 trên ES nguồn `10.1.10.10`. Luồng realtime ghi các index này. Công cụ `vbpl_v3` chỉ đọc.

Số liệu đo ngày 14/10/2026, chỉ đọc. Số liệu chất lượng ở mục 3.5 đo ngày 09/10/2026.

| Index | Một bản ghi là | Số bản ghi | Công cụ dùng để |
| --- | --- | --- | --- |
| `legal-docs` | Một văn bản | 518.261 | Đọc toàn văn và metadata. Tra văn bản đích. |
| `legal-chunk-section-v2` | Một chunk | 10.331.917 | Dùng lại vector cũ. |
| `legal-changed-v2` | Một quan hệ | 180.452 | Không dùng. v3 dò lại mọi quan hệ. |

## 3.1. Khóa nối

| Từ | Đến | Quy tắc |
| --- | --- | --- |
| `legal-chunk-section-v2.doc_id` | `legal-docs._id` | Chunk thuộc văn bản. |
| `legal-chunk-section-v2.dieu_uid`, `khoan_uid` | Chunk cùng Điều, cùng khoản | Gom chunk con với chunk `is_full`. |
| `legal-changed-v2.source_id` | `legal-docs._id` | `source_id` là số nguyên. `_id` là chuỗi. |
| `legal-changed-v2.target_matched_id` | `legal-docs._id` | Có ở 71.197/180.452 quan hệ (39,5%). |

## 3.2. `legal-docs`

`_id` là chuỗi chữ số, ví dụ `602450`. v3 giữ nguyên `_id` này.

| Trường | Kiểu | Có ở | Nghĩa |
| --- | --- | --- | --- |
| `document_number` | keyword | Mọi văn bản | Số hiệu. Không duy nhất. |
| `title` | text | Mọi văn bản | Tên văn bản. |
| `legal_type` | keyword | Mọi văn bản | Loại văn bản. 36 giá trị. |
| `legal_sectors` | mảng keyword | Thiếu ở 4 văn bản | Lĩnh vực. |
| `issuing_authority` | keyword | Mọi văn bản | Cơ quan ban hành. |
| `issuance_date` | date | Mọi văn bản | Ngày ban hành. |
| `signers` | keyword, không index | Thiếu ở 447 văn bản | Người ký, dạng `Tên:mã`. |
| `tom_tat` | text | Mọi văn bản | Tóm tắt. |
| `action` | keyword | Mọi văn bản | Phân loại văn bản. 10 giá trị. Xem [06, mục 6.1](06-bang-enum.md#62-văn-bản). |
| `url` | keyword, không index | Mọi văn bản | Link nguồn. |
| `pdf_minio_path` | keyword | 478.053 (92,2%) | Đường dẫn PDF trên MinIO. |
| `pdf_vbpl_id` | keyword | 103.849 (20,0%) | ID trên vbpl.vn. |
| `embedding` | dense_vector 1.024 | Mọi văn bản | Vector văn bản (`BAAI/bge-m3`). |
| `full_content` | text | Mọi văn bản | Toàn văn. Có văn bản còn Unicode NFD. |
| `can_cu` | mảng chuỗi, `enabled: false` | — | Các dòng căn cứ. |
| `can_cu_refs` | mảng keyword | 369.137 | Số hiệu nêu trong căn cứ. |
| `intro` | text | 397.821 | Lời dẫn. Có văn bản chứa cả dòng căn cứ, ví dụ `602450`. |
| `noi_nhan` | mảng chuỗi, `enabled: false` | — | Các dòng Nơi nhận. |
| `phu_luc` | mảng object, `enabled: false` | — | Phụ lục. Mỗi phần tử chỉ có `tieu_de`, `noi_dung`. |
| `has_tail` | boolean | Mọi văn bản | `true`: có chữ ký hoặc Nơi nhận. |
| `n_dieu` | integer | Mọi văn bản | Số Điều do bộ tách cũ đếm. |
| `content_sha256`, `grade`, `text_source`, `origin`, `ingest_job_id`, `ingest_revision`, `ingested_at`, `uploaded_by` | như v3 | 6 văn bản | Chỉ có ở văn bản người dùng tải lên (`origin = user_upload`, `uploaded_by = api`). |

`phu_luc[]` ở v2 khác v3. Ví dụ `602450`, phần tử đầu:

- `tieu_de = "PHỤ LỤC I"`: chỉ có dòng nhãn.
- `noi_dung` bắt đầu bằng `(Kèm theo Nghị định số 31/2024/NĐ-CP …)`.
- Không có `loai`, `ky_hieu`, `has_table`, `n_tables`, `n_table_rows`, `dieu_luat`.

## 3.3. `legal-chunk-section-v2`

### Loại chunk

| `chunk_type` | Số chunk | Mẫu `_id` |
| --- | --- | --- |
| `khoan` | 3.315.998 | `<doc>_d<x>_k<y>` |
| `diem` | 2.781.470 | `<doc>_d<x>_k<y>_p<z>` |
| `dieu` | 1.075.620 | `<doc>_d<x>` |
| `dieu_full` | 1.052.700 | `<doc>_d<x>_full` |
| `khoan_full` | 740.612 | `<doc>_d<x>_k<y>_full` |
| `khoan_mo_dau` | 474.670 | `<doc>_d<x>_k<y>_md` |
| `muc` | 437.665 | `<doc>_m<n>`. `<n>` có thể là số La Mã: `<doc>_mIII`. |
| `phu_luc` | 264.774 | `<doc>_pl<i>` |
| `noi_dung` | 98.573 | `<doc>_nd` |
| `dieu_mo_dau` | 89.835 | `<doc>_d<x>_md` |

- Điều trong phụ lục có `_pl<i>` sau `<doc>`.
- Văn bản kèm theo nằm trong phần chính có `_s<s>` trước `_d`, ví dụ `<doc>_s1_d3_k1`. v3 chuyển các phần này vào `phu_luc[]` và đổi ID sang `_pl<i>`.
- v2 không có `noi_dung_full`, không có đoạn `<doc>_nd<k>`.

### Trường

| Trường | Kiểu | Có ở | Nghĩa |
| --- | --- | --- | --- |
| `doc_id` | keyword | Mọi chunk | ID văn bản. |
| `chunk_type` | keyword | Mọi chunk | 10 giá trị ở bảng trên. |
| `tieu_de`, `noi_dung` | text | Mọi chunk | Tên đơn vị và nội dung. |
| `so_van_ban_refs` | mảng keyword | 918.004 (8,9%) | Số hiệu nêu trong chunk. |
| `embedding` | dense_vector 1.024 | Thiếu ở 11 chunk | Vector của `tieu_de + " " + noi_dung`. |
| `document_number`, `title`, `action`, `legal_type`, `issuing_authority`, `issuance_date`, `url`, `signers` | như văn bản | Mọi chunk | Chép từ văn bản. |
| `legal_sectors` | keyword (chuỗi) | Mọi chunk | Lĩnh vực nối bằng `", "`. |
| `dieu_uid`, `segment`, `so_dieu`, `ky_hieu_dieu` | keyword, integer, integer, keyword | 9.530.905 | Chunk thuộc Điều. |
| `khoan_uid`, `so_khoan`, `ky_hieu_khoan` | keyword, integer, keyword | 7.312.750 | Chunk thuộc khoản. |
| `so_diem` | keyword | Chunk `diem` | Ký hiệu điểm. |
| `is_full` | boolean | 6.184.930 | Chunk chứa trọn đơn vị. |
| `in_phu_luc`, `phu_luc_tieu_de`, `has_table` | boolean, text, boolean | 4.068.699 | Chunk nằm trong phụ lục. |
| `chuong` | text | 6.148.601 | Tên Chương. |
| `muc_lon` | text | 1.395.062 | Tên Mục trong Chương. |
| `so_muc` | keyword | Chunk `muc` | Ký hiệu đề mục. |
| `origin`, `ingest_job_id`, `ingest_revision`, `ingested_at`, `uploaded_by` | như v3 | 184 | Chỉ có ở chunk của văn bản tải lên. |

v2 không có `dan_chieu`, `so_doan`.

## 3.4. `legal-changed-v2`

### ID

ID có dạng `[<tiền tố>]<source_id>_<n>[<hậu tố>]`. `<n>` là bộ đếm chung của luồng realtime, không đếm lại theo văn bản. Ví dụ: `602450_78359`.

Mẫu 1.000 quan hệ ngẫu nhiên:

| Phần của ID | Giá trị | Số | Nghĩa |
| --- | --- | --- | --- |
| Tiền tố | không có | 687 | Tiêu đề văn bản nguồn nêu hành động. |
| Tiền tố | `hidden_` | 281 | `detection_mode = hidden`. |
| Tiền tố | `hhl_` | 19 | `detection_mode = het_hieu_luc`. |
| Tiền tố | `intro_` | 13 | `detection_mode = intro`. |
| Hậu tố | không có | 706 | — |
| Hậu tố | `_split` | 235 | Do luồng realtime thêm. v3 không dùng. |
| Hậu tố | `_f<n>` | 59 | Do luồng realtime thêm. v3 không dùng. |

### Trường

| Trường | Kiểu | Có ở | Nghĩa |
| --- | --- | --- | --- |
| `source_id` | integer | Mọi quan hệ | ID văn bản nguồn. |
| `source_document_number`, `source_title`, `source_action`, `source_issuing_authority`, `source_issuance_date`, `source_legal_type`, `source_legal_sectors`, `source_url` | như văn bản | Mọi quan hệ | Chép từ văn bản nguồn. |
| `source_path` | keyword | Mọi quan hệ | Đơn vị nguồn, ví dụ `Điều 1 Khoản 1`, `intro`. |
| `source_in_phu_luc` | boolean | Mọi quan hệ | Đơn vị nguồn nằm trong phụ lục. |
| `target_doc` | keyword | Mọi quan hệ | Số hiệu đích theo câu nguồn. |
| `target_matched_id` | integer | 71.197 (39,5%) | ID văn bản đích. |
| `target_candidates_count` | integer | Mọi quan hệ | Số văn bản có cùng số hiệu. |
| `target_issuance_date` | date | 62 | Ngày ban hành đích theo câu trích. |
| `target_issuing_authority` | text + keyword | 30 | Cơ quan ban hành đích theo câu trích. v3 đổi kiểu sang keyword. |
| `action` | keyword | Mọi quan hệ | 5 giá trị: `sua-doi` 64.612, `bo-sung` 41.902, `thay-the` 41.645, `bai-bo` 31.908, `huy-bo` 385. |
| `scope` | text + keyword | Mọi quan hệ | Phạm vi, chữ tự do. Xem bảng dưới. |
| `unresolved` | boolean | Mọi quan hệ | `true` ở 23.484 quan hệ (13,0%). |
| `detection_mode` | text + keyword | 58.923 | `hidden` 53.972, `het_hieu_luc` 3.365, `intro` 1.586. |
| `scope_grounding_checked`, `scope_grounding_correct`, `scope_grounding_suggestion` | boolean, boolean, text | 63.570 | Kết quả QA phạm vi. |
| `scope_resolution_method` | text + keyword | 30 | Chỉ có `explicit_declaration`. v3 đổi kiểu sang keyword. |
| `llm_refined` | boolean | 18 | Phạm vi đã thay bằng đề xuất của model. |
| `llm_hallucination_rejected` | boolean | 11 | Đề xuất của model bị loại. |
| `inherited_from_v1` | boolean | 1.580 | Cờ của luồng realtime: `true` 531, `false` 1.049. v3 không ghi trường này. |
| `origin`, `ingest_job_id`, `ingest_revision`, `ingested_at`, `uploaded_by` | như v3 | 68 | Chỉ có ở quan hệ của văn bản tải lên. |

v2 không có `vi_tri`, `cap_quan_he`, `hieu_luc_tac_dong`, `source_ngay_hieu_luc`, `cum_tu`, `doi_tuong`, `kem_theo`, `dinh_chi_*`, `gia_han_*`, `target_match_note`.

### `scope` ở v2

`scope` không có định dạng cố định. Mẫu 1.000 quan hệ ngẫu nhiên:

| Dạng | Số | Ví dụ | Vấn đề |
| --- | --- | --- | --- |
| `toàn bộ` | 342 | `toàn bộ` | — |
| `Khoản <y> Điều <x>` | 208 | `Khoản 3 Điều 2` | Chữ hoa không thống nhất với v3. |
| `Điều <x>` | 144 | `Điều 2` | Có ca gộp cả Điều khi câu chỉ sửa một điểm. Ví dụ `602450_78359`. |
| `chưa xác định` | 77 | `chưa xác định` | Không có vị trí. |
| `Điểm <z> Khoản <y> Điều <x>` | 75 | `Điểm a Khoản 3 Điều 2` | — |
| `Khoản <y>` | 36 | `Khoản 3` | Thiếu số Điều. |
| Dạng khác | 118 | `Phụ lục ba`, `Thứ tự 1, 2`, `Khoản 1, 3 Điều 37`, `nội dung: một số điều`, `toan-bo` | Nhiều vị trí trong một chuỗi, câu mô tả, hoặc chữ lỗi. Không ánh xạ được sang node. |

Một quan hệ v2 có một chuỗi `scope`. Chuỗi có nhiều vị trí thì người đọc phải tự tách.

## 3.5. Chất lượng đo được

Đo ngày 09/10/2026 trên toàn kho, chỉ đọc:

| Chỉ số | Giá trị | v3 xử lý |
| --- | --- | --- |
| Văn bản có chunk Điều rỗng nội dung | 46,6% | Dựng lại chunk. Mẫu 1.000 văn bản: 1.195 → 0. |
| Toàn văn còn NFD | 7,6% | Chuẩn hóa NFC. |
| Văn bản có `n_dieu` lệch | 3,7% | Đếm lại. |
| Văn bản không có chunk | 0,7% | Mọi văn bản có ít nhất một chunk. |
| Quan hệ chưa có đích | 60,5% | Khớp đích lại. Mẫu 1.000 văn bản: 64 → 293 quan hệ có đích, cả 293 đúng số hiệu. |
| `signers` thiếu | 447 văn bản | Chép nguyên. Chưa điền. |
| `legal_sectors` thiếu | 4 văn bản | Chép nguyên. Chưa điền. |
| `pdf_vbpl_id` thiếu | 80% | Không suy ra được từ toàn văn. |
| `pdf_minio_path` thiếu | 7,8% | Không suy ra được từ toàn văn. |
