# 4. Hợp đồng dữ liệu v3 (hiện trạng)

Tài liệu này mô tả dữ liệu **đang có** trong 3 index v3 trên ES đích `10.1.10.23`. Bên dữ liệu ghi các index này. Bên Graph và bên tìm kiếm đọc.

- Đếm ngày 28/10/2026: v3 có 236 văn bản, 14.677 chunk, 4.201 quan hệ.
- v3 có 2 nhóm bản ghi:

| Nhóm | Ghi ngày | Văn bản | Chunk | Quan hệ | Mô tả ở |
| --- | --- | --- | --- | --- | --- |
| Bản ghi gốc | 09–15/10/2026 | 204 | 6.291 | 733 | Mục 4.1–4.11. Số liệu đo ngày 19/10/2026. |
| 32 văn bản của bộ 88 testcase | 27/10/2026 | 32 | 8.386 | 3.468 | Mục 4.12. Số liệu đo ngày 28/10/2026. |

- Mục 4.1–4.11 chỉ mô tả 204 văn bản gốc, trừ khi ghi khác.
- Tài liệu ghi đúng dữ liệu, kể cả lỗi. Mỗi lỗi có số lượng và ví dụ. Bảng tóm tắt lỗi ở mục 4.10.
- Công cụ ghi 204 văn bản gốc bằng chế độ `rules` ngày 09–13/10/2026. Văn bản 132140 ghi ngày 15/10/2026.
- v3 chưa được ghi lại toàn bộ. Bên dữ liệu chỉ ghi lại v3 khi bên Graph duyệt `-v4`. Hai ngoại lệ có người dùng duyệt: văn bản 132140 (15/10/2026) và 32 văn bản (27/10/2026).
- Hợp đồng đích (sau khi ghi lại v3) là [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md). Code hiện hành là master `1117e63` (27/10/2026). Khi ghi lại, công cụ chỉ đổi hậu tố `-v4` thành `-v3`.
- So sánh v2, v3, v4 ở [05](05-phien-ban-v2-v3-v4.md).
- Ví dụ chính: Nghị định 31/2024/NĐ-CP, `legal-docs-v3/602450`. Ví dụ viết dạng `<index>/<_id>`.
- Nghĩa của giá trị enum ở [06-bang-enum.md](06-bang-enum.md). Cột "Số v3" của tài liệu 06 đếm trên bản thử v4 ngày 14/10/2026, không phải trên v3. Số đếm của v3 ở tài liệu này.
- Cách đo lại ở mục 4.11.

## 4.1. Phạm vi và quy tắc chung

| Index | Một bản ghi là | Số bản ghi | Mẫu `_id` |
| --- | --- | --- | --- |
| `legal-docs-v3` | Một văn bản | 204 (236 ngày 28/10) | `<doc>`, bằng `_id` ở `legal-docs` nguồn |
| `legal-chunk-section-v3` | Một chunk | 6.291 (14.677 ngày 28/10) | `<doc>_<đơn vị>`, ví dụ `602450_d1_k1_pa` |
| `legal-changed-v3` | Một quan hệ | 733 (4.201 ngày 28/10) | `[<tiền tố>]<source_id>_<n>`, ví dụ `602450_1` |

Quy tắc chung:

1. Mọi trường trong bảng đều có, trừ trường ghi "Có khi …".
2. Trường không có trong tài liệu này thì không có trong dữ liệu v3. Đo 19/10: không bản ghi nào có trường ngoài tài liệu. Đo 28/10: 2 văn bản của nhóm 32 văn bản có trường ngoài tài liệu (mục 4.12.2).
3. Mapping `legal-changed-v3` có `inherited_from_v1`. Dữ liệu v3 không có trường này. Không dùng.
4. Vector có 1.024 chiều (`BAAI/bge-m3`). `legal-changed-v3` không có vector.
5. Mapping v3 cho phép ES tự thêm trường. Mapping v3 không có các trường của hợp đồng đích ở mục 4.10.

| Ký hiệu | Nghĩa |
| --- | --- |
| Có khi X | Trường có khi X đúng. Trường thiếu khi X sai. |
| `null` | Trường có, giá trị là `null`. |
| Rỗng | Giá trị là `""` hoặc `[]`. |
| Ngày | Chuỗi `YYYY-MM-DD` hợp lệ. |
| Thời điểm | Chuỗi ISO 8601 có múi giờ. |

## 4.2. Khóa nối

| Từ | Đến | Quy tắc | Đo 19/10 | Ví dụ |
| --- | --- | --- | --- | --- |
| chunk `doc_id` | văn bản `_id` | Mọi chunk thuộc một văn bản có trong `legal-docs-v3`. Mọi văn bản có ít nhất một chunk. | Đúng cả hai | `602450_d1_k1_pa` → `602450` |
| chunk `dieu_uid`, `khoan_uid` | node Điều, node khoản | Gom chunk con với Điều, khoản chứa nó. `_id` của chunk bắt đầu bằng `dieu_uid`. | Đúng | `602450_d1_k1_pa`: `dieu_uid = 602450_d1`, `khoan_uid = 602450_d1_k1` |
| chunk `diem` `_id` | node điểm | v3 không có `diem_uid`. ID node điểm là `_id` của chunk `diem`. | — | `602450_d1_k1_pa` |
| quan hệ `source_id` | văn bản `_id` | Văn bản nguồn luôn có trong `legal-docs-v3`. `source_id` là số nguyên. `_id` là chuỗi. | Đúng. 77 văn bản nguồn. | `602450_1` → `602450` |
| quan hệ `target_matched_id` | `legal-docs._id` (nguồn) | Văn bản đích có trong v3 chỉ khi văn bản đó đã chuyển. | 3/109 văn bản đích có trong v3 | `602450_1` → `legal-docs/133717` |
| chunk `dan_chieu[].target_id` | `legal-docs._id` (nguồn) | Như `target_matched_id`. `null` khi chưa nối được. | 104/920 dẫn chiếu ra ngoài là `null` | `602450_d2_full` → `legal-docs/315420` |

## 4.3. Vị trí

`vi_tri`, `cum_tu[].vi_tri`, `dan_chieu[].vi_tri` và `hoi_to_vi_tri` dùng định dạng này. Vị trí thuộc văn bản đích, văn bản được dẫn chiếu, hoặc chính văn bản (`hoi_to_vi_tri`).

| Dạng | Nghĩa | Số trong `vi_tri` | Ví dụ |
| --- | --- | --- | --- |
| `Điều <x>` | Cả Điều | 208 | `Điều 11` (`legal-changed-v3/585073_59`), `Điều 43a` (`611245_25`) |
| `khoản <y> Điều <x>` | Cả khoản | 359 | `khoản 1 Điều 6` (`legal-changed-v3/602450_15`) |
| `điểm <z> khoản <y> Điều <x>` | Cả điểm | 216 | `điểm a khoản 3 Điều 2` (`legal-changed-v3/602450_1`) |
| `tên Điều <x>` | Chỉ tên Điều. Nội dung giữ nguyên. | 3 | `tên Điều 42` (`legal-changed-v3/288269_29`) |
| `tên Chương <c>` | Chỉ tên Chương | 4 | `tên Chương IV` (`legal-changed-v3/288269_27`) |
| `tên Mục <n> Chương <c>` | Chỉ tên Mục | 2 | `tên Mục 2 Chương II` (`legal-changed-v3/288269_59`) |
| `Phụ lục`, `Phụ lục <ký hiệu>` | Phụ lục. Không có ký hiệu khi câu nguồn không nêu ký hiệu. | 7 | `Phụ lục II` (`legal-changed-v3/585073_61`) |
| `Mục <ký hiệu> Phụ lục` | Mục của một phụ lục | 1 | `Mục IV Phụ lục` (`legal-changed-v3/662238_85`) |
| `tên văn bản` | Chỉ tên văn bản | 2 | `legal-changed-v3/900000013_12` |
| `toàn bộ` | Cả văn bản | 52 | `legal-changed-v3/241415_0` |

Thành phần:

- `<x>`, `<y>`: số, có thể kèm một chữ thường. Ví dụ: `47a`, `8a`.
- `<z>`: chữ cái, có thể kèm số (`a`, `đ`).
- `<c>`: số La Mã hoặc số, ghi như văn bản đích viết.
- `khoản`, `điểm`, `tên` viết thường. `Điều`, `Chương`, `Mục`, `Phụ lục` viết hoa chữ đầu.

Quy tắc:

- Gạch đầu dòng, câu, đoạn không có vị trí riêng. Vị trí dừng ở điểm, khoản hoặc Điều chứa nó.
- v3 không có vị trí `tiểu điểm`.
- `dan_chieu[].vi_tri` luôn đúng định dạng (2.191/2.191).

### 4.3.1. Vị trí ngoài định dạng

40/733 quan hệ có ít nhất một vị trí ngoài định dạng. Bên Graph không dựng node từ các vị trí này.

| Dạng | Quan hệ | Ví dụ |
| --- | --- | --- |
| `Mẫu số <ký hiệu>`, có hoặc không có phụ lục chứa mẫu | 36 (25 có nêu phụ lục) | `Mẫu số 04 Phụ lục I` (`legal-changed-v3/602450_4`), `Mẫu số 01/KK-XS` |
| `Mục <n> Chương <c> <tên văn bản>` | 2 | `Mục 1 Chương IV Quy định kỹ thuật cho 11 công tác …` (`662238_13`) |
| `Mục <n> Phần <c>` | 1 | `Mục 7 Phần I` (`662238_33`) |
| `Mục <số thập phân> Chương <c>` | 1 | `Mục 1.2 Chương II` (`662238_65`) |

