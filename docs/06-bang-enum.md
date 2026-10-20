# 6. Bảng enum

Tài liệu này giải thích mọi giá trị enum của v2 và v3. Mỗi giá trị có: nghĩa, lúc công cụ gán, ví dụ thật.

## 6.1. Cách đọc bảng

- Cột "v2": giá trị có ở index v2 hay không. "—" là không có.
- Tên giá trị viết không dấu, nối bằng `_` hoặc `-`. Ví dụ: `ve_sau` đọc là "về sau".
- Cột "Số" đếm trên bản thử `-v4` ngày 14/10/2026 (203 văn bản, 6.610 chunk, 969 quan hệ). v3 sẽ có cùng số sau khi ghi lại. Số v2 đếm cùng ngày.
- Ví dụ viết `<index>/<_id>` hoặc chỉ `<_id>` khi index đã rõ.
- Khi bảng ghi "thứ tự xét", công cụ xét từ trên xuống. Công cụ chọn dòng đầu tiên đúng.

## 6.2. Văn bản

### `origin`

Nguồn gốc văn bản. Chunk và quan hệ chép giá trị của văn bản.

| Giá trị | v2 | Nghĩa | Ví dụ |
| --- | --- | --- | --- |
| `legacy` | — (trường thiếu) | Văn bản của kho nguồn. v2 không ghi trường này cho văn bản kho. v3 ghi `legacy` khi nguồn thiếu. | `legal-docs-v3/602450` |
| `user_upload` | 6 văn bản | Văn bản người dùng tải lên qua luồng realtime. | `legal-docs-v3/900000013` |

### `uploaded_by`

| Giá trị | v2 | Nghĩa |
| --- | --- | --- |
| `api` | 6 văn bản | Luồng realtime ghi bản ghi qua API. Chỉ có ở v2. |
| `migration-v3` | — | Công cụ `vbpl_v3` ghi bản ghi. Mọi bản ghi v3. |

### `text_source`

Nơi lấy chữ của `full_content`. v3 chép từ nguồn. Nguồn thiếu thì v3 ghi `source_full_content`.

| Giá trị | v2 | Nghĩa | Số v3 |
| --- | --- | --- | --- |
| `source_full_content` | — | Chữ lấy từ `full_content` của kho nguồn. Mọi văn bản `legacy`. | 202 |
| `ocr` | 5 | Chữ nhận dạng từ ảnh (OCR). | 1 (`900000013`) |
| `mixed` | 1 | Chữ lấy một phần từ lớp chữ PDF, một phần từ OCR. | 0 |
| `text_layer` | — | Chữ lấy từ lớp chữ của PDF. | 0 |
| `docx` | — | Chữ lấy từ file Word. | 0 |

### `action` (văn bản)

Phân loại văn bản của kho nguồn. v3 chép nguyên. **Trường này không là hành động của quan hệ.** Hành động của quan hệ nằm ở `legal-changed-v3.action` (mục 6.4).

| Giá trị | Số v2 | Nghĩa | Loại văn bản thường gặp |
| --- | --- | --- | --- |
| `other` | 346.853 | Không thuộc nhóm nào dưới đây. | Quyết định, Nghị quyết, Kế hoạch, Thông báo |
| `congvan` | 124.487 | Công văn. | Công văn |
| `sua-doi` | 16.698 | Văn bản sửa đổi văn bản khác. | Quyết định, Nghị quyết, Thông tư, Nghị định |
| `huongdan` | 10.489 | Văn bản hướng dẫn thi hành. | Thông tư, Hướng dẫn, Quyết định, Thông tư liên tịch |
| `bai-bo` | 8.621 | Văn bản bãi bỏ văn bản khác. | Quyết định, Nghị quyết |
| `bo-sung` | 6.416 | Văn bản bổ sung văn bản khác. | Quyết định, Nghị quyết |
| `hopnhat` | 3.578 | Văn bản hợp nhất. | Văn bản hợp nhất |
| `huy-bo` | 629 | Văn bản hủy bỏ văn bản khác. | Quyết định, Nghị quyết |
| `thay-the` | 471 | Văn bản thay thế văn bản khác. | Quyết định |
| `tcvn` | 19 | Tiêu chuẩn. | Tiêu chuẩn Việt Nam, Tiêu chuẩn XDVN, Tiêu chuẩn ngành |

### `grade`

Chất lượng tách cấu trúc. `grade` không đo giá trị pháp lý. Thứ tự xét:

