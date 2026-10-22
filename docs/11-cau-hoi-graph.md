# 11. Câu hỏi cho bên Graph: phạm vi của cạnh

Tài liệu này nêu 2 việc bên Graph cần chốt. Bên dữ liệu chưa đổi hợp đồng cho tới khi bên Graph trả lời. Mỗi việc có bản ghi thật và cách xử lý đề xuất. Ngày soạn: 21/10/2026.

- Hợp đồng hiện hành: [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md), mục 9.10.7 (trạng thái cạnh) và 9.11 (cách nối).
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

### Đề xuất

Trường mới `chi_tiet_vi_tri` (keyword). Trường đã có trong 3 index `-v4` (lượt ghi thử ngày 21/10/2026). v3 chưa có.

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
| Quan hệ tên văn bản chỉ lấy từ tên in trong văn bản (Q11). | [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt) |
| `_id` quan hệ đổi khi chạy lại văn bản nguồn. Khi nhập lại, xóa cạnh cũ theo `source_id`, không theo `_id`. | [04, mục 4.8.2](04-hop-dong-du-lieu-v3.md#482-id) |

## 11.4. Dữ liệu v4 để bên Graph kiểm

Ngày 22/10/2026, 3 index `-v4` trên ES 10.1.10.23 được ghi lại bằng code chốt (commit `2911b77`, docs 08 mục 8.15):

| Index | Số bản ghi |
| --- | --- |
| `legal-docs-v4` | 11.000 văn bản mới nhất, ban hành từ 08/10/2025 đến 30/09/2026 |
| `legal-chunk-section-v4` | 447.597 chunk |
| `legal-changed-v4` | 42.771 quan hệ: 40.496 `validated`, 2.275 `unresolved` |

Trong 42.771 quan hệ: 37.182 có `target_matched_id`; 1.819 có `doi_tuong_loai = thu_tuc_hanh_chinh`; 274 có `chi_tiet_vi_tri`. Kiểm hợp đồng (`eval.check_contract v4`): 237 luật, 5 luật có lỗi nhỏ về đọc cấu trúc, mỗi luật dưới 1% số bản ghi (docs 08, mục 8.11.8). v3 không đổi.

Chất lượng quan hệ, đo trên mẫu phân tầng 500 văn bản của 11.000 văn bản này (docs 08, mục 8.13–8.14):

| Mức | P | R |
| --- | --- | --- |
| Phát hiện: đúng văn bản nguồn, hành động, văn bản đích | 0,890 | 0,873 |
| Phạm vi: đúng thêm vị trí bị tác động | 0,785 | 0,743 |

Mẫu này đã được dùng để sửa lỗi, nên trên văn bản chưa từng xem, số đo có thể thấp hơn.

## 11.5. Kiểm thử bên Graph cần chạy

1. Một cạnh tra cứu (`relation_only`) không làm đổi trạng thái hiệu lực của node nào.
2. Một cạnh có `chi_tiet_vi_tri` không làm node `vi_tri` mất hiệu lực toàn bộ.
3. Nhập lại một văn bản nguồn không để lại cạnh cũ khi `_id` đổi.
