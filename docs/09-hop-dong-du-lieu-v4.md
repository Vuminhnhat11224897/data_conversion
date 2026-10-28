# 9. Hợp đồng dữ liệu v4

Tài liệu này là hợp đồng dữ liệu của 3 index v4 trên ES đích `10.1.10.23`. Bên dữ liệu ghi các index này bằng công cụ `vbpl_v3`. Bên Graph và bên tìm kiếm đọc các index này.

- Hợp đồng mô tả dữ liệu mà lệnh `convert` ghi ở chế độ `llm` (mặc định), code chốt commit `8b023ca` (27/10/2026).
- Index `-v4` hiện có ghi bằng code `2911b77` (22/10/2026). Dữ liệu đó chưa theo một số quy tắc của hợp đồng. Mục 9.1 nêu các điểm này.
- Nguyên tắc chung: **chỉ lưu tác động mà văn bản nêu trực tiếp. Không suy ra tác động mà văn bản không nói.**
- Cột "Đo 21/10" là số đo ngày 21/10/2026 trên 1.000 văn bản ghi đầu tiên (code `013e897`). Các số này chưa đo lại trên 11.000 văn bản. Số đo trên 11.000 văn bản ở mục 9.1 và 9.12 (đo 22/10/2026).
- Ví dụ viết dạng `<index>/<_id>`, hoặc chỉ `_id` khi index đã rõ. Ví dụ không ghi lượt là bản ghi có trong index `-v4`; kiểm lại ngày 27/10/2026.
- Ví dụ ghi "lượt `<tên>`" lấy từ lượt chạy thử bằng code `8b023ca`, chưa ghi ES. Kết quả ở `work/<tên>/dry-run/<doc>.json`.
- Nghĩa của giá trị enum ở [06-bang-enum.md](06-bang-enum.md). Cách công cụ tạo dữ liệu ở [02-luong-hoat-dong.md](02-luong-hoat-dong.md). Luồng 4 tầng và cách đánh giá ở [08](08-quan-he-4-tang-va-danh-gia.md).

## 9.1. Trạng thái v4

| Index | Số bản ghi (đo 22/10/2026) |
| --- | --- |
| `legal-docs-v4` | 11.000 |
| `legal-chunk-section-v4` | 447.597 |
| `legal-changed-v4` | 42.771: 40.496 `validated`, 2.275 `unresolved` |

- **Phạm vi.** 11.000 văn bản mới nhất theo `issuance_date` của `legal-docs` nguồn. Ngày ban hành từ `2025-10-08` đến `2026-09-30`. Danh sách: `work/v4-2210-ids.txt`.
- **Code ghi.** Code chốt `2911b77` (22/10/2026). Đếm ngày 27/10/2026: số bản ghi của 3 index bằng số ở bảng trên. Dữ liệu chưa có thay đổi code ngày 26–27/10/2026.
- **Lượt ghi.** `ingest_job_id` cho biết lượt đã ghi văn bản:

| `ingest_job_id` | Lượt | Số văn bản |
| --- | --- | --- |
| `v3:20261022T044254Z` | `v4-2210` | 10.975 |
| `v3:20261022T083345Z` | `v4-2210-fix`: 25 văn bản hết thời gian kết nối ở lượt chính | 25 |

- **Vector.** Ngày 26/10/2026, bên dữ liệu tạo lại `embedding` của 11.000 văn bản và 447.597 chunk. Vector mới dùng toàn bộ đầu vào, không cắt ở 256 token. Các trường khác không đổi.
- **Kiểm hợp đồng.** Lệnh `python -m eval.check_contract v4` kiểm 237 quy tắc (22/10/2026). 5 quy tắc có lỗi (mục 9.12). Kết quả: `work/v4-2210-contract.txt`.
- **Đợt tiếp theo.** `work/v4-next10000b-ids.txt` có 10.200 ID (10.000 và 200 dự phòng), ban hành 25/06/2025–08/10/2025. Đợt này chưa chạy. Người dùng chưa quyết có ghi lại 11.000 văn bản hiện có bằng code `8b023ca` hay không.
- **Đánh giá theo đợt.** Mỗi đợt 10.000 văn bản mới có một mẫu 1.000 văn bản để gán nhãn và chấm (`python -m eval.sample_batch`, `eval/README.md`).
- **Duyệt.** Bên Graph duyệt v4. Sau khi duyệt, bên dữ liệu ghi lại v3 theo hợp đồng này, chỉ đổi hậu tố `-v4` thành `-v3`. Các bước ở [02, "Ghi thử vào v4"](02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3).

**Dữ liệu `-v4` hiện có khác hợp đồng ở các điểm sau.** Lệnh `convert` với code `8b023ca` ghi theo cột "Hợp đồng".

| Điểm | Hợp đồng (code `8b023ca`) | Dữ liệu `-v4` hiện có (code `2911b77`) | Ví dụ |
| --- | --- | --- | --- |
| Quy ước phụ lục (mục 9.5.1) | Vị trí ngoài thân văn bản thành `Phụ lục <n>` hoặc `Phụ lục`. Chữ vị trí gốc ghi ở `chi_tiet_vi_tri`. Phần nêu bằng tên thuộc phụ lục có `vi_tri` là phụ lục và `cap_quan_he = vi_tri`. | Vị trí giữ chữ của câu nguồn (`Mục I`). Phần nêu bằng tên có `vi_tri` rỗng, `cap_quan_he` là `noi_dung` hoặc `van_ban_kem_theo`. | `694022_0`: `-v4` có `vi_tri = []`, `cap_quan_he = van_ban_kem_theo`. Lượt `fix9-H56` có `vi_tri = ["Phụ lục 1"]`, `cap_quan_he = vi_tri`. |
| Ghi chú lịch sử (mục 9.10.7) | Văn bản chỉ có tên trong ghi chú lịch sử, hoặc trong danh sách văn bản đi sau ghi chú đó, không là đích. Luật này áp cho cả hai nhánh, trên toàn văn đơn vị. | Tầng kiểm chỉ xét 80 ký tự sau ghi chú. Nhánh quy tắc không xét ghi chú lịch sử. Văn bản ở cuối danh sách dài có thể là đích sai. | `675210_28`: `sua-doi` tới `89/2025/QH15`. Câu nguồn chỉ nêu luật này trong ghi chú lịch sử. Lượt `fix9-ho` không có quan hệ này. |
| Vector | `embedding` cắt đầu vào ở 256 token (mục 9.9). Văn bản chép vector của nguồn (mục 9.8.2). | Vector tạo lại ngày 26/10/2026 từ toàn bộ đầu vào. Vector văn bản là vector của `title`. | — |

Bên Graph dùng dữ liệu hiện có để kiểm cấu trúc và cách nối. Khi ghi lại bằng code `8b023ca`, các quan hệ ở 2 dòng đầu đổi theo cột "Hợp đồng". Lệnh `convert` cũng ghi đè vector theo dòng thứ ba.

## 9.2. Luồng tạo dữ liệu

```mermaid
flowchart LR
  S["ES nguồn: legal-docs/&lt;id&gt;"] --> T1["Tầng 1: cấu trúc"]
  T1 --> D["legal-docs-v4"]
  T1 --> C["legal-chunk-section-v4"]
  T1 --> R["Nhánh quy tắc"]
  T1 --> L["Nhánh LLM: tầng 2, 3, 4"]
  R --> G["Gộp, quy ước phụ lục, chuẩn hóa vị trí, cấp quan hệ"]
  L --> G
  G --> Q["legal-changed-v4"]
```