| Giá trị | Điều kiện | Số v3 | Ví dụ |
| --- | --- | --- | --- |
| `full` | Có phần cuối (chữ ký hoặc Nơi nhận). Không có Điều nằm trong phần cuối. Dãy Điều đúng thứ tự, hoặc văn bản không chia Điều nhưng có đề mục. | 169 | `602450` |
| `partial` | Có Điều, phụ lục hoặc đề mục. Không đủ điều kiện `full`. | 15 | `2211` |
| `minimal` | Không có Điều, phụ lục và đề mục. Văn bản vẫn có chunk `noi_dung`. | 19 | `35961` |

"Dãy Điều đúng thứ tự": số Điều tăng từng 1 trong mỗi chuỗi Điều. Văn bản có chữ "bãi bỏ" bỏ qua kiểm này, vì số Điều có thể khuyết.

### `phu_luc[].loai`

| Giá trị | Nghĩa | Ví dụ |
| --- | --- | --- |
| `labeled` | Dòng đầu là nhãn "Phụ lục …". `ky_hieu` lấy từ nhãn. | `602450`, phần tử 0: "PHỤ LỤC I" |
| `unlabeled` | Văn bản kèm theo không nhãn: Quy chế, Quy định, Điều lệ… `ky_hieu = null`. | `161618`: "QUY CHẾ …" |

### `la_vbqppl_cach`

Căn cứ để gán `la_vbqppl` (văn bản quy phạm pháp luật hay không). Thứ tự xét:

| # | Giá trị | `la_vbqppl` | Điều kiện | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| 1 | `van_ban_hop_nhat` | `false` | `legal_type = Văn bản hợp nhất`. | 2 | `589448` (35/VBHN-VPQH) |
| 2 | `van_ban_dang` | `false` | Cơ quan ban hành là cơ quan Đảng (Ban Chấp hành Trung ương, Bộ Chính trị, Ban Bí thư…). | 1 | `169729` (20/CT-TW) |
| 3 | `theo_loai` | `true` | Loại luôn là VBQPPL: Hiến pháp, Bộ luật, Luật, Pháp lệnh, Lệnh, Nghị định, Thông tư, Thông tư liên tịch, Sắc lệnh, Sắc luật. | 69 (cả 2 dòng) | `2211` (TT 42/2005/TT-BTC) |
| 3 | `theo_loai` | `false` | Loại không bao giờ là VBQPPL: Công văn, Công điện, Thông báo, Kế hoạch, Báo cáo, Hướng dẫn, Văn bản khác, Thông tri, điều ước, văn bản WTO, tiêu chuẩn. | (như trên) | `28302` (Công văn) |
| 4 | `can_kiem` | `null` | Loại không thuộc 3 nhóm (ví dụ Quy định, Quy chế, Điều lệ). | (gộp với dòng 11) | — |
| 5 | `chi_thi_tu_2016` | `false` | Chỉ thị ban hành từ 01/07/2016. | 1 | `417838` (08/CT-UBND) |
| 6 | `quyet_dinh_bo_tu_2009` | `false` | Quyết định hoặc Chỉ thị của Bộ, ban hành từ 01/01/2009. | 7 | `105925` (1955/QĐ-BGDĐT) |
| 7 | `co_quan_khong_ban_hanh_vbqppl` | `false` | Cơ quan ban hành không có thẩm quyền ban hành VBQPPL (ví dụ Ban Chỉ đạo). | 3 | `152145` (843/QĐ-BCĐCTQG) |
| 8 | `tieu_de_ca_biet` | `false` | Quyết định, Nghị quyết có tiêu đề cá biệt (bổ nhiệm, phê duyệt, phân bổ, khen thưởng…). Tiêu đề không có từ quy phạm (quy định, ban hành Quy chế, mức thu…). | 36 | `4724` (49/2005/QĐ-BNV) |
| 9 | `so_hieu_co_nam` | `true` | Quyết định, Nghị quyết, Chỉ thị có năm trong số hiệu. | 47 | `10377` (25/2005/CT-UBND) |
| 10 | `so_hieu_khong_nam` | `false` | Như trên, số hiệu không có năm, ban hành từ 01/01/2005. | 36 | `82441` (1341/QĐ-UBND) |
| 11 | `can_kiem` | `null` | Không đủ căn cứ (số hiệu không có năm, ban hành trước 2005). Cần kiểm tay. | 1 (cả dòng 4) | `19876` (109-TTg-TN) |

### `cap_hieu_luc` và `cap_hieu_luc_nhan`

15 nhóm theo khoản 1 Điều 1 Luật 87/2025/QH15. Công cụ chỉ gán khi `la_vbqppl = true`. Thứ tự xét theo bảng.