Hợp đồng đích ghi mẫu biểu là phụ lục chứa nó ("Mẫu số 04 Phụ lục I" cho `Phụ lục I`). v3 chưa áp dụng quy tắc này.

## 4.4. Đơn vị nguồn

`source_path` chỉ đơn vị của văn bản nguồn chứa câu tác động. `source_path` không dùng định dạng Vị trí: `Khoản` viết hoa, thứ tự từ Điều xuống điểm. Không so sánh trực tiếp `source_path` với `vi_tri`.

| Dạng | Nghĩa | Chunk tương ứng | Số | Ví dụ |
| --- | --- | --- | --- | --- |
| `Điều <x>` | Cả Điều của văn bản nguồn | `<doc>_d<x>` hoặc `<doc>_d<x>_full` | 128 | `Điều 16` (`legal-changed-v3/hidden_86794_0`) |
| `Điều <x> Khoản <y>` | Khoản | `<doc>_d<x>_k<y>` hoặc `…_full` | 378 | `Điều 1 Khoản 24` → `288269_d1_k24` |
| `Điều <x> Khoản <y> điểm <z>` | Điểm | `<doc>_d<x>_k<y>_p<z>` | 175 | `Điều 1 Khoản 1 điểm a` → `602450_d1_k1_pa` |
| `intro` | Lời dẫn | Node văn bản | 23 | `legal-changed-v3/intro_602450_0` |
| `Tiêu đề`, `Lời dẫn` | Chỉ có ở quan hệ hướng dẫn | Node văn bản | 20, 6 | `legal-changed-v3/hd_2211_0` |
| `Căn cứ` | Quan hệ hướng dẫn lấy đích từ phần căn cứ. Hợp đồng đích không có dạng này. | Node văn bản | 2 | `legal-changed-v3/hd_135577_0` |
| `Mục <n>` | Đề mục của văn bản không chia Điều | `<doc>_m<n>` | 1 | `Mục 1` → `318496_m1` |

v3 không có quan hệ có nguồn trong phụ lục, văn bản kèm theo, phần đầu văn bản hợp nhất hoặc nội dung không đề mục. `source_in_phu_luc` luôn là `false`.

## 4.5. Trường truy vết

Cả 3 index có 5 trường này. Đo 19/10: mọi bản ghi đúng quy tắc.

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `origin` | keyword | `legacy` hoặc `user_upload`. Chép từ nguồn. Nguồn thiếu thì `legacy`. | `legacy` (203), `user_upload` (1) |
| `ingest_job_id` | keyword | `v3:<run_id>`, `run_id` dạng `YYYYMMDDTHHMMSSZ`. Lượt đã ghi bản ghi. | `v3:20261012T075451Z` |
| `ingest_revision` | integer | Luôn bằng `1`. | `1` |
| `ingested_at` | date | Thời điểm ghi (UTC). | `2026-10-12T08:24:58.843022+00:00` |
| `uploaded_by` | keyword | Luôn bằng `migration-v3`. | `migration-v3` |

Chunk có 5 trường bằng giá trị của văn bản. Quan hệ có 5 trường bằng giá trị của văn bản nguồn.

Các lượt đã ghi v3:

| `ingest_job_id` | Văn bản | Chunk | Quan hệ |
| --- | --- | --- | --- |
| `v3:20261009T091833Z` | 100 | 1.417 | 21 |
| `v3:20261012T020742Z` | 7 | 645 | 239 |
| `v3:20261012T075451Z` | 93 | 4.197 | 455 |
| `v3:20261013T024421Z` | 3 | 29 | 18 |
| `v3:20261015T100151Z` | 1 (`132140`) | 3 | 0 |
| `v3:20261027T101856Z` | 32 (mục 4.12) | 8.386 | 3.468 |

- Lượt ngày 15/10 ghi một văn bản theo trường của mapping v3 ([02, "Ghi thử vào v4"](02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3)).
- Lượt ngày 27/10 ghi 32 văn bản không trùng ID với 204 văn bản gốc. Lượt này không đổi bản ghi gốc (đếm theo `ingest_job_id` ngày 28/10/2026).

## 4.6. `legal-docs-v3`

### 4.6.1. Ví dụ: `legal-docs-v3/602450`

Chuỗi dài giữ câu đầu và "…". Mảng dài giữ 1–2 phần tử đầu. `embedding` giữ 3 số đầu.

```json
{
  "_index": "legal-docs-v3",
  "_id": "602450",
  "_source": {
    "document_number": "31/2024/NĐ-CP",
    "title": "Nghị định 31/2024/NĐ-CP sửa đổi Nghị định 01/2012/NĐ-CP, Nghị định 61/2016/NĐ-CP và Nghị định 36/2019/NĐ-CP",
    "legal_type": "Nghị định",
    "legal_sectors": ["Thể thao - Y tế", "Văn hóa - Xã hội"],
    "issuing_authority": "Chính phủ",
    "issuance_date": "2024-03-15",
    "signers": "Trần Hồng Hà:1381",
    "tom_tat": "Nghị định này sửa đổi, bổ sung một số quy định về thủ tục cấp phép …",
    "action": "sua-doi",
    "url": "https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Nghi-dinh-31-2024-ND-CP-…-602450.aspx",
    "pdf_minio_path": "tvpl-pdf/31-2024-NĐ-CP_602450.pdf",
    "pdf_vbpl_id": "166544",
    "embedding": [-0.0624, 0.0211, 0.0225, "… (1.024 số)"],
    "full_content": "CHÍNH PHỦ | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM …",
    "content_sha256": "c5df4ece0318e6bc0141e51708adbd43bfb15183d1430782f3f540c38fb4c4ed",
    "text_source": "source_full_content",
    "can_cu": ["Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015; …"],
    "can_cu_refs": [],
    "intro": "Theo đề nghị của Bộ trưởng Bộ Văn hóa, Thể thao và Du lịch; …",
    "noi_nhan": ["Ban Bí thư Trung ương Đảng", "… (19 phần tử)", "Lưu: VT, KSTT (2). | TM. CHÍNH PHỦ KT. THỦ TƯỚNG PHÓ THỦ TƯỚNG Trần Hồng Hà"],
    "phu_luc": [
      {"tieu_de": "PHỤ LỤC I (Kèm theo Nghị định số 31/2024/NĐ-CP ngày 15 tháng 3 năm 2024 của Chính phủ)",
       "noi_dung": "| Mẫu số 01 | Đơn đề nghị cấp giấy phép mang di vật, cổ vật ra nước ngoài | …",
       "loai": "labeled", "ky_hieu": "I", "has_table": true, "n_tables": 2, "n_table_rows": 10, "dieu_luat": []},
      "… (3 phần tử)"
    ],
    "has_tail": true,
    "n_dieu": 4,
    "grade": "full",
    "la_vbqppl": true,
    "la_vbqppl_cach": "theo_loai",
    "cap_hieu_luc": 5,
    "cap_hieu_luc_nhan": "CHINH_PHU",
    "cap_hieu_luc_ghi_chu": null,
    "ngay_hieu_luc": "2024-03-15",
    "ngay_hieu_luc_cach": "ngay_ky",
    "ngay_hieu_luc_trich": "Nghị định này có hiệu lực thi hành kể từ ngày ký ban hành.",
    "ngay_het_hieu_luc": null,
    "ngay_het_hieu_luc_cach": "khong_ghi",
    "ngay_het_hieu_luc_trich": null,
    "hoi_to": false,
    "ngay_hoi_to": null,
    "ngay_hoi_to_trich": null,
    "hoi_to_vi_tri": [],
    "origin": "legacy",
    "ingest_job_id": "v3:20261012T075451Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-12T08:24:58.843022+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

Phần tử cuối của `noi_nhan` có dòng chữ ký. Đây là lỗi đã biết (mục 4.6.3).

### 4.6.2. Định danh và metadata

Công cụ chép các trường này từ `legal-docs` nguồn. Công cụ không sửa giá trị.

| Trường | Kiểu | Có | Quy tắc | Đo 19/10 |
| --- | --- | --- | --- | --- |
| `_id` | chuỗi | Mọi văn bản | Chỉ có chữ số. Bằng `_id` nguồn. | 204 |
| `document_number` | keyword | Mọi văn bản | Khác rỗng. Không duy nhất. | 204 |
| `title` | text | Mọi văn bản | Khác rỗng. | 204 |
| `legal_type` | keyword | Mọi văn bản | Khác rỗng. | 17 giá trị. Nhiều nhất: Quyết định 103, Thông tư 32, Nghị quyết 21. |
| `legal_sectors` | mảng keyword | Có khi nguồn có | Mỗi phần tử khác rỗng. | 204 |
| `issuing_authority` | keyword | Mọi văn bản | Khác rỗng. | 204 |
| `issuance_date` | date | Mọi văn bản | Là Ngày. | 204 |
| `signers` | keyword, không index | Có khi nguồn có | Dạng `Tên:mã`. Nhiều người cách nhau bằng dấu phẩy. Văn bản tải lên chỉ có tên. | 204 |
| `tom_tat` | text | Mọi văn bản | Khác rỗng. | 204 |
| `action` | keyword | Mọi văn bản | Phân loại văn bản ở nguồn. **Không phải** hành động của quan hệ. | `other` 139, `sua-doi` 21, `huongdan` 21, `congvan` 11, `huy-bo` 5, `bo-sung` 4, `hopnhat` 2, `bai-bo` 1 |
| `url` | keyword, không index | Mọi văn bản | `legacy`: bắt đầu bằng `https://thuvienphapluat.vn/`. `user_upload`: `upload://<_id>`. | 204 |
| `pdf_minio_path` | keyword | Có khi nguồn có | `tvpl-pdf/…_<_id>.pdf` hoặc `legal-upload/pdf/<sha256>.pdf`. | 96 |
| `pdf_vbpl_id` | keyword | Có khi nguồn có | Chỉ có chữ số. | 53 |
| `embedding` | dense_vector 1.024 | Mọi văn bản | Chép từ nguồn. Nguồn thiếu thì công cụ tạo vector của `title`. | 204 |

