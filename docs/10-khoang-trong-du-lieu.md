# 10. Khoảng trống dữ liệu: văn bản có, dữ liệu chưa có

Tài liệu này liệt kê các thành phần mà văn bản pháp luật thật sự có, nhưng dữ liệu v3, v4 chưa lưu hoặc lưu chưa đúng. Mỗi khoảng trống có số lượng đo được, ví dụ có ID và cách xử lý đề xuất. Dùng tài liệu này để chọn việc, ước khối lượng và đo lại sau khi sửa.

- Kho nguồn: 518.261 văn bản, 10.331.917 chunk v2, 180.452 quan hệ v2 (đo 16/10/2026).
- "Ước toàn kho" là tỉ lệ trên mẫu nhân với 518.261. Mẫu 10.000 văn bản có sai số khoảng ±1 điểm phần trăm.
- Nguồn của từng số liệu ở mục 10.7.
- Hợp đồng dữ liệu hiện tại ở [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md). Giới hạn đã chốt ở [07](07-gioi-han-va-can-chot.md).

## 10.1. Tóm tắt

Trạng thái ngày 28/10/2026. Mỗi ô ghi ngày đo. Các bảng "Cập nhật" dưới đây ghi thay đổi theo ngày.

| # | Khoảng trống | Số lượng | Ảnh hưởng | Cần quyết định |
| --- | --- | --- | --- | --- |
| S1 | Phụ lục không chia Điều là một chunk | 40,1% văn bản có phụ lục (~208.000). 42% tổng chữ của kho nằm trong các chunk này. `-v4` từ 28/10/2026: thêm 377.099 đoạn `phu_luc_doan`. Danh mục chưa có chunk theo dòng. | Tìm kiếm | Không |
| R2 | Danh mục văn bản trong phụ lục không được đọc để tìm quan hệ | ~0,6% văn bản (~3.000), mỗi văn bản hàng chục dòng | Quan hệ, Graph | Không |
| R1 | Độ phủ quan hệ thấp | Đợt 20.000 (28/10/2026, có trọng số, nhãn agent): phát hiện R 0,804. Hold-out 300 (27/10/2026): 0,861. Lần đo đầu, Blind (15/10/2026): 48,3% theo quan hệ. Mục tiêu 85%. | Graph | Không |
| S2 | Chunk lá dài hơn vector | 6,4% chunk v4 (1.452, 16/10/2026). `-v4` có vector đủ độ dài từ 26/10/2026. v2, v3 còn cắt 256 token. | Tìm kiếm | Không |
| S3 | Chương, Mục của Luật không có chunk, node, trường số | 11,2% văn bản (~57.800) | Graph, tìm kiếm | Có |
| S4 | Đề mục con của văn bản không chia Điều không có chunk | 12,9% văn bản (~66.800) | Tìm kiếm, Graph | Có |
| R3 | Thủ tục hành chính không có loại thực thể | 8,3% văn bản (~43.000) | Graph | Có |
| M1 | Văn bản không có ngày hiệu lực | ~9,2% văn bản (~47.500). 11,6% văn bản quy phạm. | Graph (thời gian) | Không |
| R5 | Phạm vi (vị trí, phần bị tác động) chưa đủ chính xác | Đợt 20.000 (28/10/2026, có trọng số, nhãn agent): phạm vi P 0,785, R 0,695. Hold-out 300 (27/10/2026): P 0,711, R 0,673. Lần đo đầu, Blind (15/10/2026): vị trí LLM đúng 77,7%, regex 85,4%. | Graph | Không |
| R4 | Vị trí không theo điều – khoản – điểm không có node | Quy ước phụ lục: thành `Phụ lục <n>` hoặc `Phụ lục`, chữ gốc ở `chi_tiet_vi_tri`. `-v4`: 10.990/70.954 quan hệ `validated` có `Phụ lục` không số (28/10/2026). | Graph | Có: cách nối `Phụ lục` không số |
| R6 | Nhóm quan hệ yếu | Blind: hủy bỏ 0%, văn bản không chia Điều có sửa đổi 0%, văn bản cũ 50%, hướng dẫn 57% | Graph | Không |
| S6 | Lỗi tách cấu trúc còn lại | 12% văn bản Blind (30/250) | Mọi index | Không |
| S8 | Điều 1 lặp; biểu mẫu trong phụ lục tách thành Điều | Biểu mẫu: đã sửa (`c394162`), có trong `-v4` từ 28/10/2026. Nhân bản: 8 văn bản (26/10/2026), chưa sửa. | Tìm kiếm, Graph | Không |
| S9 | Văn bản không có Điều: đoạn cuối bị xếp vào phần kết | Khoảng 49/2.000 văn bản của mẫu đợt 20.000 (28/10/2026) | Quan hệ, tìm kiếm | Không |
| S10 | Điều có phần đánh số La Mã bên trong: chỉ phần I vào chunk | Chưa đo. Ví dụ 672797 mất 87% chữ (28/10/2026). | Tìm kiếm, quan hệ | Không |
| R9 | Tầng trích cắt nội dung đơn vị ở 6.000 ký tự | Chưa đo. Ví dụ 669605 (28/10/2026). | Quan hệ | Không |
| R8 | Index cũ `legal-changed` còn quan hệ sai | 164.965 quan hệ trên cả hai cụm ES | Bên nào còn đọc index cũ | Có |
| D1 | Luồng mới chưa ghi vào index | v3: 236 văn bản (0,05% kho). v4: 30.988 văn bản (6,0% kho), 30.981 văn bản ghi bằng code `1117e63` ngày 27–28/10/2026 (đếm 28/10/2026). | Mọi bên | Có |

Ký hiệu nhóm: S là cấu trúc và chunk, M là metadata văn bản, R là quan hệ, D là triển khai.