| `cap_hieu_luc` | `cap_hieu_luc_nhan` | Văn bản và cơ quan | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- |
| 1 | `HIEN_PHAP` | Hiến pháp | 1 | `36948` |
| 2 | `QUOC_HOI` | Bộ luật, Luật, Sắc luật; Nghị quyết của Quốc hội | 2 | `2511` (47/2005/QH11) |
| 3 | `UBTV_QUOC_HOI` | Pháp lệnh; Nghị quyết của UBTV Quốc hội | 1 | `19070` (33/2007/PL-UBTVQH11) |
| 4 | `CHU_TICH_NUOC` | Lệnh; Quyết định của Chủ tịch nước; Sắc lệnh (`hinh_thuc_cu`) | 2 | `35961` (Sắc lệnh 33) |
| 5 | `CHINH_PHU` | Nghị định; Nghị quyết, Quyết định của Chính phủ | 6 | `602450` (31/2024/NĐ-CP) |
| 6 | `THU_TUONG` | Quyết định của Thủ tướng; Chỉ thị của Thủ tướng (`hinh_thuc_cu`) | 3 | `42020` (181/1998/QĐ-TTg) |
| 7 | `HDTP_TANDTC` | Nghị quyết của Hội đồng Thẩm phán TAND tối cao | 1 | `316651` (01/2016/NQ-HĐTP) |
| 8 | `THONG_TU` | Thông tư; Quyết định, Chỉ thị của Bộ (`hinh_thuc_cu`) | 34 | `2211` (42/2005/TT-BTC) |
| 9 | `THONG_TU_LIEN_TICH` | Thông tư liên tịch | 3 | `44546` |
| 10 | `HDND_TINH` | Nghị quyết của cơ quan cấp tỉnh | 6 | `149606` (24/2012/NQ-HĐND) |
| 11 | `UBND_TINH` | Quyết định của cơ quan cấp tỉnh; Chỉ thị cấp tỉnh (`hinh_thuc_cu`) | 32 | `10377` (25/2005/CT-UBND) |
| 12 | `CHU_TICH_UBND_TINH` | Quyết định cấp tỉnh có `QĐ-CT` trong số hiệu | 0 | — |
| 13 | `HC_KT_DAC_BIET` | Văn bản của đơn vị hành chính - kinh tế đặc biệt (cơ quan có "đặc khu") | 0 | — |
| 14 | `HDND_XA` | Nghị quyết cấp xã | 0 | — |
| 15 | `UBND_XA` | Quyết định cấp xã | 1 | `672071` (Phường Lái Thiêu) |
| `null` | `null` | Không phải VBQPPL, cấp huyện, hoặc không xác định | 111 | `4724` |

- "Cấp tỉnh": `issuing_authority` bắt đầu bằng "Tỉnh " hoặc là "Thành phố" trực thuộc trung ương (Hà Nội, Hồ Chí Minh, Cần Thơ, Đà Nẵng, Hải Phòng, Huế).
- "Cấp xã": `issuing_authority` bắt đầu bằng "Xã", "Phường" hoặc "Thị trấn".
- "Của Bộ": Bộ, Ngân hàng Nhà nước, Thanh tra Chính phủ, Ủy ban Dân tộc, Văn phòng Chính phủ, TAND tối cao, VKSND tối cao, Kiểm toán Nhà nước.

### `cap_hieu_luc_ghi_chu`

| Giá trị | `cap_hieu_luc` | Nghĩa | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- |
| `null` | 1..15 hoặc `null` | Hình thức có trong luật 2025, hoặc văn bản không phải VBQPPL. | 194 | `602450` |
| `hinh_thuc_cu` | 4, 5, 6, 8, 11 | Hình thức không có trong luật 2025. Công cụ xếp cấp theo chủ thể ban hành. Ví dụ: Sắc lệnh → 4; Quyết định của Chính phủ, văn bản của Hội đồng Bộ trưởng → 5; Chỉ thị Thủ tướng → 6; Quyết định, Chỉ thị của Bộ → 8; Chỉ thị UBND tỉnh → 11. | 7 | `10377` (Chỉ thị 25/2005/CT-UBND, cấp 11) |
| `cap_huyen` | `null` | Cơ quan cấp huyện (Huyện, Quận, Thị xã, Thành phố thuộc tỉnh). Luật 2025 bỏ cấp này. | 2 | `358316` |
| `khong_xac_dinh` | `null` | VBQPPL nhưng không khớp nhóm nào. | 0 | — |

### `ngay_hieu_luc_cach` và `ngay_hieu_luc_so_ngay`

Cách công cụ có `ngay_hieu_luc`. Công cụ chỉ đọc câu "… <loại văn bản> này có hiệu lực …" của chính văn bản. Câu trong ngoặc kép bị bỏ. Câu có thể có điều khoản đứng trước chủ ngữ: "Khoản 3 Điều 2 Thông tư này có hiệu lực …". Đó là ngày riêng của điều khoản, ghi ở `hieu_luc_rieng`.

