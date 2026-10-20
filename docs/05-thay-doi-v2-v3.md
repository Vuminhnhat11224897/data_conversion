# 5. Thay đổi từ v2 sang v3

Tài liệu này so [03-hop-dong-du-lieu-v2.md](03-hop-dong-du-lieu-v2.md) với [04-hop-dong-du-lieu-v3.md](04-hop-dong-du-lieu-v3.md). Đọc tài liệu này khi chuyển một hệ thống đang đọc v2 sang v3.

## 5.1. Tóm tắt

| Mục | v2 | v3 |
| --- | --- | --- |
| Cụm ES | `10.1.10.10` | `10.1.10.23` |
| Index văn bản | `legal-docs` | `legal-docs-v3` |
| Index chunk | `legal-chunk-section-v2` (1 shard) | `legal-chunk-section-v3` (4 shard) |
| Index quan hệ | `legal-changed-v2` | `legal-changed-v3` |
| Bên ghi | Luồng realtime | Công cụ `vbpl_v3` (`uploaded_by = migration-v3`) |
| `_id` văn bản | `<doc>` | Giữ nguyên |
| Toàn văn | Có văn bản NFD | NFC |
| Cấu trúc | Bộ tách cũ. 46,6% văn bản có chunk Điều rỗng. | Parser mới + hybrid AI. Không có chunk Điều rỗng. |
| Quan hệ | Dò bằng bộ cũ. QA một phần. 39,5% có đích. | Dò lại từ toàn văn. 100% qua QA. Bản thử v4: 947/969 (97,7%) có đích. |
| Vị trí bị tác động | `scope` chữ tự do, nhiều vị trí trong một bản ghi | `scope` giữ chữ gốc. Mỗi quan hệ có đúng một vị trí trong `vi_tri`, theo định dạng cố định. |
| Nguyên tắc quan hệ | — | Chỉ tác động văn bản nêu trực tiếp. Không suy ra tác động lên đơn vị cha, con hay văn bản khác. |
| Metadata cho đồ thị | Không có | Ngày hiệu lực (văn bản và từng đơn vị), ngày hết hiệu lực, hồi tố, `la_vbqppl`, `cap_hieu_luc`, `hieu_luc_tac_dong`, `cap_quan_he`, `dan_chieu` |

## 5.2. `legal-docs` → `legal-docs-v3`

| Trường | v2 | v3 | Thay đổi |
| --- | --- | --- | --- |
| `document_number`, `title`, `legal_type`, `legal_sectors`, `issuing_authority`, `issuance_date`, `signers`, `tom_tat`, `action`, `url`, `pdf_minio_path`, `pdf_vbpl_id` | Có | Có | Chép nguyên. |
| `embedding` | Có | Có | Chép nguyên. Nguồn thiếu thì tạo vector của `title`. |
| `full_content` | Có, có văn bản NFD | Có, NFC | Chuẩn hóa. |
| `can_cu`, `can_cu_refs`, `noi_nhan`, `has_tail` | Có | Có | Tính lại. |
| `intro` | Có văn bản chứa cả dòng căn cứ | Chỉ phần sau căn cứ, trước Điều đầu | Tính lại. |
| `n_dieu` | Bộ cũ đếm. 3,7% lệch. | Đếm Điều văn bản chính | Tính lại. |
| `phu_luc[]` | `{tieu_de, noi_dung}`. `tieu_de` chỉ có dòng nhãn. | Thêm `loai`, `ky_hieu`, `has_table`, `n_tables`, `n_table_rows`, `dieu_luat`. `tieu_de` gồm ghi chú "(Kèm theo …)". | Tính lại. Văn bản kèm theo nằm trong phần chính chuyển vào `phu_luc[]`. |
| `content_sha256`, `grade`, `text_source` | Chỉ 6 văn bản tải lên | Mọi văn bản | Mới cho `legacy`. |
| `origin`, `ingest_job_id`, `ingest_revision`, `ingested_at`, `uploaded_by` | Chỉ 6 văn bản tải lên (`uploaded_by = api`) | Mọi văn bản (`uploaded_by = migration-v3`) | Mới cho `legacy`. |
| `la_vbqppl`, `la_vbqppl_cach`, `cap_hieu_luc`, `cap_hieu_luc_nhan`, `cap_hieu_luc_ghi_chu` | Không có | Có | Mới. |
| `ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_trich` | Không có | Có | Mới. |
| `ngay_het_hieu_luc`, `ngay_het_hieu_luc_cach`, `ngay_het_hieu_luc_trich` | Không có | Có | Mới. |
| `hoi_to`, `ngay_hoi_to`, `ngay_hoi_to_trich`, `hoi_to_vi_tri` | Không có | Có | Mới. |
| `ngay_hieu_luc_so_ngay`, `hieu_luc_rieng` | Không có | Có | Mới. Số ngày sau mốc; ngày hiệu lực riêng của từng Điều, khoản, điểm. |

