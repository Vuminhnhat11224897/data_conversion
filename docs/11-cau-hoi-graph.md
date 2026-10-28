# 11. Câu hỏi cho bên Graph: phạm vi của cạnh

Tài liệu này nêu 3 việc bên Graph cần chốt. Bên dữ liệu chưa đổi hợp đồng cho tới khi bên Graph trả lời. Mỗi việc có bản ghi thật và cách xử lý đề xuất. Ngày soạn: 21/10/2026. Cập nhật: 28/10/2026.

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

Đo trên `legal-changed-v4` sau lượt ghi ngày 22/10/2026 (11.000 văn bản): 274/42.771 quan hệ có phần không có node riêng (193 mẫu biểu; 77 dòng số thứ tự; 4 gạch đầu dòng, đoạn). Đếm 28/10/2026 (30.988 văn bản, mục 11.4): 3.646/75.506 quan hệ có `chi_tiet_vi_tri`, trong đó 3.574 quan hệ `validated`. Số theo từng loại phần: chưa đo.

| Bản ghi (kiểm 28/10/2026) | `scope` | `vi_tri` | `chi_tiet_vi_tri` | Tác động thật |
| --- | --- | --- | --- | --- |
| `legal-changed-v4/695211_3` (`thay-the` lên 05/2024/TT-BXD) | `Mẫu số 02 Phụ lục I` | `["Phụ lục I"]` | `Mẫu số 02` | 1 mẫu, không phải cả Phụ lục I |
| `legal-changed-v4/688385_83` (`bai-bo` lên 226/2025/NĐ-CP) | nhiều vị trí | `["điểm a khoản 4 Điều 7"]` | `gạch đầu dòng thứ 1` | 1 gạch đầu dòng, không phải cả điểm a |
| `legal-changed-v4/693748_0` (`bai-bo` lên 773/QĐ-UBND) | `Phụ lục I` | `["Phụ lục I"]` | `Mục A Phụ lục I; số thứ tự 06, 07` | 2 dòng của Mục A |

- `_id` quan hệ đổi khi chạy lại văn bản nguồn. Ngày 22/10/2026, hai ví dụ đầu có `_id` `695211_6`, `688385_160`.
- Ví dụ thứ ba ngày 22/10/2026 có `vi_tri = ["Mục A Phụ lục I"]`. Quy ước phụ lục đổi vị trí đó thành `Phụ lục I`.

Nếu bên Graph coi cạnh như tác động lên cả node, đồ thị nói rộng hơn văn bản.

Từ code `8b023ca` (27/10/2026), quy ước phụ lục cũng ghi chữ vị trí gốc vào `chi_tiet_vi_tri` ([09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục)). Ví dụ: `legal-changed-v4/692884_0` có `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri` "Mục II Phần B Phụ lục I" (kiểm 28/10/2026). Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (876 văn bản): 197/9.760 quan hệ `validated` có `chi_tiet_vi_tri`.

### Đề xuất

Trường mới `chi_tiet_vi_tri` (keyword). Trường đã có trong 3 index `-v4` từ ngày 21/10/2026. v3 chưa có.

- Có trường này: tác động chỉ chạm phần ghi trong trường, bên trong node `vi_tri`.
- Không có: tác động lên cả node `vi_tri`.

Ví dụ: `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri = "Mẫu số 01"`.

Quy tắc chung: khi giảm độ chi tiết của node để biểu diễn, giữ nguyên giới hạn của tác động pháp lý.

### Câu hỏi 2

1. Bên Graph đồng ý dùng `chi_tiet_vi_tri` như trên không?
2. Bên Graph hiện có tính trạng thái hiệu lực của node từ các cạnh loại này không? Nếu có mà không đọc `chi_tiet_vi_tri`, 3.574 quan hệ `validated` có trường này bị tính rộng hơn văn bản (28/10/2026).

## 11.3. Thông tin đã chốt, báo để bên Graph biết