### 4.6.3. Nội dung và cấu trúc

Công cụ tính lại các trường này từ toàn văn.

| Trường | Kiểu | Có | Quy tắc | Đo 19/10 |
| --- | --- | --- | --- | --- |
| `full_content` | text | Mọi văn bản | Toàn văn nguồn, chuẩn hóa NFC. Khác rỗng. | Đúng |
| `content_sha256` | keyword | Mọi văn bản | SHA-256 (hex) của `full_content` mã hóa UTF-8. | Đúng |
| `text_source` | keyword | Mọi văn bản | Nơi lấy chữ. `legacy` luôn là `source_full_content`. | `source_full_content` 203, `ocr` 1 (`900000013`) |
| `can_cu` | mảng chuỗi, không index | Mọi văn bản | Mỗi phần tử là một dòng bắt đầu bằng "Căn cứ". Rỗng khi không có căn cứ. | Đúng |
| `can_cu_refs` | mảng keyword | Mọi văn bản | Số hiệu nêu trong `can_cu`. | Rỗng ở 44 |
| `intro` | text | Mọi văn bản | Lời dẫn sau căn cứ, trước Điều đầu tiên. Rỗng khi không có. | Rỗng ở 6 |
| `noi_nhan` | mảng chuỗi, không index | Mọi văn bản | Các dòng sau "Nơi nhận". Rỗng ở 53. **Có lỗi**, xem dưới bảng. | — |
| `phu_luc` | mảng object, `enabled: false` | Mọi văn bản | Phụ lục và văn bản kèm theo. ES không tìm kiếm được trường này. Mục 4.6.4. | 97 văn bản có, 371 phần tử |
| `has_tail` | boolean | Mọi văn bản | `true` khi văn bản có chữ ký hoặc Nơi nhận. | `true` 188 |
| `n_dieu` | integer | Mọi văn bản | Số Điều của văn bản chính. Không tính Điều trong phụ lục và chuỗi Điều kèm theo. | — |
| `grade` | keyword | Mọi văn bản | Chất lượng tách cấu trúc. Không đo giá trị pháp lý. | `full` 170, `partial` 15, `minimal` 19 |

Lỗi đã biết của `noi_nhan`:

- 132/204 văn bản có ký tự `|` ở phần tử cuối. Phần lớn là dòng "Lưu: …" nối với khối chữ ký. Ví dụ `10377`: `Lưu : VP. | TM. ỦY BAN NHÂN DÂN TỈNH KT. CHỦ TỊCH PHÓ CHỦ TỊCH Nguyễn Văn Đảm`.
- Một số văn bản không có mục "Nơi nhận" nhưng có `noi_nhan` là dòng chữ ký. Ví dụ `119343`: `["BỘ TRƯỞNG, CHỦ NHIỆM Nguyễn Xuân Phúc"]`.
- Một số văn bản có chữ tách rời từng ký tự ("N ơ i nhận"). Ví dụ `287278`, `186498`.

Tên người ký nằm ở `signers`. Không lấy tên người ký từ `noi_nhan`.

### 4.6.4. `phu_luc[]`

- Mỗi phần tử là một phụ lục có nhãn, hoặc một văn bản kèm theo không nhãn.
- Thứ tự phần tử là thứ tự trong văn bản.
- Phần tử thứ `i` (đếm từ 0) có chunk ID bắt đầu bằng `<doc>_pl<i>`.
- Phụ lục không chia Điều có một chunk `phu_luc` chứa toàn bộ phụ lục. Đo 19/10: 342 phần tử không chia Điều, 342 chunk `phu_luc`.

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `loai` | chuỗi | `labeled` (262) hoặc `unlabeled` (109). | `labeled` |
| `ky_hieu` | chuỗi \| `null` | Ký hiệu trong nhãn. `null` khi `unlabeled` hoặc nhãn không có ký hiệu. Không duy nhất trong một văn bản. | `I`; `01` |
| `tieu_de` | chuỗi | Tiêu đề đầy đủ, gồm ghi chú "(Kèm theo …)". Khác rỗng. | `PHỤ LỤC I (Kèm theo Nghị định số 31/2024/NĐ-CP …)` |
| `noi_dung` | chuỗi | Nội dung sau tiêu đề. Bảng ở dạng dòng `\| … \|`. Có thể rỗng. | `\| Mẫu số 01 \| …` |
| `has_table` | boolean | `true` khi `n_table_rows ≥ 2`. | `true` |
| `n_tables` | integer | Số bảng. | `2` |
| `n_table_rows` | integer | Số dòng bắt đầu bằng `\|`. Lệch ở 1/371 phần tử (`132723`, phần tử 0: ghi 2, đếm được 1). | `10` |
| `dieu_luat` | mảng object | Các Điều của phần này. Rỗng khi phần không chia Điều. Mục 4.6.5. | `[]` |

### 4.6.5. `phu_luc[].dieu_luat[]`

29 phần tử có Điều, tổng 448 Điều, 939 khoản, 258 điểm.

| Trường | Kiểu | Có | Nghĩa |
| --- | --- | --- | --- |
| `so_dieu` | integer | Luôn | Phần số của Điều. |
| `ky_hieu` | chuỗi | Luôn | Ký hiệu đầy đủ, ví dụ `47a`. Bắt đầu bằng `so_dieu`. |
| `tieu_de` | chuỗi | Luôn | Tên Điều. Rỗng khi Điều không có tên. |
| `noi_dung` | chuỗi | Luôn | Toàn bộ nội dung Điều, gồm các khoản. |
| `so_van_ban_refs` | mảng chuỗi | Luôn | Số hiệu nêu trong Điều. |
| `khoan` | mảng object | Luôn | Các khoản. Rỗng khi Điều không chia khoản. |
| `mo_dau` | chuỗi | Có khi `khoan` khác rỗng | Phần trước khoản đầu tiên. |
| `chuong` | chuỗi | Có khi Điều nằm trong một Chương | Tên Chương. 310/448 Điều. |
| `van_ban_kem_theo` | integer | Có khi Điều thuộc chuỗi Điều kèm theo | Thứ tự chuỗi, từ 1. Bằng `segment` của chunk. 104/448 Điều. |
| `khoan[].so_khoan`, `khoan[].ky_hieu` | integer, chuỗi | Luôn | Như `so_dieu`, `ky_hieu`. |
| `khoan[].noi_dung` | chuỗi | Luôn | Toàn bộ nội dung khoản, gồm các điểm. |
| `khoan[].so_van_ban_refs` | mảng chuỗi | Luôn | Số hiệu nêu trong khoản. |
| `khoan[].diem` | mảng object | Luôn | Các điểm. Rỗng khi khoản không chia điểm. |
| `khoan[].mo_dau` | chuỗi | Có khi `diem` khác rỗng | Phần trước điểm đầu tiên. |
| `khoan[].diem[].ky_hieu`, `noi_dung`, `so_van_ban_refs` | chuỗi, chuỗi, mảng chuỗi | Luôn | Ký hiệu, nội dung, số hiệu của điểm. |

v3 không có `dieu_luat[].muc`, `diem[].tieu_diem` và `diem[].mo_dau`.

### 4.6.6. Địa vị pháp lý

Công cụ tính các trường này bằng quy tắc, từ `legal_type`, `issuing_authority`, `document_number`, `issuance_date`, `title`. Công cụ không gọi model. Đo 19/10: mọi văn bản đúng các quy tắc trong bảng.

| Trường | Kiểu | Quy tắc | Đo 19/10 |
| --- | --- | --- | --- |
| `la_vbqppl` | boolean \| `null` | `true`: văn bản quy phạm pháp luật. `null` khi và chỉ khi `la_vbqppl_cach = can_kiem`. | `true` 94, `false` 109, `null` 1 |
| `la_vbqppl_cach` | keyword | Căn cứ phân loại. | `theo_loai` 69, `so_hieu_co_nam` 47, `so_hieu_khong_nam` 37, `tieu_de_ca_biet` 36, `quyet_dinh_bo_tu_2009` 7, `co_quan_khong_ban_hanh_vbqppl` 3, `van_ban_hop_nhat` 2, `can_kiem` 1, `chi_thi_tu_2016` 1, `van_ban_dang` 1 |
| `cap_hieu_luc` | integer \| `null` | 1..15 theo Luật 87/2025/QH15. `null` khi `la_vbqppl` khác `true`. | `null` 112. Nhiều nhất: 8 (34), 11 (32). |
| `cap_hieu_luc_nhan` | keyword \| `null` | Nhãn của `cap_hieu_luc`. `null` khi và chỉ khi `cap_hieu_luc = null`. | Đúng |
| `cap_hieu_luc_ghi_chu` | keyword \| `null` | `hinh_thuc_cu`, `cap_huyen`, `khong_xac_dinh` hoặc `null`. `cap_huyen`, `khong_xac_dinh` đi với `cap_hieu_luc = null`. | `null` 195, `hinh_thuc_cu` 7 (`10377`), `cap_huyen` 2 |