Cập nhật 19/10/2026 (code, chưa ghi vào index; kết quả ở [08, mục 8.6](08-quan-he-4-tang-va-danh-gia.md#86-vòng-sửa-ngày-19102026)):

- R2: chế độ `llm` đọc dòng bảng của phụ lục không chia Điều. Chế độ `rules` chưa đọc.
- R4: vị trí ngoài định dạng chuyển sang `doi_tuong`.
- R1: hold-out mới đạt P 93,4%, R 75,2%. Blind trừ `review50` đạt P 86,7%, R 56,3%.
- S7: `noi_nhan` hết khối chữ ký nằm cùng dòng bảng (lỗi có ở 338/532 văn bản v4).

Cập nhật 20/10/2026 (luồng chốt, chưa ghi vào index; kết quả ở [08, mục 8.8](08-quan-he-4-tang-va-danh-gia.md#88-vòng-3-20102026-và-hold-out-3)):

| # | Trạng thái mới |
| --- | --- |
| R1 | Hold-out 3 (158 văn bản mới): quan hệ P 96,9%, R 93,1%; mức văn bản R 92,6%; mức Điều khoản R 73,7%. Mục tiêu 85% đạt ở mức quan hệ và văn bản, chưa đạt ở mức Điều khoản. |
| R2 | Đã làm ở chế độ `llm`: Điều "bãi bỏ các văn bản tại Phụ lục, Danh mục, Danh sách kèm theo" cho một quan hệ với mỗi văn bản. Phụ lục viết thành đoạn văn được đọc theo đề mục. |
| R3 | Dòng danh mục thủ tục có quan hệ lên quyết định đã công bố thủ tục, tên thủ tục ở `doi_tuong` (quy ước Q5, [07](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt)). Thực thể thủ tục vẫn chưa có. |
| R4 | Đã làm: vị trí ngoài định dạng thành `doi_tuong`. |
| R5 | Vị trí đúng trên hold-out 3: 78,1% (code vòng 3). Sau đó nhánh quy tắc sửa lỗi đọc danh sách vị trí lẫn cấp; chưa có hold-out mới để đo lại. |
| R6 | Hold-out 3 theo nhóm (quan hệ R): hủy bỏ 100%, thay thế 100%, sửa đổi 96,6%, hướng dẫn 60%, văn bản cũ 0% (2 quan hệ: một lệch dạng số hiệu "31/CP-1996", một bị sót). Mỗi nhóm có 4–12 văn bản. |
| D1 | Luồng chốt 20/10/2026. Chưa ghi index. Ghi lại cần duyệt. |

Cập nhật 21–27/10/2026. Trạng thái trước lượt ghi đêm 27–28/10/2026: index `-v4` có 11.000 văn bản, ghi lại 22/10/2026 bằng code `2911b77`. Code `8b023ca` (27/10/2026) chưa ghi ES. Các mốc code ở [05, mục 5.2.4](05-phien-ban-v2-v3-v4.md#524-thay-đổi-code-2227102026).

| # | Trạng thái mới |
| --- | --- |
| R1 | Bộ chấm 27/10/2026, phát hiện P / R. Hold-out 300 (độc lập, nhãn agent chưa qua người duyệt): 0,900 / 0,861. H5 + H6 (đã dùng để sửa): 0,895 / 0,873. Mục tiêu 85% đạt ở R của phát hiện. Chi tiết ở [05, mục 5.4.3](05-phien-ban-v2-v3-v4.md#543-chất-lượng-đo-được). |
| R2 | 22/10/2026: danh mục ở phụ lục mọi dạng (danh sách đánh số, bảng) và câu ngoài bảng (quy tắc 15, 16). H5 + H6, phát hiện R: 0,765 → 0,873 ([08, mục 8.14](08-quan-he-4-tang-va-danh-gia.md#814-sửa-lỗi-sau-benchmark-500-văn-bản-22102026)). Đã có trong `-v4`. |
| R4 | 26–27/10/2026: quy ước phụ lục. Vị trí không theo điều – khoản – điểm thành `Phụ lục <n>` hoặc `Phụ lục`. Chưa có trong `-v4`. Chi tiết ở R4. |
| R5 | Bộ chấm 27/10/2026, phạm vi P / R. Hold-out 300: 0,711 / 0,673. H5 + H6: 0,833 / 0,773. Lỗi còn lại theo cơ chế ở [07, mục 7.2](07-gioi-han-va-can-chot.md#72-lỗi-dữ-liệu-đã-biết). |
| S8 | Khoảng trống mới (26/10/2026): Điều 1 lặp và biểu mẫu tách thành Điều. Chưa sửa. |
| D1 | v4: 11.000 văn bản (2,1% kho) từ 22/10/2026. Ghi lại v3 cần bên Graph duyệt v4. |

Cập nhật 28/10/2026. Đêm 27–28/10/2026, công cụ ghi `-v4` bằng code `1117e63`: 19.988 văn bản mới và ghi lại 11.000 văn bản cũ. Chi tiết lượt ghi ở [05, mục 5.2.4](05-phien-ban-v2-v3-v4.md#524-thay-đổi-code-2227102026).

| # | Trạng thái mới |
| --- | --- |
| R1 | Đợt 20.000, mẫu 2.000 văn bản, nhãn agent chưa người duyệt. Phát hiện có trọng số: P 0,901 [0,873–0,922], R 0,804 [0,750–0,852]. Chi tiết ở [05, mục 5.4.3](05-phien-ban-v2-v3-v4.md#543-chất-lượng-đo-được). |
| R4 | Quy ước phụ lục có trong `-v4`. 10.990/70.954 quan hệ `validated` có `Phụ lục` không số. |
| R5 | Đợt 20.000, phạm vi có trọng số: P 0,785 [0,713–0,842], R 0,695 [0,630–0,752]. |
| S1, S2 | `-v4` có vector đủ độ dài. Thêm đoạn tìm kiếm `phu_luc_doan` (377.099) và `muc_doan` (101.033). |
| S8 | Biểu mẫu trong phụ lục không còn tách thành Điều (`c394162`). Nhân bản Điều chưa sửa. |
| S9, S10, R9 | Khoảng trống mới, tìm thấy khi chấm đợt 20.000. Chưa sửa. |
| D1 | v4: 30.988 văn bản (6,0% kho). 17 văn bản lỗi. Đợt tiếp theo chưa có lệnh chạy. v3: 236 văn bản (thêm 32 văn bản ngày 27/10/2026, người dùng duyệt). |

## 10.2. Cấu trúc và chunk

### S1. Phụ lục không chia Điều là một chunk

Mỗi phụ lục không chia Điều là một chunk `phu_luc`. Chunk này chứa cả bảng, danh mục hoặc biểu mẫu. Vector chỉ đại diện khoảng 200 từ đầu.

| Chỉ số (mẫu 10.000, 15/10/2026) | Giá trị | Ước toàn kho |
| --- | --- | --- |
| Văn bản có phụ lục | 40,1% | ~208.000 |
| Văn bản có bảng (ở bất kỳ đâu) | 37,1% | ~192.000 |
| Văn bản có danh mục hoặc danh sách | 15,5% | ~80.000 |
| Văn bản có biểu mẫu | 4,8% | ~25.000 |
| Phụ lục lưu thành một chunk (không chia Điều) | 85,2% số phụ lục | ~320.000 phụ lục |
| Phụ lục một chunk dài hơn 1.000 ký tự | 89,1% của nhóm trên | — |
| Chữ nằm trong phụ lục một chunk | 42,1% tổng ký tự của kho | — |
| Dòng bảng trong phụ lục một chunk | 318.673 dòng | ~16,5 triệu dòng |

Loại phụ lục, tính theo số phụ lục: bảng khác 33,9%, danh mục 28,6%, quy định có Điều 14,8%, biểu mẫu 12,4%, văn bản thường 10,3%. Trung vị độ dài: danh mục 3.981 ký tự, biểu mẫu 3.492, bảng 3.441.

Ví dụ: `683636_pl1` là danh mục 25 quyết định bị bãi bỏ, dài 11.324 ký tự, lưu trong một chunk.

Đề xuất: giữ chunk `phu_luc` làm chunk đầy đủ. Thêm đoạn con khoảng 200 từ. Mỗi đoạn con lặp lại tiêu đề phụ lục và dòng tên cột. Danh mục văn bản: mỗi dòng một chunk (khoảng 3.000 văn bản). Số chunk tăng khoảng 3,9 triệu (+38%).

Trạng thái 28/10/2026: đã làm đoạn con (`c394162`, `57b9033`). Chunk `phu_luc` giữ ID làm node. Đoạn con là chunk `phu_luc_doan` (`<id>_doan<k>`, trường `so_doan`, `phu_luc_uid`), dài 300 từ. Đoạn cắt ở dòng bảng, đoạn văn hoặc câu. Đoạn trong bảng lặp dòng tên cột. `-v4` có 377.099 chunk `phu_luc_doan` và 701.376 chunk trong phụ lục. Danh mục văn bản chưa có chunk theo dòng.

### S2. Chunk lá dài hơn vector

Embedding cắt đầu vào ở 256 token, khoảng 200 từ. Chunk `_full` dài không mất gì, vì chunk con đã có vector. Chunk lá không có chunk con, nên phần sau khoảng 200 từ không có trong vector nào.

| `chunk_type` (v4, 16/10/2026) | Dài hơn 200 từ | Tỉ lệ trong loại |
| --- | --- | --- |
| `phu_luc` | 490 | 89% |
| `khoan` | 368 | 5% |
| `muc` | 229 | 53% |
| `diem` | 201 | 3% |
| `dieu` | 108 | 7% |
| `tieu_diem`, `dieu_mo_dau`, `khoan_mo_dau` | 56 | 1–7% |
| **Tổng chunk lá** | **1.452** | **6,4% tổng chunk** |

Ví dụ: `478253_mV` (đề mục V của một Kế hoạch) dài 3.668 từ. `478253_pl0` dài 57.301 từ.

Đề xuất: chia đoạn con khoảng 200 từ cho mọi chunk lá dài, giống `noi_dung` hiện nay. Đoạn con không là node đồ thị. Đoạn con cần hậu tố ID mới, khác `_p` (điểm) và `_s` (chuỗi Điều kèm theo).

Trạng thái 28/10/2026: `-v4` có vector đủ độ dài (`57b9033`). Dịch vụ cắt ở 8.192 token. Chunk `phu_luc`, `muc` dài có thêm đoạn `phu_luc_doan`, `muc_doan` (hậu tố `_doan<k>`). Chunk lá `khoan`, `diem`, `dieu` dài không có đoạn con. Với vector đủ độ dài, nhóm này không mất chữ khi tìm bằng vector. v2, v3 vẫn có khoảng trống này.

### S3. Chương, Mục của Luật không có chunk, node, trường số

Chương và Mục chỉ là hai trường chữ `chuong`, `muc_lon` lặp lại trên mọi chunk của Điều bên trong. Không có chunk, không có ID node, không có trường số. Kiểu trường là `text`, nên không lọc chính xác được.

| Chỉ số (mẫu 10.000, 16/10/2026) | Phần chính | Văn bản kèm theo | Gộp | Ước toàn kho |
| --- | --- | --- | --- | --- |
| Có Chương | 209 | 875 | 1.082 (10,8%) | ~56.000 |
| Có Mục trong Chương | 81 | 109 | 188 (1,9%) | ~9.700 |
| Có ít nhất một cấp trên Điều | 223 | — | 1.115 (11,2%) | ~57.800 |

- Văn bản kèm theo (Quy chế, Quy định ban hành kèm theo Quyết định) chiếm 81% số văn bản có Chương.
- Theo loại văn bản: Luật 92% có Chương, Pháp lệnh 86%, Văn bản hợp nhất 79%, Nghị định 42%, Thông tư 35%, Quyết định 17%.
- v4 có 31/2.009 quan hệ (1,5%) có vị trí là Chương hoặc Mục. Các quan hệ này không có node đích. Ví dụ: `288269_27` có `vi_tri = tên Chương IV`.
- Văn bản sửa và văn bản bị sửa có thể đánh số khác nhau. `206663` viết "Chương 4", `288269` gọi là "Chương IV".
- Parser cắt Chương và Mục đúng: không có tiêu đề nào lọt vào nội dung Điều. 2/209 văn bản gán thiếu Chương (`146745`, `470235`).

Đề xuất: thêm chunk `chuong` (`<doc>_c<n>`) và `muc_lon` (`<doc>_c<n>_m<k>`). Thêm trường `chuong_uid`, `so_chuong`, `so_muc_lon` dạng số đã chuẩn hóa trên chunk của Điều. Chuẩn hóa số trong `vi_tri`.

### S4. Đề mục con của văn bản không chia Điều

Văn bản không chia Điều (công văn, kế hoạch, chỉ thị) có chunk `muc` cho đề mục cấp lớn nhất. Đề mục con nằm chung trong chunk cha. Tên đề mục nằm ở dòng đầu `noi_dung`, không nằm ở `tieu_de`.

| Chỉ số (mẫu 10.000, 16/10/2026) | Giá trị | Ước toàn kho |
| --- | --- | --- |
| Văn bản không chia Điều | 39,7% | ~205.500 |
| Có đề mục | 2.300 (23,0% kho) | ~119.200 |
| Có đề mục con (1, 2 hoặc a, b trong đề mục lớn) | 1.288 (12,9% kho) | ~66.800 |

Ví dụ: `478253_mV` chứa đề mục "1. Phòng, chống một số bệnh truyền nhiễm …" và các đề mục con khác trong cùng một chunk.

Đề xuất: đưa tên đề mục vào `tieu_de`. Tạo chunk con cho đề mục con, có `muc_uid` của đề mục cha.

Trạng thái 28/10/2026: đề mục dài có thêm đoạn tìm kiếm `muc_doan` (150 từ, trường `muc_uid`, `so_doan`). `-v4` có 101.033 chunk `muc_doan`. Đoạn tìm kiếm cắt theo độ dài, không theo đề mục con. Đề mục con vẫn chưa có chunk, chưa có node.

### S5. Tiểu mục và Phần

| Cấp | Mẫu 10.000 | Ước toàn kho | Hiện trạng |
| --- | --- | --- | --- |
| Tiểu mục | 1 văn bản | ~50 | Parser không nhận. Dòng tiêu đề không nằm trong chunk nào. Ví dụ: `681813` mất dòng "Tiểu mục 1 – QUY ĐỊNH CHUNG VỀ ĐƯỜNG NGANG". |
| Phần (trên Chương) | 0 văn bản thật | ~0 | 12 văn bản có dòng "Phần …" trước Điều cuối. Kiểm tay 3 văn bản: cả 3 không phải cấp trên Điều (`17422`, `165959`, `70528`). |

Đề xuất: parser nhận "Tiểu mục" là một cấp để không mất chữ. Không cần node riêng.

### S6. Lỗi tách cấu trúc còn lại

Bộ Blind (250 văn bản, 15/10/2026): 30 văn bản (12%) có lỗi cấu trúc với parser mới.

| Loại lỗi | Số lỗi | Ví dụ |
| --- | --- | --- |
| Gộp sai (hai đơn vị thành một) | 19 | `575020` |
| Tách sai (một đơn vị thành hai) | 11 | `303189` |
| Thiếu nội dung | 8 | `411815` |
| Nhãn Điều sai | 2 | `268635` |

Các mẫu lỗi đã gặp:

- Điều không có tên: câu đầu bị lấy làm tên Điều.
- Nội dung mới không có ngoặc kép bị tách thành đơn vị của văn bản nguồn.
- Số chú thích dạng `2[14]`.
- Dòng trích dẫn bắt đầu bằng "Điều 14 Nghị định số …" bị nhận là một Điều. Ví dụ: `70528` là Thông tư không chia Điều, nhưng bị xếp thành văn bản có Điều.

Bộ Blind thiên về văn bản có quan hệ. Không nhân tỉ lệ 12% cho toàn kho.

Lỗi Điều 1 lặp và biểu mẫu tách thành Điều ở mục S8.

### S7. Lỗi đã sửa trong code, còn trong dữ liệu v3, v4

| Lỗi | v3 (204) | v4 cũ (532, 16/10/2026) | v4 (11.000, 21/10/2026) | Hết khi |
| --- | --- | --- | --- | --- |
| `noi_nhan` chứa dòng chữ ký khi văn bản không có mục "Nơi nhận" | 11 | 18 | 48 ([08, mục 8.11.8](08-quan-he-4-tang-va-danh-gia.md#8118-ghi-thêm-10000-văn-bản-vào-v4-2122102026)) | Ghi lại. Sau khi ghi lại còn 48: code chưa sửa hết. |
| Đề mục đầu tiên chứa phần đầu văn bản (quốc hiệu, số hiệu). Ví dụ `318496_m1`, `478253_mI`. | Chưa đo | Chưa đo | Chưa đo | Ghi lại |

### S8. Điều 1 lặp và biểu mẫu tách thành Điều

Một văn bản có thể có nhiều Điều 1 hợp lệ. Ví dụ: Điều 1 của quyết định và Điều 1 của quy định ban hành kèm theo. Mỗi Điều 1 có `dieu_uid` riêng. Lỗi là khi parser tạo Điều 1 từ chỗ không phải Điều, hoặc tạo cùng một Điều 1 hai lần.

| Nhóm (`legal-chunk-section-v4`, 26/10/2026) | Số văn bản | Hợp lệ | Ví dụ (kiểm 27/10/2026) |
| --- | --- | --- | --- |
| Văn bản có Điều 1 | 8.709 | — | — |
| Có từ 2 Điều 1, `dieu_uid` khác nhau | 1.295 (khoảng 15%) | — | — |
| – Điều 1 của quyết định và Điều 1 của quy định kèm theo (`_d1`, `_pl0_d1`) | 1.083 | Có | `679976` (199/2025/QĐ-UBND): `679976_d1`, `679976_pl0_d1` |
| – Nhiều văn bản hoặc phụ lục kèm theo, mỗi cái một Điều 1 | 14 | Phần lớn có | `683086` (167/2025/QĐ-UBND): `683086_d1`, `683086_pl0_d1`, `683086_pl1_d1`. Cần xem lại `680927` (039/2025/QĐ-UBND): toàn văn có Quy chế hai lần, hai bản khác nhau một chữ. |
| – Biểu mẫu trong phụ lục bị tách thành Điều 1 | Khoảng 187 | Không. Lỗi tách cấu trúc. | `694210` (279/QĐ-BNNMT): 63/180 phụ lục có Điều 1, ví dụ `694210_pl27_d1`: "Cho phép …… (Tên tổ chức, cá nhân) ……". `688084` (53/2025/TT-NHNN): 7 mẫu quyết định "Chấp thuận …" thành Điều 1. |
| – Cùng một Điều 1 xuất hiện từ 2 lần, dưới mã khác nhau | 8; 24 nếu chỉ so 400 ký tự đầu | Không. Lỗi nhân bản. | `692617` (08/2026/TT-BNNMT): `692617_pl1_d1` và `692617_pl3_d1` cùng chữ "Trích dẫn các văn bản pháp quy …" |

- Số văn bản biểu mẫu được ước bằng dấu hiệu chữ: "……", "(Tên …)", "(*)", "Cho phép", "Chấp thuận", "Chứng nhận". Số này có thể lệch vài chục.
- Ảnh hưởng đến tìm kiếm: kết quả có Điều 1 của biểu mẫu, hoặc có cùng một Điều hai lần.
- Ảnh hưởng đến Graph: vị trí "Điều 1" của văn bản đích có thể trỏ nhầm node.

Đề xuất và trạng thái (28/10/2026):

1. Parser không tách đoạn dưới "Mẫu số …" của phụ lục thành Điều. **Đã làm** ở `c394162` (`structure.sample_form`): phần biểu mẫu lưu phẳng như bảng. Có trong `-v4` từ 28/10/2026.
2. Parser bỏ Điều trùng nội dung trong một văn bản. Chưa làm.
3. Đơn vị đổi thì công cụ phải hỏi lại LLM cho đơn vị đó. Đo lại chất lượng trên bộ có biểu mẫu: chưa đo.

Đếm lại trên `-v4` ngày 28/10/2026 (30.988 văn bản):

| Chỉ số | Giá trị |
| --- | --- |
| Văn bản có Điều 1 | 24.653 |
| Có từ 2 Điều 1, `dieu_uid` khác nhau | 2.568 (10,4%). Phần lớn là Điều 1 của quyết định và của văn bản kèm theo (hợp lệ). Số theo từng nhóm: chưa đo. |
| `694210`, `688084` | Mỗi văn bản chỉ còn một Điều 1 (`694210_d1`, `688084_d1`). `694210` có 180 chunk `phu_luc` và 1.685 chunk `phu_luc_doan`. |
| `692617` | Vẫn có `692617_pl1_d1` và `692617_pl3_d1` (nhân bản) |

Cách đo lại: truy vấn `legal-chunk-section-v4`, lọc `ky_hieu_dieu = "1"`, gom `dieu_uid` theo `doc_id`. Văn bản có từ 2 `dieu_uid` thuộc nhóm "Có từ 2 Điều 1". So `noi_dung` của các Điều 1 để tìm nhân bản. Dùng dấu hiệu chữ ở trên để tìm biểu mẫu.

### S9. Đoạn cuối của văn bản không có Điều

Văn bản không chia Điều (kế hoạch, công văn) có đoạn cuối sau đề mục cuối. Ví dụ: "Kế hoạch này thay thế …", "Trong quá trình thực hiện …". LLM lập dàn ý (tầng 1) xếp đoạn này vào phần kết. Công cụ không gửi phần kết cho tầng trích quan hệ. Phần kết cũng không vào chunk.

| Chỉ số (mẫu 2.000 văn bản của đợt 20.000, 28/10/2026) | Giá trị |
| --- | --- |
| Văn bản có đoạn cuối bị xếp vào phần kết | Khoảng 49 |
| Ví dụ | 681383, 671394, 669547 |
| Ước toàn kho | Chưa đo |

- Ảnh hưởng đến quan hệ: câu "… này thay thế …" ở đoạn cuối không có quan hệ. Tầng "không quan hệ" của mẫu có khoảng 7 văn bản sót vì lỗi này hoặc lỗi R9.
- Ảnh hưởng đến tìm kiếm: chữ của đoạn cuối không có trong chunk nào.

Đề xuất (chưa sửa, chờ người dùng quyết): định nghĩa phần kết trong prompt lập dàn ý là chỉ nơi nhận và khối chữ ký. Đoạn có nội dung đi vào đề mục cuối hoặc thành chunk riêng. Dàn ý đổi thì công cụ phải hỏi lại LLM cho văn bản đó.

### S10. Phần đánh số La Mã bên trong một Điều

Một số Điều có phần đánh số I., II., III. bên trong. Parser chỉ đưa phần I vào chunk. Các phần sau mất khỏi chunk.

- Ví dụ: 672797 mất 13.843 ký tự, tức 87% chữ của văn bản (28/10/2026).
- Số văn bản bị lỗi: chưa đo.
- Ảnh hưởng: tìm kiếm không thấy chữ đã mất. Quan hệ nêu trong phần mất không được trích.

Đề xuất (chưa sửa): parser nhận phần La Mã trong Điều là cấp con của Điều, hoặc giữ cả chữ trong chunk Điều. Cách đo: so tổng độ dài `noi_dung` của chunk lá với độ dài `full_content`.

## 10.3. Metadata văn bản

### M1. Ngày hiệu lực

Mẫu ngẫu nhiên 3.000 văn bản (`work/analyze-mau3000`, đo 12/10/2026):

| Cách có ngày | Tỉ lệ | Ước toàn kho |
| --- | --- | --- |
| Đọc từ câu chữ | 50,4% | ~261.200 |
| Suy ra bằng ngày ban hành (`mac_dinh_ngay_ban_hanh`, văn bản không quy phạm) | 40,4% | ~209.400 |
| **Không có ngày** | **9,2%** | **~47.500** |
| – Không tìm thấy câu hiệu lực | 4,7% | ~24.200 |
| – Phụ thuộc ngày đăng Công báo | 2,0% | ~10.200 |
| – Không đọc được ngày | 1,5% | ~7.600 |
| – Văn bản hợp nhất | 1,1% | ~5.500 |

- Văn bản quy phạm: có ngày 88,4%, đọc từ câu chữ 78,8%. Nhóm thấp: Nghị định 53,3%, Thông tư liên tịch 59,1%, Thông tư 69,3%.
- 17/3.000 văn bản có ngày hiệu lực trước ngày ban hành. Cần kiểm.
- v4 (16/10/2026): 68/532 văn bản và 4.170/22.825 chunk (18,3%) có `ngay_hieu_luc = null`.

Đề xuất: lấy ngày đăng Công báo từ nguồn ngoài cho nhóm "phụ thuộc ngày đăng Công báo". Kiểm tay nhóm "không tìm thấy" của văn bản quy phạm.

### M2. Ngày hiệu lực riêng và hồi tố của điều khoản

- v4: 7/532 văn bản có `hieu_luc_rieng`. 20/532 văn bản có hồi tố.
- Câu chỉ mô tả nội dung ("Quy định về các ngành, nghề … có hiệu lực từ …") không gán được cho điều khoản.
- Câu có điều kiện chỉ nằm ở `ngay_hieu_luc_trich`, không vào chunk.
- Hồi tố ngầm hoặc theo từng điều khoản chưa có số đo độ phủ.

Đề xuất: lập nhãn chuẩn cho 100 văn bản có câu hiệu lực phức tạp rồi đo độ phủ.

### M3. Văn bản quy phạm và cấp hiệu lực

| Chỉ số | Giá trị |
| --- | --- |
| `la_vbqppl = null` (cần kiểm tay) | 6/532 văn bản v4 (1,1%). Chủ yếu văn bản trước năm 2005, số hiệu không có năm. |
| Lỗi đã biết | `46830`: văn bản theo luật năm 1996 bị gán theo Luật 2025 |
| Chunk, quan hệ có `la_vbqppl` | 0%. Phải nối qua văn bản để lọc. |

Đề xuất: chép `la_vbqppl` sang chunk, và sang quan hệ (`source_la_vbqppl`, `target_la_vbqppl`).

### M4. Trường thiếu ở nguồn

Đo trên `legal-docs` nguồn, 16/10/2026:

| Trường | Văn bản thiếu |
| --- | --- |
| `pdf_minio_path` | 40.208 (7,8%) |
| `signers` | 447 |
| `legal_sectors` | 4 |

Công cụ chép nguyên các trường này. Chưa có lệnh điền.

### M5. Độ chính xác metadata chưa có nhãn của người

Đánh giá trước chỉ dùng LLM chấm, đạt khoảng 97–99%. Chưa có nhãn chuẩn của người cho ngày hiệu lực, hết hiệu lực, hồi tố, `la_vbqppl`.

## 10.4. Quan hệ

### R1. Độ phủ quan hệ

| Bộ (15/10/2026) | Chế độ | P | R | P theo văn bản | R theo văn bản |
| --- | --- | --- | --- | --- | --- |
| Blind (250) | `rules` | 94,5% | 35,0% | 62,1% | 46,4% |
| Blind (250) | `llm` | 90,5% | 48,3% | 77,7% | 67,6% |

- Mục tiêu 85%. Chưa đạt.
- Lỗi theo tầng (Blind, `llm`): ngữ nghĩa 223 (thiếu hoặc thừa hành động), phạm vi 57, cấu trúc 38, tham chiếu 21, phân loại 17.
- Đợt 20.000 (28/10/2026, mẫu 2.000, nhãn agent chưa người duyệt): phát hiện R có trọng số 0,804 [0,750–0,852]. Sót 860 mục (không trọng số): 563 sót đích, 167 có nhưng `unresolved`, 91 đúng đích khác hành động, 39 văn bản công cụ không ra quan hệ nào.
- Quy mô kho: 32.835 văn bản nguồn có `action` sửa đổi, bổ sung, bãi bỏ, thay thế, hủy bỏ (6,3%). 10.489 văn bản hướng dẫn. 3.578 văn bản hợp nhất. v2 có 180.452 quan hệ từ 72.454 văn bản.

### R2. Danh mục văn bản trong phụ lục

- Văn bản có danh mục văn bản bãi bỏ, hết hiệu lực, được áp dụng: 61/10.000 (~0,6%, ~3.000 văn bản).
- Cả hai chế độ không đọc phụ lục không chia Điều. Ba lượt chạy thử có 0 quan hệ có nguồn trong loại phụ lục này.
- Ví dụ: `683636` có Phụ lục II liệt kê 25 quyết định bị bãi bỏ. Công cụ tạo 0 quan hệ, nhãn chuẩn có 23.

Đề xuất: code đọc từng dòng bảng. Một dòng cho một quan hệ, `source_path = Phụ lục <n> STT <k>`. Hành động lấy từ tiêu đề phụ lục hoặc cột "Ghi chú". LLM chỉ đọc tên cột khi không rõ.

Trạng thái 22/10/2026: đã làm ở chế độ `llm`, có trong `-v4` (quy tắc 15, 16 ở [08, mục 8.11.3](08-quan-he-4-tang-va-danh-gia.md#8113-quy-tắc)). Lỗi còn lại ở [08, mục 8.14](08-quan-he-4-tang-va-danh-gia.md#814-sửa-lỗi-sau-benchmark-500-văn-bản-22102026).

### R3. Thủ tục hành chính

- 830/10.000 văn bản (8,3%, ~43.000) có danh mục thủ tục hành chính. Thủ tục hành chính chiếm 46% số danh mục.
- Thủ tục hành chính không phải văn bản. Graph không có loại node cho nó.
- Index cũ tạo quan hệ sai từ các bảng này. Ví dụ: `legal-changed/132140_7` ghi "2809/QĐ-CT sửa đổi toàn bộ 03/2009/TT-BXD". Thông tư đó chỉ là căn cứ pháp lý của một thủ tục.

Đề xuất: quyết định có làm loại thực thể "thủ tục hành chính" hay không. Nếu làm: node thủ tục, quan hệ "công bố", "sửa đổi", "bãi bỏ" thủ tục, quan hệ "căn cứ" tới văn bản.

### R4. Vị trí ngoài định dạng và dòng danh mục

| Chỉ số | Giá trị |
| --- | --- |
| v4 cũ (532 văn bản, 16/10/2026), vị trí ngoài định dạng | 14/2.009 (0,7%). Ví dụ: `Tên Điều 23` (`660522_65`), `tên Phụ lục I` (`691249_9`), `Phụ lục 04, dòng “Điểm thành tích”` (`588531_13`). |
| Chế độ `llm`, vị trí ngoài định dạng | 17/759 (2,2%), phần lớn là dòng danh mục: `Phụ lục I Mục III số 2, 3` (`eval-llm-blind`, `600990_2`) |
| v4 (11.000 văn bản, 21/10/2026), vị trí ngoài định dạng | 198/38.357. 196 vị trí là `Mục` hoặc `Phần` đứng một mình, ví dụ `Mục IV` ([08, mục 8.11.8](08-quan-he-4-tang-va-danh-gia.md#8118-ghi-thêm-10000-văn-bản-vào-v4-2122102026)). Dữ liệu ghi lại 22/10/2026 có cùng loại lỗi. |
| Dòng "số thứ tự N" làm vị trí | Không có node (C4). Index `-v4` ngày 22/10/2026: luồng quy tắc ghi vào `scope` và để `vi_tri` rỗng. Từ 28/10/2026 (code `1117e63`): vị trí là phụ lục chứa dòng, số thứ tự ở `chi_tiet_vi_tri`. Ví dụ `693748_0`: `chi_tiet_vi_tri = "Mục A Phụ lục I; số thứ tự 06, 07"`. |

Trạng thái: Q10 (19/10/2026) chuyển vị trí ngoài định dạng sang `doi_tuong`. Q13, Q14 (26–27/10/2026) thêm quy ước phụ lục ([07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt)). Định dạng vị trí ở [09, mục 9.5](09-hop-dong-du-lieu-v4.md#95-vị-trí).

**Quy ước phụ lục (từ code `8b023ca`, có trong `-v4` từ 28/10/2026).** Code `resolver.appendix_scope` chạy hai lần, cho cạnh của cả hai nhánh. Lần 1 ở cuối bước gộp. Lần 2 trong `convert.tidy_positions`, sau khi code tính vị trí từ `scope` của nhánh quy tắc và vị trí của dòng danh mục.

- Vị trí ngoài phần thân thành `Phụ lục <n>` khi chữ nêu đúng một số phụ lục. Không nêu số hoặc nêu nhiều số thì thành `Phụ lục`. Chữ gốc nằm ở `chi_tiet_vi_tri`.
- Phần thân (`resolver.body_place`) giữ nguyên: vị trí có chữ "điểm", "khoản", "Điều", "Chương", và `tên văn bản`, `tên Mục <n>`. `Mục <n>` đứng một mình thành phụ lục.
- Quy ước áp cả cho `cum_tu[].vi_tri` của `thay-cum-tu`.
- Phần nêu bằng tên thành phụ lục chỉ khi chữ nêu thứ phụ lục chứa (`resolver.appendix_like`), hoặc phần là thủ tục hành chính, hoặc đơn vị nguồn là dòng của phụ lục. `doi_tuong` giữ chữ gốc.
- Cạnh đã đổi có `cap_quan_he = vi_tri`.

| Chỉ số (lượt `fix9-H56` và `fix9-ho`, 876 văn bản, 27/10/2026) | Giá trị |
| --- | --- |
| Quan hệ `validated` | 9.760 |
| Vị trí chỉ là phụ lục | 557 (5,7%). 196 quan hệ có `chi_tiet_vi_tri`. |
| – `Phụ lục <n>` | 265, trong đó 16 còn `doi_tuong`. Ví dụ `694022_0`: `Phụ lục 1`, `doi_tuong` = "danh mục và nội dung 02 thủ tục hành chính có số thứ tự 11, 17 mục I, phần A, Phụ lục 1". `691307_0`: `Phụ lục I`, `chi_tiet_vi_tri = "Mục I Phụ lục I"`. |
| – `Phụ lục` không số | 292, trong đó 150 còn `doi_tuong`. Ví dụ `685249_0`: `doi_tuong` = "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ". `683435_14`: `chi_tiet_vi_tri = "Mục 14; Mục 89; Mục 90"`. |
| Vị trí ngoài phần thân chưa đổi theo quy ước | 0. Code `8ccb1da` để lọt 57/9.759 quan hệ. |
| Vị trí `tên văn bản`, `tên Mục <n>` giữ nguyên | 4 quan hệ |

| Chỉ số (`legal-changed-v4`, 28/10/2026, code `1117e63`) | Giá trị |
| --- | --- |
| Quan hệ `validated` | 70.954 |
| Vị trí là phụ lục | 14.911 (21,0%) |
| – `Phụ lục <n>` | 3.921 |
| – `Phụ lục` không số | 10.990 (15,5%), ở 3.550 văn bản nguồn. 7.904 còn `doi_tuong`; 2.413 có `chi_tiet_vi_tri`; 6.808 là quan hệ lên thủ tục hành chính. |
| `vi_tri = ["tên văn bản"]` | 51 quan hệ (mọi trạng thái) |

- Tỉ lệ `Phụ lục` không số ở `-v4` cao hơn lượt `fix9-*` (15,5% so với 3,0%). Phần lớn là quan hệ lên thủ tục hành chính.
- Ví dụ `694022_0`, `689945_1`, `685249_0`, `683435_14` có trong `-v4` với giá trị như bảng trên (kiểm 28/10/2026).

Việc còn lại: bên Graph chốt cách nối `Phụ lục` không số ([11](11-cau-hoi-graph.md)). `Phụ lục <n>` nối vào node phụ lục `<n>` của văn bản đích.

### R5. Độ chính xác vị trí

| Chế độ (Blind, 15/10/2026) | Vị trí đúng |
| --- | --- |
| `rules` | 85,4% |
| `llm` | 77,7% |

Ở chế độ `llm`, quan hệ cả hai đường cùng thấy lấy vị trí của regex. Quan hệ chỉ LLM thấy dùng vị trí của LLM.

Số đo mới (code `8b023ca`, bộ chấm 27/10/2026, chạy lại chặt, lượt `fix9-*`). Phạm vi: đúng văn bản nguồn, hành động, văn bản đích và vị trí hoặc phần bị tác động. Bộ chấm áp quy ước phụ lục như nhau cho nhãn và công cụ.

| Bộ | Độc lập | Phạm vi P / R / F1 |
| --- | --- | --- |
| Hold-out 300 (bỏ văn bản 675259) | Có. Nhãn agent, chưa qua người duyệt. | 0,711 / 0,673 / 0,691 |
| Stress C4/B8c (57 văn bản, 18 văn bản đối chứng) | Một phần | 0,677 / 0,794 / 0,731 |
| H5 + H6 (500 văn bản) | Không | 0,833 / 0,773 / 0,801 |
| 7 bộ cũ | Không | 0,861 / 0,792 / 0,825 |

- Trên hold-out 300, F1 của phạm vi thấp hơn F1 của phát hiện khoảng 19 điểm (0,691 so với 0,880).
- Lỗi phạm vi theo cơ chế (936 lỗi, 26/10/2026) ở [07, mục 7.2](07-gioi-han-va-can-chot.md#72-lỗi-dữ-liệu-đã-biết). Hướng sửa chính là sửa prompt; khi đó phải hỏi lại LLM.
- Dữ liệu `-v4` ngày 22/10 (code `2911b77`), H5 + H6, bộ chấm cũ: phạm vi P / R 0,785 / 0,743 (22/10/2026).
- Dữ liệu `-v4` hiện có (code `1117e63`), đợt 20.000, mẫu 2.000, nhãn agent chưa người duyệt (28/10/2026). Phạm vi có trọng số: P 0,785 [0,713–0,842], R 0,695 [0,630–0,752]. Không trọng số: P / R / F1 0,785 / 0,702 / 0,741. Độ đúng `vi_tri` so với nhãn: 0,877.

### R6. Nhóm quan hệ yếu

Điểm theo văn bản (P / R), chế độ `llm`, bộ Blind, 15/10/2026:

| Nhóm | Số văn bản | P / R |
| --- | --- | --- |
| Hủy bỏ | 5 | 0% / 0% |
| Văn bản không chia Điều có sửa đổi | — | 0% |
| Văn bản cũ (trước năm 2000) | 9 | 50% / 50%. Bộ Dev: 25% / 25%. |
| Hướng dẫn | 14 | 57% / 57% |
| Thay thế | 8 | 60% / 50% |
| Sửa đổi | 23 | 81% / 52% |
| Công bố thủ tục hành chính | 18 | 78% / 75% |
| Mẫu ngẫu nhiên | 124 | 72% / 64% |

Mỗi nhóm có 5–23 văn bản. Sai số của từng nhóm lớn.

### R7. Quan hệ chờ duyệt và đích chưa nối

| Chỉ số | Giá trị |
| --- | --- |
| v4 cũ (532 văn bản, 16/10/2026), `cap_quan_he = chua_xac_dinh` | 73/2.009 (3,6%) |
| v4 (11.000 văn bản, 22/10/2026), `unresolved` | 2.275/42.771 (5,3%). Lý do: `vi_tri_chua_xac_dinh` 734, `dich_chua_gan_cau_thuc_hien` 569, `phan_kem_theo_chua_ro` 522, `vi_tri_khong_co_trong_nguon` 326, `van_ban_dich_khong_co_trong_nguon` 124. |
| v4 (11.000 văn bản, 22/10/2026), có `target_matched_id` | 37.182/42.771 (87%) |
| v4 (30.988 văn bản, 28/10/2026), `resolution_status = unresolved` | 4.552/75.506 (6,0%). Lý do: `vi_tri_chua_xac_dinh` 1.708, `dich_chua_gan_cau_thuc_hien` 1.487, `vi_tri_khong_co_trong_nguon` 555, `phan_kem_theo_chua_ro` 551, `van_ban_dich_khong_co_trong_nguon` 251. Trường cũ `unresolved = true`: 2.147 (2,8%). |
| v4 (30.988 văn bản, 28/10/2026), có `target_matched_id` | 64.277/75.506 (85,1%) |
| Chế độ `llm`, `unresolved` (Blind) | 71/759 (9,4%) đo ngày 15/10. Ước 100/759 (13,2%) sau khi sửa quy tắc ngày 16/10. |
| v4 cũ, `target_matched_id = null` | 87/2.009 (4,3%) |
| v4 cũ, đích đã nối nhưng chưa có trong v4 | 1.583/1.922 (82%). Node đích chưa có chunk. |
| Đơn vị do văn bản trước bổ sung (Điều 47a, khoản 7a) | Không có trong văn bản gốc. Chưa đo số lượng. Ví dụ `611245_7`. |
| Quan hệ từ lời dẫn khác nhau giữa hai chế độ | 24 quan hệ (Blind). Chờ chốt. |

### R9. Nội dung đơn vị bị cắt ở 6.000 ký tự

Tầng trích (`extract.py`) gửi `noi_dung` của mỗi đơn vị cho LLM. Code rút gọn chữ trong ngoặc kép, rồi cắt `noi_dung` ở 6.000 ký tự đầu (`extract.extract`). Câu hành động nằm sau ký tự thứ 6.000 không được LLM đọc.

- Ví dụ: 669605. Câu "Kế hoạch này thay thế …" ở cuối một mục dài bị cắt (28/10/2026).
- Số đơn vị dài hơn 6.000 ký tự: chưa đo.
- Đơn vị nêu từ 8 số hiệu đã được hỏi theo phần ([05, mục 5.2.3](05-phien-ban-v2-v3-v4.md#523-v4-chế-độ-llm-luồng-chốt)). Đơn vị dài nhưng nêu ít số hiệu không được hỏi theo phần.

Đề xuất (chưa sửa): hỏi theo phần mọi đơn vị dài hơn giới hạn, giống đơn vị nêu nhiều số hiệu. Đơn vị đổi cách hỏi thì công cụ phải hỏi lại LLM.

### R8. Index cũ `legal-changed`

Index `legal-changed` (trước v2) có 164.965 quan hệ trên cả `10.1.10.10` và `10.1.10.23`. Index này có nhiều quan hệ sai. Ví dụ: văn bản 132140 có 21 quan hệ, cả 21 đều sai (20 quan hệ "sửa đổi toàn bộ" lấy từ bảng thủ tục, 1 quan hệ trỏ vào chính nó).

Đề xuất: xác nhận còn bên nào đọc index này không. Nếu không, đánh dấu ngừng dùng.

## 10.5. Triển khai

Trạng thái ngày 28/10/2026.

| Chỉ số | Giá trị |
| --- | --- |
| v3 | 236 văn bản (0,05% kho), 14.677 chunk, 4.201 quan hệ (28/10/2026). 204 văn bản theo quy tắc ngày 13/10. 32 văn bản thêm 27/10/2026 (code `8b023ca`, sửa tay, người dùng duyệt). Không ghi lại toàn bộ khi bên Graph chưa duyệt v4. |
| v4 | 30.988 văn bản (6,0% kho), ban hành từ 12/03/2025 đến 30/09/2026. 1.534.375 chunk; 75.506 quan hệ (70.954 `validated`, 4.552 `unresolved`) trên 13.627 văn bản (28/10/2026). |
| Code chạy hiện hành | `1117e63` (27/10/2026). 30.981 văn bản `-v4` ghi bằng code này. 7 văn bản còn bản ghi 22/10/2026 (`2911b77`). Các mốc code ở [05, mục 5.2.4](05-phien-ban-v2-v3-v4.md#524-thay-đổi-code-2227102026). |
| Lượt ghi đêm 27–28/10/2026 | `v4-next20000`: 20.000 văn bản mới, 20 luồng, 22:48 → 04:18. 10 văn bản lỗi chưa ghi. `v4-2710`: ghi lại 11.000 văn bản cũ, 04:18 → 07:40. 7 văn bản lỗi. |
| Đợt tiếp theo | ID sau 10.000 đầu của `work/v4-next10000b-ids.txt` và `work/v4-next10000c-ids.txt`. Số ID còn lại: chưa đếm. Chưa có lệnh chạy, chờ người dùng quyết. |
| Nút thắt | ES đích, ES nguồn và máy embedding đều qua VPN `tun0` (khoảng 2,5 MB/s, 27–28/10/2026). Chạy hai lượt cùng lúc thì nhiều lỗi `ConnectionError … timed out`. |
| Dung lượng `-v4` (11.000 văn bản, 21/10/2026) | `legal-docs-v4` 544 MB, `legal-chunk-section-v4` 6,5 GB, `legal-changed-v4` 20 MB |
| Dung lượng `-v4` (30.988 văn bản, 28/10/2026) | `legal-docs-v4` 1,4 GB, `legal-chunk-section-v4` 33,9 GB, `legal-changed-v4` 44,3 MB |
| Tốc độ, có gọi LLM (21–22/10/2026) | 16,3 văn bản/phút ban ngày (3 lời gọi cùng lúc); 45,4 văn bản/phút sau 22:00 (10 lời gọi). Khoảng 8,4 lời gọi mỗi văn bản. |
| Tốc độ, dùng lại câu trả lời đã lưu (22/10/2026) | Khoảng 60 văn bản/phút, 10 luồng |
| Thời gian, chế độ `llm` (15/10/2026) | Khoảng 12 giây mỗi văn bản ở 3 lời gọi cùng lúc (Blind). Bộ Blind thiên về văn bản có quan hệ, nên đây là cận trên. |
| Thời gian, chế độ `rules` | Khoảng 1,4 giây mỗi văn bản khi dùng lại cache QA |
| Đánh giá theo đợt | Mỗi 10.000 văn bản mới: lấy mẫu 1.000 văn bản (`python -m eval.sample_batch`), gán nhãn, chấm bằng `eval.strata` (`eval/README.md`). Đợt 20.000: mẫu 2.000 văn bản, chấm 28/10/2026. |
| Nhãn chuẩn | Do agent LLM gán. CSV duyệt hold-out 300 (`bernmark/ho300/duyet_ho300.csv`, 1.431 dòng) chờ người duyệt. Nhãn đợt 20.000 (9.137 quan hệ) đã khóa, chờ người duyệt. |

## 10.6. Thứ tự xử lý đề xuất

Cập nhật ngày 28/10/2026. Các bước cũ đã xong: đọc danh mục văn bản trong phụ lục (R2, 20–22/10), chuyển vị trí ngoài định dạng và quy ước phụ lục cho mọi vị trí (R4, 19/10 và 26–27/10, `8b023ca`), ghi lại v4 và đo trên bộ mới (D1, R1, 22/10 và 26–27/10). Đêm 27–28/10: ghi lại 11.000 văn bản `-v4` bằng code `1117e63`, chạy 20.000 văn bản mới, chấm mẫu 2.000 văn bản (D1, R1, R5). Biểu mẫu trong phụ lục, vector đủ độ dài, đoạn tìm kiếm phụ lục và đề mục (S1, S2, S8, `c394162`, `57b9033`).

| Bước | Việc | Khoảng trống | Lý do | Trạng thái |
| --- | --- | --- | --- | --- |
| 1 | Người duyệt CSV hold-out 300 và nhãn đợt 20.000, rồi chấm lại | R1, R5, M5 | Số đo độc lập có nhãn của người. Hiện chỉ có nhãn agent. | Chờ người duyệt |
| 2 | Sửa lỗi tìm thấy khi chấm đợt 20.000: đoạn cuối văn bản không có Điều, cắt 6.000 ký tự, phần La Mã trong Điều | S9, R9, S10 | Khoảng 49/2.000 văn bản mẫu có lỗi S9 (28/10/2026). 672797 mất 87% chữ (S10). | Chờ quyết. Đơn vị đổi thì hỏi lại LLM cho đơn vị đó. |
| 3 | Chạy lại 17 văn bản lỗi; chạy đợt tiếp theo, chấm mẫu theo T2 | D1 | Tăng độ phủ v4. Có số đo trên văn bản mới. | Chờ quyết. Nên sửa bước 2 trước. |
| 4 | Sửa prompt: cả văn bản hay một phần, thủ tục hành chính, cặp hành động dễ nhầm | R1, R5, R6 | 37% lỗi phạm vi kéo theo từ lỗi phát hiện; 28% ghi cả văn bản thay vì một phần (26/10/2026). | Chưa làm. Phải hỏi lại LLM. Mẫu đợt 20.000 dùng được để đo. |
| 5 | Sửa parser: Điều trùng nội dung | S8, S6 | 8 văn bản trong 11.000 (26/10/2026) | Chưa sửa. Biểu mẫu đã sửa (`c394162`). |
| 6 | Bên Graph chốt cách nối `Phụ lục` không số | R4 | 10.990/70.954 quan hệ `validated` có `Phụ lục` không số (28/10/2026) | Chờ bên Graph ([11](11-cau-hoi-graph.md)) |
| 7 | Chunk theo dòng cho danh mục văn bản | S1 | Đoạn tìm kiếm phụ lục đã có (28/10/2026). Dòng danh mục chưa có chunk. | Chưa làm |
| 8 | Node Chương, Mục và đề mục con | S3, S4 | ~11% và ~13% văn bản. Cần chốt hợp đồng trước. | Chưa làm |
| 9 | Ngày đăng Công báo, chép `la_vbqppl` sang chunk và quan hệ | M1, M3 | Graph cần thời gian và lọc VBQPPL | Chưa làm |
| 10 | Thủ tục hành chính | R3 | Cần quyết định phạm vi | Chờ quyết |

Cần anh/chị quyết định:

1. Có sửa các lỗi S9, R9, S10 trước đợt tiếp theo không.
2. Có chạy đợt tiếp theo không, và khi nào (D1).
3. Cách nối `vi_tri = ["Phụ lục"]` không số: bên Graph trả lời ([11](11-cau-hoi-graph.md), R4).
4. Đổi C4: mỗi dòng danh mục văn bản là node đích (S1, R4). Từ code 27/10/2026, vị trí của dòng là phụ lục chứa dòng.
5. Thêm node Chương, Mục và đề mục con vào hợp đồng (S3, S4).
6. Quan hệ từ lời dẫn không nêu vị trí: `validated` cấp văn bản, hay `unresolved` (R7).
7. Có làm thực thể thủ tục hành chính không (R3).
8. Ngừng dùng index cũ `legal-changed` (R8).

## 10.7. Nguồn số liệu và cách đo lại

| Nguồn | Phạm vi | Ngày | Lệnh |
| --- | --- | --- | --- |
| Mẫu ngẫu nhiên 10.000 văn bản nguồn (seed `20261015`), phụ lục và danh mục | S1, R2, R3 | 15/10/2026 | `python -m eval.survey_appendix 10000 <file>` rồi `python -m eval.survey_appendix_report <file>` |
| Cùng mẫu 10.000, cấp trên Điều và đề mục | S3, S4, S5 | 16/10/2026 | `python -m eval.survey_levels 10000 <file>` rồi `python -m eval.survey_levels_report <file>` |
| Mẫu ngẫu nhiên 3.000, ngày hiệu lực | M1 | 12/10/2026 | `python -m vbpl_v3 analyze --name mau3000 --sample 3000` |
| Index v4 cũ (532 văn bản) | S2, S7, M3, R4, R7 | 16/10/2026 | Truy vấn ES đích |
| Index v4 (11.000 văn bản), số bản ghi, kiểm hợp đồng | S7, R4, R7, 10.5 | 21–22/10/2026 | `python -m eval.check_contract v4`. Số ở [08, mục 8.11.8](08-quan-he-4-tang-va-danh-gia.md#8118-ghi-thêm-10000-văn-bản-vào-v4-2122102026) và [8.15](08-quan-he-4-tang-va-danh-gia.md#815-chốt-luồng-và-ghi-lại-v4-22102026). |
| `legal-chunk-section-v4`, Điều 1 lặp | S8 | 26/10/2026; ví dụ kiểm lại 27/10/2026 | Truy vấn ES đích (cách đo ở S8) |
| `legal-docs-v4`, `legal-chunk-section-v4`, `legal-changed-v4` (30.988 văn bản) | 10.1, S8, R4, R7, 10.5 | 28/10/2026 | Truy vấn `_count`, `_search` (aggregation) trên ES đích, chỉ đọc |
| Mẫu `eval/sets/dot-20000-20261028` (2.000 văn bản), nhãn `eval/gold/dot-20000-20261028-g300` và `-r` | R1, R5, S9, S10, R9 | 28/10/2026 | Kết quả ở `work/dot-20000-20261028-2000-ket-qua.json`. Cách chấm ở `eval/README.md`. |
| Lượt chạy lại chặt `fix9-H56` (501 văn bản) và `fix9-ho` (375 văn bản: hold-out 300 và bộ stress), code `8b023ca` | R4 (quy ước phụ lục) | 27/10/2026 | Đọc `work/<lượt>/dry-run/*.json`. Đếm quan hệ `validated` có mọi vị trí dạng `Phụ lục` hoặc `Phụ lục <ký hiệu>`. |
| Bộ chấm 27/10/2026 trên 9 bộ (`eval/score.py` của `8b023ca`, lượt `fix9-*`) | R1, R5 | 27/10/2026 | Bảng đầy đủ của code `8ccb1da` ở `bernmark/fix3/ket_qua_fix7.txt`. Số của `8b023ca` ở thông điệp commit. [08, mục 8.17](08-quan-he-4-tang-va-danh-gia.md#817-thu-hẹp-quy-ước-phụ-lục-ghi-chú-lịch-sử-ở-đơn-vị-bị-cắt-27102026) |
| Lỗi phạm vi theo cơ chế, 9 bộ phân tích | R5 | 26/10/2026 | `bernmark/fix3/pham_vi_tong_quan.py` |
| Bộ Blind, Dev | S6, R1, R5, R6 | 15/10/2026 | `python -m eval.score <bộ> <lượt>` |
| ES nguồn | M4, R1 (quy mô), R8 | 16/10/2026 | Truy vấn `_count` |

Cách đếm cấp trên Điều (S3, S5): chỉ tính dòng tiêu đề ở đầu dòng, nằm trước Điều cuối cùng, không nằm trong bảng, trong ngoặc kép hay trong phụ lục không chia Điều. Cách phân loại phụ lục (S1): quy tắc theo tiêu đề và vài dòng đầu. Kiểm tay 40 phụ lục thấy vài phụ lục xếp sai loại, nên tỉ lệ theo loại có thể lệch vài điểm.

Hai lệnh `survey_*` chỉ đọc ES nguồn. Mỗi lệnh chạy khoảng 20 phút cho 10.000 văn bản.