`ngay_hieu_luc_cach` là mốc tính. `ngay_hieu_luc_so_ngay` là số ngày sau mốc mà câu nêu. Bên đọc tự tính lại được: ngày = mốc + số ngày.

| Giá trị | `ngay_hieu_luc` | `ngay_hieu_luc_so_ngay` | Câu mẫu | Có `_trich` | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- | --- |
| `ngay_cu_the` | Ngày ghi trong câu | `null` | "có hiệu lực từ ngày 01 tháng 7 năm 2007" | Có | 50 | `19070` → `2007-07-01` |
| `ngay_ky` | `issuance_date` + số ngày | `0` ("kể từ ngày ký / ban hành") hoặc N ("sau N ngày kể từ ngày ký") | "có hiệu lực sau 15 ngày kể từ ngày ký" | Có | 88 (0 ngày: 69; 10 ngày: 13; 15 ngày: 4; 7 và 45 ngày: 1 mỗi loại) | `602450` → `2024-03-15` (0); `35552`: ký 18/05/2004 → `2004-06-02` (15) |
| `ngay_thong_qua` | Ngày thông qua + số ngày | `0` hoặc N | Nghị quyết HĐND: "có hiệu lực sau 10 ngày, kể từ ngày thông qua" | Có | 3 | `149606` → `2012-10-15` (10); `401532` → `2018-07-10` (0) |
| `ngay_dang_cong_bao` | `null`. Hệ thống không có ngày đăng Công báo. | `0` hoặc N | "có hiệu lực sau 15 ngày, kể từ ngày đăng Công báo" | Có | 9 | `4724` (15) |
| `mac_dinh_ngay_ban_hanh` | `issuance_date` | `null` | Không có câu hiệu lực. **Giá trị suy ra.** Chỉ dùng khi `la_vbqppl = false`. | Không | 31 | `28302` (Công văn) |
| `khong_doc_duoc` | `null` | `null` | Có câu hiệu lực. Công cụ không đọc được ngày. | Có | 5 | `2211` |
| `khong_tim_thay` | `null` | `null` | Không có câu hiệu lực. Văn bản có `la_vbqppl` là `true` hoặc `null`. | Không | 15 | `2511` (Luật 47/2005/QH11) |
| `van_ban_hop_nhat` | `null` | `null` | Văn bản hợp nhất. Công cụ không bóc ngày. | Không | 2 | `589448` |

Giá trị cũ `sau_n_ngay_ky`, `sau_n_ngay_thong_qua`, `phu_thuoc_ngay_dang_cong_bao` không còn dùng. Chúng thành `ngay_ky`, `ngay_thong_qua`, `ngay_dang_cong_bao` kèm `ngay_hieu_luc_so_ngay` (V9).

`hieu_luc_rieng[]` và chunk dùng cùng bộ giá trị này. Chunk lấy ngày của văn bản thì có `ngay_hieu_luc_rieng = false`.

### `ngay_het_hieu_luc_cach`

Công cụ chỉ đọc câu của chính văn bản. Hết hiệu lực do văn bản khác nằm ở `legal-changed-v3`.

| Giá trị | `ngay_het_hieu_luc` | Câu mẫu | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- |
| `ngay_cu_the` | Ngày ghi trong câu | "… này hết hiệu lực kể từ ngày …"; "… có hiệu lực từ … đến hết ngày 31/12/2013" | 3 | `163439` → `2013-12-31` |
| `het_nam` | 31/12 của năm ghi trong câu | "… đến hết năm 2025"; "… cho giai đoạn 2021 - 2025" | 0 | — |
| `khong_ghi` | `null` | Văn bản không tự ghi ngày hết hiệu lực. **Không có nghĩa là còn hiệu lực.** | 200 | `602450` |

## 6.3. Chunk

### `chunk_type`

