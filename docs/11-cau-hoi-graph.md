# 11. Câu hỏi cho bên Graph: phạm vi của cạnh

Tài liệu này nêu 3 việc bên Graph cần chốt. Bên dữ liệu chưa đổi hợp đồng cho tới khi bên Graph trả lời. Mỗi việc có bản ghi thật và cách xử lý đề xuất. Ngày soạn: 21/10/2026. Cập nhật: 27/10/2026.

| Việc | Mục |
| --- | --- |
| 1. Quan hệ đã rõ đích và hành động, chưa rõ phạm vi (`relation_only`) | 11.1 |
| 2. Cạnh gắn vào node chứa, tác động chỉ lên một phần của node (`chi_tiet_vi_tri`) | 11.2 |
| 3. Cạnh vào phụ lục không nêu ký hiệu (`vi_tri = ["Phụ lục"]`) | 11.6 |

- Hợp đồng hiện hành: [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md), mục 9.5.1 (quy ước phụ lục), 9.10.7 (trạng thái cạnh) và 9.11 (cách nối).
- Rule xử lý mới: [08, mục 8.11](08-quan-he-4-tang-va-danh-gia.md#811-rule-tổng-quát-kiểm-sự-thật-không-kiểm-hình-thức-21102026).

## 11.1. Việc 1: quan hệ đã rõ đích và hành động, chưa rõ phạm vi

### Hiện trạng

| `resolution_status` | Bên Graph |
| --- | --- |
| `validated` | Dựng cạnh |
| `unresolved` | Không dựng cạnh |

Một số quan hệ có đích và hành động chắc chắn, nhưng câu nguồn không nêu phần nào bị tác động. Ví dụ: "Bãi bỏ một số quy định của Quyết định số X". Hiện công cụ để các quan hệ này ở `unresolved`, nên đồ thị không có thông tin rằng X bị tác động.

### Đề xuất

Thêm một trạng thái, tạm gọi `relation_only`. Tên có thể đổi. Điều cần chốt là hành vi của bên đọc.

| Điều đã xác nhận | Hiển thị quan hệ? | Dùng để xác định phần chịu tác động? |
| --- | --- | --- |
| Đích, hành động, phạm vi cụ thể | Có | Có, theo phạm vi |
| Đích, hành động, phạm vi toàn bộ | Có | Có, toàn bộ |
| Đích, hành động; biết tác động một phần, chưa rõ phần nào (`relation_only`) | Có, nếu Graph hỗ trợ | Không |
| Đích hoặc việc thực hiện chưa chắc (`unresolved`) | Không | Không |
| Có căn cứ là đề nghị, kể lại | Không có quan hệ | Không |

Bản ghi thật, lượt chạy lại `Cp-h2` (21/10/2026, chưa ghi ES). Hiện bản ghi có `resolution_status = unresolved`. Đề xuất đổi giá trị đó thành `relation_only`:

```json
{
  "_id": "641337_0",
  "source_path": "Điều 2",
  "action": "sua-doi",
  "target_doc": "3533/QĐ-UBND",
  "target_matched_id": 580598,
  "scope": "chưa xác định",
  "vi_tri": [],
  "cap_quan_he": "chua_xac_dinh",
  "unresolved": true,
  "resolution_status": "unresolved",
  "resolution_reason": "vi_tri_chua_xac_dinh",
  "evidence": "Quyết định này sửa đổi, bổ sung Quyết định số 3533/QĐ-UBND ngày 23 tháng 9 năm 2023 của Chủ tịch Ủy ban nhân dân tỉnh công bố Danh mục thủ tục hành chính …"
}
```

Ví dụ thứ hai: `273699_0`, `sua-doi` lên 1620/QĐ-UBND (`target_matched_id` 122632), bằng chứng "sửa đổi, bổ sung 29 (hai mươi chín) thủ tục hành chính đã được công bố theo Quyết định số 1620/QĐ-UBND".

Độ đúng của nhóm này, đo trên 5 bộ hold-out (lượt C′, đếm theo cặp hành động và đích trong từng văn bản):

| Ứng viên `vi_tri_chua_xac_dinh` | Đúng theo nhãn | Sai theo nhãn | Tỉ lệ đúng | Khoảng 95% (Wilson) |
| --- | --- | --- | --- | --- |
| Có `target_matched_id` | 32 | 19 | 63% | 49%–75% |
| Không có `target_matched_id` | 6 | 2 | 75% | 41%–93% |
| Tổng | 38 | 21 | 64% | 52%–75% |

Khoảng 1/3 ứng viên của nhóm này sai. Vì vậy cạnh `relation_only` chỉ dùng để tra cứu, không dùng để suy ra hiệu lực.

Nghĩa của `relation_only`:

1. Đích và hành động có bằng chứng.
2. Phạm vi chính xác chưa đủ căn cứ.
3. Bên Graph được dựng quan hệ để tra cứu.
4. Bên Graph không dùng quan hệ này để suy ra phần nào hết hiệu lực, hoặc để tạo nội dung hợp nhất.
5. Không có `target_matched_id` thì chưa nối vào văn bản cụ thể.

Trong lúc chờ trả lời, công cụ giữ các quan hệ này ở `unresolved`.

### Câu hỏi 1

Bên Graph có hỗ trợ trạng thái `relation_only` với 5 điểm trên không? Nếu có, bên Graph cần tên trường hay giá trị nào?

## 11.2. Việc 2: cạnh gắn vào node chứa, tác động chỉ lên một phần của node

### Hiện trạng

Phần không có node riêng có `vi_tri` là node chứa nó. Đây là các quyết định C3, C4, E1 ở [07](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt): mẫu biểu, đoạn, câu, gạch đầu dòng của khoản, tiết, dòng số thứ tự. Giới hạn thật chỉ còn trong `scope`. Hợp đồng dặn bên đọc không dùng `scope`.

Đo trên `legal-changed-v4` sau lượt ghi ngày 22/10/2026 (11.000 văn bản, mục 11.4): 274/42.771 quan hệ có phần không có node riêng (193 mẫu biểu; 77 dòng số thứ tự; 4 gạch đầu dòng, đoạn).

| Bản ghi | `scope` | `vi_tri` | `chi_tiet_vi_tri` | Tác động thật |
| --- | --- | --- | --- | --- |
| `legal-changed-v4/695211_6` (`thay-the` lên 05/2024/TT-BXD) | `Mẫu số 02 Phụ lục I` | `["Phụ lục I"]` | `Mẫu số 02` | 1 mẫu, không phải cả Phụ lục I |
| `legal-changed-v4/688385_160` (`bai-bo` lên 226/2025/NĐ-CP) | nhiều vị trí | `["điểm a khoản 4 Điều 7"]` | `gạch đầu dòng thứ 1` | 1 gạch đầu dòng, không phải cả điểm a |
| `legal-changed-v4/693748_0` (`bai-bo` lên 773/QĐ-UBND) | `Mục A Phụ lục I` | `["Mục A Phụ lục I"]` | `số thứ tự 06, 07` | 2 dòng của Mục A |

Nếu bên Graph coi cạnh như tác động lên cả node, đồ thị nói rộng hơn văn bản.

Từ code `8b023ca` (27/10/2026), quy ước phụ lục cũng ghi chữ vị trí gốc vào `chi_tiet_vi_tri` ([09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục)). Ví dụ: `692884_0` (lượt `fix9-H56`, chưa ghi ES) có `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri` "Mục II Phần B Phụ lục I". Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (876 văn bản): 197/9.760 quan hệ `validated` có `chi_tiet_vi_tri`.

### Đề xuất

Trường mới `chi_tiet_vi_tri` (keyword). Trường đã có trong 3 index `-v4` từ ngày 21/10/2026. v3 chưa có.

- Có trường này: tác động chỉ chạm phần ghi trong trường, bên trong node `vi_tri`.
- Không có: tác động lên cả node `vi_tri`.

Ví dụ: `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri = "Mẫu số 01"`.

Quy tắc chung: khi giảm độ chi tiết của node để biểu diễn, giữ nguyên giới hạn của tác động pháp lý.

### Câu hỏi 2

1. Bên Graph đồng ý dùng `chi_tiet_vi_tri` như trên không?
2. Bên Graph hiện có tính trạng thái hiệu lực của node từ các cạnh loại này không? Nếu có mà không đọc `chi_tiet_vi_tri`, 274 quan hệ trên bị tính rộng hơn văn bản.

## 11.3. Thông tin đã chốt, báo để bên Graph biết

| Thay đổi | Mục |
| --- | --- |
| `doi_tuong_loai`: `van_ban` hoặc `thu_tuc_hanh_chinh`. Cạnh lên thủ tục trỏ tới quyết định công bố thủ tục; tên thủ tục ở `doi_tuong`; mã ở `ma_thu_tuc`. | [09, mục 9.10.6](09-hop-dong-du-lieu-v4.md#9106-tác-động) |
| Quy ước phụ lục (người dùng chốt 26/10/2026, thu hẹp 27/10/2026): vị trí ngoài thân văn bản ghi là phụ lục chứa nó. Chữ vị trí gốc ghi ở `chi_tiet_vi_tri`. Phần nêu bằng tên thuộc phụ lục có `vi_tri` là phụ lục và giữ tên ở `doi_tuong`. Cạnh lên thủ tục có `vi_tri` là phụ lục chứa thủ tục. | [09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục) |
| Văn bản chỉ có tên trong ghi chú lịch sử, hoặc trong danh sách văn bản đi sau ghi chú đó, không là đích (26–27/10/2026). | [09, mục 9.10.7](09-hop-dong-du-lieu-v4.md#9107-trạng-thái-cạnh-và-nhánh-dò) |
| Quan hệ tên văn bản chỉ lấy từ tên in trong văn bản (Q11). | [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt) |
| `_id` quan hệ đổi khi chạy lại văn bản nguồn. Khi nhập lại, xóa cạnh cũ theo `source_id`, không theo `_id`. | [04, mục 4.8.2](04-hop-dong-du-lieu-v3.md#482-id) |

## 11.4. Dữ liệu v4 để bên Graph kiểm

Trạng thái ngày 27/10/2026. Chi tiết ở [09, mục 9.1](09-hop-dong-du-lieu-v4.md#91-trạng-thái-v4).

Ngày 22/10/2026, bên dữ liệu ghi lại 3 index `-v4` trên ES 10.1.10.23 bằng code `2911b77` (docs 08 mục 8.15). Đếm ngày 27/10/2026: số bản ghi không đổi.

| Index | Số bản ghi |
| --- | --- |
| `legal-docs-v4` | 11.000 văn bản mới nhất, ban hành từ 08/10/2025 đến 30/09/2026 |
| `legal-chunk-section-v4` | 447.597 chunk |
| `legal-changed-v4` | 42.771 quan hệ: 40.496 `validated`, 2.275 `unresolved` |

- Trong 42.771 quan hệ: 37.182 có `target_matched_id`; 1.819 có `doi_tuong_loai = thu_tuc_hanh_chinh`; 274 có `chi_tiet_vi_tri`.
- Kiểm hợp đồng (`eval.check_contract v4`, 22/10/2026): 237 quy tắc, 5 quy tắc có lỗi nhỏ về đọc cấu trúc. Mỗi quy tắc lỗi dưới 1% số bản ghi ([09, mục 9.12](09-hop-dong-du-lieu-v4.md#912-bất-biến-để-kiểm)).
- Ngày 26/10/2026, bên dữ liệu tạo lại vector của mọi văn bản và chunk `-v4`. Vector mới không cắt đầu vào ở 256 token.
- v3 không đổi.

**Code hiện tại khác dữ liệu này.** Code chốt hiện tại là `8b023ca` (27/10/2026). Dữ liệu `-v4` chưa có các thay đổi sau:

| Thay đổi | Ảnh hưởng tới cạnh | Mục |
| --- | --- | --- |
| Quy ước phụ lục | Vị trí ngoài thân văn bản thành phụ lục; chữ gốc ghi ở `chi_tiet_vi_tri`. Phần nêu bằng tên thuộc phụ lục (thủ tục, danh mục, biểu mẫu, dòng của danh mục) có `vi_tri` là phụ lục và `cap_quan_he = vi_tri`. Dữ liệu `-v4` hiện ghi `vi_tri` rỗng và `cap_quan_he` là `noi_dung` hoặc `van_ban_kem_theo`. Ví dụ: `694022_0`. | [09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục) |
| Ghi chú lịch sử phủ cả danh sách | Văn bản chỉ có tên trong danh sách sau ghi chú lịch sử không là đích. Dữ liệu `-v4` còn đích sai loại này. Ví dụ: `675210_28` (`sua-doi` tới `89/2025/QH15`). | [09, mục 9.10.7](09-hop-dong-du-lieu-v4.md#9107-trạng-thái-cạnh-và-nhánh-dò) |

- Đợt 10.000 văn bản tiếp theo (ban hành 25/06/2025–08/10/2025) chưa chạy.
- Người dùng chưa quyết có ghi lại 11.000 văn bản `-v4` bằng code `8b023ca` hay không.

Chất lượng quan hệ (docs 08, mục 8.14, 8.15, 8.17):

| Dữ liệu | Bộ đo, ngày đo | Phát hiện P / R | Phạm vi P / R | Ghi chú |
| --- | --- | --- | --- | --- |
| `-v4` hiện có (code `2911b77`) | H5 + H6, 500 văn bản, 22/10/2026, bộ chấm cũ | 0,890 / 0,873 | 0,785 / 0,743 | Đã dùng để sửa lỗi. Không độc lập. |
| Code `8b023ca` | H5 + H6, 27/10/2026, bộ chấm 27/10 | 0,895 / 0,873 | 0,833 / 0,773 | Không độc lập. |
| Code `8b023ca` | Hold-out 300, 27/10/2026, bộ chấm 27/10 | 0,900 / 0,861 | 0,711 / 0,673 | Độc lập. Nhãn do agent gán, chưa qua người duyệt. Bỏ văn bản 675259. |

- Phát hiện: đúng văn bản nguồn, hành động, văn bản đích. Phạm vi: đúng thêm vị trí bị tác động.
- Bộ chấm 27/10 áp quy ước phụ lục như code. Số đo theo hai bộ chấm không so trực tiếp được.
- Trên văn bản chưa từng xem, phạm vi thấp hơn rõ: P 0,711, R 0,673 ở hold-out 300.

## 11.5. Kiểm thử bên Graph cần chạy

1. Một cạnh tra cứu (`relation_only`) không làm đổi trạng thái hiệu lực của node nào.
2. Một cạnh có `chi_tiet_vi_tri` không làm node `vi_tri` mất hiệu lực toàn bộ.
3. Nhập lại một văn bản nguồn không để lại cạnh cũ khi `_id` đổi.
4. Một cạnh có `vi_tri = ["Phụ lục"]` không làm văn bản đích mất hiệu lực toàn bộ (mục 11.6).

## 11.6. Việc 3: cạnh vào phụ lục không nêu ký hiệu

### Hiện trạng

Quy ước phụ lục ([09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục), code `8b023ca`): phần ngoài thân văn bản có vị trí là phụ lục chứa nó. Chữ vị trí gốc ghi ở `chi_tiet_vi_tri`.

| Vị trí | Khi nào | Node đích |
| --- | --- | --- |
| `Phụ lục <n>` | Chữ nêu đúng một ký hiệu phụ lục | `<doc>_pl<i>` với `phu_luc[i].ky_hieu = <n>` |
| `Phụ lục` | Chữ không nêu ký hiệu, hoặc nêu từ hai ký hiệu trở lên | Chưa có node xác định |

Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (876 văn bản, code `8b023ca`, chưa ghi ES). Có 9.760 quan hệ `validated`:

| Nhóm | Quan hệ |
| --- | --- |
| Vị trí là phụ lục | 557 (5,7%) |
| `Phụ lục <n>` | 265 |
| `Phụ lục` | 292 |
| `Phụ lục`, còn `doi_tuong` (phần nêu bằng tên) | 150 |
| `Phụ lục`, không có `doi_tuong` (vị trí gốc đổi thành phụ lục) | 142 |
| `Phụ lục`, có `chi_tiet_vi_tri` | 101 |
| `Phụ lục`, có `target_matched_id` | 266 |
| `Phụ lục`, `doi_tuong_loai = thu_tuc_hanh_chinh` | 79 |
| `Phụ lục`, `source_path` bắt đầu bằng "Phụ lục" | 77 |

Bản ghi thật:

| Bản ghi | Câu trích (`evidence`) | `doi_tuong` hoặc `chi_tiet_vi_tri` | Vì sao không có ký hiệu |
| --- | --- | --- | --- |
| `685249_0` (lượt `fix9-H56`): `bai-bo` tới `1548/QĐ-UBND` | "Bãi bỏ 03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ tại Quyết định số 1548/QĐ-UBND …" | `doi_tuong` "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ" | Câu nêu thủ tục, không nêu phụ lục. |
| `intro_687577_0` (lượt `fix9-H56`): `sua-doi` tới `223/NQ-HĐND` | "… ĐIỀU CHỈNH NỘI DUNG TẠI PHỤ LỤC BAN HÀNH KÈM THEO NGHỊ QUYẾT SỐ 223/NQ-HĐND …" | — | Tên văn bản nêu "phụ lục" không ký hiệu. |
| `685398_10` (lượt `fix9-ho`): `thay-the` tới `733/QĐ-UBND` | "… Quy trình có số thứ tự 1, 2 … tại Mục I Phần D Phụ lục kèm theo Quyết định số 733/QĐ-UBND …" | `chi_tiet_vi_tri` "Phụ lục Mục I Phần D số thứ tự 1, 2; số thứ tự 1, 2" | Câu nêu "Phụ lục kèm theo" không ký hiệu. |
| `681557_174` (lượt `fix9-ho`): `thay-the` tới `34/2014/NĐ-CP` | "Thay thế Phụ lục danh sách xã, phường, thị trấn khu vực biên giới đất liền ban hành kèm theo Nghị định số 34/2014/NĐ-CP bằng Phụ lục I …" | `chi_tiet_vi_tri` "Phụ lục danh sách xã, phường, thị trấn khu vực biên giới đất liền" | Phụ lục của văn bản đích không có ký hiệu. "Phụ lục I" là phụ lục của văn bản nguồn. |
| `legal-changed-v4/697544_2`: `bo-sung` tới `17/2026/TT-BNNMT` | "Mẫu số 01 (Phụ lục ban hành kèm theo Thông tư số 17/2026/TT-BNNMT)" | — | Câu nêu "Phụ lục" không ký hiệu. Bản ghi có trong `-v4` hiện có. |

- Code không đọc ký hiệu từ câu trích. Câu trích có thể nêu ký hiệu phụ lục của văn bản nguồn (`681557_174`).
- Đo 27/10/2026 (cùng 2 lượt): 18/142 quan hệ không có `doi_tuong` có câu trích nêu đúng một ký hiệu phụ lục.
- Nếu bên Graph nối cạnh này như cạnh lên cả văn bản, đồ thị nói rộng hơn văn bản. `685249_0` bãi bỏ 3 thủ tục, không bãi bỏ Quyết định 1548/QĐ-UBND.

### Đề xuất

| # | Cách nối | Ưu | Nhược |
| --- | --- | --- | --- |
| A | Nối vào node văn bản đích. Cạnh giữ `vi_tri = ["Phụ lục"]`, `doi_tuong` và `chi_tiet_vi_tri`. Bên Graph không dùng cạnh này để tính hiệu lực của cả văn bản. | Không chọn sai phụ lục. Không cần cấu trúc của văn bản đích. | Cạnh không chỉ tới phụ lục. Bên đọc phải xem `vi_tri` để biết cạnh không chạm cả văn bản. |
| B | Văn bản đích có đúng một phụ lục thì nối vào node phụ lục đó. Các trường hợp khác dùng A. | Đúng node khi văn bản đích có một phụ lục. | Cần `phu_luc[]` của văn bản đích. Văn bản đích chưa có trong index thì không có `phu_luc[]`. |
| C | Nối vào mọi node phụ lục của văn bản đích. | Không cần chọn phụ lục. | Đồ thị nói rộng hơn văn bản: mọi phụ lục đều chịu tác động. |
| D | Tạo một node "phụ lục chưa rõ" cho mỗi văn bản đích và nối vào đó. | Tách cạnh vào phụ lục khỏi cạnh vào văn bản. | Thêm một loại node không có chunk. ID `<doc>_pl` không dùng được: `_pl` ở cuối ID là điểm `l` ([09, mục 9.9.2](09-hop-dong-du-lieu-v4.md#992-loại-chunk-và-id)). |

Bên dữ liệu đề xuất B, và A cho các trường hợp còn lại. Hai phương án này không làm cạnh rộng hơn văn bản.

Trong lúc chờ trả lời, dữ liệu giữ `vi_tri = ["Phụ lục"]`. Bên dữ liệu không suy ra ký hiệu phụ lục.

### Câu hỏi 3

1. Bên Graph chọn phương án nào: A, B, C hay D?
2. Với B: bên Graph đếm phụ lục của văn bản đích từ `legal-docs-v4.phu_luc`, hay từ index khác? Văn bản đích không có trong index thì bên Graph dùng A không?
3. 150/292 cạnh `Phụ lục` còn `doi_tuong`. Bên Graph có dùng `doi_tuong` như giới hạn trong node, giống `chi_tiet_vi_tri` ở mục 11.2 không?
4. Từ code `8b023ca`, bên dữ liệu ghi chữ vị trí gốc ở `chi_tiet_vi_tri` (101/292 cạnh `Phụ lục`). Bên Graph có dùng trường này cho cạnh vào phụ lục không?