## 5.3. `legal-chunk-section-v2` → `legal-chunk-section-v3`

| Mục | v2 | v3 |
| --- | --- | --- |
| `chunk_type` | 10 giá trị | Thêm `noi_dung_full`, `tieu_diem` (12 giá trị) |
| Dưới cấp điểm | Không có | Chunk `tieu_diem` `<doc>_d<x>_k<y>_p<z>_t<n>` cho mục gạch đầu dòng của điểm. Trường `diem_uid`, `so_tieu_diem`. |
| Ngày hiệu lực | Không có | Mọi chunk có `ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_so_ngay`, `ngay_hieu_luc_rieng`. Chunk hồi tố có `ngay_hoi_to`. |
| Văn bản không cấu trúc, nội dung dài | Một chunk `<doc>_nd` | `<doc>_nd_full` và các đoạn `<doc>_nd<k>` (trường `so_doan`). Mỗi đoạn tối đa khoảng 200 âm tiết. |
| Văn bản kèm theo nằm trong phần chính | `<doc>_s<s>_d<x>…` | `<doc>_pl<i>_d<x>…`. **ID đổi.** |
| Trùng ID | — | Chunk sau có thêm `_2`, `_3`… |
| Chunk Điều rỗng nội dung | 46,6% văn bản | 0 |
| `dan_chieu[]` | Không có | Mới |
| `embedding` | Có | Dùng lại vector v2 khi chuỗi `tieu_de + " " + noi_dung` không đổi. Chuỗi khác thì tạo vector mới. |
| 5 trường truy vết | Chỉ chunk của văn bản tải lên | Mọi chunk |
| Các trường khác | — | Giữ tên, kiểu và nghĩa |

## 5.4. `legal-changed-v2` → `legal-changed-v3`

Công cụ không chép quan hệ v2. Công cụ dò lại mọi quan hệ từ toàn văn. **Không có ánh xạ một–một giữa bản ghi v2 và bản ghi v3.**