| Giá trị | v2 | Cấp node | Nội dung | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| `dieu` | 1.075.620 | Điều | Trọn một Điều không có khoản. `is_full = true`. | 839 | `611245_d3` |
| `dieu_full` | 1.052.700 | Điều | Trọn một Điều có khoản. `is_full = true`. | 647 | `602450_d1_full` |
| `dieu_mo_dau` | 89.835 | Điều | Phần trước khoản đầu, dài từ 40 ký tự. | 131 | `206663_d3_md` |
| `khoan` | 3.315.998 | Khoản | Trọn một khoản không có điểm. `is_full = true`. | 2.160 | `602450_d2_k1` |
| `khoan_full` | 740.612 | Khoản | Trọn một khoản có điểm. `is_full = true`. | 359 | `602450_d1_k1_full` |
| `khoan_mo_dau` | 474.670 | Khoản | Phần trước điểm đầu, dài từ 40 ký tự. | 274 | `602450_d1_k1_md` |
| `diem` | 2.781.470 | Điểm | Trọn một điểm, gồm các tiểu điểm. | 1.271 | `602450_d1_k1_pa` |
| `tieu_diem` | — | Tiểu điểm | Mục gạch đầu dòng (tiết) thứ `n` của một điểm. Có khi điểm có từ 2 dòng gạch đầu dòng cùng ký hiệu. Node nhỏ nhất. | 320 | `<doc>_d<x>_k<y>_p<z>_t<n>` |
| `phu_luc` | 264.774 | Phụ lục | Một phần của `phu_luc[]` không chia Điều. | 341 | `602450_pl0` |
| `muc` | 437.665 | Đề mục | Một đề mục (I, II hoặc 1., 2.) của văn bản không chia Điều. | 147 | `318496_m1` |
| `noi_dung` | 98.573 | Nội dung | Văn bản không chia Điều, không có đề mục. `_nd`: trọn nội dung ngắn. `_nd<k>`: đoạn thứ `k`. | 104 | `35961_nd1` |
| `noi_dung_full` | — | Nội dung | Trọn nội dung dài (trên 200 âm tiết). `is_full = true`. | 17 | `35961_nd_full` |

### `dan_chieu[].loai`

Loại dẫn chiếu trong chunk. Số đếm theo dẫn chiếu (2.216 dẫn chiếu).

| Giá trị | Nghĩa | `van_ban` | `target_id` | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| `ngoai` | Dẫn tới văn bản khác, nêu số hiệu hoặc tên luật. | Số hiệu hoặc tên | ID đích, hoặc `null` khi chưa nối được | 726 | `356281_d4_full`: "Điều 16 Luật Thủy lợi" → `322933` |
| `noi_bo` | Dẫn tới chính văn bản. Câu có "… này" ("Điều này", "Luật này", "khoản này"). Công cụ đổi "Điều này" thành số Điều chứa chunk. | `null` | Bằng `doc_id` | 711 | `356281_d15_full`: "Khoản 1 Điều này" → `khoản 1 Điều 15` |
| `noi_bo_ngam` | Dẫn vị trí, không nêu văn bản ("theo quy định tại khoản 2 Điều 5"). Không dùng cho văn bản sửa đổi: ở đó vị trí trần thuộc văn bản bị sửa. | `null` | Bằng `doc_id` | 577 | `356281_d16_full`: "tại Điều 1" |
| `van_ban_bi_sua` | Câu có "… này" nằm trong nội dung mới (trong ngoặc kép) của văn bản sửa đổi. Câu chỉ văn bản bị sửa. Không xác định được văn bản bị sửa thì công cụ bỏ dẫn chiếu. | Số hiệu văn bản bị sửa | ID văn bản bị sửa | 202 | `602450_d2_full`: "Điều 5 Nghị định này" → `61/2016/NĐ-CP` |

## 6.4. Quan hệ

Mỗi quan hệ có đúng một vị trí. Câu nêu N vị trí cho N quan hệ. Vì vậy số quan hệ ở v3 mới lớn hơn số câu tác động.

### `action` (quan hệ)

Loại tác động. Công cụ nhận hành động từ chữ trong câu nguồn. Câu nêu thẩm quyền hoặc đề nghị ("kiến nghị đình chỉ", "có quyền …") không là hành động. Ghi chú lịch sử ("đã được sửa đổi tại …") không là hành động.