| Thay đổi | Mục |
| --- | --- |
| `doi_tuong_loai`: `van_ban` hoặc `thu_tuc_hanh_chinh`. Cạnh lên thủ tục trỏ tới quyết định công bố thủ tục; tên thủ tục ở `doi_tuong`; mã ở `ma_thu_tuc`. | [09, mục 9.10.6](09-hop-dong-du-lieu-v4.md#9106-tác-động) |
| Quy ước phụ lục (người dùng chốt 26/10/2026, thu hẹp 27/10/2026): vị trí ngoài thân văn bản ghi là phụ lục chứa nó. Chữ vị trí gốc ghi ở `chi_tiet_vi_tri`. Phần nêu bằng tên thuộc phụ lục có `vi_tri` là phụ lục và giữ tên ở `doi_tuong`. Cạnh lên thủ tục có `vi_tri` là phụ lục chứa thủ tục. | [09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục) |
| Văn bản chỉ có tên trong ghi chú lịch sử, hoặc trong danh sách văn bản đi sau ghi chú đó, không là đích (26–27/10/2026). | [09, mục 9.10.7](09-hop-dong-du-lieu-v4.md#9107-trạng-thái-cạnh-và-nhánh-dò) |
| Quan hệ tên văn bản chỉ lấy từ tên in trong văn bản (Q11). | [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt) |
| `_id` quan hệ đổi khi chạy lại văn bản nguồn. Khi nhập lại, xóa cạnh cũ theo `source_id`, không theo `_id`. | [04, mục 4.8.2](04-hop-dong-du-lieu-v3.md#482-id) |
| Không có quan hệ lấy từ tên văn bản và lời dẫn (`intro_`, `hd_`) (R6, 27/10/2026). Quan hệ hướng dẫn chỉ có khi một Điều nêu văn bản được hướng dẫn. Thay V1, Q2. | [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt) |
| Một thay đổi có ở cả đơn vị cha và đơn vị con thì chỉ giữ cạnh của đơn vị con (R1, R2, 27/10/2026). | [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt) |
| Chunk `phu_luc_doan`, `muc_doan` là đoạn tìm kiếm, không là node. Node là chunk `phu_luc`, `muc` (`phu_luc_uid`, `muc_uid`). | [09](09-hop-dong-du-lieu-v4.md) |

## 11.4. Dữ liệu v4 để bên Graph kiểm

Trạng thái ngày 28/10/2026. Chi tiết ở [09, mục 9.1](09-hop-dong-du-lieu-v4.md#91-trạng-thái-v4). Dashboard số liệu: https://claude.ai/artifact/9sGL8D5ZSGcNLibgQwvMjQ (28/10/2026).

Đêm 27–28/10/2026, bên dữ liệu ghi 3 index `-v4` trên ES 10.1.10.23 bằng code `1117e63`. Lượt `v4-next20000` thêm 19.988 văn bản mới. Lượt `v4-2710` ghi lại 11.000 văn bản cũ. 7 văn bản cũ lỗi khi ghi lại, nên còn bản ghi 22/10/2026 (code `2911b77`): 679994, 682498, 685655, 686325, 694929, 694935, 696357.

| Index | Số bản ghi (đếm 28/10/2026) |
| --- | --- |
| `legal-docs-v4` | 30.988 văn bản, ban hành từ 12/03/2025 đến 30/09/2026 |
| `legal-chunk-section-v4` | 1.534.375 chunk, đủ vector |
| `legal-changed-v4` | 75.506 quan hệ trên 13.627 văn bản: 70.954 `validated`, 4.552 `unresolved` |

- Trong 75.506 quan hệ: 64.277 có `target_matched_id` (85,1%); 7.717 có `doi_tuong_loai = thu_tuc_hanh_chinh`; 3.646 có `chi_tiet_vi_tri`; 74.847 có `evidence`.
- Trường cũ `unresolved = true` có ở 2.147 quan hệ. Bên Graph đọc `resolution_status`, không đọc trường này.
- Kiểm toàn bộ quan hệ (28/10/2026): `source_*`, `cap_quan_he`, `hieu_luc_tac_dong` đúng 100%; `target_matched_id` đúng 99,99%; 205 dòng `thay-cum-tu` thiếu `cum_tu`. Kết quả `eval.check_contract v4` trên dữ liệu này: chưa đo.
- Chunk có thêm loại `phu_luc_doan` (377.099) và `muc_doan` (101.033). Hai loại này là đoạn tìm kiếm, không là node.
- Vector văn bản và chunk `-v4` không cắt đầu vào ở 256 token. v3 vẫn dùng vector 256 token.
- Chunk có 30.987 `doc_id` khác nhau (đếm chính xác 28/10/2026). 1 `doc_id` có chunk mà không có bản ghi văn bản: 672275 (1.500 chunk), một trong 10 văn bản mới lỗi. 2 văn bản không có chunk: 682498, 685655, thuộc 7 văn bản ghi lại lỗi. Nguyên nhân: lượt ghi xóa chunk cũ trước, rồi lỗi giữa chừng.
- v3: không ghi lại toàn bộ. Hai ngoại lệ có người dùng duyệt: văn bản 132140 (15/10/2026) và 32 văn bản của bộ 88 testcase (27/10/2026). v3 có 236 văn bản (28/10/2026).

Từ 28/10/2026, `-v4` có hai thay đổi chính của code 26–27/10/2026:

| Thay đổi | Ảnh hưởng tới cạnh | Mục |
| --- | --- | --- |
| Quy ước phụ lục | Vị trí ngoài thân văn bản thành phụ lục; chữ gốc ghi ở `chi_tiet_vi_tri`. Phần nêu bằng tên thuộc phụ lục (thủ tục, danh mục, biểu mẫu, dòng của danh mục) có `vi_tri` là phụ lục và `cap_quan_he = vi_tri`. Ví dụ: `694022_0` có `vi_tri = ["Phụ lục 1"]` (kiểm 28/10/2026). | [09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục) |
| Ghi chú lịch sử phủ cả danh sách | Văn bản chỉ có tên trong danh sách sau ghi chú lịch sử không là đích. Ví dụ: 675210 không còn quan hệ tới `89/2025/QH15` (kiểm 28/10/2026). | [09, mục 9.10.7](09-hop-dong-du-lieu-v4.md#9107-trạng-thái-cạnh-và-nhánh-dò) |

- Đợt tiếp theo chưa có lệnh chạy.

Chất lượng quan hệ (docs 05, mục 5.4.3; docs 08, mục 8.14, 8.15, 8.17):

| Dữ liệu | Bộ đo, ngày đo | Phát hiện P / R | Phạm vi P / R | Ghi chú |
| --- | --- | --- | --- | --- |
| `-v4` hiện có (code `1117e63`) | Mẫu 2.000 văn bản của đợt 20.000, 28/10/2026, có trọng số | 0,901 / 0,804 | 0,785 / 0,695 | Độc lập. Nhãn agent đã khóa, chưa qua người duyệt. |
| `-v4` ngày 22/10 (code `2911b77`) | H5 + H6, 500 văn bản, 22/10/2026, bộ chấm cũ | 0,890 / 0,873 | 0,785 / 0,743 | Đã dùng để sửa lỗi. Không độc lập. |
| Code `8b023ca` | H5 + H6, 27/10/2026, bộ chấm 27/10 | 0,895 / 0,873 | 0,833 / 0,773 | Không độc lập. |
| Code `8b023ca` | Hold-out 300, 27/10/2026, bộ chấm 27/10 | 0,900 / 0,861 | 0,711 / 0,673 | Độc lập. Nhãn do agent gán, chưa qua người duyệt. Bỏ văn bản 675259. |

- Phát hiện: đúng văn bản nguồn, hành động, văn bản đích. Phạm vi: đúng thêm vị trí bị tác động.
- Bộ chấm từ 27/10 áp quy ước phụ lục như code. Số đo theo hai bộ chấm không so trực tiếp được.
- Trên văn bản chưa từng xem, phạm vi thấp hơn rõ: R 0,695 ở đợt 20.000, R 0,673 ở hold-out 300.
- Lỗi thật tìm thấy khi chấm đợt 20.000 ở [07, mục 7.2](07-gioi-han-va-can-chot.md#72-lỗi-dữ-liệu-đã-biết). Một lỗi chạm cách nối cạnh: đích trùng số hiệu sau sáp nhập tỉnh (679575).

## 11.5. Kiểm thử bên Graph cần chạy

1. Một cạnh tra cứu (`relation_only`) không làm đổi trạng thái hiệu lực của node nào.
2. Một cạnh có `chi_tiet_vi_tri` không làm node `vi_tri` mất hiệu lực toàn bộ.
3. Nhập lại một văn bản nguồn không để lại cạnh cũ khi `_id` đổi.
4. Một cạnh có `vi_tri = ["Phụ lục"]` không làm văn bản đích mất hiệu lực toàn bộ (mục 11.6).

## 11.6. Việc 3: cạnh vào phụ lục không nêu ký hiệu

### Hiện trạng

Quy ước phụ lục ([09, mục 9.5.1](09-hop-dong-du-lieu-v4.md#951-quy-ước-phụ-lục), từ code `8b023ca`, có trong `-v4` từ 28/10/2026): phần ngoài thân văn bản có vị trí là phụ lục chứa nó. Chữ vị trí gốc ghi ở `chi_tiet_vi_tri`.

| Vị trí | Khi nào | Node đích |
| --- | --- | --- |
| `Phụ lục <n>` | Chữ nêu đúng một ký hiệu phụ lục | `<doc>_pl<i>` với `phu_luc[i].ky_hieu = <n>` |
| `Phụ lục` | Chữ không nêu ký hiệu, hoặc nêu từ hai ký hiệu trở lên | Chưa có node xác định |

Số quan hệ `validated` theo nhóm. Cột `-v4`: đếm 28/10/2026 trên `legal-changed-v4` (code `1117e63`). Cột `fix9-*`: đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (876 văn bản, code `8b023ca`).

| Nhóm | `-v4` (28/10/2026) | `fix9-*` (27/10/2026) |
| --- | --- | --- |
| Quan hệ `validated` | 70.954 | 9.760 |
| Vị trí là phụ lục | 14.911 (21,0%) | 557 (5,7%) |
| `Phụ lục <n>` | 3.921 | 265 |
| `Phụ lục` | 10.990 (15,5%) | 292 (3,0%) |
| `Phụ lục`, còn `doi_tuong` (phần nêu bằng tên) | 7.904 | 150 |
| `Phụ lục`, không có `doi_tuong` (vị trí gốc đổi thành phụ lục) | 3.086 | 142 |
| `Phụ lục`, có `chi_tiet_vi_tri` | 2.413 | 101 |
| `Phụ lục`, có `target_matched_id` | 9.188 | 266 |
| `Phụ lục`, `doi_tuong_loai = thu_tuc_hanh_chinh` | 6.808 | 79 |
| `Phụ lục`, `source_path` bắt đầu bằng "Phụ lục" | 4.151 | 77 |

- Ở `-v4`, nhóm `Phụ lục` có ở 3.550 văn bản nguồn. Văn bản 658621 có 423 cạnh loại này.
- Phần lớn cạnh `Phụ lục` ở `-v4` là cạnh lên thủ tục hành chính (6.808/10.990). Ở lượt `fix9-*`, cạnh thủ tục chỉ chiếm 79/292.

Bản ghi thật:

| Bản ghi | Câu trích (`evidence`) | `doi_tuong` hoặc `chi_tiet_vi_tri` | Vì sao không có ký hiệu |
| --- | --- | --- | --- |
| `legal-changed-v4/685249_0`: `bai-bo` tới `1548/QĐ-UBND` | "Bãi bỏ 03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ tại Quyết định số 1548/QĐ-UBND …" | `doi_tuong` "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ" | Câu nêu thủ tục, không nêu phụ lục. |
| `legal-changed-v4/685398_9`: `thay-the` tới `733/QĐ-UBND` | "Thay thế các quy trình nội bộ giải quyết thủ tục hành chính tại Quyết định số 733/QĐ-UBND ngày 23/4/2025;" | `chi_tiet_vi_tri` "Phụ lục Mục I Phần D số thứ tự 1, 2; số thứ tự 1, 2" | Chữ gốc nêu "Phụ lục Mục I Phần D", không có ký hiệu phụ lục. |
| `legal-changed-v4/681557_130`: `thay-the` tới `34/2014/NĐ-CP` | "Thay thế Phụ lục danh sách xã, phường, thị trấn khu vực biên giới đất liền ban hành kèm theo Nghị định số 34/2014/NĐ-CP bằng Phụ lục I …" | `chi_tiet_vi_tri` "Phụ lục danh sách xã, phường, thị trấn khu vực biên giới đất liền" | Phụ lục của văn bản đích không có ký hiệu. "Phụ lục I" là phụ lục của văn bản nguồn. |
| `legal-changed-v4/697544_2`: `bo-sung` tới `17/2026/TT-BNNMT` | "Mẫu số 01 (Phụ lục ban hành kèm theo Thông tư số 17/2026/TT-BNNMT)" | — | Câu nêu "Phụ lục" không ký hiệu. |

- Bản ghi trên kiểm ngày 28/10/2026. Ngày 27/10/2026, `685398_9` và `681557_130` có `_id` `685398_10` và `681557_174` (lượt `fix9-ho`).
- Bản 27/10/2026 của bảng có `intro_687577_0` (tên văn bản nêu "phụ lục" không ký hiệu). Code `1117e63` không ghi quan hệ từ tên văn bản (R6), nên bản ghi này không còn.

- Code không đọc ký hiệu từ câu trích. Câu trích có thể nêu ký hiệu phụ lục của văn bản nguồn (`681557_174`).
- Đo 27/10/2026 trên lượt `fix9-*`: 18/142 quan hệ không có `doi_tuong` có câu trích nêu đúng một ký hiệu phụ lục. Trên `-v4`: chưa đo.
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
3. 7.904/10.990 cạnh `Phụ lục` của `-v4` còn `doi_tuong` (28/10/2026). Bên Graph có dùng `doi_tuong` như giới hạn trong node, giống `chi_tiet_vi_tri` ở mục 11.2 không?
4. Từ code `8b023ca`, bên dữ liệu ghi chữ vị trí gốc ở `chi_tiet_vi_tri` (2.413/10.990 cạnh `Phụ lục` của `-v4`, 28/10/2026). Bên Graph có dùng trường này cho cạnh vào phụ lục không?