| Bản ghi | Công cụ lấy từ | Cách tạo | Bước ở [02, mục 2.4](02-luong-hoat-dong.md#24-luồng-một-văn-bản) |
| --- | --- | --- | --- |
| Văn bản | `legal-docs/<id>` nguồn | Chép metadata. Tách cấu trúc. Tính địa vị pháp lý và thời điểm hiệu lực bằng quy tắc. | 1–4 |
| Chunk | Cấu trúc của văn bản | Một chunk cho mỗi Điều, khoản, điểm, tiểu điểm, phụ lục, đề mục, đoạn. Gắn dẫn chiếu, ngày hiệu lực, vector. | 5, 7, 8 |
| Quan hệ | Câu chữ của văn bản | Nhánh LLM và nhánh quy tắc cùng dò. Công cụ gộp hai nhánh, nối văn bản đích, tách một vị trí một quan hệ. | 6, 9–12 |

Quan hệ đi qua các bước sau, theo thứ tự. Chi tiết ở [02, mục 2.5.8](02-luong-hoat-dong.md#258-nhánh-llm-4-tầng-và-gộp).

| # | Bước | Code |
| --- | --- | --- |
| 1 | Nhánh quy tắc tìm ứng viên bằng regex. QA (model LLM) giữ ứng viên có căn cứ. | `relations.detect`, `qa.verify` |
| 2 | Tầng 2: LLM đọc các đơn vị có tín hiệu, gom theo Điều. LLM ghi hành động, đích, phạm vi và câu trích. | `extract.extract` |
| 3 | Đơn vị nêu từ 8 văn bản trở lên: công cụ hỏi LLM theo phần. Văn bản nằm trong chữ của đơn vị hoặc trong danh sách kèm theo. Mỗi phần có 5 văn bản và giữ lời dẫn của đơn vị. | `extract.list_parts`, `LIST_MIN`, `LIST_PART` |
| 4 | Mỗi phần mang toàn văn đơn vị ở khóa `_noi_dung_goc`. Công cụ không gửi khóa bắt đầu bằng `_` cho LLM. | `extract.list_parts` |
| 5 | Tầng 3: code đổi chữ LLM đọc thành đích, vị trí, `doi_tuong`. | `resolver` |
| 6 | Tầng 4: code kiểm từng hàng với câu nguồn. Hàng bị loại không ghi ES. Lý do loại ghi ở `work/<run>/extract/<doc>/rejected.json`. | `validate.check` |
| 7 | Tầng 4 kiểm ghi chú lịch sử trên toàn văn đơn vị (`_noi_dung_goc`), không chỉ trên phần LLM đọc. Câu lấy từ phần bị cắt là câu của chính đơn vị. | `validate.only_noted` |
| 8 | Công cụ bỏ quan hệ của nhánh quy tắc có đích chỉ nằm trong ghi chú lịch sử. Bước này chạy sau QA. | `convert.model_relations`, `validate.only_in_history` |
| 9 | Công cụ gộp hai nhánh theo đơn vị nguồn, hành động và văn bản đích. | `convert.model_relations` |
| 10 | Công cụ áp quy ước phụ lục (mục 9.5.1) lần thứ nhất, cho quan hệ của cả hai nhánh. | `resolver.appendix_scope` |
| 11 | Công cụ thêm quan hệ hướng dẫn (`hd_`) và hợp nhất (`hn_`). Các quan hệ này không qua bước 10. | `references.guidance`, `relations.consolidation` |
| 12 | Quan hệ chưa có `vi_tri` nhận vị trí đọc từ `scope`. | `convert.convert_document` |
| 13 | Vị trí ngoài định dạng chuyển sang `doi_tuong`. Dòng "số thứ tự" của danh mục nhận phụ lục chứa dòng. | `convert.tidy_positions` |
| 14 | Công cụ áp quy ước phụ lục lần thứ hai, cho mọi quan hệ. Lần này phủ vị trí và `doi_tuong` ghi ở bước 12–13, và `cum_tu[].vi_tri`. Áp lại không đổi kết quả của bước 10. | `convert.tidy_positions(appendix=True)`, `resolver.appendix_scope` |
| 15 | Cùng đơn vị nguồn, hành động và văn bản đích: công cụ bỏ vị trí cha, giữ vị trí con. | `convert.tidy_positions` |
| 16 | Công cụ tách một vị trí một quan hệ. Cặp cụm từ nêu vị trí riêng thì vị trí của cặp là vị trí của quan hệ. Chữ vị trí gốc của bước 10 và 14 ghi vào `chi_tiet_vi_tri`. | `convert.one_per_position` |
| 17 | Công cụ tính `cap_quan_he`, `resolution_status` (mục 9.10.7, 9.10.8). | `convert.settle` |

Bước 14 chỉ chạy ở chế độ `llm`.

- Công cụ ghi theo thứ tự: chunk, văn bản, quan hệ.
- Khi ghi lại một văn bản, công cụ xóa chunk và quan hệ cũ của văn bản đó. Chunk khớp theo `doc_id`. Quan hệ khớp theo `source_id`. Sau đó công cụ ghi bản ghi mới.
- Văn bản hợp nhất không qua nhánh LLM. Quan hệ duy nhất của văn bản hợp nhất là `hop-nhat`.

## 9.3. Phạm vi và quy ước

| Index | Một bản ghi là | Số bản ghi (đo 22/10/2026) | Mẫu `_id` |
| --- | --- | --- | --- |
| `legal-docs-v4` | Một văn bản | 11.000 | `<doc>`, bằng `_id` ở `legal-docs` nguồn. Ví dụ: `694952`. |
| `legal-chunk-section-v4` | Một chunk | 447.597 | `<doc>_<đơn vị>`. Ví dụ: `694952_d1_k3_pa`. |
| `legal-changed-v4` | Một quan hệ | 42.771 | `[<tiền tố>]<source_id>_<n>`. Ví dụ: `694952_4`. |

Quy tắc chung:

1. Trường ghi "Luôn" hoặc "Mọi …" có ở mọi bản ghi. Trường ghi "Có khi X" có khi X đúng và thiếu khi X sai.
2. Bên đọc chỉ dùng trường có trong hợp đồng. Đo 22/10/2026: không bản ghi nào có trường ngoài hợp đồng.
3. Mapping cho phép ES tự thêm trường. Công cụ không ghi trường ngoài hợp đồng.
4. Mapping `legal-changed-v4` có trường `inherited_from_v1`. Dữ liệu không có trường này. Không dùng trường này.
5. Vector có 1.024 chiều, model `BAAI/bge-m3`. `legal-changed-v4` không có vector.

| Ký hiệu | Nghĩa |
| --- | --- |
| Có khi X | Trường có khi X đúng. Trường thiếu khi X sai. |
| `null` | Trường có. Giá trị là `null`. |
| Rỗng | Giá trị là `""` hoặc `[]`. |
| Ngày | Chuỗi `YYYY-MM-DD` hợp lệ. |
| Thời điểm | Chuỗi ISO 8601 có múi giờ. |
| A ⇔ B | A đúng khi và chỉ khi B đúng. |

## 9.4. Khóa nối

| Từ | Đến | Quy tắc | Đo 21/10 | Ví dụ |
| --- | --- | --- | --- | --- |
| chunk `doc_id` | văn bản `_id` | Mọi chunk thuộc một văn bản có trong `legal-docs-v4`. Mọi văn bản có ít nhất một chunk. | Đúng cả hai | `694952_d1_k3_pa` → `694952` |
| chunk `dieu_uid`, `khoan_uid`, `diem_uid` | node Điều, khoản, điểm | Các trường này gom chunk con với đơn vị chứa nó. `_id` của chunk bắt đầu bằng `dieu_uid`. | — | `694952_d1_k3_pa`: `dieu_uid = 694952_d1`, `khoan_uid = 694952_d1_k3` |
| quan hệ `source_id` | văn bản `_id` | Văn bản nguồn luôn có trong `legal-docs-v4`. `source_id` là số nguyên. `_id` là chuỗi. | Đúng | `694952_4` → `694952` |
| quan hệ `target_matched_id` | `legal-docs._id` nguồn | Văn bản đích có trong v4 chỉ khi văn bản đó nằm trong 11.000 văn bản của mục 9.1. | Trên 1.000 văn bản: 3.193 quan hệ có đích, 716 đích khác nhau, 10 quan hệ có đích trong v4. Đo 22/10/2026 trên 11.000 văn bản: 37.182 quan hệ có đích. | `694952_4` → `legal-docs/643741` |
| chunk `dan_chieu[].target_id` | `legal-docs._id` nguồn | Như `target_matched_id`. `null` khi công cụ chưa nối được. | 1.395/6.469 dẫn chiếu `ngoai`, `van_ban_bi_sua` có `null` | `697023_d22_k3` → `legal-docs/657421` |

## 9.5. Vị trí

Các trường `vi_tri`, `cum_tu[].vi_tri`, `dan_chieu[].vi_tri`, `hoi_to_vi_tri` và `hieu_luc_rieng[].vi_tri` dùng định dạng này. Vị trí thuộc văn bản đích, văn bản được dẫn chiếu, hoặc chính văn bản (`hoi_to_vi_tri`, `hieu_luc_rieng`).

Cột "Quy ước phụ lục" cho biết bước 10 và 14 ở mục 9.2 làm gì với dạng đó (mục 9.5.1).

| Dạng | Nghĩa | Quy ước phụ lục | Ví dụ (`legal-changed-v4`) |
| --- | --- | --- | --- |
| `Điều <x>` | Cả Điều | Giữ | `Điều 18` (`697543_4`), `Điều 36a` (`697023_79`) |
| `khoản <y> Điều <x>` | Cả khoản | Giữ | `khoản 3 Điều 39` (`900000015_14`), `khoản 1b Điều 4` (`hidden_696341_0`) |
| `điểm <z> khoản <y> Điều <x>` | Cả điểm | Giữ | `điểm a khoản 1 Điều 8` (`694952_4`), `điểm đ1 khoản 3 Điều 4` (`697025_9`), `điểm 2.2 khoản 2 Điều 3` (`693628_7`) |
| `tiểu điểm <n> điểm <z> khoản <y> Điều <x>` | Mục gạch đầu dòng thứ `n` của một điểm | Giữ | `tiểu điểm 3 điểm b khoản 6 Điều 37` (`697176_24`) |
| `tên Điều <x>` | Chỉ tên Điều. Nội dung Điều giữ nguyên. | Giữ | `tên Điều 7` (`694599_35`) |
| `tên Chương <c>` | Chỉ tên Chương | Giữ | `tên Chương II` (`694501_126`) |
| `Chương <c>` | Cả Chương | Giữ | `Chương I` (`672539_6`) |
| `tên Mục <n> Chương <c>` | Chỉ tên Mục của một Chương | Giữ | — |
| `Mục <n> Chương <c>` | Cả Mục của một Chương | Giữ | `Mục 6 Chương II` (`694149_54`) |
| `Phụ lục <ký hiệu>` | Phụ lục có ký hiệu đó | Kết quả của quy ước | `Phụ lục II` (`696878_0`) |
| `Phụ lục` | Phụ lục. Câu nguồn không nêu ký hiệu, hoặc nêu nhiều ký hiệu. | Kết quả của quy ước | `Phụ lục` (`697544_2`) |
| `tên Mục <n>` | Chỉ tên Mục. Câu không nêu Chương chứa Mục. | Giữ khi `<n>` là số Ả Rập | `tên Mục 1` (`694501_127`) |
| `Mục <n>` | Cả Mục. Câu không nêu Chương chứa Mục. | Đổi thành `Phụ lục`. Chữ gốc ở `chi_tiet_vi_tri`. | `Mục I` (`693608_0`) |
| `Mục <ký hiệu> Phụ lục [<ký hiệu>]`, `Mục <ký hiệu> Phần <ký hiệu> Phụ lục [<ký hiệu>]` | Mục, Phần của một phụ lục | Đổi thành `Phụ lục <ký hiệu>`, hoặc `Phụ lục` khi không có ký hiệu. Chữ gốc ở `chi_tiet_vi_tri`. | `Mục A Phụ lục I` (`696025_0`), `Mục A Phần I Phụ lục I` (`697544_0`) |
| `tên văn bản` | Chỉ tên văn bản | Giữ | `694149_152` |
| `toàn bộ` | Cả văn bản | Giữ | `697547_0` |

Code `8b023ca` không ghi dạng có cột "Đổi …". Dữ liệu `-v4` hiện có (code `2911b77`) còn các dạng này (mục 9.1).

Thành phần:

- `<x>`, `<y>`: số, có thể kèm một chữ thường. Ví dụ: `36a`, `1b`.
- `<z>`: chữ cái, có thể kèm số (`a`, `đ`, `đ1`, `b1`), hoặc số thập phân (`2.2`).
- `<c>`: số La Mã hoặc số (`II`, `1`). Công cụ ghi đúng như văn bản đích viết.
- `tiểu điểm`, `khoản`, `điểm`, `tên` viết thường. `Điều`, `Chương`, `Mục`, `Phần`, `Phụ lục` viết hoa chữ đầu.

Quy tắc:

1. Một quan hệ có một vị trí. Câu "khoản 2, 3, 4 Điều 7" cho 3 quan hệ: `khoản 2 Điều 7`, `khoản 3 Điều 7`, `khoản 4 Điều 7`.
2. Câu "điểm a và điểm b khoản 2 Điều 11" cho `điểm a khoản 2 Điều 11` và `điểm b khoản 2 Điều 11`. Điểm trước nhận khoản và Điều của điểm sau.
3. Gạch đầu dòng của khoản hoặc của Điều, câu, đoạn không có node. Vị trí dừng ở khoản hoặc Điều chứa nó. Câu "đoạn 3, điểm a, khoản 2, Điều 4" cho `điểm a khoản 2 Điều 4`.
4. Gạch đầu dòng của một điểm là tiểu điểm. Câu "gạch đầu dòng thứ 3 điểm b khoản 6" cho `tiểu điểm 3 điểm b khoản 6 Điều 37` (`697176_24`).
5. Tiết hoặc mục số La Mã bên trong một Điều không có node. Câu "điểm b tiết 3.5, mục III, Điều 1" cho `Điều 1`.
6. Mẫu biểu nằm ở phụ lục chứa nó. Câu "Mẫu số 04 Phụ lục I" cho `Phụ lục I`. Tên mẫu nằm ở `chi_tiet_vi_tri` (mục 9.10.6).
7. Một dòng "số thứ tự N" của danh mục hoặc bảng không có node. Vị trí là phụ lục chứa danh mục. Câu chỉ nêu danh mục bằng tên thì `vi_tri` là phụ lục và `doi_tuong` là tên danh mục (mục 9.5.1).
8. Câu nêu Mục mà câu dẫn nêu đúng một phụ lục ("Sửa đổi, bổ sung Phụ lục III …: 2. Bổ sung Mục 6") cho Mục 6 của Phụ lục III. Theo quy ước phụ lục, vị trí là `Phụ lục III` và `chi_tiet_vi_tri` là "Mục 6 Phụ lục III".
9. Vị trí nằm sau số hiệu văn bản đích là một phần tên của văn bản đó. Câu "thay thế Quyết định số 42/2018/QĐ-UBND … sửa đổi Điểm a, Khoản 2 Điều 3 …" cho `toàn bộ`.
10. Công cụ đổi `Tên Điều` thành `tên Điều` và `Phụ lục số 07` thành `Phụ lục 07`.
11. Vị trí không theo định dạng này là tên của một phần. Ở bước 13, công cụ chuyển vị trí đó sang `doi_tuong` (mục 9.10.6). Bước 14 xét `doi_tuong` đó theo quy ước phụ lục.
12. Cùng đơn vị nguồn, hành động và văn bản đích thì không có cả vị trí cha lẫn vị trí con. Công cụ giữ vị trí con. Câu "Sửa đổi điểm a, khoản 16 Điều 2" cho `điểm a khoản 16 Điều 2`, không cho `khoản 16 Điều 2`.

Đo 22/10/2026 trên `-v4` (code `2911b77`, chưa có quy ước phụ lục): 198/38.323 vị trí ngoài định dạng của `eval.check_contract` (`work/v4-2210-contract.txt`). Ví dụ: `Mục I` (`693608_0`). Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (code `8b023ca`): 0/9.906 vị trí. Mục 9.12, dòng 10.

### 9.5.1. Quy ước phụ lục

Phần ngoài thân văn bản đích thường nằm trong phụ lục hoặc văn bản kèm theo: danh mục, thủ tục, biểu mẫu, phương án. Phần đó không có node riêng. Công cụ ghi vị trí là phụ lục chứa phần đó. Code: `resolver.appendix_scope`, `resolver.body_place`. Công cụ áp quy ước ở bước 10 và bước 14 (mục 9.2).

Vị trí của thân văn bản (`resolver.body_place`):

- vị trí có chữ `điểm`, `khoản`, `Điều` hoặc `Chương`, kể cả `tên Điều <x>`, `tên Chương <c>`, `Mục <n> Chương <c>`;
- `tên văn bản`;
- `tên Mục <n>`, với `<n>` là số Ả Rập.

`Mục <n>` không nêu Chương không thuộc thân văn bản. Vị trí này thường là Mục của một phương án hoặc danh mục.

| # | Quan hệ khi áp quy ước | Công cụ làm | Ví dụ |
| --- | --- | --- | --- |
| 1 | Có `vi_tri` khác `toàn bộ` | Mỗi vị trí ngoài thân văn bản đổi thành phụ lục. `scope` bằng vị trí mới. `doi_tuong` không đổi. Chữ vị trí gốc ghi ở `chi_tiet_vi_tri` của cạnh tới phụ lục. Công cụ đổi cả `cum_tu[].vi_tri` theo cùng luật. | `692884_0` (lượt `fix9-H56`): `Mục II Phần B Phụ lục I` → `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri` "Mục II Phần B Phụ lục I". `690014_81` (lượt `fix9-ho`, `thay-cum-tu`): `vi_tri = ["Phụ lục II"]`, `chi_tiet_vi_tri` "Mục III Phần XI Phụ lục II". |
| 2 | Không có `vi_tri`, có `doi_tuong`, và một điều kiện ở bảng dưới đúng | Ghi `vi_tri` là phụ lục, đọc ký hiệu từ chữ của `doi_tuong`. `scope` bằng vị trí mới. `doi_tuong` và `kem_theo` giữ chữ gốc. Công cụ không ghi `chi_tiet_vi_tri` mới. | `685249_0` (lượt `fix9-H56`): `doi_tuong` "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ", `kem_theo = false` → `vi_tri = ["Phụ lục"]`. `694022_0` (lượt `fix9-H56`): `doi_tuong` "danh mục và nội dung 02 thủ tục hành chính có số thứ tự 11, 17 mục I, phần A, Phụ lục 1", `kem_theo = true` → `vi_tri = ["Phụ lục 1"]`. |
| 3 | Không có `vi_tri`, có `doi_tuong`, không điều kiện nào đúng | Giữ tên ở `doi_tuong`. `vi_tri` rỗng. | `676559_0` (lượt `fix9-H56`): `doi_tuong` "một số điều của các Thông tư trong lĩnh vực lâm nghiệp", `cap_quan_he = noi_dung`. Khác: "phần căn cứ", "đơn giá ban hành kèm theo Quyết định X". |
| 4 | Vị trí của thân văn bản, `toàn bộ` | Giữ | `694952_4`; `694149_152` (lượt `fix9-ho`): `tên văn bản` |

Ký hiệu phụ lục:

- `Phụ lục <n>` khi chữ nêu đúng một phụ lục có ký hiệu: số La Mã, số hoặc một chữ cái. "Phụ lục số 01" cho `Phụ lục 01`.
- `Phụ lục` khi chữ không nêu ký hiệu, hoặc nêu từ hai ký hiệu trở lên.

Điều kiện của ca 2 (một điều kiện đúng là đủ):

| Điều kiện | Code | Ví dụ (chưa ghi ES) |
| --- | --- | --- |
| `doi_tuong` có một trong các chữ: "phụ lục", "danh mục", "thủ tục", "TTHC", "biểu mẫu", "mẫu" hoặc "mẫu số" kèm ký hiệu, "phương án", "quy trình nội bộ", "Mục <số>", "Phần <số hoặc chữ>", "số thứ tự", "STT" | `resolver.appendix_like` | `678019_2` (lượt `fix9-H56`): `doi_tuong` "số thứ tự 65 mục III, phần B, phụ lục II" → `vi_tri = ["Phụ lục II"]`. `675263_8` (lượt `fix9-ho`): `doi_tuong` "Phụ lục 02 Danh Mục hàng hóa, dịch vụ do Nhà nước định giá" → `vi_tri = ["Phụ lục 02"]`. |
| `doi_tuong_loai = thu_tuc_hanh_chinh` | `resolver.appendix_scope` | `680352_0` (lượt `fix9-H56`): `doi_tuong` "Cấp chứng chỉ nghiệp vụ chuyên môn về đấu thầu" → `vi_tri = ["Phụ lục"]` |
| `source_path` là dòng bảng (có ` STT `) hoặc bắt đầu bằng "Phụ lục" | `resolver.appendix_scope` | `685697_0` (lượt `fix9-ho`): `source_path` "Phụ lục 1 Mục 11 STT 6", `doi_tuong` "Bổ sung nhà cung cấp Dược liệu: …" → `vi_tri = ["Phụ lục"]` |

`chi_tiet_vi_tri` của ca 1:

- Trường có các đoạn nối bằng `; `: chữ vị trí gốc, rồi chi tiết đã có (ví dụ dòng số thứ tự). Ví dụ: `689945_1` (lượt `fix9-H56`) có `vi_tri = ["Phụ lục"]`, `chi_tiet_vi_tri` "Mục I; số thứ tự 1, 2, 3, 4".
- Nhiều vị trí gốc đổi về cùng một phụ lục thì công cụ gộp thành một cạnh. Ví dụ: `683435_14` (lượt `fix9-H56`) có `vi_tri = ["Phụ lục"]`, `chi_tiet_vi_tri` "Mục 14; Mục 89; Mục 90".
- Một đoạn có thể lặp lại trong trường. Ví dụ: `680742_0` (lượt `fix9-ho`) có `chi_tiet_vi_tri` "Phụ lục stt 6; stt 6". Đo 27/10/2026: 12/197 quan hệ `validated` có `chi_tiet_vi_tri` có đoạn lặp.

Hệ quả:

- Quan hệ ở ca 1 và ca 2 có `cap_quan_he = vi_tri`, kể cả khi còn `doi_tuong` (mục 9.10.8).
- `cap_quan_he` là `noi_dung` hoặc `van_ban_kem_theo` chỉ ở ca 3.
- `Phụ lục <n>` nối vào node phụ lục có ký hiệu `<n>`. `Phụ lục` chưa có node xác định (mục 9.11.2).
- Code `8b023ca` không ghi các dạng có cột "Đổi …" ở bảng mục 9.5.

Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (876 văn bản, code `8b023ca`, chưa ghi ES). Có 9.760 quan hệ `validated`. 557 quan hệ (5,7%) có vị trí là phụ lục:

| `vi_tri` | Quan hệ | Còn `doi_tuong` | Có `chi_tiet_vi_tri` |
| --- | --- | --- | --- |
| `Phụ lục <n>` | 265 | 16 | 95 |
| `Phụ lục` | 292 | 150 | 101 |

Cùng lượt đo: 0 vị trí ngoài thân văn bản còn dạng khác `Phụ lục`. 0 quan hệ có `doi_tuong` đúng điều kiện ca 2 mà `vi_tri` rỗng.

Giới hạn: `Phụ lục` không ký hiệu không chỉ tới một node phụ lục. Câu hỏi cho bên Graph ở [11, mục 11.6](11-cau-hoi-graph.md#116-việc-3-cạnh-vào-phụ-lục-không-nêu-ký-hiệu).

## 9.6. Đơn vị nguồn

`source_path` chỉ đơn vị của văn bản nguồn chứa câu tác động. `source_path` không dùng định dạng Vị trí: `Khoản` viết hoa, thứ tự từ Điều xuống điểm. Không so sánh trực tiếp `source_path` với `vi_tri`.

| Dạng | Nghĩa | Chunk tương ứng | Đo 21/10 | Ví dụ (`legal-changed-v4`) |
| --- | --- | --- | --- | --- |
| `Điều <x>` | Cả Điều của văn bản nguồn | `<doc>_d<x>` hoặc `<doc>_d<x>_full` | 782 | `Điều 2` (`697671_0`) |
| `Điều <x> Khoản <y>` | Khoản | `<doc>_d<x>_k<y>` hoặc `…_full` | 1.913 | `Điều 1 Khoản 1` (`694952_0`) |
| `Điều <x> Khoản <y> điểm <z>` | Điểm | `<doc>_d<x>_k<y>_p<z>` | 437 | `Điều 1 Khoản 3 điểm a` (`694952_4`) → chunk `694952_d1_k3_pa` |
| `Phụ lục <n> ` + một dạng ở trên | Điều trong phần thứ `n` của `phu_luc[]`, đếm từ 1 | `<doc>_pl<n−1>_d<x>…` | 9 | `Phụ lục 1 Điều 10` (`696841_1`) |
| `… Văn bản kèm theo <s> …` | Điều thuộc chuỗi Điều kèm theo thứ `s` | `…_s<s>_d<x>…` | Gồm trong 9 ở trên | `Phụ lục 2 Văn bản kèm theo 3 Điều 3 Khoản 12 điểm c` |
| `intro` | Tên in trong văn bản, hoặc lời dẫn. Tên lưu ở nguồn (`title`) không tạo quan hệ. | Node văn bản | 109 | `intro_697656_0` (nhánh LLM), `intro_697272_0` (nhánh quy tắc) |
| `Tiêu đề`, `Lời dẫn` | Chỉ có ở quan hệ hướng dẫn `hd_` | Node văn bản | 26, 0 | `hd_672539_0` |
| `Phần đầu` | Phần đầu của văn bản hợp nhất. Phần này nêu văn bản được hợp nhất. Chỉ có ở `hn_`. | Node văn bản | 69 | `hn_697639_0` |
| `Mục <n>` | Đề mục của văn bản không chia Điều. `<n>` là nhãn như văn bản viết (`1`, `IX`, `PHẦN I`). | `<doc>_m<n>` | 53 | `Mục 8` (`697108_0`) |
| `Nội dung` | Văn bản không chia Điều, không có đề mục | `<doc>_nd` hoặc `<doc>_nd_full` | 22 | `697506_0` |
| `Phụ lục <n> Mục <m>`, `Phụ lục <n>` | Đề mục `<m>` của phụ lục thứ `n` viết thành đoạn văn, không chia Điều, không là bảng. `Phụ lục <n>` khi phụ lục không có đề mục. | Không có chunk riêng. Node nguồn là phụ lục `<doc>_pl<n−1>`. | 62, 3 | `Phụ lục 1 Mục 2` (`697671_2`), `Phụ lục 2` (`694298_0`) |
| `Phụ lục <n> STT <k>`, `Phụ lục <n> Mục <m> STT <k>` | Một dòng bảng của phụ lục thứ `n` không chia Điều. `<m>` là ký hiệu đề mục chứa bảng. `<k>` là số ở cột "TT"/"STT", hoặc thứ tự dòng khi cột không có số. | Không có chunk riêng. Node nguồn là phụ lục `<doc>_pl<n−1>`. | 6, 79 | `Phụ lục 1 STT 27` (`693445_0`), `Phụ lục 1 Mục A STT 4` (`697309_0`) |

Quy tắc của dòng bảng:

1. Dòng có quan hệ khi dòng nêu số hiệu văn bản đích. Chữ chỉ hành động nằm ở một trong các nơi sau:
   - chính dòng đó, hoặc cột hành động của dòng;
   - đề mục của danh sách thủ tục chứa dòng;
   - Điều thực hiện hành động lên danh sách.
2. Văn bản ở cột căn cứ pháp lý không là văn bản đích. Công cụ bỏ cột này trước khi đọc.
3. Một Điều đã nêu cùng hành động lên cùng văn bản đích thì dòng của phụ lục chỉ là chi tiết. Quan hệ thuộc Điều đó. Dòng không có quan hệ riêng.
4. Một Điều thực hiện hành động lên "các văn bản tại Phụ lục …" thì mỗi văn bản của danh sách có một quan hệ. `source_path` là Điều đó.
5. Danh mục mà văn bản chỉ "công bố" (kết quả rà soát, danh mục thủ tục) không có quan hệ.
6. Danh sách việc cần làm (cột "Thời hạn thực hiện", "Cơ quan chủ trì") không có quan hệ.
7. Thủ tục nêu bằng tên: `doi_tuong` là tên thủ tục, `doi_tuong_loai = thu_tuc_hanh_chinh`, `vi_tri` là phụ lục (mục 9.5.1, ca 2). Ví dụ: `686631_0` (lượt `fix9-H56`), `source_path` "Phụ lục 1 Mục B STT 1", `vi_tri = ["Phụ lục"]`.

## 9.7. Trường truy vết

Cả 3 index có 5 trường này.

| Trường | Kiểu | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- |
| `origin` | keyword | `legacy` hoặc `user_upload`. Công cụ chép từ nguồn. Nguồn thiếu thì `legacy`. | `legacy` 994, `user_upload` 6 |
| `ingest_job_id` | keyword | `v3:<run_id>`. `run_id` là giờ UTC bắt đầu lượt, dạng `YYYYMMDDTHHMMSSZ`. Tiền tố `v3:` là tên công cụ, không là tên index. | Mục 9.1 |
| `ingest_revision` | integer | Luôn bằng `1`. | `1` |
| `ingested_at` | date | Thời điểm ghi (UTC). | `2026-10-22T07:26:23.340740+00:00` (`694952`) |
| `uploaded_by` | keyword | Luôn bằng `migration-v3`. | `migration-v3` |

Chunk có 5 trường bằng giá trị của văn bản chứa nó. Quan hệ có 5 trường bằng giá trị của văn bản nguồn.

## 9.8. `legal-docs-v4`

### 9.8.1. Ví dụ: `legal-docs-v4/694952`

Chuỗi dài giữ phần đầu và "…". Mảng dài giữ phần tử đầu. `embedding` giữ 3 số đầu.

```json
{
  "_index": "legal-docs-v4",
  "_id": "694952",
  "_source": {
    "document_number": "120/2026/UBTVQH15",
    "title": "Nghị quyết 120/2026/UBTVQH15 sửa đổi Nghị quyết 70/2025/UBTVQH15 quy định về nguyên tắc, tiêu chí và định mức phân bổ vốn đầu tư công …",
    "legal_type": "Nghị quyết",
    "legal_sectors": ["Đầu tư", "Tài chính nhà nước"],
    "issuing_authority": "Uỷ ban Thường vụ Quốc hội",
    "issuance_date": "2026-02-03",
    "signers": "Trần Thanh Mẫn:2140",
    "tom_tat": "Nghị quyết này sửa đổi, bổ sung một số quy định về phân bổ vốn đầu tư công từ ngân sách nhà nước giai đoạn 2026-2030 …",
    "action": "sua-doi",
    "url": "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-quyet-120-2026-UBTVQH15-…-694952.aspx",
    "pdf_minio_path": "tvpl-pdf/120-2026-UBTVQH15_694952.pdf",
    "embedding": [-0.0372, -0.0114, 0.0024, "… (1.024 số)"],
    "full_content": "ỦY BAN THƯỜNG VỤ QUỐC HỘI | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM …",
    "content_sha256": "2a99f3c2cb86564d6aa306576621abcf4ca20aaa868c13dcb58c89090647745b",
    "text_source": "source_full_content",
    "can_cu": ["Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam …", "… (4 phần tử)"],
    "can_cu_refs": ["203/2025/QH15", "58/2024/QH15", "… (6 phần tử)"],
    "intro": "QUYẾT NGHỊ:",
    "noi_nhan": [],
    "phu_luc": [],
    "has_tail": true,
    "n_dieu": 2,
    "grade": "full",
    "la_vbqppl": true,
    "la_vbqppl_cach": "so_hieu_co_nam",
    "cap_hieu_luc": 3,
    "cap_hieu_luc_nhan": "UBTV_QUOC_HOI",
    "cap_hieu_luc_ghi_chu": null,
    "ngay_hieu_luc": "2026-02-03",
    "ngay_hieu_luc_cach": "ngay_thong_qua",
    "ngay_hieu_luc_so_ngay": 0,
    "ngay_hieu_luc_trich": "Nghị quyết này có hiệu lực thi hành từ ngày thông qua và áp dụng cho các năm ngân sách giai đoạn 2026 - 2030.",
    "hieu_luc_rieng": [],
    "ngay_het_hieu_luc": null,
    "ngay_het_hieu_luc_cach": "khong_ghi",
    "ngay_het_hieu_luc_trich": null,
    "hoi_to": false,
    "ngay_hoi_to": null,
    "ngay_hoi_to_trich": null,
    "hoi_to_vi_tri": [],
    "origin": "legacy",
    "ingest_job_id": "v3:20261022T044254Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-22T07:26:23.340740+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 9.8.2. Định danh và metadata

Công cụ chép các trường này từ `legal-docs` nguồn. Công cụ không sửa giá trị.

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `_id` | chuỗi | Mọi văn bản | Chỉ có chữ số. Bằng `_id` nguồn. | 1.000 |
| `document_number` | keyword | Mọi văn bản | Khác rỗng. Không duy nhất. | 1.000 |
| `title` | text | Mọi văn bản | Khác rỗng. Tên lưu ở nguồn. Công cụ chỉ dùng trường này cho tìm kiếm, đối chiếu và `source_title`. | 1.000 |
| `legal_type` | keyword | Mọi văn bản | Khác rỗng. | 13 giá trị. Nhiều nhất: Quyết định 492, Công văn 194, Văn bản hợp nhất 69. |
| `legal_sectors` | mảng keyword | Có khi nguồn có | Mỗi phần tử khác rỗng. | 1.000 |
| `issuing_authority` | keyword | Mọi văn bản | Khác rỗng. | 1.000 |
| `issuance_date` | date | Mọi văn bản | Là Ngày. | 1.000 |
| `signers` | keyword, không index | Có khi nguồn có | Dạng `Tên:mã`. Nhiều người cách nhau bằng dấu phẩy. Văn bản tải lên chỉ có tên. | 1.000 |
| `tom_tat` | text | Mọi văn bản | Khác rỗng. | 1.000 |
| `action` | keyword | Mọi văn bản | Phân loại văn bản ở nguồn. **Không là** hành động của quan hệ. | 1.000 |
| `url` | keyword, không index | Mọi văn bản | `legacy`: bắt đầu bằng `https://thuvienphapluat.vn/`. `user_upload`: `upload://<_id>` (`900000017`). | 1.000 |
| `pdf_minio_path` | keyword | Có khi nguồn có | `tvpl-pdf/…_<_id>.pdf` hoặc `legal-upload/pdf/<sha256>.pdf`. | 984 |
| `pdf_vbpl_id` | keyword | Có khi nguồn có | Chỉ có chữ số. | 92 |
| `embedding` | dense_vector 1.024 | Mọi văn bản | Công cụ chép từ nguồn. Nguồn thiếu thì công cụ tạo vector của `title`. Dữ liệu `-v4` hiện có: vector của `title`, tạo lại ngày 26/10/2026 (mục 9.1). | 1.000 |

### 9.8.3. Nội dung và cấu trúc

Công cụ tính các trường này từ toàn văn.

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `full_content` | text | Mọi văn bản | Toàn văn nguồn, chuẩn hóa NFC. Khác rỗng. | 1.000 |
| `content_sha256` | keyword | Mọi văn bản | SHA-256 (hex) của `full_content` mã hóa UTF-8. | 1.000 |
| `text_source` | keyword | Mọi văn bản | Nơi lấy chữ. `legacy` luôn là `source_full_content`. `user_upload`: giá trị của nguồn. | `source_full_content` 994, `ocr` 5, `mixed` 1 |
| `can_cu` | mảng chuỗi, không index | Mọi văn bản | Mỗi phần tử là một dòng bắt đầu bằng "Căn cứ". Rỗng khi văn bản không có căn cứ. | Rỗng ở 205 |
| `can_cu_refs` | mảng keyword | Mọi văn bản | Số hiệu nêu trong `can_cu`. | Rỗng ở 262 |
| `intro` | text | Mọi văn bản | Lời dẫn sau căn cứ, trước Điều đầu tiên. Công văn: phần trước đề mục đầu tiên. Rỗng khi không có. | Rỗng ở 60 |
| `noi_nhan` | mảng chuỗi, không index | Mọi văn bản | Mỗi dòng sau "Nơi nhận" là một phần tử. Rỗng khi văn bản không có mục "Nơi nhận". Dòng chữ ký không là nơi nhận. | Rỗng ở 89 |
| `phu_luc` | mảng object, `enabled: false` | Mọi văn bản | Phụ lục và văn bản kèm theo. ES không tìm kiếm được trường này. Mục 9.8.4. | Khác rỗng ở 534 |
| `has_tail` | boolean | Mọi văn bản | `true` khi văn bản có chữ ký hoặc mục "Nơi nhận". | `true` 982 |
| `n_dieu` | integer | Mọi văn bản | Số Điều của văn bản chính. Không tính Điều trong phụ lục và chuỗi Điều kèm theo. | `0` ở 310 |
| `grade` | keyword | Mọi văn bản | Chất lượng tách cấu trúc: `full`, `partial`, `minimal`. Không đo giá trị pháp lý. | `full` 876, `minimal` 95, `partial` 29 |

### 9.8.4. `phu_luc[]`

- Mỗi phần tử là một phụ lục có nhãn, hoặc một văn bản kèm theo không nhãn.
- Thứ tự phần tử là thứ tự trong văn bản.
- Phần tử thứ `i` (đếm từ 0) có chunk ID bắt đầu bằng `<doc>_pl<i>`.
- Phụ lục không chia Điều có một chunk `phu_luc` chứa toàn bộ phụ lục. Bảng, danh mục, biểu mẫu nằm trong chunk đó. Công cụ không tách chunk theo dòng bảng.
- Đo 21/10: 965 phần tử ở 534 văn bản. `labeled` 691, `unlabeled` 274. 114 phần tử chia Điều. 657 phần tử có bảng.

| Trường | Kiểu | Quy tắc | Ví dụ `697598`, `phu_luc[0]` |
| --- | --- | --- | --- |
| `loai` | chuỗi | `labeled` hoặc `unlabeled`. | `labeled` |
| `ky_hieu` | chuỗi \| `null` | Ký hiệu trong nhãn. `null` khi `unlabeled` hoặc nhãn không có ký hiệu. Không duy nhất trong một văn bản. | `D` |
| `tieu_de` | chuỗi | Tiêu đề đầy đủ, gồm ghi chú "(Kèm theo …)". Khác rỗng. | `PHỤ LỤC DANH MỤC 13 THUỐC BIỆT DƯỢC GỐC … (Kèm theo Quyết định số 142/QĐ-QLD …)` |
| `noi_dung` | chuỗi | Nội dung sau tiêu đề. Bảng ở dạng dòng `\| … \|`. Có thể rỗng. | `\| STT \| Tên thuốc \| Hoạt chất, hàm lượng \| …` |
| `has_table` | boolean | `true` ⇔ `n_table_rows ≥ 2`. | `true` |
| `n_tables` | integer | Số bảng. | `1` |
| `n_table_rows` | integer | Số dòng bắt đầu bằng `\|`. | `15` |
| `dieu_luat` | mảng object | Các Điều của phần này. Rỗng khi phần không chia Điều. Mục 9.8.5. | `[]` |

Ví dụ phần tử chia Điều: `legal-docs-v4/697599`, `phu_luc[0]` là Quy chế kèm theo Quyết định 1784/QĐ-BKHCN. Phần tử này có `loai = unlabeled`, `ky_hieu = null` và 29 Điều trong `dieu_luat`.

### 9.8.5. `phu_luc[].dieu_luat[]`

| Trường | Kiểu | Có | Nghĩa |
| --- | --- | --- | --- |
| `so_dieu` | integer | Luôn | Phần số của Điều. |
| `ky_hieu` | chuỗi | Luôn | Ký hiệu đầy đủ, ví dụ `47a`. Bắt đầu bằng `so_dieu`. |
| `tieu_de` | chuỗi | Luôn | Tên Điều. Rỗng khi Điều không có tên. |
| `noi_dung` | chuỗi | Luôn | Toàn bộ nội dung Điều, gồm các khoản. |
| `so_van_ban_refs` | mảng chuỗi | Luôn | Số hiệu nêu trong Điều. |
| `khoan` | mảng object | Luôn | Các khoản. Rỗng khi Điều không chia khoản. |
| `mo_dau` | chuỗi | Có khi `khoan` khác rỗng | Phần trước khoản đầu tiên. |
| `chuong` | chuỗi | Có khi Điều nằm trong một Chương | Tên Chương. Ví dụ: `Chương I - QUY ĐỊNH CHUNG` (`697599`). |
| `muc` | chuỗi | Có khi Điều nằm trong một Mục của Chương | Tên Mục. |
| `van_ban_kem_theo` | integer | Có khi Điều thuộc chuỗi Điều kèm theo | Thứ tự chuỗi, từ 1. Bằng `segment` của chunk. |
| `khoan[].so_khoan`, `khoan[].ky_hieu` | integer, chuỗi | Luôn | Như `so_dieu`, `ky_hieu`. |
| `khoan[].noi_dung` | chuỗi | Luôn | Toàn bộ nội dung khoản, gồm các điểm. |
| `khoan[].so_van_ban_refs` | mảng chuỗi | Luôn | Số hiệu nêu trong khoản. |
| `khoan[].diem` | mảng object | Luôn | Các điểm. Rỗng khi khoản không chia điểm. |
| `khoan[].mo_dau` | chuỗi | Có khi `diem` khác rỗng | Phần trước điểm đầu tiên. |
| `khoan[].diem[].ky_hieu`, `noi_dung`, `so_van_ban_refs` | chuỗi, chuỗi, mảng chuỗi | Luôn | Ký hiệu, nội dung, số hiệu của điểm. |
| `khoan[].diem[].tieu_diem` | mảng object | Có khi điểm có từ 2 dòng gạch đầu dòng | Các tiểu điểm. Mỗi phần tử có `ky_hieu` (`"1"`, `"2"`… theo thứ tự), `noi_dung`, `so_van_ban_refs`. |
| `khoan[].diem[].mo_dau` | chuỗi | Cùng `tieu_diem` | Phần trước tiểu điểm đầu tiên. |

### 9.8.6. Địa vị pháp lý

Công cụ tính các trường này bằng quy tắc, từ `legal_type`, `issuing_authority`, `document_number`, `issuance_date`, `title`. Công cụ không gọi model. Thứ tự xét ở [06, `la_vbqppl_cach`](06-bang-enum.md#la_vbqppl_cach).

| Trường | Kiểu | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- |
| `la_vbqppl` | boolean \| `null` | `true`: văn bản quy phạm pháp luật. `null` ⇔ `la_vbqppl_cach = can_kiem`. | `true` 193, `false` 807, `null` 0 |
| `la_vbqppl_cach` | keyword | Căn cứ phân loại. | `theo_loai` 372, `so_hieu_khong_nam` 211, `quyet_dinh_bo_tu_2009` 119, `so_hieu_co_nam` 102, `tieu_de_ca_biet` 81, `van_ban_hop_nhat` 69, `chi_thi_tu_2016` 18, `co_quan_khong_ban_hanh_vbqppl` 15, `van_ban_dang` 13 |
| `cap_hieu_luc` | integer \| `null` | 1..15 theo Luật 87/2025/QH15. `null` khi `la_vbqppl` khác `true`. | Có giá trị ở 193 |
| `cap_hieu_luc_nhan` | keyword \| `null` | Nhãn của `cap_hieu_luc`. `null` ⇔ `cap_hieu_luc = null`. | `UBND_TINH` 89, `THONG_TU` 62, `CHINH_PHU` 31, `HDND_TINH` 6, `THU_TUONG` 3, `UBTV_QUOC_HOI` 2 |
| `cap_hieu_luc_ghi_chu` | keyword \| `null` | `hinh_thuc_cu`, `cap_huyen`, `khong_xac_dinh` hoặc `null`. `cap_huyen` và `khong_xac_dinh` đi với `cap_hieu_luc = null`. | `null` 1.000 |

`la_vbqppl` chỉ có ở văn bản. Chunk và quan hệ không có trường này. Để lọc chunk hoặc quan hệ theo `la_vbqppl`, nối qua `doc_id` hoặc `source_id`.

### 9.8.7. Thời điểm hiệu lực

Công cụ chỉ đọc câu của chính văn bản. Công cụ bỏ câu nằm trong ngoặc kép. Chủ ngữ của câu phải đúng loại văn bản, ví dụ "Thông tư này" với Thông tư.

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `ngay_hieu_luc` | date \| `null` | Ngày có hiệu lực. `null` khi cách đọc không cho ngày. Đo 21/10: `null` ở 85. | `2026-02-03` (`694952`) |
| `ngay_hieu_luc_cach` | keyword | Mốc tính ngày, hoặc lý do không có ngày. Bảng dưới. | `ngay_thong_qua` |
| `ngay_hieu_luc_so_ngay` | integer \| `null` | Số ngày sau mốc mà câu nêu. "sau 45 ngày kể từ ngày ký" cho `45`. "kể từ ngày ký" cho `0`. `null` khi câu ghi ngày cụ thể hoặc không có câu. | `0` |
| `ngay_hieu_luc_trich` | keyword, không index \| `null` | Câu gốc, tối đa 300 ký tự. `null` ⇔ cách đọc là `mac_dinh_ngay_ban_hanh`, `khong_tim_thay` hoặc `van_ban_hop_nhat`. | `Nghị quyết này có hiệu lực thi hành từ ngày thông qua …` |
| `ngay_het_hieu_luc` | date \| `null` | Ngày hết hiệu lực do chính văn bản ghi. `null` ⇔ `ngay_het_hieu_luc_cach = khong_ghi`. | `2026-04-30` (`696878`) |
| `ngay_het_hieu_luc_cach` | keyword | `ngay_cu_the`, `het_nam`, `khong_ghi`. | `khong_ghi` 989, `ngay_cu_the` 11 |
| `ngay_het_hieu_luc_trich` | keyword, không index \| `null` | Câu gốc. `null` ⇔ `khong_ghi`. | `Nghị định này có hiệu lực kể từ ngày ký đến ngày 30 tháng 4 năm 2026` (`696878`) |
| `hoi_to` | boolean | `true`: văn bản áp dụng từ một ngày trước `issuance_date`. `hoi_to = true` ⇔ `ngay_hoi_to` khác `null`. | `true` ở 13 (`900000017`) |
| `ngay_hoi_to` | date \| `null` | Ngày bắt đầu áp dụng hồi tố. Trước `issuance_date`. | `2026-01-01` (`900000017`, ban hành `2026-09-09`) |
| `ngay_hoi_to_trich` | keyword, không index \| `null` | Câu gốc. `null` ⇔ `hoi_to = false`. | `Các mức phụ cấp ưu đãi nghề quy định tại Nghị định này được thực hiện kể từ ngày 01 tháng 01 năm 2026` |
| `hoi_to_vi_tri` | mảng keyword | Vị trí hồi tố trong chính văn bản. Rỗng là cả văn bản. | `[]` ở cả 13 văn bản hồi tố |
| `hieu_luc_rieng` | mảng object | Ngày hiệu lực văn bản nêu riêng cho một số Điều, khoản, điểm của chính nó. Rỗng khi không có. | Khác rỗng ở 1 (`695172`) |

| `ngay_hieu_luc_cach` | `ngay_hieu_luc` | Đo 21/10 | Ví dụ |
| --- | --- | --- | --- |
| `ngay_ky` | Ngày ký cộng `ngay_hieu_luc_so_ngay` | 371 | `697007` |
| `mac_dinh_ngay_ban_hanh` | `issuance_date`. Giá trị suy ra. Chỉ khi `la_vbqppl = false`. | 317 | `696470` (Công văn) |
| `ngay_cu_the` | Ngày câu ghi | 213 | `695172` |
| `van_ban_hop_nhat` | `null`. Văn bản hợp nhất không có ngày hiệu lực riêng. | 69 | `696338` |
| `khong_doc_duoc` | `null`. Câu có, nhưng công cụ không đọc được ngày. | 15 | `696498`: "… kể từ ngày Thông tư số 03/2026/TT-BYT có hiệu lực thi hành" |
| `ngay_thong_qua` | Ngày thông qua | 14 | `694952` |
| `khong_tim_thay` | `null` | 1 | `688849` |
| `ngay_dang_cong_bao` | `null`. Công cụ không biết ngày đăng Công báo. | 0 | — |

`hieu_luc_rieng[]` có các trường `vi_tri` (mảng Vị trí), `ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_so_ngay`, `ngay_hieu_luc_trich`. Công cụ bỏ câu nêu điều khoản của văn bản khác.

Ví dụ `695172` có một phần tử: `vi_tri = ["khoản 4 Điều 4"]`, `ngay_hieu_luc = 2026-07-01`. Câu gốc: "Quy định tại khoản 4 Điều 4 của Nghị định này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026".

**`ngay_het_hieu_luc = null` không có nghĩa là văn bản còn hiệu lực.** Văn bản khác có thể thay thế, bãi bỏ hoặc hủy bỏ văn bản này. Thông tin đó nằm ở `legal-changed-v4`: quan hệ có `target_matched_id` là văn bản này và `vi_tri = ["toàn bộ"]`.

## 9.9. `legal-chunk-section-v4`

- Một chunk là một đơn vị nội dung để tìm kiếm.
- Chunk có `is_full = true` chứa trọn một Điều, một khoản hoặc toàn bộ nội dung.
- Đơn vị có chunk con thì chunk `is_full` lặp lại nội dung của chunk con. Khi gộp kết quả tìm kiếm, bỏ trùng theo `dieu_uid` và `khoan_uid`.
- Công cụ tạo vector từ `tieu_de + " " + noi_dung` sau khi gộp khoảng trắng. Dịch vụ embedding của lệnh `convert` cắt đầu vào ở 256 token. Phần sau token 256 không có trong vector.
- Chunk `phu_luc` thường dài hơn giới hạn này. Vector chỉ đại diện cho phần đầu của phụ lục. Tìm nội dung phụ lục bằng truy vấn chữ trên `noi_dung`.
- Dữ liệu `-v4` hiện có dùng vector tạo lại ngày 26/10/2026 từ toàn bộ đầu vào, không cắt (mục 9.1). Lệnh `convert` ghi lại một văn bản thì vector của văn bản đó lại cắt ở 256 token.

### 9.9.1. Ví dụ: `legal-chunk-section-v4/694952_d1_k3_pa`

Chunk này chứa câu tạo ra quan hệ `legal-changed-v4/694952_4`.

```json
{
  "_index": "legal-chunk-section-v4",
  "_id": "694952_d1_k3_pa",
  "_source": {
    "doc_id": "694952",
    "chunk_type": "diem",
    "tieu_de": "Sửa đổi, bổ sung một số điều của Nghị quyết số 70/2025/UBTVQH15 ngày 07 tháng 02 năm 2025 …",
    "noi_dung": "Sửa đổi, bổ sung điểm a khoản 1 Điều 8 như sau: “a) Bảo đảm tương quan hợp lý giữa việc phát triển các vùng kinh tế trọng điểm …",
    "so_van_ban_refs": [],
    "dieu_uid": "694952_d1",
    "segment": 0,
    "so_dieu": 1,
    "ky_hieu_dieu": "1",
    "khoan_uid": "694952_d1_k3",
    "so_khoan": 3,
    "ky_hieu_khoan": "3",
    "so_diem": "a",
    "diem_uid": "694952_d1_k3_pa",
    "ngay_hieu_luc": "2026-02-03",
    "ngay_hieu_luc_cach": "ngay_thong_qua",
    "ngay_hieu_luc_so_ngay": 0,
    "ngay_hieu_luc_rieng": false,
    "document_number": "120/2026/UBTVQH15",
    "title": "Nghị quyết 120/2026/UBTVQH15 sửa đổi Nghị quyết 70/2025/UBTVQH15 …",
    "action": "sua-doi",
    "legal_type": "Nghị quyết",
    "issuing_authority": "Uỷ ban Thường vụ Quốc hội",
    "issuance_date": "2026-02-03",
    "url": "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-quyet-120-2026-UBTVQH15-…-694952.aspx",
    "signers": "Trần Thanh Mẫn:2140",
    "legal_sectors": "Đầu tư, Tài chính nhà nước",
    "embedding": [-0.0168, -0.0070, -0.0095, "… (1.024 số)"],
    "origin": "legacy",
    "ingest_job_id": "v3:20261022T044254Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-22T07:26:23.340740+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 9.9.2. Loại chunk và ID

| `chunk_type` | Mẫu `_id` | Nội dung | Đo 21/10 | Ví dụ |
| --- | --- | --- | --- | --- |
| `dieu` | `<doc>_d<x>` | Trọn một Điều không có khoản | 2.864 | `697599_d2` |
| `dieu_full` | `<doc>_d<x>_full` | Trọn một Điều có khoản | 6.013 | `697599_pl0_d3_full` |
| `dieu_mo_dau` | `<doc>_d<x>_md` | Phần trước khoản đầu. Có khi phần này dài từ 40 ký tự. | 648 | `696826_d1_md` |
| `khoan` | `<doc>_d<x>_k<y>` | Trọn một khoản không có điểm | 18.488 | `697599_pl0_d2_k1` |
| `khoan_full` | `<doc>_d<x>_k<y>_full` | Trọn một khoản có điểm | 4.756 | `694952_d1_k3_full` |
| `khoan_mo_dau` | `<doc>_d<x>_k<y>_md` | Phần trước điểm đầu. Có khi phần này dài từ 40 ký tự. | 3.708 | `697599_pl0_d9_k1_md` |
| `diem` | `<doc>_d<x>_k<y>_p<z>` | Trọn một điểm, gồm các tiểu điểm | 18.243 | `694952_d1_k3_pa` |
| `tieu_diem` | `<doc>_d<x>_k<y>_p<z>_t<n>` | Mục gạch đầu dòng thứ `n` của một điểm. Có khi điểm có từ 2 dòng gạch đầu dòng. | 4.462 | `697648_pl0_d9_k3_pa_t1` |
| `phu_luc` | `<doc>_pl<i>` | Phần thứ `i` (từ 0) của `phu_luc[]`. Có khi phần đó không chia Điều. | 851 | `697598_pl0` |
| `muc` | `<doc>_m<n>` | Một đề mục của văn bản không chia Điều | 933 | `697443_m4` |
| `noi_dung` | `<doc>_nd`, `<doc>_nd<k>` | Văn bản không chia Điều, không có đề mục. `_nd`: nội dung ngắn. `_nd<k>`: đoạn thứ `k` của nội dung dài. | 606 | `696897_nd1` |
| `noi_dung_full` | `<doc>_nd_full` | Trọn nội dung dài (trên 200 âm tiết). | 102 | `696897_nd_full` |

Quy tắc ID:

1. Điều trong phụ lục có thêm `_pl<i>` sau `<doc>`. Ví dụ: `697599_pl0_d2_k1`.
2. Điều thuộc chuỗi Điều kèm theo thứ `s` có thêm `_s<s>` trước `_d`. Ví dụ: `697685_pl0_s1_d1_k1`.
3. `_pl<i>` luôn có số. `_pl` ở cuối ID là điểm `l`. Ví dụ: `697024_d26_k2_pl`.
4. `_t<n>` sau `_p<z>` là tiểu điểm thứ `n`, đếm từ 1.
5. Hai chunk trùng ID thì chunk sau có thêm `_2`, `_3`… Ví dụ: `697061_mII_2`.

### 9.9.3. Trường

"Chunk thuộc Điều" là 8 loại: `dieu`, `dieu_full`, `dieu_mo_dau`, `khoan`, `khoan_full`, `khoan_mo_dau`, `diem`, `tieu_diem`.

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `_id` | chuỗi | Mọi chunk | Bắt đầu bằng `<doc_id>_`. Khớp mẫu của `chunk_type`. | — |
| `doc_id` | keyword | Mọi chunk | Bằng `_id` của văn bản. | — |
| `chunk_type` | keyword | Mọi chunk | 12 giá trị ở mục 9.9.2. | — |
| `tieu_de` | text | Mọi chunk | Tên Điều với chunk thuộc Điều. Tiêu đề phụ lục với `phu_luc`. Rỗng với `muc`, `noi_dung`, `noi_dung_full` và Điều không tên. | — |
| `noi_dung` | text | Mọi chunk | `tieu_de + noi_dung` khác rỗng. | Đúng ở mọi chunk |
| `so_van_ban_refs` | mảng keyword | Mọi chunk | Số hiệu nêu trong chunk. Chunk `_md` luôn rỗng. | — |
| `embedding` | dense_vector 1.024 | Mọi chunk | Vector của `tieu_de + " " + noi_dung`. | — |
| `document_number`, `title`, `action`, `legal_type`, `issuing_authority`, `issuance_date`, `url`, `signers` | như văn bản | Có khi văn bản có | Bằng trường cùng tên của văn bản. | — |
| `legal_sectors` | keyword (chuỗi) | Có khi văn bản có | Chuỗi, không là mảng. Các phần tử nối bằng `", "`. | — |
| `dieu_uid` | keyword | Chunk thuộc Điều | Phần đầu `_id` đến hết `_d<x>`. ID node Điều. | — |
| `segment` | integer | Chunk thuộc Điều | `0`: chuỗi Điều đầu. `s ≥ 1`: chuỗi Điều kèm theo thứ `s`. `segment > 0` ⇔ `_id` có `_s<s>`. | `> 0` ở 1.222 |
| `so_dieu`, `ky_hieu_dieu` | integer, keyword | Chunk thuộc Điều | Phần số và ký hiệu đầy đủ. `dieu_uid` kết thúc bằng `_d<ky_hieu_dieu>`. | — |
| `chuong` | text | Có khi Điều nằm trong Chương | Tên Chương. | 45.976 |
| `muc_lon` | text | Có khi Điều nằm trong Mục của Chương | Tên Mục. | 16.149 |
| `khoan_uid` | keyword | `khoan`, `khoan_full`, `khoan_mo_dau`, `diem`, `tieu_diem` | Phần đầu `_id` đến hết `_k<y>`. ID node khoản. | — |
| `so_khoan`, `ky_hieu_khoan` | integer, keyword | Cùng `khoan_uid` | Phần số và ký hiệu đầy đủ. | — |
| `so_diem` | keyword | `diem`, `tieu_diem` | Ký hiệu điểm. | — |
| `diem_uid` | keyword | `diem`, `tieu_diem` | `_id` của chunk `diem`. ID node điểm. | — |
| `so_tieu_diem` | integer | `tieu_diem` | Thứ tự tiểu điểm, từ 1. | — |
| `is_full` | boolean | `dieu`, `dieu_full`, `khoan`, `khoan_full`, `noi_dung_full` | Chỉ có giá trị `true`. | — |
| `in_phu_luc` | boolean | Có khi `_id` có `_pl<i>` | Chỉ có giá trị `true`. | 14.710 |
| `phu_luc_tieu_de` | text | Cùng `in_phu_luc` | 500 ký tự đầu của `phu_luc[i].tieu_de`. | — |
| `has_table` | boolean | Cùng `in_phu_luc` | Bằng `phu_luc[i].has_table`. | — |
| `so_muc` | keyword | `muc` | Ký hiệu đề mục: `4`, `II`. | — |
| `so_doan` | integer | `<doc>_nd<k>` | Bằng `k`. Đánh số liên tục từ 1. Văn bản có đoạn thì có đúng một `noi_dung_full`. | — |
| `dan_chieu` | mảng object | Có khi chunk có dẫn chiếu | Khác rỗng khi có. Mục 9.9.4. | 10.568 |
| `ngay_hieu_luc` | date \| `null` | Mọi chunk | Ngày hiệu lực của chính đơn vị. Văn bản nêu ngày riêng cho đơn vị (hoặc đơn vị cha) thì dùng ngày đó. Văn bản không nêu thì dùng ngày của văn bản. | `null` ở 29.836 |
| `ngay_hieu_luc_cach` | keyword | Mọi chunk | Cách đọc của ngày trên. Cùng giá trị với văn bản (mục 9.8.7). | — |
| `ngay_hieu_luc_so_ngay` | integer \| `null` | Mọi chunk | Như trường cùng tên của văn bản. | — |
| `ngay_hieu_luc_rieng` | boolean | Mọi chunk | `true` khi ngày hiệu lực lấy từ `hieu_luc_rieng`. | `true` ở 0 |
| `ngay_hoi_to` | date | Có khi đơn vị nằm trong phạm vi hồi tố | Bằng `ngay_hoi_to` của văn bản. | 410 (`900000013_d1`) |
| 5 trường truy vết | | Mọi chunk | Mục 9.7. | — |

Đo 21/10: 29.836 chunk có `ngay_hieu_luc = null`. Lý do: `van_ban_hop_nhat` 29.672, `khong_doc_duoc` 85, `khong_tim_thay` 79.

### 9.9.4. `dan_chieu[]`

| Trường | Kiểu | Quy tắc | Ví dụ (`697023_d22_k3`) |
| --- | --- | --- | --- |
| `loai` | keyword | `noi_bo`, `noi_bo_ngam`, `ngoai`, `van_ban_bi_sua`. Đo 21/10, số chunk: `noi_bo` 7.840, `noi_bo_ngam` 5.015, `ngoai` 2.970, `van_ban_bi_sua` 88. | `van_ban_bi_sua` |
| `vi_tri` | keyword | Là Vị trí (mục 9.5). | `Điều 25` |
| `van_ban` | keyword \| `null` | Số hiệu hoặc tên văn bản được dẫn. `null` khi `loai` là `noi_bo` hoặc `noi_bo_ngam`. | `106/2025/NĐ-CP` |
| `target_id` | integer \| `null` | `_id` văn bản được dẫn ở `legal-docs` nguồn. Bằng `doc_id` khi `loai` là `noi_bo` hoặc `noi_bo_ngam`. `null` khi công cụ chưa nối được. | `657421` |
| `trich` | keyword, không index | Câu chữ gốc, tối đa 200 ký tự. | `Điều 25 Nghị định này` |

Dẫn chiếu không là quan hệ. Số hiệu văn bản trong bảng hoặc danh mục chỉ là dẫn chiếu hoặc `so_van_ban_refs`. Ví dụ: chunk `696022_pl0` là danh mục thủ tục hành chính mà Quyết định 1091/QĐ-UBND công bố. Chunk này có `64/2025/TT-BTC` và `47/2019/TT-BTC` trong `so_van_ban_refs`. Văn bản `696022` không có quan hệ tới hai Thông tư đó.

## 9.10. `legal-changed-v4`

- Một quan hệ là một tác động của một đơn vị nguồn lên **một** vị trí của văn bản đích. Một vị trí là một cạnh và là một quan hệ.
- Câu nguồn nêu N vị trí thì công cụ ghi N quan hệ. Các quan hệ này có cùng `scope` và khác `vi_tri`. Ví dụ: `697309_0` có `scope` nêu 4 vị trí.
- "Sửa đổi, bổ sung" trên một vị trí cho 2 quan hệ riêng: `sua-doi` (`694952_4`) và `bo-sung` (`694952_5`). Công cụ không gộp hai quan hệ này.
- Tiêu đề, lời dẫn và từng Điều có quan hệ riêng, kể cả khi cùng văn bản đích.
- Quan hệ có trong câu chữ và là tác động trực tiếp. Công cụ không suy ra tác động lên đơn vị cha, đơn vị con hay văn bản khác.
- Văn bản chỉ có tên trong ghi chú lịch sử không là đích. Ví dụ: "Luật X đã được sửa đổi, bổ sung theo Luật số A, Luật số B". Công cụ loại quan hệ tới A và B (mục 9.10.7).
- Hai nhánh dò quan hệ: nhánh LLM (luồng 4 tầng, model `qwen3.6-35b`) và nhánh quy tắc. Trường `extraction` ghi nhánh nào đọc được quan hệ (mục 9.10.7).
- Quan hệ hướng dẫn `hd_` và quan hệ hợp nhất `hn_` lấy bằng quy tắc, không qua model.
- Đo 21/10: 469/1.000 văn bản có ít nhất một quan hệ.

### 9.10.1. Ví dụ: `legal-changed-v4/694952_4`

Cả hai nhánh cùng đọc được quan hệ này. Câu tác động nằm ở chunk `694952_d1_k3_pa` (mục 9.9.1).

```json
{
  "_index": "legal-changed-v4",
  "_id": "694952_4",
  "_source": {
    "source_id": 694952,
    "source_document_number": "120/2026/UBTVQH15",
    "source_title": "Nghị quyết 120/2026/UBTVQH15 sửa đổi Nghị quyết 70/2025/UBTVQH15 … do Ủy ban Thường vụ Quốc hội ban hành",
    "source_action": "sua-doi",
    "source_issuing_authority": "Uỷ ban Thường vụ Quốc hội",
    "source_issuance_date": "2026-02-03",
    "source_legal_type": "Nghị quyết",
    "source_legal_sectors": "Đầu tư, Tài chính nhà nước",
    "source_url": "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-quyet-120-2026-UBTVQH15-…-694952.aspx",
    "source_path": "Điều 1 Khoản 3 điểm a",
    "source_in_phu_luc": false,
    "source_ngay_hieu_luc": "2026-02-03",
    "target_doc": "70/2025/UBTVQH15",
    "target_matched_id": 643741,
    "target_candidates_count": 1,
    "target_issuance_date": "2025-02-07",
    "target_section": "quyet_dinh",
    "action": "sua-doi",
    "scope": "điểm a khoản 1 Điều 8",
    "vi_tri": ["điểm a khoản 1 Điều 8"],
    "cap_quan_he": "vi_tri",
    "doi_tuong_loai": "van_ban",
    "hieu_luc_tac_dong": "ve_sau",
    "unresolved": false,
    "extraction": "llm+rules",
    "resolution_status": "validated",
    "resolution_reason": null,
    "evidence": "Sửa đổi, bổ sung điểm a khoản 1 Điều 8 như sau:",
    "scope_grounding_checked": true,
    "scope_grounding_correct": true,
    "scope_resolution_method": "explicit_declaration",
    "origin": "legacy",
    "ingest_job_id": "v3:20261022T044254Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-22T07:26:23.340740+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 9.10.2. Ví dụ khác

Các ví dụ chỉ nêu trường khác ví dụ ở mục 9.10.1.

`697176_24`: chỉ nhánh LLM đọc được. Câu "gạch đầu dòng thứ 3" cho vị trí tiểu điểm.

```json
{
  "source_path": "Điều 10 Khoản 3",
  "action": "sua-doi",
  "target_doc": "24/2024/TT-BGDĐT",
  "target_matched_id": 622931,
  "vi_tri": ["tiểu điểm 3 điểm b khoản 6 Điều 37"],
  "cap_quan_he": "vi_tri",
  "detection_mode": "llm",
  "extraction": "llm",
  "resolution_status": "validated",
  "target_section": "kem_theo",
  "evidence": "Sửa đổi, bổ sung gạch đầu dòng thứ 3 điểm b khoản 6 như sau:"
}
```

`672539_2`: chỉ nhánh LLM đọc được. Câu không nói "Điều 1" thuộc Thông tư hay thuộc văn bản ban hành kèm theo. Quan hệ chờ duyệt và không có cạnh.

```json
{
  "source_path": "Điều 10 Khoản 7 điểm a",
  "action": "bai-bo",
  "target_doc": "103/2014/TT-BTC",
  "vi_tri": ["Điều 1"],
  "cap_quan_he": "vi_tri",
  "unresolved": false,
  "detection_mode": "llm",
  "extraction": "llm",
  "resolution_status": "unresolved",
  "resolution_reason": "phan_kem_theo_chua_ro",
  "target_section": "khong_ro"
}
```

`685249_0` (lượt `fix9-H56`, chưa ghi ES): tác động lên thủ tục hành chính do văn bản đích công bố. Thủ tục nêu bằng tên. Theo quy ước phụ lục (mục 9.5.1), `vi_tri` là phụ lục và `doi_tuong` giữ tên. Bản ghi cùng `_id` trong `-v4` hiện có `vi_tri = []`, `cap_quan_he = noi_dung` (mục 9.1).

```json
{
  "source_path": "Điều 1",
  "action": "bai-bo",
  "target_doc": "1548/QĐ-UBND",
  "target_matched_id": 661664,
  "scope": "Phụ lục",
  "vi_tri": ["Phụ lục"],
  "doi_tuong": "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ",
  "kem_theo": false,
  "doi_tuong_loai": "thu_tuc_hanh_chinh",
  "cap_quan_he": "vi_tri",
  "extraction": "llm+rules",
  "resolution_status": "validated",
  "target_section": "khong_ap_dung"
}
```

`696924_0`: mã thủ tục có trong câu nguồn, nên quan hệ có `ma_thu_tuc = "1.002483"`. `doi_tuong` là "Cấp giấy xác nhận nội dung quảng cáo mỹ phẩm (mã thủ tục hành chính 1.002483); …".

### 9.10.3. ID

`_id` có dạng `<tiền tố><source_id>_<n>`.

| Tiền tố | `detection_mode` | Nơi có câu tác động | Đo 21/10 | Ví dụ |
| --- | --- | --- | --- | --- |
| không có | Thiếu (nhánh quy tắc) | Điều, khoản, điểm, đề mục | 1.083 | `694952_4` |
| không có | `llm` | Điều, khoản, điểm, đề mục, dòng bảng, phụ lục | 1.907 | `697176_24` |
| `hidden_` | `hidden` | Tiêu đề văn bản nguồn không nêu hành động. Câu tác động nằm trong một Điều. | 316 | `hidden_697643_0` |
| `intro_` | `intro` (nhánh quy tắc) | Lời dẫn | 49 | `intro_697272_0` |
| `intro_` | `llm` | Tên in trong văn bản, hoặc lời dẫn | 60 | `intro_697656_0` |
| `hhl_` | `het_hieu_luc` | Câu "… hết hiệu lực kể từ ngày …" của văn bản nguồn. Hành động `bai-bo`. | 60 | `hhl_697399_0` |
| `hd_` | `title_guidance` | Tiêu đề hoặc lời dẫn nêu văn bản được hướng dẫn | 26 | `hd_672539_0` |
| `hn_` | `hop_nhat` | Phần đầu văn bản hợp nhất | 69 | `hn_697639_0` |

Quy tắc:

1. `n` đếm từ 0 trong mỗi tiền tố của một văn bản nguồn. Công cụ đánh số sau khi tách theo vị trí. Dãy số không khuyết.
2. `n` đổi khi công cụ chạy lại văn bản nguồn. **Không dùng `_id` quan hệ làm khóa lâu dài.**
3. `detection_mode` có kiểu text. Lọc bằng `detection_mode.keyword`.
4. `detection_mode = llm` ⇔ `extraction = llm`. Quan hệ `llm+rules` giữ `detection_mode` của nhánh quy tắc.
5. Quan hệ của nhánh quy tắc có `detection_mode = title_guidance` ⇔ `action` là `huong-dan` hoặc `quy-dinh-chi-tiet`. Nhánh LLM cũng đọc hai hành động này (`697147_0`).
6. `detection_mode = hop_nhat` ⇔ `action = hop-nhat`.

### 9.10.4. Văn bản nguồn

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `source_id` | integer | Luôn | Bằng `_id` của một văn bản. | — |
| `source_document_number`, `source_title`, `source_action`, `source_issuing_authority`, `source_issuance_date`, `source_legal_type`, `source_url` | như văn bản | Luôn | Bằng trường cùng tên (bỏ `source_`) của văn bản nguồn. | — |
| `source_legal_sectors` | keyword (chuỗi) | Luôn | Lĩnh vực của văn bản nguồn nối bằng `", "`. | — |
| `source_path` | keyword | Luôn | Đơn vị nguồn (mục 9.6). | — |
| `source_in_phu_luc` | boolean | Luôn | `true` ⇔ `source_path` bắt đầu bằng "Phụ lục". | `true` 159 |
| `source_ngay_hieu_luc` | date \| `null` | Luôn | Ngày hiệu lực của đơn vị nguồn: ngày văn bản nêu riêng cho đơn vị đó (`hieu_luc_rieng`), hoặc `ngay_hieu_luc` của văn bản nguồn. | `null` 120 |
| `source_ngay_hoi_to` | date | Có khi `hieu_luc_tac_dong = ve_truoc` | Bằng `ngay_hoi_to` của văn bản nguồn. | 262 |

### 9.10.5. Văn bản đích

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `target_doc` | keyword | Luôn | Số hiệu đích như câu nguồn in, bỏ khoảng trắng: `70/2025/UBTVQH15`, `36-CP` (`900000015_0`). Luật nêu bằng tên không có số hiệu: tên luật, ví dụ `Luật Thi đua, khen thưởng`. | 17 quan hệ có tên luật |
| `target_matched_id` | integer \| `null` | Luôn | `_id` đích ở `legal-docs` nguồn. `null` khi công cụ chưa nối được. Khác `null` thì: khác `source_id`; ngày ban hành đích không sau `source_issuance_date`. | `null` 377 |
| `target_candidates_count` | integer | Luôn | Số văn bản có cùng số hiệu, gồm dạng bỏ năm. Từ 1 khi `target_matched_id` khác `null`. | — |
| `target_issuance_date` | date | Có khi câu trích có ngày | Ngày ban hành đích theo câu trích. Đích đã nối thì bằng `issuance_date` của đích, trừ khi có `target_match_note`. | 2.674 |
| `target_issuing_authority` | keyword | Có khi câu trích nêu cơ quan | Cơ quan ban hành đích theo câu trích. | 471 |
| `target_match_note` | keyword | Có khi ngày lệch | Chỉ có giá trị `lech_ngay_trich_dan`. | 10 (`697544_2`) |
| `target_section` | keyword | Có khi `extraction` là `llm` hoặc `llm+rules` | Phần của văn bản đích mà nhánh LLM đọc được. `quyet_dinh`: văn bản chính. `kem_theo`: văn bản ban hành kèm theo. `khong_ro`: câu không nói rõ. `khong_ap_dung`: tác động lên cả văn bản. | `quyet_dinh` 1.857, `khong_ap_dung` 617, `kem_theo` 604, `khong_ro` 192 |

### 9.10.6. Tác động

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `action` | keyword | Luôn | 13 giá trị ở bảng `hieu_luc_tac_dong` dưới. | `bai-bo` 919, `bo-sung` 897, `sua-doi` 798, `thay-cum-tu` 583, `thay-the` 243, `hop-nhat` 69, `huong-dan` 28, `quy-dinh-chi-tiet` 24, `dinh-chinh` 4, `ngung-hieu-luc` 4, `gia-han` 1, `huy-bo` 0, `dinh-chi` 0 |
| `scope` | text + keyword | Luôn | Phạm vi theo câu nguồn. Khác rỗng. Không có định dạng cố định. Có thể nêu nhiều vị trí, nối bằng `; `. Giá trị đặc biệt: `toàn bộ`, `một số điều`, `một số cụm từ`, `chưa xác định`. **Dùng `vi_tri` để nối, không dùng `scope`.** | — |
| `vi_tri` | mảng keyword | Luôn | Một Vị trí trong văn bản đích (mục 9.5), hoặc rỗng. Mảng không có quá một phần tử. `scope = toàn bộ` thì `vi_tri = ["toàn bộ"]`. | Rỗng 442, `toàn bộ` 581 |
| `cap_quan_he` | keyword | Luôn | Mức chi tiết của quan hệ (mục 9.10.8). | — |
| `hieu_luc_tac_dong` | keyword | Luôn | Ý nghĩa thời gian. Công cụ tính từ `action` và hồi tố (bảng dưới). | `ve_sau` 3.179, `ve_truoc` 262, `khong_ap_dung` 121, `tu_dau` 4, `tam_ngung` 4 |
| `unresolved` | boolean | Luôn | Trường của phạm vi. `true`: công cụ chưa xác nhận phạm vi. `scope = chưa xác định` thì `true`. **Không dùng trường này để quyết định cạnh.** Dùng `resolution_status`. | `true` 112 |
| `doi_tuong` | keyword | Có khi câu nguồn nêu phần bị tác động bằng tên, không bằng số | Tên phần bị tác động, như câu nguồn viết. Phần thuộc phụ lục (danh mục, thủ tục, biểu mẫu, phương án, dòng danh mục) có `vi_tri` là phụ lục chứa nó (mục 9.5.1). Ví dụ: `685249_0` (lượt `fix9-H56`), `vi_tri = ["Phụ lục"]`. Phần khác đi với `vi_tri` rỗng. Câu nêu cả phần lẫn vị trí điều khoản của nó thì có cả hai. `dinh-chinh` có thể có `phần căn cứ`, `phần Nơi nhận`. | 332 |
| `kem_theo` | boolean | Có ⇔ có `doi_tuong` | `true`: phần đó thuộc văn bản ban hành kèm theo văn bản đích. Vị trí trong phần kèm theo do `target_section` cho biết, không do `kem_theo`. `kem_theo` không đổi `cap_quan_he` khi `vi_tri` khác rỗng (mục 9.10.8). Ví dụ: `694022_0` (lượt `fix9-H56`) có `kem_theo = true`, `vi_tri = ["Phụ lục 1"]`, `cap_quan_he = vi_tri`. | `true` 123, `false` 209 |
| `chi_tiet_vi_tri` | keyword | Có khi tác động chỉ chạm một phần không có node riêng bên trong node `vi_tri` | Phần đó như câu nguồn viết: mẫu biểu, đoạn, câu, gạch đầu dòng của khoản, tiết, dòng số thứ tự. Ví dụ: `vi_tri = ["Phụ lục"]`, `chi_tiet_vi_tri = "Mẫu TP-TVPL-02-sđ"` (`694280_2`). Quy ước phụ lục cũng ghi ở đây chữ vị trí gốc đã đổi thành phụ lục (mục 9.5.1). Ví dụ: `692884_0` (lượt `fix9-H56`), `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri = "Mục II Phần B Phụ lục I"`. Các đoạn nối bằng `; `. Cạnh có trường này không làm cả node `vi_tri` chịu tác động. Chờ bên Graph chốt ([11](11-cau-hoi-graph.md#112-việc-2-cạnh-gắn-vào-node-chứa-tác-động-chỉ-lên-một-phần-của-node)). | 41 |
| `doi_tuong_loai` | keyword | Luôn | Loại đối tượng bị tác động (quy ước Q12). `van_ban`: văn bản đích hoặc một phần của nó. `thu_tuc_hanh_chinh`: một hoặc nhiều thủ tục hành chính do văn bản đích công bố. Công cụ gán `thu_tuc_hanh_chinh` khi phần bị tác động có tên là thủ tục. Công cụ cũng gán giá trị này cho dòng của danh mục thủ tục. | `van_ban` 3.388, `thu_tuc_hanh_chinh` 182 |
| `ma_thu_tuc` | keyword | Có khi `doi_tuong_loai = thu_tuc_hanh_chinh` và câu hoặc dòng có mã | Mã thủ tục quốc gia, dạng `<d>.<6 chữ số>`. Ví dụ: `1.002483` (`696924_0`). | 70 |
| `cum_tu` | mảng object | Có ⇔ `action = thay-cum-tu` | Khác rỗng. | 583 |
| `cum_tu[].cu`, `cum_tu[].moi` | keyword | Cùng `cum_tu` | Cụm từ cũ, cụm từ mới. Khác rỗng. | — |
| `cum_tu[].vi_tri` | mảng keyword | Cùng `cum_tu` | Bằng `vi_tri` của quan hệ. Quan hệ chỉ giữ các cặp áp dụng tại vị trí của nó (`683793_47`). | — |
| `dinh_chi_tu_ngay` | date \| `null` | Có khi `action` là `dinh-chi` hoặc `ngung-hieu-luc` | Ngày bắt đầu. Câu không ghi ngày thì bằng `source_ngay_hieu_luc`. | `2026-02-04` (`693902_0`) |
| `dinh_chi_den_ngay` | date \| `null` | Như trên | Ngày kết thúc. | `2026-04-15` (`693902_0`) |
| `dinh_chi_den_khi` | keyword \| `null` | Như trên | Điều kiện kết thúc, ghi bằng lời. Câu "… cho đến khi có kết luận thanh tra" cho `có kết luận thanh tra`. | — |
| `gia_han_den_ngay` | date \| `null` | Có khi `action = gia-han` | Ngày hết hiệu lực mới. "đến hết tháng 12 năm 2016" cho `2016-12-31`. | — |
| `gia_han_den_khi` | keyword \| `null` | Như trên | Điều kiện ("có văn bản thay thế") hoặc thời hạn thêm ("thêm 06 tháng"). | — |
| `detection_mode` | text + keyword | Có khi `_id` có tiền tố, hoặc `extraction = llm` | Mục 9.10.3. | — |

| `action` | `hieu_luc_tac_dong` |
| --- | --- |
| `sua-doi`, `bo-sung`, `bai-bo`, `thay-the`, `thay-cum-tu`, `gia-han` | `ve_sau`. Đổi thành `ve_truoc` khi văn bản nguồn hồi tố và đơn vị nguồn nằm trong `hoi_to_vi_tri`. |
| `huy-bo`, `dinh-chinh` | `tu_dau` |
| `dinh-chi`, `ngung-hieu-luc` | `tam_ngung` |
| `huong-dan`, `quy-dinh-chi-tiet`, `hop-nhat` | `khong_ap_dung` |

### 9.10.7. Trạng thái cạnh và nhánh dò

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `extraction` | keyword | Luôn | `rules`: chỉ nhánh quy tắc đọc được, QA giữ. `llm`: chỉ nhánh LLM đọc được, qua tầng kiểm. `llm+rules`: cả hai nhánh cùng đọc được. | `llm` 1.967, `llm+rules` 1.303, `rules` 300 |
| `resolution_status` | keyword | Luôn | `validated`: đủ căn cứ. Bên Graph dựng cạnh. `unresolved`: hành động có thật nhưng chưa đủ căn cứ. Quan hệ chờ duyệt, không có cạnh. | `validated` 3.380, `unresolved` 190 |
| `resolution_reason` | keyword \| `null` | Luôn | `null` ⇔ `validated`. Giá trị ở bảng dưới. | Bảng dưới |
| `evidence` | text | Có ⇔ `extraction` là `llm` hoặc `llm+rules` | Câu trích thực hiện hành động, tối đa 2.000 ký tự. Tầng kiểm đã xác nhận các đoạn của câu có trong văn bản nguồn. Các đoạn nối bằng ` … `. | 3.270 |

| `resolution_reason` | Nghĩa | Đo 21/10 | Ví dụ |
| --- | --- | --- | --- |
| `vi_tri_chua_xac_dinh` | Câu nêu tác động lên một phần, nhưng không nêu vị trí. | 78 | `697108_0` |
| `dich_chua_gan_cau_thuc_hien` | Có câu nêu hành động, văn bản có nêu đích, nhưng cấu trúc không gắn câu đó với đích. | 59 | `900000015_0` |
| `phan_kem_theo_chua_ro` | Vị trí có thể thuộc văn bản chính hoặc văn bản ban hành kèm theo. Câu không nói rõ. | 48 | `672539_2` |
| `van_ban_dich_khong_co_trong_nguon` | Văn bản đích không có trong đoạn nguồn mà LLM đọc. | 4 | `695439_0` |
| `vi_tri_khong_co_trong_nguon` | Số của vị trí không có trong đoạn nguồn. | 1 | `672540_36` |

Quy tắc:

1. `cap_quan_he = chua_xac_dinh` thì `resolution_status = unresolved` và `resolution_reason = vi_tri_chua_xac_dinh`. Quy tắc này đúng ở mọi nhánh.
2. Quan hệ `rules` và `llm+rules` là `validated`, trừ quy tắc 1.
3. Quan hệ `llm`: tầng phân giải và tầng kiểm quyết định `resolution_status` ([02, mục 2.5.8](02-luong-hoat-dong.md#258-nhánh-llm-4-tầng-và-gộp)).
4. `resolution_status` và `unresolved` là hai trường khác nhau. `672539_2` có `unresolved = false` và `resolution_status = unresolved`.

**Quan hệ bị loại.** Tầng kiểm loại hàng không có căn cứ. Hàng bị loại không ghi ES và không có `resolution_reason`. Lý do loại ghi ở `work/<run>/extract/<doc>/rejected.json`. Danh sách lý do ở [08, mục 8.2.2](08-quan-he-4-tang-va-danh-gia.md#822-trạng-thái-của-quan-hệ).

| Lý do loại | Nghĩa | Ví dụ (lượt `fix9-ho`) |
| --- | --- | --- |
| `ghi_chu_lich_su` | Văn bản đích chỉ có tên trong ghi chú lịch sử ("… đã được sửa đổi, bổ sung bởi/theo/tại …"), hoặc trong danh sách văn bản đi sau ghi chú đó. Tầng kiểm đọc toàn văn đơn vị, kể cả khi LLM chỉ đọc một phần của đơn vị (mục 9.2, bước 7). | 675210, `Điều 86 Khoản 4`: "… Luật Phí và lệ phí số 97/2015/QH13 đã được sửa đổi, bổ sung … theo Luật số 09/2017/QH14, …, Luật số 89/2025/QH15". Tầng kiểm loại `sua-doi`, `bo-sung` tới `89/2025/QH15`. |

Nhánh quy tắc dùng cùng luật ghi chú lịch sử, sau QA (mục 9.2, bước 8). Công cụ bỏ quan hệ đó và không ghi lý do.

### 9.10.8. Cấp quan hệ

Công cụ xét các dòng từ trên xuống. Công cụ chọn dòng đầu tiên có điều kiện đúng.

| # | `cap_quan_he` | Điều kiện | `vi_tri` | Đo 21/10 | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| 1 | `vi_tri` | `vi_tri` có một Vị trí khác `toàn bộ`. Câu nằm ở đâu cũng vậy: Điều, lời dẫn, tiêu đề. Quan hệ có cả `doi_tuong` cũng ở dòng này: phần nêu bằng tên thuộc phụ lục có `vi_tri` là phụ lục (mục 9.5.1). | Một phần tử | 2.547 | `694952_4`; `685249_0` (lượt `fix9-H56`): `vi_tri = ["Phụ lục"]` và có `doi_tuong` |
| 2 | `van_ban_kem_theo` | Có `doi_tuong` và `kem_theo = true`. Chỉ phần nêu bằng tên không thuộc phụ lục. | Rỗng | 98 | `696606_0` |
| 3 | `noi_dung` | Có `doi_tuong` và `kem_theo = false`. Chỉ phần nêu bằng tên không thuộc phụ lục. | Rỗng | 165 | `676559_0` |
| 4 | `van_ban` | `vi_tri = ["toàn bộ"]`; hoặc `detection_mode` là `intro`, `title_guidance`, `het_hieu_luc`, `hop_nhat`; hoặc `source_path` là `intro`, `Tiêu đề`, `Lời dẫn`, `Phần đầu`; hoặc `scope` là `toàn bộ`, `một số điều`, `một số cụm từ`. | `["toàn bộ"]` hoặc rỗng | 682 | `697547_0`, `697671_2` (`một số điều`) |
| 5 | `chua_xac_dinh` | Không đúng dòng nào ở trên. Công cụ ghi thêm quan hệ vào `work/<run>/review.jsonl`. | Rỗng | 78 | `697108_0` |

Cột "Đo 21/10" lấy từ dữ liệu chưa có quy ước phụ lục. Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (876 văn bản, code `8b023ca`), 9.760 quan hệ `validated`: `vi_tri` 8.452, `van_ban` 1.234, `noi_dung` 44, `van_ban_kem_theo` 30.

### 9.10.9. QA phạm vi

Các trường này chỉ có ở quan hệ đi qua QA của nhánh quy tắc (`extraction` là `rules` hoặc `llm+rules`). Khi nhánh LLM thay phạm vi của nhánh quy tắc, công cụ bỏ các trường này.

| Trường | Kiểu | Có | Quy tắc | Đo 21/10 |
| --- | --- | --- | --- | --- |
| `scope_resolution_method` | keyword | Có khi quy tắc xác nhận phạm vi | `explicit_declaration` hoặc `liet_ke_vi_tri`. Khi có, `scope_grounding_correct = true`. | `explicit_declaration` 858, `liet_ke_vi_tri` 79 |
| `scope_grounding_checked` | boolean | Có khi công cụ đã kiểm phạm vi | Chỉ có giá trị `true`. | 1.074 |
| `scope_grounding_correct` | boolean | Cùng `scope_grounding_checked` | `true`: dẫn chứng hỗ trợ phạm vi. `false` thì `unresolved = true`. | `true` 1.047, `false` 27 |
| `scope_grounding_suggestion` | text + keyword | Có khi model đề xuất mà công cụ không áp dụng | Phạm vi do model LLM đề xuất. Chỉ để tham khảo. | 216 |
| `llm_refined` | boolean | Có khi công cụ áp dụng đề xuất | Chỉ có giá trị `true`. Khi có, `scope_grounding_correct = true` và `unresolved = false`. | 24 (`hhl_697179_0`) |
| `llm_hallucination_rejected` | boolean | Có khi QA phạm vi không đạt | `true`: dẫn chứng của model không có trong văn bản nguồn. `false`: dẫn chứng có trong nguồn, nhưng model trả `correct = false`. | `true` 7, `false` 20 |

## 9.11. Cách nối cho đồ thị

ES chỉ lưu tác động trực tiếp. Bên Graph tính trạng thái hiệu lực từ các cạnh.

### 9.11.1. Node

| Node | ID | Lấy từ |
| --- | --- | --- |
| Văn bản | `<doc>` | `legal-docs-v4/<doc>` |
| Chương, Mục của văn bản | — | Trường `chuong`, `muc_lon` trên chunk. Không có chunk riêng. |
| Điều | `dieu_uid` | Chunk `dieu`, `dieu_full`, `dieu_mo_dau` |
| Khoản | `khoan_uid` | Chunk `khoan`, `khoan_full`, `khoan_mo_dau` |
| Điểm | `diem_uid` | Chunk `diem` |
| Tiểu điểm | `_id` của chunk `tieu_diem` | Chunk `tieu_diem` |
| Phụ lục | `<doc>_pl<i>` | Chunk `phu_luc`, hoặc Điều trong phụ lục |
| Đề mục, nội dung | `_id` của chunk `muc`, `noi_dung`, `noi_dung_full` | Chunk tương ứng |

Dựng một node cho mỗi `dieu_uid`, `khoan_uid` và `diem_uid`. Không dựng một node cho mỗi chunk: chunk `_full` và `_md` cùng thuộc một node. Ví dụ: khoản có điểm `683793_d13_k18` không có chunk `khoan` riêng, nhưng là `khoan_uid` của chunk `683793_d13_k18_pb`.

### 9.11.2. Từ vị trí sang node

| Vị trí | ID node | Ví dụ |
| --- | --- | --- |
| `Điều <x>` | `<doc>_d<x>` | `Điều 18` (`697543_4`) → `660468_d18` |
| `khoản <y> Điều <x>` | `<doc>_d<x>_k<y>` | `khoản 3 Điều 39` (`900000015_14`) → `660567_d39_k3` |
| `điểm <z> khoản <y> Điều <x>` | `<doc>_d<x>_k<y>_p<z>` | `điểm a khoản 1 Điều 8` (`694952_4`) → `643741_d8_k1_pa` |
| `tiểu điểm <n> điểm <z> khoản <y> Điều <x>` | `<doc>_d<x>_k<y>_p<z>_t<n>`. Văn bản đích không có tiểu điểm đó thì dùng node điểm. | `697176_24` có `target_section = kem_theo`, nên node nằm trong phụ lục: `622931_pl<i>_d37_k6_pb_t3` |
| `tên Điều <x>` | `<doc>_d<x>`. Cạnh tác động lên tên, không lên nội dung. | `tên Điều 7` (`694599_35`) → `88203_d7` |
| `Phụ lục <ký hiệu>` | `<doc>_pl<i>` với `phu_luc[i].ky_hieu` bằng ký hiệu | Văn bản 695478 có `phu_luc[1].ky_hieu = II`. `Phụ lục II` của văn bản này là `695478_pl1`. `694022_0` (lượt `fix9-H56`): `Phụ lục 1` → node phụ lục có ký hiệu `1` của văn bản `672745`. |
| `Mục <x> Phụ lục <ký hiệu>`, `Mục <x> Phần <y> Phụ lục <ký hiệu>` | Node phụ lục. Mục, Phần của phụ lục không có node riêng. Chỉ dữ liệu `-v4` hiện có còn dạng này (mục 9.5). | `Mục A Phụ lục I` (`696025_0`) → node phụ lục có `ky_hieu = I` |
| `toàn bộ` | Node văn bản | `697547_0` → `legal-docs/239508` |
| `Phụ lục` (không ký hiệu) | Chưa có node xác định. Văn bản đích có thể có nhiều phụ lục. Câu hỏi cho bên Graph ở [11, mục 11.6](11-cau-hoi-graph.md#116-việc-3-cạnh-vào-phụ-lục-không-nêu-ký-hiệu). | `697544_2`; `685249_0` (lượt `fix9-H56`). Đo 27/10/2026 (mục 9.5.1): 292/9.760 quan hệ `validated`. |
| `Chương <c>`, `tên Chương <c>`, `Mục <n> Chương <c>`, `tên Mục <n> Chương <c>`, `tên Mục <n>` | Chưa chốt. Chương và Mục không có node riêng (mục 9.11.1). | `tên Chương II` (`694501_126`), `tên Mục 1` (`694501_127`) |
| `tên văn bản` | Node văn bản. Cạnh tác động lên tên, không lên nội dung. | `694149_152` |

- Vị trí thuộc văn bản kèm theo thì ID có thêm `_pl<i>`. Ví dụ dạng ID: `697599_pl0_d3_k5`. Dữ liệu chỉ đánh dấu khi câu nguồn nói rõ (`target_section = kem_theo`). Công cụ không suy ra.
- Node đích chỉ có chunk khi văn bản đích có trong v4. Đo 21/10 trên 1.000 văn bản: 10/3.193 quan hệ có đích trong v4.

### 9.11.3. Cạnh

1. Mỗi quan hệ có `resolution_status = validated` cho một cạnh chi tiết. Quan hệ `unresolved` không có cạnh.
2. Bỏ qua quan hệ có vị trí ngoài định dạng (mục 9.5).
3. Phía nguồn: node theo `source_path`. `source_path` là `intro`, `Tiêu đề`, `Lời dẫn` hoặc `Phần đầu` thì phía nguồn là node văn bản. Dòng bảng và đề mục của phụ lục thì phía nguồn là node phụ lục.
4. Phía đích: node theo `vi_tri`. `vi_tri = ["toàn bộ"]`, hoặc `vi_tri` rỗng, thì phía đích là node văn bản. `vi_tri = ["Phụ lục"]` chưa có node xác định (mục 9.11.2).
5. Cạnh có `chi_tiet_vi_tri` chỉ chạm một phần của node đích (mục 9.10.6).
6. Cạnh tổng hợp nối văn bản nguồn với văn bản đích. Bên Graph dựng cạnh này từ `source_id` và `target_matched_id`. Quan hệ có `target_matched_id = null` không có cạnh tổng hợp.

### 9.11.4. Không lan tác động

| Ca | ES lưu | ES không lưu |
| --- | --- | --- |
| Sửa đổi, thay thế, bãi bỏ cả Điều | Một quan hệ vào node Điều | Quan hệ vào khoản, điểm của Điều đó |
| Bãi bỏ một khoản | Một quan hệ vào node khoản | Trạng thái của Điều chứa khoản |
| Bổ sung đơn vị mới (Điều 36a, khoản 1b) | Một quan hệ có vị trí của đơn vị mới (`697023_79`) | Node mới. Bên Graph tạo node nếu cần. |
| Chuỗi sửa đổi: câu nêu "khoản 3 Điều 17 Thông tư A, được sửa đổi tại Thông tư B" | Một quan hệ vào Thông tư A | Quan hệ vào Thông tư B. Câu đó là ghi chú lịch sử. |
| Văn bản hết hiệu lực | Quan hệ vào văn bản đó | Hết hiệu lực của văn bản quy định chi tiết nó |
| Thay cụm từ "trong toàn bộ Thông tư" | Một quan hệ có `vi_tri = ["toàn bộ"]` | Danh sách khoản có cụm từ |
| Công bố thủ tục hành chính | Không có quan hệ | Quan hệ tới văn bản nêu trong bảng thủ tục (`696022_pl0`, mục 9.9.4) |
| Bãi bỏ, sửa đổi, thay thế thủ tục đã công bố | Một quan hệ tới quyết định đã công bố thủ tục. `doi_tuong_loai = thu_tuc_hanh_chinh`, `doi_tuong` là tên thủ tục. `vi_tri` là phụ lục chứa thủ tục (`685249_0`, lượt `fix9-H56`). | Quan hệ lên Điều, khoản của quyết định đó. Cạnh nói về thủ tục, không về nội dung quyết định. |

Trạng thái hiệu lực của node (còn, hết một phần, hết toàn bộ, tạm ngừng) do bên Graph tính từ các cạnh. ES không lưu trạng thái này.

### 9.11.5. Thời gian trên cạnh

| Trường | Dùng để |
| --- | --- |
| `source_ngay_hieu_luc` | Ngày tác động bắt đầu với `ve_sau`. Đây là ngày hiệu lực của đơn vị nguồn. |
| `source_ngay_hoi_to` | Ngày tác động bắt đầu với `ve_truoc`. |
| `dinh_chi_tu_ngay`, `dinh_chi_den_ngay`, `dinh_chi_den_khi` | Khoảng tạm ngừng với `tam_ngung`. |
| `gia_han_den_ngay`, `gia_han_den_khi` | Ngày hoặc điều kiện kết thúc mới với `gia-han`. |
| `ngay_hieu_luc`, `ngay_hieu_luc_so_ngay` của chunk đích | Ngày hiệu lực của chính node đích. |

## 9.12. Bất biến để kiểm

Lệnh `python -m eval.check_contract v4` kiểm các bất biến này. Lệnh chỉ đọc ES. Cột cuối là kết quả đo ngày 22/10/2026 trên 11.000 văn bản của `-v4`: 237 quy tắc, 5 quy tắc có lỗi (`work/v4-2210-contract.txt`). Dữ liệu này ghi bằng code `2911b77` (mục 9.1).

Các bất biến đúng với quy ước phụ lục (mục 9.5.1). Quan hệ có `vi_tri` là phụ lục và có `doi_tuong` có `cap_quan_he = vi_tri` (dòng 14). `kem_theo` vẫn đi cùng `doi_tuong` (dòng 17). `Phụ lục` và `Phụ lục <ký hiệu>` đúng định dạng (dòng 10).

| # | Bất biến | Kết quả |
| --- | --- | --- |
| 1 | Mọi chunk có `doc_id` trong `legal-docs-v4`. Mọi văn bản có ít nhất một chunk. | Đạt |
| 2 | `tieu_de + noi_dung` của chunk khác rỗng. | Đạt |
| 3 | `_id` chunk bắt đầu bằng `dieu_uid`. `in_phu_luc` ⇔ `_id` có `_pl<i>`. `segment > 0` ⇔ `_id` có `_s<s>`. | Đạt |
| 4 | `vi_tri` có tối đa một phần tử. | Đạt |
| 5 | `scope = toàn bộ` thì `vi_tri = ["toàn bộ"]`. `scope = chưa xác định` thì `unresolved = true`. | Đạt |
| 6 | `source_in_phu_luc` ⇔ `source_path` bắt đầu bằng "Phụ lục". `source_path` đúng dạng mục 9.6. | Đạt |
| 7 | `target_matched_id` khác `source_id`. Có `target_matched_id` thì `target_candidates_count ≥ 1` và ngày đích không sau ngày nguồn. | Đạt |
| 8 | `la_vbqppl = null` ⇔ `la_vbqppl_cach = can_kiem`. | Đạt |
| 9 | `ngay_het_hieu_luc = null` ⇔ `khong_ghi`. `hoi_to` ⇔ có `ngay_hoi_to`. | Đạt |
| 10 | Vị trí đúng định dạng mục 9.5. | Không đạt: 198/38.323 vị trí (`502519_19`, `676974_0`, `693608_0`). Đo 21/10/2026 trên lượt `v4-10000`: 196/198 là `Mục` hoặc `Phần` đứng một mình (docs/08 mục 8.11.8). Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho` (code `8b023ca`): 0/9.906 vị trí. |
| 11 | `noi_nhan` không có dòng chữ ký. | Không đạt: 48/11.000 văn bản (`676778`, `677730`, `677789`). |
| 12 | `phu_luc[].n_table_rows` bằng số dòng bắt đầu bằng `\|`. | Không đạt: 3/11.788 phần tử (`681303_pl0`, `693632_pl0`, `695959_pl0`). |
| 13 | Mọi quan hệ có `resolution_status`, `extraction`, `doi_tuong_loai`. `resolution_reason = null` ⇔ `validated`. | Đạt |
| 14 | `cap_quan_he = chua_xac_dinh` thì `unresolved` và `vi_tri_chua_xac_dinh`. `cap_quan_he` đúng thứ tự xét ở mục 9.10.8: `vi_tri` khác rỗng và khác `["toàn bộ"]` thì `vi_tri`, kể cả khi có `doi_tuong`. | Đạt |
| 15 | Tiền tố `_id` khớp `detection_mode`. `detection_mode = llm` ⇔ `extraction = llm`. `n` đếm từ 0, không khuyết. | Đạt |
| 16 | `evidence` và `target_section` có ⇔ `extraction` là `llm` hoặc `llm+rules`. | Đạt |
| 17 | `kem_theo` có ⇔ `doi_tuong` có. | Đạt |
| 18 | `cum_tu` có ⇔ `action = thay-cum-tu`. `cum_tu[].vi_tri = vi_tri`. | Đạt |
| 19 | `hieu_luc_tac_dong` khớp `action` (mục 9.10.6). `source_ngay_hoi_to` có ⇔ `ve_truoc`. | Đạt |
| 20 | Không bản ghi nào có trường ngoài hợp đồng. | Đạt |
| 21 | `phu_luc[].dieu_luat[].ky_hieu` bắt đầu bằng `so_dieu` (mục 9.8.5). | Không đạt: 1/20.660 Điều (`682123_pl0_d07`). |
| 22 | `scope_grounding_correct = false` thì `unresolved = true` (mục 9.10.9). | Không đạt: 1/255 quan hệ (`677855_0`). Quan hệ chỉ do nhánh quy tắc đọc, phạm vi là danh sách số thứ tự. |

## 9.13. Giới hạn đã biết

| Giới hạn | Ảnh hưởng | Chi tiết |
| --- | --- | --- |
| v4 chỉ có văn bản ban hành từ 08/10/2025 đến 30/09/2026. | Phần lớn văn bản đích chưa có trong v4. Node đích chưa có chunk. Đo 21/10 trên 1.000 văn bản: 10/3.193 quan hệ có đích trong v4. | Mục 9.1. Đợt 10.000 văn bản tiếp theo chưa chạy. |
| Phụ lục không chia Điều là một chunk. | Vector của `convert` chỉ đại diện phần đầu phụ lục. Đo 21/10 trên 1.000 văn bản: 851 chunk `phu_luc`. | Mục 9.9 |
| Thủ tục hành chính không có node. | Quan hệ lên thủ tục trỏ vào văn bản đã công bố thủ tục, `vi_tri` là phụ lục chứa thủ tục. Bên Graph dùng `doi_tuong_loai` để tách cạnh lên thủ tục. | Mục 9.5.1, 9.10.6, 9.11.4 |
| `Phụ lục` không ký hiệu không chỉ tới một node phụ lục. | Bên Graph chưa nối được cạnh vào một phụ lục cụ thể. Đo 27/10/2026 trên lượt `fix9-H56` và `fix9-ho`: 292/9.760 quan hệ `validated`, 150 quan hệ trong số đó còn `doi_tuong`. | Mục 9.5.1, 9.11.2, [11, mục 11.6](11-cau-hoi-graph.md#116-việc-3-cạnh-vào-phụ-lục-không-nêu-ký-hiệu) |
| `chi_tiet_vi_tri` của quy ước phụ lục có thể lặp một đoạn. | Ví dụ "Phụ lục stt 6; stt 6" (`680742_0`, lượt `fix9-ho`). Đo 27/10/2026: 12/197 quan hệ `validated` có `chi_tiet_vi_tri`. | Mục 9.5.1 |
| Chương và Mục của văn bản đích chưa có node chốt. | Bên Graph chưa nối được cạnh có các vị trí này. | Mục 9.11.2 |
| Dữ liệu `-v4` hiện có còn vị trí ngoài định dạng, phần lớn là `Mục <số La Mã>` đứng một mình. | 198/38.323 vị trí (22/10/2026). Bên Graph bỏ qua các cạnh này. Code `8b023ca` đổi các vị trí này thành phụ lục: 0/9.906 vị trí ngoài định dạng (27/10/2026, lượt `fix9-H56` và `fix9-ho`). | Mục 9.1, 9.12 dòng 10 |
| Parser tách biểu mẫu trong phụ lục thành Điều 1 ("Điều 1. Cho phép … (Tên tổ chức, cá nhân) …"). | Tìm kiếm trả về Điều 1 của biểu mẫu. Vị trí `Điều 1` của văn bản đích có thể trỏ nhầm node. Đo 26/10/2026 trên `legal-chunk-section-v4`: khoảng 187 văn bản, ước lượng bằng dấu hiệu chữ. Ví dụ: 279/QĐ-BNNMT có hơn 100 phụ lục kiểu này. | [10, mục 10.2](10-khoang-trong-du-lieu.md#102-cấu-trúc-và-chunk) |
| Parser ghi cùng một Điều 1 từ hai lần trở lên, dưới mã khác nhau. | Tìm kiếm trả về hai lần. Đo 26/10/2026: 8 văn bản, tới 24 văn bản nếu chỉ so 400 ký tự đầu. Ví dụ: 53/2025/TT-NHNN, 08/2026/TT-BNNMT. Hai Điều 1 khác nội dung thường hợp lệ: Điều 1 của quyết định và Điều 1 của quy định kèm theo (`<doc>_d1`, `<doc>_pl0_d1`; 1.083 văn bản). | [10, mục 10.2](10-khoang-trong-du-lieu.md#102-cấu-trúc-và-chunk) |
| Công cụ có thể cắt sai tên luật ở `target_doc`. | `hd_697309_0` có `target_doc = Luật Đã` và `target_matched_id = null`. | — |
| Kết quả LLM đổi giữa các lượt chạy, kể cả khi temperature bằng 0. | Cùng code, hai lượt lệch 2–4 điểm ở mức quan hệ. Một dòng bảng có thể có quan hệ ở lượt này, không có ở lượt khác. | [08, mục 8.8.4](08-quan-he-4-tang-va-danh-gia.md#884-chốt-luồng-20102026) |
| Nhãn chuẩn do LLM gán. Chưa có nhãn của người. | Chỉ số quan hệ và metadata có thể lệch. | [08, mục 8.5](08-quan-he-4-tang-va-danh-gia.md) |
| Văn bản có toàn văn tiếng Anh. | Công cụ bỏ qua văn bản đó: không ghi văn bản, chunk, quan hệ. Nhật ký ghi `skipped = tieng_anh`. | [02, mục 2.4](02-luong-hoat-dong.md#24-luồng-một-văn-bản) |

Các giới hạn khác và quyết định đã chốt ở [07-gioi-han-va-can-chot.md](07-gioi-han-va-can-chot.md).