| Giá trị | v2 | Nghĩa | Chữ trong câu | `hieu_luc_tac_dong` | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- | --- |
| `bo-sung` | 41.902 | Thêm nội dung mới: thêm Điều, khoản, điểm, hoặc thêm câu vào đơn vị có sẵn. | "bổ sung" sau "sửa đổi," hoặc trước "một số", "Điều N", "khoản N", "điểm x", "nội dung", "tên gọi" | `ve_sau`, `ve_truoc` | 313 | `602450_0` |
| `sua-doi` | 64.612 | Sửa nội dung đang có. "Sửa đổi, bổ sung X" cho 2 quan hệ: `sua-doi` và `bo-sung`. | "sửa đổi" | `ve_sau`, `ve_truoc` | 268 | `602450_1` |
| `thay-cum-tu` | — | Thay một cụm từ bằng cụm từ khác. Cặp cụm từ nằm ở `cum_tu`. | "thay (thế) cụm từ / từ ngữ / từ “X” bằng “Y”" | `ve_sau`, `ve_truoc` | 231 | `602450_14` |
| `bai-bo` | 31.908 | Bỏ một đơn vị hoặc cả văn bản. Phần bị bỏ hết hiệu lực từ ngày tác động bắt đầu. | "bãi bỏ"; "Bỏ <đơn vị>" ("Bỏ gạch đầu dòng thứ ba điểm b …"); "<văn bản> hết hiệu lực kể từ ngày … này có hiệu lực"; "Các Thông tư sau đây hết hiệu lực: a) …" | `ve_sau`, `ve_truoc` | 46 | `488371_48`; `378946_0` |
| `thay-the` | 41.645 | Thay cả một đơn vị hoặc cả văn bản. Đơn vị cũ hết hiệu lực. | "thay thế" (không phải "thay thế cụm từ") | `ve_sau`, `ve_truoc` | 40 | `585073_61` |
| `dinh-chinh` | — | Sửa lỗi kỹ thuật hoặc lỗi trình bày của văn bản đích. | "đính chính" | `tu_dau` | 22 | `383494_3` |
| `huong-dan` | — | Văn bản nguồn hướng dẫn thi hành văn bản đích. Văn bản đích không đổi. | Tiêu đề có "hướng dẫn" | `khong_ap_dung` | 21 | `hd_2211_0` |
| `hop-nhat` | — | Văn bản hợp nhất trình bày lại văn bản gốc. Văn bản đích không đổi. | Văn bản đầu tiên nêu ở phần đầu văn bản hợp nhất (văn bản gốc) | `khong_ap_dung` | 8 | `hn_589448_0` |
| `quy-dinh-chi-tiet` | — | Văn bản nguồn quy định chi tiết văn bản đích. Văn bản đích không đổi. | Tiêu đề có "quy định chi tiết" | `khong_ap_dung` | 7 | `hd_123273_0` |
| `huy-bo` | 385 | Hủy bỏ. Khác `bai-bo`: phần bị hủy coi như không có giá trị từ đầu. | "hủy bỏ", "huỷ bỏ" | `tu_dau` | 6 | `241415_0` |
| `dinh-chi` | — | Dừng thi hành trong một khoảng thời gian. Thời gian nằm ở `dinh_chi_*`. | "(tạm) đình chỉ (việc) thi hành / thực hiện" | `tam_ngung` | 3 | `181025_0` |
| `ngung-hieu-luc` | — | Ngưng hiệu lực trong một khoảng thời gian. Dùng lại `dinh_chi_*`. | "(tạm) ngưng / ngừng (thi hành) hiệu lực" | `tam_ngung` | 2 | `564293_0` |
| `gia-han` | — | Kéo dài thời hạn hiệu lực. Ngày mới nằm ở `gia_han_den_ngay`. | "gia hạn / kéo dài (thời hạn) hiệu lực / áp dụng". "gia hạn nộp thuế" không tính. | `ve_sau` | 2 | `318496_0` |

Số v3 tính cả quan hệ ở lời dẫn. Ví dụ: `ngung-hieu-luc` có `564293_0` (Điều 1) và `intro_564293_0` (lời dẫn).

### `hieu_luc_tac_dong`

Tác động bắt đầu từ ngày nào và kéo dài bao lâu. `ve_sau`, `ve_truoc` chỉ hướng thời gian.

| Giá trị | Đọc là | Nghĩa | Bắt đầu | Kết thúc | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- | --- |
| `ve_sau` | về sau | Thay đổi áp dụng từ ngày đơn vị nguồn có hiệu lực. Trước ngày đó, văn bản đích giữ nội dung cũ. | `source_ngay_hieu_luc` | Không giới hạn. `gia-han`: phần được gia hạn còn hiệu lực đến `gia_han_den_ngay` hoặc `gia_han_den_khi`. | 863 | `602450_1`: áp dụng từ 15/03/2024 |
| `ve_truoc` | về trước (hồi tố) | Văn bản nguồn hồi tố. Thay đổi áp dụng từ một ngày trước ngày nguồn có hiệu lực. Chỉ đơn vị nguồn nằm trong `hoi_to_vi_tri` có giá trị này. | `source_ngay_hoi_to` | Không giới hạn | 37 | `509618_45`: tính từ 01/01/2019 |
| `tu_dau` | từ đầu | `huy-bo`: phần bị hủy coi như không có giá trị từ đầu. `dinh-chinh`: nội dung đã sửa lỗi coi như đúng từ đầu. | Ngày văn bản đích có hiệu lực | Không giới hạn | 28 | `241415_0`, `383494_3` |
| `tam_ngung` | tạm ngừng | Phần bị tác động ngừng áp dụng trong một khoảng. Sau khoảng đó, phần này áp dụng lại, trừ khi văn bản khác quy định khác. | `dinh_chi_tu_ngay` | `dinh_chi_den_ngay` hoặc `dinh_chi_den_khi` | 5 | `564293_0`: 24/04/2023 → 31/12/2023 |
| `khong_ap_dung` | không áp dụng | Quan hệ không đổi nội dung và hiệu lực của đích: hướng dẫn, quy định chi tiết, hợp nhất. | — | — | 36 | `hd_2211_0`, `hn_589448_0` |