### 4.6.7. Thời điểm hiệu lực

Công cụ chỉ đọc câu của chính văn bản. Công cụ bỏ câu nằm trong ngoặc kép. Chủ ngữ của câu phải đúng loại văn bản ("Thông tư này" với Thông tư).

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `ngay_hieu_luc` | date \| `null` | Ngày có hiệu lực. `null` khi cách đọc không cho ngày (31/204). | `2024-03-15` |
| `ngay_hieu_luc_cach` | keyword | Cách đọc ngày. Giá trị ở bảng dưới. | `ngay_ky` |
| `ngay_hieu_luc_trich` | keyword, không index \| `null` | Câu gốc, tối đa 300 ký tự. `null` khi và chỉ khi cách đọc là `mac_dinh_ngay_ban_hanh`, `khong_tim_thay` hoặc `van_ban_hop_nhat`. | `Nghị định này có hiệu lực thi hành kể từ ngày ký ban hành.` |
| `ngay_het_hieu_luc` | date \| `null` | Ngày hết hiệu lực do chính văn bản ghi. `null` khi và chỉ khi `ngay_het_hieu_luc_cach = khong_ghi`. | `2013-12-31` (`legal-docs-v3/163439`) |
| `ngay_het_hieu_luc_cach` | keyword | `ngay_cu_the` (3), `khong_ghi` (201). | `khong_ghi` |
| `ngay_het_hieu_luc_trich` | keyword, không index \| `null` | Câu gốc. `null` khi và chỉ khi `khong_ghi`. | `Quyết định này có hiệu lực kể từ ngày 01/01/2013 đến hết ngày 31/12/2013.` |
| `hoi_to` | boolean | `true`: văn bản áp dụng từ một ngày trước `issuance_date`. `true` khi và chỉ khi `ngay_hoi_to` khác `null`. | `true` 11 (`legal-docs-v3/509618`) |
| `ngay_hoi_to` | date \| `null` | Ngày bắt đầu áp dụng hồi tố. Trước `issuance_date`. | `2019-01-01` |
| `ngay_hoi_to_trich` | keyword, không index \| `null` | Câu gốc. `null` khi và chỉ khi `hoi_to = false`. | `Quy định tại khoản 8 Điều 1 và khoản 3 Điều 2 Nghị định này được áp dụng từ ngày 01 tháng 01 năm 2019` |
| `hoi_to_vi_tri` | mảng keyword | Vị trí hồi tố trong chính văn bản. Rỗng là cả văn bản. | Khác rỗng ở 2 văn bản |

