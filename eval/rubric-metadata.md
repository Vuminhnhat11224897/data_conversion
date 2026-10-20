# Tiêu chí gán nhãn chuẩn (gold) cho metadata văn bản

Bạn đọc một văn bản pháp luật Việt Nam và ghi 6 trường về địa vị pháp lý và thời điểm hiệu lực của chính văn bản đó.
Bạn không thấy kết quả của công cụ. Làm độc lập. Chỉ dùng chữ của văn bản và các quy tắc dưới đây. Không đoán.

## Dữ liệu vào

Gói văn bản có: `so_hieu`, `loai`, `co_quan`, `ngay_ban_hanh`, `ten`, `toan_van`.

## Trường

| Trường | Giá trị | Quy tắc |
| --- | --- | --- |
| `la_vbqppl` | `true` \| `false` | `true` khi văn bản là văn bản quy phạm pháp luật theo luật ban hành VBQPPL có hiệu lực **lúc văn bản được ban hành**: đúng hình thức, đúng cơ quan có thẩm quyền, chứa quy tắc xử sự chung, áp dụng nhiều lần. `false` với văn bản cá biệt (bổ nhiệm, phê duyệt, khen thưởng, giao chỉ tiêu, phân bổ ngân sách, công bố thủ tục hành chính), công văn, thông báo, kế hoạch, văn bản hợp nhất, văn bản của Đảng, điều ước quốc tế, tiêu chuẩn. Hiến pháp, Bộ luật, Luật, Pháp lệnh, Lệnh, Nghị định, Thông tư, Thông tư liên tịch luôn `true`. |
| `cap_hieu_luc` | 1..15 \| `null` | Bảng dưới. `null` khi `la_vbqppl = false`, hoặc cơ quan cấp huyện. |
| `ngay_hieu_luc` | `YYYY-MM-DD` \| `null` | Ngày văn bản có hiệu lực. Cách tính ở mục dưới. |
| `ngay_het_hieu_luc` | `YYYY-MM-DD` \| `null` | Ngày hết hiệu lực **do chính văn bản ghi** ("… có hiệu lực từ … đến hết ngày 31/12/2013", "… áp dụng đến hết năm 2025" → `2025-12-31`). Văn bản không tự ghi: `null`. Không suy từ văn bản khác. |
| `ngay_hoi_to` | `YYYY-MM-DD` \| `null` | Văn bản (hoặc một phần) áp dụng từ một ngày **trước** `ngay_ban_hanh`: ngày đó. Không có: `null`. |
| `hieu_luc_rieng` | mảng | Ngày hiệu lực văn bản nêu riêng cho một số Điều, khoản, điểm **của chính nó**, khác ngày chung. Mỗi câu một phần tử `{"vi_tri": [...], "ngay_hieu_luc": "YYYY-MM-DD"}`. Vị trí viết `Điều 5`, `khoản 2 Điều 5`, `điểm a khoản 2 Điều 5`, mỗi vị trí một phần tử, đủ cấp. Không có: `[]`. Câu hồi tố (ngày trước `ngay_ban_hanh`) không ghi ở đây, chỉ ghi `ngay_hoi_to`. |

## `ngay_hieu_luc`

Đọc câu hiệu lực của chính văn bản ("Quyết định này có hiệu lực …"). Bỏ câu nằm trong ngoặc kép và câu nói về văn bản khác.

| Câu | `ngay_hieu_luc` |
| --- | --- |
| "có hiệu lực từ ngày 01/7/2024" | `2024-07-01` |
| "có hiệu lực (thi hành) kể từ ngày ký (ban hành)" | `ngay_ban_hanh` |
| "có hiệu lực sau N ngày kể từ ngày ký" | `ngay_ban_hanh` + N ngày |
| Nghị quyết HĐND: "có hiệu lực sau N ngày kể từ ngày thông qua"; "kể từ ngày … thông qua" | Ngày thông qua ghi trong văn bản + N |
| "sau N ngày kể từ ngày đăng Công báo", "kể từ ngày đăng Công báo" | `null` (văn bản không ghi ngày đăng) |
| Có câu nhưng không ra một ngày ("từ năm học 2004 - 2005") | `null` |
| Không có câu hiệu lực, `la_vbqppl = true` | `null` |
| Không có câu hiệu lực, `la_vbqppl = false` | `ngay_ban_hanh` |
| Văn bản hợp nhất | `null` |

Câu nêu ngày chung và "trừ quy định tại khoản 2 Điều này": ngày chung là `ngay_hieu_luc`. Ngày của các vị trí được trừ ghi ở `hieu_luc_rieng`.

## `cap_hieu_luc` (Luật 87/2025/QH15)

| Cấp | Văn bản và cơ quan |
| --- | --- |
| 1 | Hiến pháp |
| 2 | Bộ luật, Luật, Nghị quyết của Quốc hội |
| 3 | Pháp lệnh, Nghị quyết của Ủy ban Thường vụ Quốc hội |
| 4 | Lệnh, Quyết định của Chủ tịch nước; Sắc lệnh |
| 5 | Nghị định; Nghị quyết, Quyết định của Chính phủ; văn bản của Hội đồng Bộ trưởng |
| 6 | Quyết định, Chỉ thị của Thủ tướng Chính phủ |
| 7 | Nghị quyết của Hội đồng Thẩm phán Tòa án nhân dân tối cao |
| 8 | Thông tư; Quyết định, Chỉ thị của Bộ trưởng, Thủ trưởng cơ quan ngang bộ |
| 9 | Thông tư liên tịch |
| 10 | Nghị quyết của Hội đồng nhân dân cấp tỉnh |
| 11 | Quyết định, Chỉ thị của Ủy ban nhân dân cấp tỉnh |
| 12 | Quyết định của Chủ tịch Ủy ban nhân dân cấp tỉnh (số hiệu `QĐ-CT`) |
| 13 | Văn bản của đơn vị hành chính - kinh tế đặc biệt |
| 14 | Nghị quyết của Hội đồng nhân dân cấp xã |
| 15 | Quyết định của Ủy ban nhân dân cấp xã |

Cơ quan cấp huyện (huyện, quận, thị xã, thành phố thuộc tỉnh): `null`.

## Kết quả

Một file JSON là mảng, mỗi văn bản một phần tử, cùng thứ tự với file vào:

```json
{"doc_id": "...", "la_vbqppl": true, "cap_hieu_luc": 11, "ngay_hieu_luc": "2024-07-01", "ngay_het_hieu_luc": null,
 "ngay_hoi_to": null, "hieu_luc_rieng": [{"vi_tri": ["khoản 2 Điều 5"], "ngay_hieu_luc": "2025-01-01"}],
 "trich": {"ngay_hieu_luc": "câu gốc", "la_vbqppl": "lý do ngắn"}, "chua_chac": ["tên trường nếu không chắc"]}
```

`trich` chép nguyên văn câu dùng để kết luận (hoặc lý do ngắn với `la_vbqppl`, `cap_hieu_luc`). `chua_chac` liệt kê trường bạn không chắc.