| Mục | v2 | v3 |
| --- | --- | --- |
| `_id` | `<n>` là bộ đếm chung. Có hậu tố `_split`, `_f<n>`. Ví dụ `602450_78359`. | `<n>` đếm từ 0 theo từng văn bản nguồn và tiền tố. Không có hậu tố, không khuyết số. Ví dụ `602450_1`. |
| Tiền tố `_id` | `hidden_`, `hhl_`, `intro_` | Thêm `hd_` (quan hệ hướng dẫn), `hn_` (quan hệ hợp nhất) |
| `action` | 5 giá trị | 13 giá trị. Thêm `thay-cum-tu`, `dinh-chi`, `ngung-hieu-luc`, `dinh-chinh`, `gia-han`, `huong-dan`, `quy-dinh-chi-tiet`, `hop-nhat`. |
| `detection_mode` | `hidden`, `het_hieu_luc`, `intro` | Thêm `title_guidance`, `hop_nhat` |
| Một bản ghi | Một câu, nhiều vị trí | Một vị trí. Câu có N vị trí cho N quan hệ cùng `scope`. |
| `scope` | Chữ tự do, một chuỗi cho nhiều vị trí | Chữ gốc, chuẩn hóa `toàn bộ`. Không dùng để nối. |
| `vi_tri` | Không có | Mảng có tối đa một vị trí đủ cấp, định dạng cố định |
| Đơn vị nguồn | Thường dừng ở khoản | Xuống tới điểm (`Điều 1 Khoản 1 điểm a`) |
| Văn bản hợp nhất | Có thể có quan hệ từ ghi chú | Chỉ có quan hệ `hop-nhat` tới văn bản được hợp nhất |
| Lời dẫn và Điều cùng đích | Có ca bị bỏ | Luôn có quan hệ riêng |
| QA | `scope_grounding_checked` ở 35,2% | Mọi quan hệ qua QA hành động. Phạm vi được xác nhận bằng quy tắc hoặc QA phạm vi. |
| `unresolved = true` | 13,0% | Bản thử v4: 9/969 (0,9%) |
| `scope_resolution_method` | text + keyword. Chỉ `explicit_declaration`. | keyword. Thêm `liet_ke_vi_tri`. |
| `target_issuing_authority` | text + keyword | keyword |
| `inherited_from_v1` | 1.580 bản ghi | Không ghi. Mapping còn trường này. |
| Trường mới | — | `vi_tri`, `cap_quan_he`, `hieu_luc_tac_dong`, `source_ngay_hieu_luc` (ngày của đơn vị nguồn), `source_ngay_hoi_to`, `cum_tu`, `doi_tuong`, `kem_theo`, `dinh_chi_tu_ngay`, `dinh_chi_den_ngay`, `dinh_chi_den_khi`, `gia_han_den_ngay`, `gia_han_den_khi`, `target_match_note` |

So sánh trên cùng văn bản `602450` (NĐ 31/2024/NĐ-CP):

| | v2 | v3 |
| --- | --- | --- |
| Số quan hệ | 18 | 40. Mỗi điểm sửa đổi là một quan hệ. |
| Ví dụ | `602450_78359`: `source_path = Điều 1 Khoản 1`, `scope = Điều 2` | `602450_1`: `source_path = Điều 1 Khoản 1 điểm a`, `vi_tri = ["điểm a khoản 3 Điều 2"]` |
| Ca lỗi | `602450_78360`: `scope = Phụ lục ba`, `unresolved = true` | Vị trí phụ lục theo định dạng `Phụ lục <ký hiệu>` hoặc `Mẫu số <mã> Phụ lục <ký hiệu>` |

## 5.5. Việc cần làm ở bên đọc

1. Đổi tên index. Đề xuất: dùng alias riêng, ví dụ `legal-docs-current`, trỏ tới index v3.
2. Đọc `vi_tri` để nối node. Không phân tích `scope`.
3. Không lưu `_id` quan hệ làm khóa lâu dài. `_id` đổi khi chạy lại văn bản nguồn.
4. Không đọc `vi_tri` như danh sách nhiều vị trí. Mỗi quan hệ có tối đa một vị trí. Gom các quan hệ cùng câu bằng `source_id`, `source_path`, `action`, `scope`.
5. Cập nhật ID chunk đã lưu: `<doc>_s<s>_…` của v2 thành `<doc>_pl<i>_…` của v3.
6. Phân biệt 2 trường `action`. `legal-docs-v3.action` phân loại văn bản (`huongdan`). `legal-changed-v3.action` là hành động của quan hệ (`huong-dan`).
7. `target_matched_id` và `dan_chieu[].target_id` trỏ tới `legal-docs` nguồn. Văn bản đích chỉ có trong v3 khi văn bản đó đã chuyển.
8. `legal_sectors` trên chunk và `source_legal_sectors` trên quan hệ vẫn là chuỗi, không phải mảng.