Giá trị của `ngay_hieu_luc_cach` trong v3. Một số tên khác hợp đồng đích. Cột cuối nêu tên tương ứng ở [09, mục 9.8.7](09-hop-dong-du-lieu-v4.md#987-thời-điểm-hiệu-lực).

| Giá trị v3 | `ngay_hieu_luc` | Số | Ví dụ | Tên ở hợp đồng đích |
| --- | --- | --- | --- | --- |
| `ngay_ky` | Bằng `issuance_date` ("kể từ ngày ký") | 70 | `602450` | `ngay_ky`, `so_ngay = 0` |
| `sau_n_ngay_ky` | `issuance_date` + N ngày | 19 | `192600`: ký 23/10/2009, "sau 10 ngày" → `2009-11-02` | `ngay_ky`, `so_ngay = N` |
| `ngay_cu_the` | Ngày ghi trong câu | 50 | `163439` → `2013-01-01` | `ngay_cu_the` |
| `ngay_thong_qua` | Ngày thông qua | 1 | `401532` → `2018-07-10` | `ngay_thong_qua`, `so_ngay = 0` |
| `sau_n_ngay_thong_qua` | Ngày thông qua + N ngày | 2 | `149606` → `2012-10-15` | `ngay_thong_qua`, `so_ngay = N` |
| `phu_thuoc_ngay_dang_cong_bao` | `null`. Hệ thống không có ngày đăng Công báo. | 9 | `82441` | `ngay_dang_cong_bao` |
| `mac_dinh_ngay_ban_hanh` | `issuance_date`. **Giá trị suy ra.** Chỉ có khi `la_vbqppl = false`. | 31 | `28302` | `mac_dinh_ngay_ban_hanh` |
| `khong_doc_duoc` | `null`. Có câu hiệu lực, công cụ không đọc được ngày. | 5 | `142289` ("từ năm học 2004 - 2005") | `khong_doc_duoc` |
| `khong_tim_thay` | `null`. Không có câu hiệu lực. | 15 | `2511` | `khong_tim_thay` |
| `van_ban_hop_nhat` | `null`. Công cụ không bóc ngày. | 2 | `589448` | `van_ban_hop_nhat` |

v3 không có `ngay_hieu_luc_so_ngay`. Số ngày N chỉ có trong `ngay_hieu_luc_trich`.

v3 không có `hieu_luc_rieng`. Ngày hiệu lực riêng của từng Điều, khoản không có trong dữ liệu.

**`ngay_het_hieu_luc = null` không có nghĩa là văn bản còn hiệu lực.** Văn bản khác có thể thay thế, bãi bỏ, hủy bỏ văn bản này. Thông tin đó nằm ở `legal-changed-v3`: quan hệ có `target_matched_id` là văn bản này và `vi_tri = ["toàn bộ"]`.

## 4.7. `legal-chunk-section-v3`

- Một chunk là một đơn vị nội dung để tìm kiếm.
- Chunk có `is_full = true` chứa trọn một Điều, một khoản hoặc toàn bộ nội dung.
- Đơn vị có chunk con thì chunk `is_full` lặp lại nội dung của chunk con. Khi gộp kết quả tìm kiếm, bỏ trùng theo `dieu_uid` và `khoan_uid`.
- Vector tạo từ `tieu_de + " " + noi_dung` sau khi gộp khoảng trắng. Dịch vụ embedding cắt đầu vào ở 256 token. Phần sau token 256 không có trong vector.
- Chunk v3 không có ngày hiệu lực. Lấy ngày từ văn bản qua `doc_id`.

### 4.7.1. Ví dụ: `legal-chunk-section-v3/602450_d1_k1_pa`

Chunk này chứa câu tạo ra quan hệ `legal-changed-v3/602450_1`.

```json
{
  "_index": "legal-chunk-section-v3",
  "_id": "602450_d1_k1_pa",
  "_source": {
    "doc_id": "602450",
    "chunk_type": "diem",
    "tieu_de": "Sửa đổi, bổ sung một số điều của Nghị định số 01/2012/NĐ-CP …",
    "noi_dung": "Sửa đổi, bổ sung điểm a khoản 3 như sau: …",
    "so_van_ban_refs": [],
    "dieu_uid": "602450_d1",
    "segment": 0,
    "so_dieu": 1,
    "ky_hieu_dieu": "1",
    "khoan_uid": "602450_d1_k1",
    "so_khoan": 1,
    "ky_hieu_khoan": "1",
    "so_diem": "a",
    "document_number": "31/2024/NĐ-CP",
    "title": "Nghị định 31/2024/NĐ-CP sửa đổi …",
    "action": "sua-doi",
    "legal_type": "Nghị định",
    "issuing_authority": "Chính phủ",
    "issuance_date": "2024-03-15",
    "url": "https://thuvienphapluat.vn/…-602450.aspx",
    "signers": "Trần Hồng Hà:1381",
    "legal_sectors": "Thể thao - Y tế, Văn hóa - Xã hội",
    "embedding": [-0.08, -0.0196, -0.0303, "… (1.024 số)"],
    "origin": "legacy",
    "ingest_job_id": "v3:20261012T075451Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-12T08:24:58.843022+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 4.7.2. Loại chunk và ID

v3 có 11 loại chunk. v3 không có loại `tieu_diem`.

| `chunk_type` | Mẫu `_id` | Nội dung | Số | Ví dụ |
| --- | --- | --- | --- | --- |
| `dieu` | `<doc>_d<x>` | Trọn một Điều không có khoản | 841 | `611245_d3` |
| `dieu_full` | `<doc>_d<x>_full` | Trọn một Điều có khoản | 647 | `602450_d1_full` |
| `dieu_mo_dau` | `<doc>_d<x>_md` | Phần trước khoản đầu. Có khi phần này dài từ 40 ký tự. | 129 | `206663_d3_md` |
| `khoan` | `<doc>_d<x>_k<y>` | Trọn một khoản không có điểm | 2.160 | `602450_d2_k1` |
| `khoan_full` | `<doc>_d<x>_k<y>_full` | Trọn một khoản có điểm | 359 | `602450_d1_k1_full` |
| `khoan_mo_dau` | `<doc>_d<x>_k<y>_md` | Phần trước điểm đầu. Có khi phần này dài từ 40 ký tự. | 274 | `602450_d1_k1_md` |
| `diem` | `<doc>_d<x>_k<y>_p<z>` | Trọn một điểm, gồm các gạch đầu dòng | 1.271 | `602450_d1_k1_pa` |
| `phu_luc` | `<doc>_pl<i>` | Phần thứ `i` (từ 0) của `phu_luc[]`. Có khi phần đó không chia Điều. | 342 | `602450_pl0` |
| `muc` | `<doc>_m<n>` | Một đề mục của văn bản không chia Điều | 147 | `318496_m1` |
| `noi_dung` | `<doc>_nd`, `<doc>_nd<k>` | Văn bản không chia Điều, không có đề mục. `_nd`: nội dung ngắn. `_nd<k>`: đoạn thứ `k` của nội dung dài. | 104 | `35961_nd1` |
| `noi_dung_full` | `<doc>_nd_full` | Trọn nội dung dài (trên 200 âm tiết). | 17 | `35961_nd_full` |

Quy tắc ID:

1. Điều trong phụ lục có thêm `_pl<i>` sau `<doc>`. Ví dụ: `105559_pl0_d1`.
2. Điều thuộc chuỗi Điều kèm theo thứ `s` có thêm `_s<s>` trước `_d`. Ví dụ: `332709_pl1_s10_d1`.
3. `_pl<i>` luôn có số. `_pl` ở cuối ID là điểm `l`. Ví dụ: `66935_d9_k2_pl`.
4. Hai chunk trùng ID thì chunk sau có thêm `_2`, `_3`… Đo 19/10: v3 không có ID nào như vậy.

### 4.7.3. Trường

"Chunk thuộc Điều" là 7 loại: `dieu`, `dieu_full`, `dieu_mo_dau`, `khoan`, `khoan_full`, `khoan_mo_dau`, `diem`. Đo 19/10: mọi chunk đúng các quy tắc trong bảng.

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `_id` | chuỗi | Mọi chunk | Bắt đầu bằng `<doc_id>_`. Khớp mẫu của `chunk_type`. |
| `doc_id` | keyword | Mọi chunk | Bằng `_id` của văn bản. |
| `chunk_type` | keyword | Mọi chunk | 11 giá trị ở mục 4.7.2. |
| `tieu_de` | text | Mọi chunk | Tên Điều với chunk thuộc Điều. Tiêu đề phụ lục với `phu_luc`. Rỗng với `muc`, `noi_dung`, `noi_dung_full` và Điều không tên. |
| `noi_dung` | text | Mọi chunk | `tieu_de + noi_dung` khác rỗng. |
| `so_van_ban_refs` | mảng keyword | Mọi chunk | Số hiệu nêu trong chunk. Chunk `_md` luôn rỗng. |
| `embedding` | dense_vector 1.024 | Mọi chunk | Vector của `tieu_de + " " + noi_dung`. |
| `document_number`, `title`, `action`, `legal_type`, `issuing_authority`, `issuance_date`, `url`, `signers` | như văn bản | Có khi văn bản có | Bằng trường cùng tên của văn bản. |
| `legal_sectors` | keyword (chuỗi) | Có khi văn bản có | Chuỗi, không phải mảng. Các phần tử nối bằng `", "`. |
| `dieu_uid` | keyword | Chunk thuộc Điều | Phần đầu `_id` đến hết `_d<x>`. ID node Điều. |
| `segment` | integer | Chunk thuộc Điều | `0`: chuỗi Điều đầu. `s ≥ 1`: chuỗi Điều kèm theo thứ `s`. `segment > 0` khi và chỉ khi `_id` có `_s<s>`. 318 chunk có `segment > 0`. |
| `so_dieu`, `ky_hieu_dieu` | integer, keyword | Chunk thuộc Điều | Phần số và ký hiệu đầy đủ. `dieu_uid` kết thúc bằng `_d<ky_hieu_dieu>`. |
| `chuong` | text | Có khi Điều nằm trong Chương | Tên Chương. 3.616 chunk. |
| `muc_lon` | text | Có khi Điều nằm trong Mục của Chương | Tên Mục. 496 chunk. |
| `khoan_uid` | keyword | `khoan`, `khoan_full`, `khoan_mo_dau`, `diem` | Phần đầu `_id` đến hết `_k<y>`. ID node khoản. |
| `so_khoan`, `ky_hieu_khoan` | integer, keyword | Cùng `khoan_uid` | Phần số và ký hiệu đầy đủ. |
| `so_diem` | keyword | `diem` | Ký hiệu điểm. |
| `is_full` | boolean | `dieu`, `dieu_full`, `khoan`, `khoan_full`, `noi_dung_full` | Chỉ có giá trị `true`. |
| `in_phu_luc` | boolean | Có khi `_id` có `_pl<i>` | Chỉ có giá trị `true`. 2.089 chunk. |
| `phu_luc_tieu_de` | text | Cùng `in_phu_luc` | 500 ký tự đầu của `phu_luc[i].tieu_de`. |
| `has_table` | boolean | Cùng `in_phu_luc` | Bằng `phu_luc[i].has_table`. |
| `so_muc` | keyword | `muc` | Ký hiệu đề mục: `2`, `II`. |
| `so_doan` | integer | `<doc>_nd<k>` | Bằng `k`. Đánh số liên tục từ 1. Văn bản có đoạn thì có đúng một `noi_dung_full`. |
| `dan_chieu` | mảng object | Có khi chunk có dẫn chiếu | Khác rỗng khi có. 1.082 chunk, 2.191 dẫn chiếu. Mục 4.7.4. |
| 5 trường truy vết | | Mọi chunk | Mục 4.5. |

v3 không có `diem_uid`, `so_tieu_diem`, `ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_so_ngay`, `ngay_hieu_luc_rieng`, `ngay_hoi_to` trên chunk.

### 4.7.4. `dan_chieu[]`

| Trường | Kiểu | Quy tắc | Ví dụ (`602450_d2_full`) |
| --- | --- | --- | --- |
| `loai` | keyword | `ngoai` (718), `noi_bo` (699), `noi_bo_ngam` (572), `van_ban_bi_sua` (202). | `van_ban_bi_sua` |
| `vi_tri` | keyword | Là Vị trí (mục 4.3). | `Điều 5` |
| `van_ban` | keyword \| `null` | Số hiệu hoặc tên văn bản được dẫn. `null` khi `loai` là `noi_bo`, `noi_bo_ngam`. | `61/2016/NĐ-CP` |
| `target_id` | integer \| `null` | `_id` văn bản được dẫn ở `legal-docs`. Bằng `doc_id` khi `loai` là `noi_bo`, `noi_bo_ngam`. `null` khi chưa nối được. | `315420` |
| `trich` | keyword, không index | Câu chữ gốc, tối đa 200 ký tự. | `Điều 5 Nghị định này` |

Mapping khai báo `dan_chieu` là `object`, không phải `nested`. Truy vấn ES không giữ được cặp `vi_tri` và `target_id` của cùng một dẫn chiếu. Đọc cặp này từ `_source`.

## 4.8. `legal-changed-v3`

- Một quan hệ là một tác động của một đơn vị nguồn lên vị trí của văn bản đích.
- Phần lớn quan hệ có một vị trí. 68/733 quan hệ có từ 2 vị trí trong cùng một bản ghi (mục 4.8.5).
- "Sửa đổi, bổ sung" trên một vị trí cho 2 quan hệ riêng: `sua-doi` và `bo-sung`. Công cụ không gộp.
- Tiêu đề, lời dẫn và từng Điều có quan hệ riêng, kể cả khi cùng văn bản đích.
- Quan hệ dò từ câu chữ đã qua QA bằng model LLM `qwen-legal`. Quan hệ hướng dẫn (`hd_`) lấy bằng quy tắc, không qua QA.
- v3 có một số tác động suy ra lên đơn vị cha hoặc đơn vị con ([05, mục 5.4.1](05-phien-ban-v2-v3-v4.md#541-dữ-liệu)). Chưa đo số lượng.
- Khi ghi lại một văn bản, công cụ xóa mọi quan hệ có `source_id` của văn bản đó rồi ghi lại.

### 4.8.1. Ví dụ: `legal-changed-v3/602450_1`

```json
{
  "_index": "legal-changed-v3",
  "_id": "602450_1",
  "_source": {
    "source_id": 602450,
    "source_document_number": "31/2024/NĐ-CP",
    "source_title": "Nghị định 31/2024/NĐ-CP sửa đổi …",
    "source_action": "sua-doi",
    "source_issuing_authority": "Chính phủ",
    "source_issuance_date": "2024-03-15",
    "source_legal_type": "Nghị định",
    "source_legal_sectors": "Thể thao - Y tế, Văn hóa - Xã hội",
    "source_url": "https://thuvienphapluat.vn/…-602450.aspx",
    "source_path": "Điều 1 Khoản 1 điểm a",
    "source_in_phu_luc": false,
    "source_ngay_hieu_luc": "2024-03-15",
    "target_doc": "01/2012/NĐ-CP",
    "target_matched_id": 133717,
    "target_candidates_count": 1,
    "target_issuance_date": "2012-01-04",
    "action": "sua-doi",
    "scope": "điểm a khoản 3 Điều 2",
    "vi_tri": ["điểm a khoản 3 Điều 2"],
    "cap_quan_he": "vi_tri",
    "hieu_luc_tac_dong": "ve_sau",
    "unresolved": false,
    "scope_grounding_checked": true,
    "scope_grounding_correct": true,
    "scope_resolution_method": "explicit_declaration",
    "origin": "legacy",
    "ingest_job_id": "v3:20261012T075451Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-12T08:24:58.843022+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 4.8.2. ID

`_id` có dạng `<tiền tố><source_id>_<n>`.

| Tiền tố | `detection_mode` | Số | Ví dụ |
| --- | --- | --- | --- |
| không có | thiếu | 665 | `602450_1` |
| `hidden_` | `hidden` | 17 | `hidden_86794_0` |
| `intro_` | `intro` | 23 | `intro_602450_0` |
| `hd_` | `title_guidance` | 28 | `hd_2211_0` |

- v3 không có tiền tố `hhl_` (`het_hieu_luc`) và `hn_` (`hop_nhat`).
- `n` đếm từ 0 trong mỗi tiền tố của một văn bản nguồn.
- **Dãy `n` có thể bị khuyết.** 15/94 nhóm (tiền tố, văn bản nguồn) có số khuyết. Ví dụ: `192512` chỉ có `192512_9`. `378946` chỉ có `378946_2`, `378946_3`.
- `n` đổi khi chạy lại văn bản nguồn. **Không dùng `_id` quan hệ làm khóa lâu dài.**
- `detection_mode = title_guidance` khi và chỉ khi `action` là `huong-dan` hoặc `quy-dinh-chi-tiet`.

### 4.8.3. Văn bản nguồn

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `source_id` | integer | Luôn | Bằng `_id` của một văn bản. |
| `source_document_number`, `source_title`, `source_action`, `source_issuing_authority`, `source_issuance_date`, `source_legal_type`, `source_url` | như văn bản | Luôn | Bằng trường cùng tên (bỏ `source_`) của văn bản nguồn. |
| `source_legal_sectors` | keyword (chuỗi) | Luôn | Lĩnh vực của văn bản nguồn nối bằng `", "`. |
| `source_path` | keyword | Luôn | Đơn vị nguồn (mục 4.4). |
| `source_in_phu_luc` | boolean | Luôn | `true` khi và chỉ khi `source_path` bắt đầu bằng "Phụ lục". v3: luôn `false`. |
| `source_ngay_hieu_luc` | date \| `null` | Luôn | `ngay_hieu_luc` của văn bản nguồn. `null` ở 12 quan hệ. |
| `source_ngay_hoi_to` | date | Có khi `hieu_luc_tac_dong = ve_truoc` | Bằng `ngay_hoi_to` của văn bản nguồn. 33 quan hệ. |

### 4.8.4. Văn bản đích

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `target_doc` | keyword | Luôn | Số hiệu đích theo câu nguồn, không có khoảng trắng. Câu nêu luật bằng tên mà dòng căn cứ không có số hiệu thì là tên luật: `Luật Thủy lợi` (`hd_356281_0`). |
| `target_matched_id` | integer \| `null` | Luôn | `_id` đích ở `legal-docs`. `null` khi chưa nối được (21/733). Khác `null` thì: khác `source_id`; ngày ban hành đích không sau `source_issuance_date`. |
| `target_candidates_count` | integer | Luôn | Số văn bản có cùng số hiệu, gồm dạng bỏ năm. Từ 1 khi `target_matched_id` khác `null`. |
| `target_issuance_date` | date | Có khi câu trích có ngày | Ngày ban hành đích theo câu trích. Đích đã nối thì bằng `issuance_date` của đích, trừ khi có `target_match_note`. 546 quan hệ. |
| `target_issuing_authority` | keyword | Có khi câu trích nêu cơ quan | Cơ quan ban hành đích theo câu trích. 26 quan hệ. |
| `target_match_note` | keyword | Có khi ngày lệch | Chỉ có `lech_ngay_trich_dan`. 8 quan hệ. |

### 4.8.5. Tác động

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `action` | keyword | Luôn | 12 giá trị: `bo-sung` 279, `sua-doi` 263, `thay-cum-tu` 67, `thay-the` 40, `bai-bo` 28, `huong-dan` 21, `dinh-chinh` 16, `quy-dinh-chi-tiet` 7, `huy-bo` 6, `dinh-chi` 4, `gia-han` 1, `ngung-hieu-luc` 1. Không có `hop-nhat`. |
| `scope` | text + keyword | Luôn | Phạm vi theo câu nguồn. Khác rỗng. Không có định dạng cố định. Có thể nêu nhiều vị trí. **Dùng `vi_tri` để nối, không dùng `scope`.** |
| `vi_tri` | mảng keyword | Luôn | Các Vị trí trong văn bản đích (mục 4.3), hoặc rỗng. `scope = toàn bộ` thì `vi_tri = ["toàn bộ"]`. Số phần tử ở bảng dưới. |
| `cap_quan_he` | keyword | Luôn | Mức chi tiết của cả quan hệ (mục 4.8.7). |
| `hieu_luc_tac_dong` | keyword | Luôn | Ý nghĩa thời gian. Tính từ `action` và hồi tố. `ve_sau` 645, `ve_truoc` 33, `khong_ap_dung` 28, `tu_dau` 22, `tam_ngung` 5. |
| `unresolved` | boolean | Luôn | `true`: phạm vi chưa được xác nhận. `scope = chưa xác định` thì `true`. `true` ở 14 quan hệ. |
| `doi_tuong` | keyword | Có khi câu nguồn nêu phần bị tác động bằng tên, không có số | Tên phần bị tác động. Thường đi với `vi_tri` rỗng. 16 quan hệ. |
| `kem_theo` | boolean | Cùng `doi_tuong` | `true`: phần đó ban hành kèm theo văn bản đích (11). `false` (5). |
| `cum_tu` | mảng object | Có khi `action = thay-cum-tu` | Khác rỗng. 67 quan hệ. |
| `cum_tu[].cu`, `cum_tu[].moi` | keyword | Cùng `cum_tu` | Cụm từ cũ, cụm từ mới. Khác rỗng. |
| `cum_tu[].vi_tri` | mảng keyword | Cùng `cum_tu` | Các vị trí áp dụng cặp cụm từ này. Thường bằng `vi_tri` của quan hệ. Khác ở 3 quan hệ: rỗng (`662238_10`, `662238_38`) hoặc là một phần của `vi_tri` (`662238_72`). |
| `dinh_chi_tu_ngay` | date \| `null` | Có khi `action` là `dinh-chi`, `ngung-hieu-luc` | Ngày bắt đầu. Câu không ghi ngày thì bằng `source_ngay_hieu_luc`. `null` ở `50709_0`. |
| `dinh_chi_den_ngay` | date \| `null` | Như trên | Ngày kết thúc. Ví dụ `564293_0`: `2023-12-31`. |
| `dinh_chi_den_khi` | keyword \| `null` | Như trên | Điều kiện kết thúc, ghi bằng lời. Ví dụ `181025_1`: `có văn bản mới của Ủy ban nhân dân tỉnh`. |
| `gia_han_den_ngay` | date \| `null` | Có khi `action = gia-han` | Ngày hết hiệu lực mới. Ví dụ `318496_0`: `2016-12-31`. |
| `gia_han_den_khi` | keyword \| `null` | Như trên | Điều kiện hoặc thời hạn thêm. |
| `detection_mode` | text + keyword | Có khi `_id` có tiền tố | Nơi có câu tác động (mục 4.8.2). 68 quan hệ. |

Số vị trí trong một quan hệ:

| Số phần tử của `vi_tri` | Quan hệ |
| --- | --- |
| 0 | 49 |
| 1 | 616 |
| 2–4 | 58 |
| 6–14 | 8 |
| 38, 44 | 2 (`611245_25` có 44) |

- 68 quan hệ có từ 2 vị trí thuộc 14 văn bản nguồn. Theo hành động: `thay-cum-tu` 32, `sua-doi` 14, `bo-sung` 10, `bai-bo` 4, `thay-the` 4, `dinh-chinh` 4.
- Ví dụ: `602450_12` (`sua-doi`) có `["điểm b khoản 3 Điều 2", "điểm đ khoản 3 Điều 2", "điểm e khoản 3 Điều 2"]`.
- Một số câu liệt kê đã được tách thành nhiều quan hệ một vị trí. Ví dụ: `383494_11`, `383494_12`, `383494_13`.

v3 không có `resolution_status`, `resolution_reason`, `extraction`, `evidence`, `target_section`. Mapping v3 cũng không có các trường này.

### 4.8.6. QA phạm vi

Đo 19/10: mọi quan hệ đúng các quy tắc trong bảng.

| Trường | Kiểu | Có | Quy tắc | Số |
| --- | --- | --- | --- | --- |
| `scope_resolution_method` | keyword | Có khi quy tắc xác nhận phạm vi | `explicit_declaration` hoặc `liet_ke_vi_tri`. Khi có, `scope_grounding_correct = true`. | 494, 79 |
| `scope_grounding_checked` | boolean | Có khi đã kiểm phạm vi | Chỉ có giá trị `true`. | 635 |
| `scope_grounding_correct` | boolean | Cùng `scope_grounding_checked` | `true`: dẫn chứng hỗ trợ phạm vi. `false` thì `unresolved = true`. | `true` 623, `false` 12 |
| `scope_grounding_suggestion` | text + keyword | Có khi model đề xuất mà công cụ không áp dụng | Phạm vi do model LLM đề xuất. Chỉ để tham khảo. | 20 |
| `llm_refined` | boolean | Có khi công cụ áp dụng đề xuất | Chỉ có giá trị `true`. Khi có, `scope_grounding_correct = true`, `unresolved = false`. | 28 |
| `llm_hallucination_rejected` | boolean | Có khi QA phạm vi không đạt | `true`: dẫn chứng của model không có trong văn bản nguồn. `false`: dẫn chứng có trong nguồn, nhưng model trả `correct = false`. Khi có, `scope_grounding_correct = false`. | `true` 11, `false` 1 |

### 4.8.7. Cấp quan hệ

Công cụ xét các dòng từ trên xuống. Công cụ chọn dòng đầu tiên có điều kiện đúng.

| # | `cap_quan_he` | Điều kiện | `vi_tri` | Số |
| --- | --- | --- | --- | --- |
| 1 | `vi_tri` | `vi_tri` có ít nhất một Vị trí khác `toàn bộ`. Câu nằm ở đâu cũng vậy: Điều, lời dẫn, tiêu đề. | Một hoặc nhiều phần tử | 630 |
| 2 | `van_ban_kem_theo` | Có `doi_tuong` và `kem_theo = true`. | Rỗng | 11 |
| 3 | `noi_dung` | Có `doi_tuong` và `kem_theo = false`. | Rỗng | 5 |
| 4 | `van_ban` | `vi_tri = ["toàn bộ"]`; hoặc `detection_mode` là `intro`, `title_guidance`; hoặc `source_path` là `intro`, `Tiêu đề`, `Lời dẫn`, `Căn cứ`; hoặc `scope` là `một số điều`, `một số cụm từ`. | `["toàn bộ"]` hoặc rỗng | 85 |
| 5 | `chua_xac_dinh` | Không đúng dòng nào ở trên. | Rỗng | 2 |

Ngoại lệ: 2 quan hệ có `doi_tuong`, `kem_theo = true` và một vị trí "Mẫu số …" ngoài định dạng. Hai quan hệ này có `cap_quan_he = van_ban_kem_theo`, không phải `vi_tri`. Ví dụ: `192512_9`, `282089_62`.

## 4.9. Cách nối cho đồ thị

ES chỉ lưu tác động. Bên Graph tính trạng thái hiệu lực từ các cạnh. Mục này nêu cách đọc dữ liệu v3 như hiện có.

### 4.9.1. Node

| Node | ID | Lấy từ |
| --- | --- | --- |
| Văn bản | `<doc>` | `legal-docs-v3/<doc>` |
| Chương, Mục của Luật | — | Trường `chuong`, `muc_lon` trên chunk. Không có chunk riêng. |
| Điều | `dieu_uid` | Chunk `dieu`, `dieu_full`, `dieu_mo_dau` |
| Khoản | `khoan_uid` | Chunk `khoan`, `khoan_full`, `khoan_mo_dau` |
| Điểm | `_id` của chunk `diem` | Chunk `diem` |
| Phụ lục | `<doc>_pl<i>` | Chunk `phu_luc` hoặc Điều trong phụ lục |
| Đề mục, nội dung | `_id` của chunk `muc`, `noi_dung`, `noi_dung_full` | Chunk tương ứng |

Dựng một node cho mỗi `dieu_uid` và mỗi `khoan_uid`. Không dựng một node cho mỗi chunk: chunk `_full` và `_md` cùng thuộc một node. v3 không có node tiểu điểm.

### 4.9.2. Từ vị trí sang node

| Vị trí | ID node | Ví dụ |
| --- | --- | --- |
| `Điều <x>` | `<doc>_d<x>` | `Điều 26` (`288269_12`) → `206663_d26` |
| `khoản <y> Điều <x>` | `<doc>_d<x>_k<y>` | `khoản 7a Điều 3` (`611245_14`) → `206663_d3_k7a` |
| `điểm <z> khoản <y> Điều <x>` | `<doc>_d<x>_k<y>_p<z>` | `điểm a khoản 1 Điều 43` (`288269_32`) → `206663_d43_k1_pa` |
| `tên Điều <x>` | `<doc>_d<x>`. Cạnh tác động lên tên, không lên nội dung. | `tên Điều 42` (`288269_29`) → `206663_d42` |
| `tên Chương <c>`, `tên Mục <n> Chương <c>` | Không có node. Chương và Mục không có node riêng. | `tên Chương IV` (`288269_27`) |
| `Phụ lục <ký hiệu>` | `<doc>_pl<i>` với `phu_luc[i].ky_hieu` bằng ký hiệu | `legal-docs-v3/602450`: `phu_luc[1].ky_hieu = II` → `602450_pl1` |
| `Mục <x> Phụ lục` | Node phụ lục. Mục của phụ lục không có node riêng. | `Mục IV Phụ lục` (`662238_85`) |
| `toàn bộ` | Node văn bản | `241415_0` → `legal-docs/217555` |

- Node đích chỉ có chunk khi văn bản đích đã chuyển sang v3. Đo 19/10: 3/109 văn bản đích có trong v3.
- **v3 không đánh dấu vị trí thuộc văn bản chính hay văn bản kèm theo.** Ví dụ: `383494_3` đính chính `điểm b khoản 7 Điều 3` của QĐ 28/2017/QĐ-UBND (`366183`). Vị trí này thuộc Quy định kèm theo (node dạng `366183_pl0_d3_k7_pb`), không thuộc Quyết định. Bản ghi v3 không nói điều này. Khi văn bản đích có chuỗi Điều kèm theo, bên Graph không tự gán vị trí vào văn bản chính.

### 4.9.3. Cạnh

1. v3 không có `resolution_status`. Dựng cạnh chi tiết khi `unresolved = false` và `cap_quan_he` khác `chua_xac_dinh`.
2. Quan hệ có N vị trí cho N cạnh, mỗi vị trí một cạnh.
3. Bỏ qua vị trí ngoài định dạng (mục 4.3.1). Các vị trí khác của cùng quan hệ vẫn dựng cạnh.
4. Phía nguồn: node theo `source_path`. `source_path` là `intro`, `Tiêu đề`, `Lời dẫn`, `Căn cứ` thì phía nguồn là node văn bản.
5. Phía đích: node theo `vi_tri`. `vi_tri = ["toàn bộ"]` hoặc rỗng ở quan hệ cấp văn bản thì phía đích là node văn bản.
6. Cạnh tổng hợp nối văn bản nguồn với văn bản đích. Bên Graph dựng cạnh này từ `source_id` và `target_matched_id`. Quan hệ có `target_matched_id = null` không có cạnh tổng hợp.

### 4.9.4. Không lan tác động

| Ca | ES lưu | ES không lưu |
| --- | --- | --- |
| Sửa đổi, thay thế, bãi bỏ cả Điều | Quan hệ vào node Điều | Trạng thái của khoản, điểm trong Điều đó |
| Bãi bỏ một khoản | Quan hệ vào node khoản | Trạng thái của Điều chứa khoản |
| Bổ sung đơn vị mới (Điều 47a, khoản 2a) | Quan hệ có vị trí của đơn vị mới | Node mới. Bên Graph tạo node nếu cần. |
| Văn bản hết hiệu lực | Quan hệ vào văn bản đó | Hết hiệu lực của văn bản quy định chi tiết nó |
| Thay cụm từ "trong toàn bộ Thông tư" | Một quan hệ có `vi_tri = ["toàn bộ"]` | Danh sách khoản có cụm từ |

v3 có một số tác động suy ra lên đơn vị cha hoặc đơn vị con (mục 4.8). Trạng thái hiệu lực của node (còn, hết một phần, hết toàn bộ, tạm ngừng) do bên Graph tính từ các cạnh. ES không lưu trạng thái này.

### 4.9.5. Thời gian trên cạnh

| Trường | Dùng để |
| --- | --- |
| `source_ngay_hieu_luc` | Ngày tác động bắt đầu với `ve_sau`. Đây là ngày hiệu lực của văn bản nguồn. `null` ở 12 quan hệ. |
| `source_ngay_hoi_to` | Ngày tác động bắt đầu với `ve_truoc`. |
| `dinh_chi_tu_ngay`, `dinh_chi_den_ngay`, `dinh_chi_den_khi` | Khoảng tạm ngừng với `tam_ngung`. |
| `gia_han_den_ngay`, `gia_han_den_khi` | Ngày hoặc điều kiện kết thúc mới với `gia-han`. |
| `ngay_hieu_luc` của văn bản đích | Ngày hiệu lực của node đích. Chunk v3 không có ngày riêng. |

## 4.10. Khác với hợp đồng đích và lỗi đã biết

Hợp đồng đích là [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md). Ghi lại v3 cần được duyệt ([02, "Ghi thử vào v4"](02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3)).

Các dòng 1–16 hết khi ghi lại v3 bằng code hiện hành. Dòng 17 **không** hết. Bảng đếm trên 204 văn bản gốc. Nhóm 32 văn bản khác hợp đồng đích ở các điểm của mục 4.12.3.

- Dòng 3: từ 19/10/2026, công cụ chuyển vị trí ngoài định dạng sang `doi_tuong` ([09, mục 9.5](09-hop-dong-du-lieu-v4.md#95-vị-trí)).
- Dòng 16: từ 19/10/2026, parser tách khối chữ ký nằm cùng dòng bảng (`Lưu: VT. | TM. …`). Chạy parser hiện tại trên 132 văn bản v3 có lỗi: còn 0 (đo 20/10/2026).
- Dòng 17: parser hiện tại vẫn cho `132723_pl0` cùng giá trị `n_table_rows` như v3 (đo 20/10/2026).

| # | Mục | v3 hiện có | Hợp đồng đích | Số lượng v3 |
| --- | --- | --- | --- | --- |
| 1 | Số vị trí trong một quan hệ | Có thể nhiều | Đúng một, hoặc rỗng | 68/733 quan hệ |
| 2 | Vị trí mẫu biểu | `Mẫu số …` | Phụ lục chứa mẫu | 36 quan hệ |
| 3 | Vị trí ngoài định dạng khác | `Mục … Chương … <tên>`, `Mục 7 Phần I`, `Mục 1.2 Chương II` | Chặn hoặc chuẩn hóa | 4 quan hệ |
| 4 | Trạng thái cạnh | Không có | `resolution_status`, `resolution_reason`, `extraction`, `evidence`, `target_section` | 733/733 |
| 5 | Văn bản chính hay kèm theo | Không đánh dấu | `target_section`, `resolution_reason = phan_kem_theo_chua_ro` | Chưa đo |
| 6 | Quan hệ hợp nhất | Không có | `hop-nhat` (`hn_`) | 0. v3 có 2 văn bản hợp nhất (`589448`, `651872`). |
| 7 | Tác động suy ra | Có một số | Chỉ tác động văn bản nêu trực tiếp | Chưa đo |
| 8 | Dãy `n` của `_id` | Có thể khuyết | Không khuyết | 15/94 nhóm |
| 9 | `source_path = Căn cứ` | Có | Không có dạng này | 2 quan hệ |
| 10 | `cum_tu[].vi_tri` | Có thể khác `vi_tri` | Bằng `vi_tri` | 3 quan hệ |
| 11 | Ngày hiệu lực văn bản | Tên cách đọc cũ. Không có `ngay_hieu_luc_so_ngay`. | `ngay_ky`, `ngay_thong_qua`, `ngay_dang_cong_bao` + `ngay_hieu_luc_so_ngay` | 30 văn bản có tên cũ. 204 thiếu trường. |
| 12 | Ngày hiệu lực riêng | Không có `hieu_luc_rieng` | Có | 204/204 văn bản |
| 13 | Ngày hiệu lực trên chunk | Không có | `ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_so_ngay`, `ngay_hieu_luc_rieng`, `ngay_hoi_to` | 6.291/6.291 chunk |
| 14 | Node điểm | Không có `diem_uid` | `diem_uid` | 1.271 chunk `diem` |
| 15 | Tiểu điểm | Không có chunk, không có vị trí | Chunk `tieu_diem`, vị trí `tiểu điểm …` | — |
| 16 | `noi_nhan` | Dính dòng chữ ký | Chỉ có nơi nhận | 132/204 văn bản có `\|` ở phần tử cuối |
| 17 | `n_table_rows` | Lệch số dòng | Đúng số dòng | 1/371 phần tử |

## 4.11. Cách đo lại

Lệnh `python -m eval.check_contract v3 [<file lỗi>.json]` đọc toàn bộ 3 index v3 bằng scroll. Lệnh chỉ đọc. Lệnh kiểm 232 quy tắc của hợp đồng đích. Tên quy tắc dùng số mục của tài liệu này. File lỗi liệt kê ID của mọi bản ghi sai theo từng quy tắc.

Kết quả ngày 19/10/2026 (204 văn bản gốc): 213 quy tắc đúng ở mọi bản ghi. 19 quy tắc sai tương ứng với các dòng ở mục 4.10. Lệnh chạy khoảng 1 phút. Ngày 28/10/2026 chưa chạy lại lệnh này sau lượt 27/10.

Khi đo lại sau một lượt ghi v3:

1. Chạy `python -m eval.check_contract v3`.
2. Đếm theo `ingest_job_id` bằng aggregation `terms` trên từng index.
3. Cập nhật số liệu và ngày đo trong tài liệu này. Dòng ở mục 4.10 hết lỗi thì xóa dòng đó.

## 4.12. 32 văn bản ghi ngày 27/10/2026

Mục này mô tả lượt `v3:20261027T101856Z`. Số liệu đếm ngày 28/10/2026 trên ES đích, chỉ đọc.

### 4.12.1. Nguồn và cách ghi

- Người dùng duyệt lượt này ngày 27/10/2026: ghi 32 văn bản của bộ 88 testcase vào v3, theo cấu trúc v3.
- 32 văn bản là văn bản của `loi_du_lieu_v4_32_van_ban.md`: Luật 19, Nghị định 8, Thông tư 5. Ví dụ: `146/2025/QH15`, `15/2026/NĐ-CP`, `154/2025/TT-BTC`.
- Mapping v3 không đổi.

| Bước | Cách làm |
| --- | --- |
| 1. Tạo bản ghi | Code `8b023ca` chạy lại chặt, với câu trả lời LLM đã lưu của lượt `v4-2210`. |
| 2. Sửa tay | Áp các bản sửa ở `work/v3-32/patches/`. Mỗi quan hệ thêm hoặc sửa có câu trích nguyên văn. |
| 3. Sửa chung | Bỏ dòng cha trùng dòng con. Bỏ dòng trùng. Áp quy ước "Bỏ cụm từ" (mục 4.12.3). |
| 4. Bỏ trường | Bỏ trường không có ở v3 (mục 4.12.3). |
| 5. Ghi | Ghi 3 index v3. Vector chunk cắt ở 256 token, như bản ghi gốc. |

- Số quan hệ: 5.706 sau bước 1, 3.468 sau bước 4 (`work/v3-32/apply-report.json`).
- File cuối: `work/v3-32/final/`.
- Gỡ lượt này: `work/v3-32/manifest.json` liệt kê ID của 32 văn bản, 8.386 chunk, 3.468 quan hệ.
- Ghi lại v3 toàn bộ bằng `convert` sẽ mất các sửa tay của bước 2.

### 4.12.2. Số liệu

**Văn bản.** `grade`: `full` 31, `partial` 1.

- 2 văn bản có thêm trường `don_vi_soan_thao`, `don_vi_soan_thao_trich`: `687594` (`154/2025/TT-BTC`), `678340` (`95/2025/TT-BTC`).
- Hợp đồng v3, hợp đồng đích và code `vbpl_v3` không có 2 trường này. Nguồn chưa rõ. Không dùng.

**Chunk.** 8 loại:

| `chunk_type` | Số |
| --- | --- |
| `diem` | 3.094 |
| `khoan` | 2.783 |
| `khoan_full` | 818 |
| `dieu_full` | 721 |
| `khoan_mo_dau` | 662 |
| `dieu` | 221 |
| `dieu_mo_dau` | 46 |
| `phu_luc` | 41 |

**Quan hệ.**

| Trường | Số |
| --- | --- |
| `action` | `bo-sung` 1.114, `sua-doi` 937, `thay-cum-tu` 919, `bai-bo` 452, `thay-the` 38, `quy-dinh-chi-tiet` 7, `huong-dan` 1 |
| `cap_quan_he` | `vi_tri` 3.388, `van_ban` 79, `noi_dung` 1 |
| Số phần tử của `vi_tri` | 1: 3.410; 0: 58 |
| `unresolved = true` | 46 |
| `target_matched_id = null` | 194 |
| `doi_tuong` có giá trị | 228 |
| `source_path` | `Điều …` 3.410, `intro` 57, `Tiêu đề` 1 |
| `source_in_phu_luc = true` | 0 |

Tiền tố `_id` và `detection_mode`:

| Tiền tố | Quan hệ | `detection_mode` |
| --- | --- | --- |
| không có | 3.428 | thiếu 2.000, `llm` 1.254, `kiem_tay_20261027` 139, `intro` 30, `title_guidance` 5 |
| `intro_` | 27 | `intro` 14, `llm` 13 |
| `hhl_` | 10 | `het_hieu_luc` |
| `hd_` | 2 | `title_guidance` |
| `hidden_` | 1 | `hidden` |

- `kiem_tay_20261027`: quan hệ thêm tay ở bước 2.
- Ở nhóm này, tiền tố và `detection_mode` không luôn khớp. Quy tắc "`detection_mode = title_guidance` khi và chỉ khi …" của mục 4.8.2 không đúng ở đây.
- Nhóm này còn quan hệ có nguồn `intro`, `Tiêu đề`. Code `8b023ca` có trước quy tắc R6 (bỏ quan hệ mức văn bản).

### 4.12.3. Quy ước riêng của nhóm 32 văn bản

Nhóm này giữ kiểu trường của v3. Một số ca của hợp đồng đích không ghi được bằng trường v3. Bảng nêu cách ghi:

| Ca | Nhóm 32 văn bản ghi | Hợp đồng đích ([09](09-hop-dong-du-lieu-v4.md)) |
| --- | --- | --- |
| "Bỏ cụm từ “X” tại P" | `action = bai-bo`, `vi_tri = [P]`, `doi_tuong = cụm từ “X”`, `cap_quan_he = vi_tri`, không có `cum_tu`. Lý do: v3 cần `cu`, `moi` khác rỗng. 113 quan hệ. Ví dụ `675259_149`: `tên Điều 44`, `cụm từ “cấp đổi,”`. | `thay-cum-tu`, `cum_tu = [{cu: X, moi: ""}]` (R4) |
| Phần không có node | Chữ của `chi_tiet_vi_tri` ghi vào `doi_tuong`. Ví dụ `689421_108`: `vi_tri = ["Phụ lục"]`, `doi_tuong = Mẫu số 02`. | `chi_tiet_vi_tri` |
| Quan hệ chờ duyệt | `unresolved = true` | `resolution_status = unresolved`, `resolution_reason` |
| Trạng thái, dẫn chứng | Không có `resolution_status`, `resolution_reason`, `extraction`, `evidence`, `target_section`, `doi_tuong_loai` | Có |
| Ngày hiệu lực riêng | Văn bản không có `hieu_luc_rieng`, `ngay_hieu_luc_so_ngay`. Chunk không có `ngay_hieu_luc*`. | Có |
| Tiểu điểm | Không có chunk `tieu_diem`. Chunk không có `diem_uid`. | Chunk `tieu_diem`, `diem_uid` |
| Vector chunk | 256 token đầu | `-v4` ngày 27–28/10/2026: cả chunk |
| "Bổ sung cụm từ “Y” vào …" | Còn 11 quan hệ `bo-sung` có `doi_tuong` bắt đầu bằng "cụm từ". Chưa kiểm từng dòng. | Không là quan hệ (R5) |