### `cap_quan_he`

Mức chi tiết của quan hệ. Thứ tự xét ở [09, mục 9.10.8](09-hop-dong-du-lieu-v4.md#9108-cấp-quan-hệ). Dữ liệu v3 hiện có xét theo [04, mục 4.8.7](04-hop-dong-du-lieu-v3.md#487-cấp-quan-hệ).

| Giá trị | Nghĩa | `vi_tri` | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- |
| `vi_tri` | Quan hệ nêu một vị trí: Điều, khoản, điểm, tiểu điểm, tên Điều, phụ lục (kể cả phụ lục chứa mẫu biểu). Câu nằm ở Điều, lời dẫn hay tiêu đề đều vậy. | Một phần tử | 859 | `602450_1`; `intro_564293_0` (lời dẫn) |
| `van_ban` | Quan hệ ở cấp cả văn bản: thay thế, bãi bỏ toàn bộ; lời dẫn "sửa đổi một số điều"; hướng dẫn, hợp nhất không nêu điều khoản; câu hết hiệu lực. | `["toàn bộ"]` hoặc rỗng | 94 | `241415_0` |
| `van_ban_kem_theo` | Phần ban hành kèm theo văn bản đích, chỉ nêu bằng tên ("đơn giá … ban hành kèm theo Quyết định X"). Tên nằm ở `doi_tuong`. | Rỗng | 9 | `662238_17` |
| `noi_dung` | Phần chỉ nêu bằng tên, không ban hành kèm theo ("bảng giá ca máy công bố tại Văn bản X"; "phần căn cứ"). Tên nằm ở `doi_tuong`. | Rỗng | 5 | `383494_0` |
| `chua_xac_dinh` | Thay đổi cấp điều khoản, công cụ không tìm được vị trí. Cần rà tay. | Rỗng | 2 | `449124_1` |

### `detection_mode`

Nơi có câu tác động trong văn bản nguồn. Tiền tố `_id` khớp giá trị này.

| Giá trị | v2 | Nghĩa | Tiền tố `_id` | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| (trường thiếu) | 121.529 | Tiêu đề văn bản nguồn nêu hành động. Câu tác động nằm trong Điều, khoản, điểm, hoặc đề mục của công văn. | không có | 891 | `602450_1` |
| `hidden` | 53.972 | Tiêu đề văn bản nguồn không nêu hành động. Câu tác động nằm trong một Điều. | `hidden_` | 17 | `hidden_86794_0` |
| `intro` | 1.586 | Câu tác động nằm trong lời dẫn ("… ban hành Nghị định sửa đổi, bổ sung một số điều của …"). Lời dẫn luôn có quan hệ riêng. | `intro_` | 25 | `intro_602450_0` |
| `het_hieu_luc` | 3.365 | Câu "… hết hiệu lực kể từ ngày … này có hiệu lực" trong văn bản nguồn. Hành động `bai-bo` cho mỗi văn bản nêu trong câu, phạm vi `toàn bộ`. Không qua QA. | `hhl_` | 0 | — |
| `title_guidance` | — | Quan hệ hướng dẫn hoặc quy định chi tiết. Đích lấy từ tiêu đề hoặc lời dẫn. | `hd_` | 28 | `hd_2211_0` |
| `hop_nhat` | — | Quan hệ hợp nhất. Đích lấy từ phần đầu văn bản hợp nhất. | `hn_` | 8 | `hn_589448_0` |

### `scope_resolution_method`

Cách quy tắc xác nhận phạm vi, không cần QA phạm vi.

| Giá trị | v2 | Nghĩa | Số v3 | Ví dụ |
| --- | --- | --- | --- | --- |
| (trường thiếu) | 180.422 | Phạm vi đi qua QA phạm vi, hoặc không cần kiểm (không có số). | 156 | `241415_0` |
| `explicit_declaration` | 30 | Câu nguồn nêu rõ vị trí đích ("Sửa đổi, bổ sung điểm a khoản 3 Điều 2 như sau"). | 563 | `602450_1` |
| `liet_ke_vi_tri` | — | Câu `thay-cum-tu` hoặc `dinh-chinh` liệt kê vị trí. Công cụ giữ cả danh sách, rồi tách mỗi vị trí thành một quan hệ. | 250 | `383494_11` |

### `target_match_note`

| Giá trị | Nghĩa | Số v3 | Ví dụ |
| --- | --- | --- | --- |
| `lech_ngay_trich_dan` | Ngày trong câu trích khác ngày ban hành đã lưu. Công cụ nối theo số hiệu có năm, cùng năm ban hành, một đích duy nhất. Với số hiệu địa phương, đích phải cùng cơ quan. | 17 | `186386_0` |

### Giá trị đặc biệt của `scope`

| Giá trị | Nghĩa | `cap_quan_he` | Số v3 |
| --- | --- | --- | --- |
| `toàn bộ` | Cả văn bản. Công cụ chuẩn hóa `toan-bo`, `toàn văn`, "trong toàn bộ Thông tư" thành giá trị này. `vi_tri = ["toàn bộ"]`. | `van_ban` | 60 |
| `một số điều` | Câu nêu "một số điều / một số nội dung" của đích. Vị trí chi tiết nằm ở quan hệ khác. | `van_ban` | 23 |
| `một số cụm từ` | Câu nêu "một số (cụm) từ" của đích. Vị trí chi tiết nằm ở quan hệ khác. | `van_ban` | 9 |
| `chưa xác định` | Quy tắc không tìm được phạm vi. `unresolved = true`. | `chua_xac_dinh` hoặc `van_ban` | 4 |

### Giá trị đặc biệt của `doi_tuong`

| Giá trị | Nghĩa | Ví dụ |
| --- | --- | --- |
| `phần căn cứ` | `dinh-chinh` sửa phần căn cứ của đích. | `383494_0` |
| `phần Nơi nhận` | `dinh-chinh` sửa phần Nơi nhận của đích. | Một quan hệ khác của `383494` |
| Chữ khác | Tên phần bị tác động, chép từ câu nguồn. | `662238_17`: "Bảng 1 Mục 8 Chương 1 của Định mức …" |

### `source_path` không chỉ Điều, khoản, điểm

| Giá trị | Nghĩa | Phía nguồn của cạnh |
| --- | --- | --- |
| `intro` | Lời dẫn của văn bản nguồn. | Node văn bản |
| `Tiêu đề` | Quan hệ hướng dẫn lấy đích từ tiêu đề. | Node văn bản |
| `Lời dẫn` | Quan hệ hướng dẫn lấy đích từ lời dẫn. | Node văn bản |
| `Phần đầu` | Quan hệ hợp nhất lấy đích từ phần đầu văn bản hợp nhất. | Node văn bản |
| `Mục <n>` | Đề mục của văn bản không chia Điều. | Chunk `<doc>_m<n>` |
| `Nội dung` | Nội dung của văn bản không chia Điều, không đề mục. | Chunk `<doc>_nd` hoặc `<doc>_nd_full` |

## 6.5. Nhật ký lượt chạy

Các giá trị dưới đây nằm ở `work/<run>/documents.jsonl`. Các giá trị này không có trên ES.

### `qa`

| Giá trị | Nghĩa | Việc cần làm |
| --- | --- | --- |
| `done` | QA xong mọi nhóm ứng viên. | — |
| `incomplete` | Có nhóm gọi model lỗi. Nhóm đó không có quan hệ. Chi tiết ở `qa_errors`. | Chạy lại ([02, mục 2.6](02-luong-hoat-dong.md#26-làm-tiếp-và-chạy-lại)). |
| `skipped` | Không có ứng viên, hoặc lượt chạy với `--no-qa`. | — |

### `layout.signals`

Tín hiệu bố cục rủi ro. Có tín hiệu thì công cụ hỏi model LLM vị trí phụ lục và văn bản kèm theo.

| Giá trị | Nghĩa |
| --- | --- |
| `tail_dieu` | Parser thấy chuỗi Điều (từ "Điều 1, Điều 2") nằm sau chữ ký hoặc Nơi nhận. |
| `long_noi_nhan` | Nơi nhận dài hơn 2.000 ký tự. Nội dung có thể đã lọt vào Nơi nhận. |
| `segment_in_main` | Phần chính có chuỗi Điều đánh số lại. Văn bản kèm theo có thể nằm trong phần chính. |
| `unlabeled_without_note` | Phần kèm theo không nhãn thiếu ghi chú "(Ban hành kèm theo …)". |
| `empty_labeled_part` | Phụ lục có nhãn, không có Điều, nội dung ngắn hơn 80 ký tự. |

`layout.applied = true` khi công cụ áp dụng bố cục của model. `layout.reason` ghi lý do khi công cụ giữ bố cục quy tắc.
