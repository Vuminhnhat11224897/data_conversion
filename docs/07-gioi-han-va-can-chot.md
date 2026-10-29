# 7. Giới hạn, lỗi đã biết và quyết định đã chốt

Trạng thái ngày 28/10/2026. Code chạy hiện hành là commit `1117e63` (27/10/2026). Index `-v4` có 30.988 văn bản. Công cụ ghi 30.981 văn bản bằng code `1117e63` trong đêm 27–28/10/2026. 7 văn bản còn bản ghi ngày 22/10/2026 (code `2911b77`). Các mốc code ở [05, mục 5.2.4](05-phien-ban-v2-v3-v4.md#524-thay-đổi-code-2227102026).

- Mục 7.1 đến 7.3: bảng đầu của mỗi mục đo trên bản thử `-v4` ngày 14/10/2026 (203 văn bản, 6.610 chunk, 969 quan hệ). Dòng và bảng thêm từ 27/10/2026 ghi ngày đo riêng.
- Mục 7.4: quyết định ngày 14/10/2026 (bảng 1), quy ước ngày 19–20/10/2026 (bảng 2), quyết định ngày 26–27/10/2026 (bảng 3, bảng 4).
- Mục 7.5: việc còn lại, cập nhật ngày 28/10/2026.
- Giới hạn của hợp đồng v4 ở [09, mục 9.13](09-hop-dong-du-lieu-v4.md#913-giới-hạn-đã-biết).

## 7.1. Giới hạn của dữ liệu

| Giới hạn | Hệ quả | Ví dụ |
| --- | --- | --- |
| Node nhỏ nhất là tiểu điểm (gạch đầu dòng của điểm). Gạch đầu dòng của khoản hoặc Điều, câu, đoạn không có node. | Vị trí dừng ở khoản hoặc Điều chứa đơn vị đó. | `378946_0`: `tiểu điểm 3 điểm b khoản 3 Điều 17` |
| Mẫu biểu không có node. | Vị trí là phụ lục chứa mẫu. Câu không nêu ký hiệu phụ lục thì vị trí là `Phụ lục`. | `602450_19`: "Mẫu số 01 Phụ lục kèm theo Nghị định số 61/2016/NĐ-CP" → `Phụ lục` |
| Danh mục có số thứ tự, bảng định mức, mục đánh số `1.2.2`: chưa làm (C4). | Tên phần nằm ở `doi_tuong`, `vi_tri` rỗng. | `662238_143`: `doi_tuong` = "điểm a Mục 1.2.2 Chương II của Định mức …" |
| Văn bản đích chỉ có chunk khi đã chuyển sang v3. Ảnh chụp: 3/117 văn bản đích có trong v3. | Phần lớn vị trí đích chưa có node chunk. | `602450_1` → `legal-docs/133717`, chưa có trong v3 |
| Đơn vị do văn bản trước bổ sung (Điều 47a, khoản 7a) không có trong văn bản gốc. | Vị trí không có chunk ở văn bản gốc. | `611245_7`: `khoản 1 Điều 47a`; không có `206663_d47a_k1` |
| Vị trí thuộc văn bản kèm theo chỉ được đánh dấu khi câu nguồn nói rõ (C2). | Bên Graph không biết vị trí thuộc Quyết định hay Quy định kèm theo. | `383494_3` |
| Ngày hiệu lực riêng chỉ có khi câu nêu điều khoản cụ thể. | Câu chỉ mô tả nội dung ("Quy định về các ngành, nghề … có hiệu lực từ ngày …") không gán được cho điều khoản. Câu có điều kiện ("Đối với các TCPHT là tổ chức tín dụng được kiểm soát đặc biệt, …") không ghi vào chunk; câu nằm ở `hieu_luc_rieng[].ngay_hieu_luc_trich`. | `509618`: khoản 1–6 Điều 1 có ngày riêng `2023-10-19` |
| QA hành động dùng model LLM (`LITELLM_MODEL`). Câu kể hoặc câu bị động đi qua model. | Model có thể loại sai một quan hệ. Câu mở đầu bằng chính hành động và nêu rõ vị trí không qua model. | — |
| Dịch vụ embedding cũ cắt đầu vào ở 256 token. Từ 26/10/2026, `-v4` có vector đủ độ dài. v2, v3 vẫn cắt 256 token. | Ở v2, v3, phần đuôi chunk dài không tìm được bằng vector. | — |
| `signers` (447 văn bản), `legal_sectors` (4 văn bản) còn thiếu ở nguồn. Kho mới thu thập (10.1.10.23) thiếu thêm `tom_tat`, `signers` (47.807 văn bản), `issuance_date` (14.895), `issuing_authority` (13.274). | Từ 29/10/2026 công cụ đọc lại trường thiếu từ `full_content` (`metadata_fill`, docs/09). | — |

Giới hạn thêm ngày 27/10/2026, của quy ước phụ lục (mục 7.4 bảng 3). Index `-v4` có giới hạn này từ 28/10/2026 (code `1117e63`).

| Giới hạn | Hệ quả | Ví dụ |
| --- | --- | --- |
| `Phụ lục` không số không chỉ tới một node phụ lục. Đếm 28/10/2026 trên `legal-changed-v4`: 10.990/70.954 quan hệ `validated` (15,5%) có `vi_tri = ["Phụ lục"]`. 6.808 quan hệ trong số này là quan hệ lên thủ tục hành chính. | Bên Graph chưa biết nối cạnh vào node nào. Câu hỏi ở [11](11-cau-hoi-graph.md). `Phụ lục <n>` nối vào node phụ lục `<n>` của văn bản đích. Chữ của vị trí gốc nằm ở `chi_tiet_vi_tri`. | `685249_0`: `vi_tri = ["Phụ lục"]`, `doi_tuong` = "03 thủ tục hành chính cấp tỉnh thuộc lĩnh vực hoạt động khoa học và công nghệ". `689945_1`: `vi_tri = ["Phụ lục"]`, `chi_tiet_vi_tri = "Mục I; số thứ tự 1, 2, 3, 4"`. (kiểm 28/10/2026) |

## 7.2. Lỗi dữ liệu đã biết

| Bản ghi | Lỗi | Hệ quả |
| --- | --- | --- |
| `449124_0`, `449124_1` (QĐ 787/QĐ-UBND) | Danh mục có số thứ tự. `cap_quan_he = chua_xac_dinh`, `vi_tri` rỗng. 2/3 khoản không có quan hệ. | Thiếu quan hệ. Không có node đích. Chưa làm (C4). |
| `662238_13`, `662238_14`, `662238_42`, `662238_86`, `662238_140` | 5 vị trí `Mục …` ngoài định dạng, ví dụ `Mục 1 Chương IV Quy định kỹ thuật …`, `Mục 7 Phần I`. | Không ánh xạ được sang node. |
| `662238_28`, `662238_29`, `662238_30` | `thay-cum-tu` có `cum_tu = []`. | Không biết cụm từ nào thay đổi. |
| `282089_66` | Mã tờ khai `02/KK-TNCN` bị nhận là văn bản đích. `target_matched_id = null`. | Quan hệ thừa. |

Lỗi đã sửa trong bản này (so với v3 ngày 13/10/2026):

| Lỗi cũ | Bản ghi mới |
| --- | --- |
| TT 30/2018/TT-BTC: thiếu quan hệ "Bỏ gạch đầu dòng thứ ba …", 2 quan hệ lấy vị trí từ nội dung mới | `378946_0` (`bai-bo`, đích TT 55/2016/TT-BTC), `378946_1` (`khoản 1 Điều 2`) |
| 19 vị trí `Mẫu số …` ngoài định dạng | Vị trí là phụ lục, ví dụ `602450_10` → `Phụ lục I` |
| "điểm a và điểm b khoản 2 Điều 11" mất điểm a | `282089_26` (điểm a), `282089_27` (điểm b); tương tự `476418` |
| Cặp `cum_tu` có `vi_tri` rỗng | `662238_11`, `662238_50` có vị trí |
| Vị trí lấy nhầm số Điều từ ghi chú lịch sử ("… đã được bổ sung bởi khoản 1 Điều 183 …") | `509618_4`: `khoản 20 Điều 3` |
| `181025_1`: `chua_xac_dinh` | QA loại. Câu chỉ tạm dừng xử lý hồ sơ, không đình chỉ văn bản. |
| `192512_9`, `282089_62`: vừa có `doi_tuong` vừa có `vi_tri` | Hợp lệ theo hợp đồng mới: câu nêu phụ lục chứa mẫu. `192512_0`, `282089_65` có `cap_quan_he = vi_tri`. |

Lỗi đã biết của luồng hiện tại (code `1117e63`, cập nhật 28/10/2026):

| Lỗi | Số đo | Ví dụ | Hướng sửa |
| --- | --- | --- | --- |
| Biểu mẫu trong phụ lục bị tách thành Điều 1 | **Đã sửa** ở `c394162` (27/10/2026), có trong `-v4` từ 28/10/2026. Trước khi sửa: khoảng 187 văn bản (26/10/2026). | `694210` (279/QĐ-BNNMT): trước có 63/180 phụ lục có Điều 1 dạng biểu mẫu. Nay chỉ còn `694210_d1`. `688084` chỉ còn `688084_d1`. (kiểm 28/10/2026) | Đã sửa. Chi tiết ở [10, S8](10-khoang-trong-du-lieu.md#s8-điều-1-lặp-và-biểu-mẫu-tách-thành-điều). |
| Cùng một Điều 1 xuất hiện từ 2 lần, dưới mã khác nhau | 8 văn bản; 24 văn bản nếu chỉ so 400 ký tự đầu (26/10/2026). Chưa đo lại trên `-v4` mới. | `692617_pl1_d1` và `692617_pl3_d1` (08/2026/TT-BNNMT) vẫn có (kiểm 28/10/2026) | Sửa parser: bỏ Điều trùng nội dung trong một văn bản |
| Phạm vi sai hoặc thiếu | 936 lỗi trên 9 bộ (26/10/2026). Đợt 20.000, có trọng số: phạm vi P 0,785, R 0,695 (28/10/2026, nhãn agent). | Bảng cơ chế dưới đây | Sửa prompt |
| `thay-cum-tu` thiếu `cum_tu` | 205/75.506 quan hệ `-v4` (28/10/2026) | — | Chưa phân tích |
| Chunk và bản ghi văn bản không khớp | 1 `doc_id` có chunk mà không có văn bản: 672275 (1.500 chunk). 2 văn bản không có chunk: 682498, 685655. Đếm chính xác 28/10/2026. | — | Lượt ghi xóa chunk cũ trước, rồi lỗi giữa chừng. Chạy lại 17 văn bản lỗi sẽ sửa. |
| Văn bản lỗi khi ghi đêm 27–28/10/2026 | 10 văn bản mới chưa ghi: 650872, 651044, 651412, 663486, 668834, 670096, 671294, 672275, 672379, 675570. 7 văn bản còn bản ghi 22/10: 679994, 682498, 685655, 686325, 694929, 694935, 696357. | — | Chạy lại cùng lượt, **không** có `--redo` |

Lỗi thật tìm thấy khi chấm đợt 20.000 (28/10/2026, mẫu 2.000 văn bản). Code `1117e63` chưa sửa các lỗi này. Người dùng chưa quyết.

| # | Lỗi | Số đo | Ví dụ | Nguồn lỗi |
| --- | --- | --- | --- | --- |
| 1 | Văn bản không có Điều: LLM lập dàn ý xếp đoạn cuối ("Kế hoạch này thay thế …", "Trong quá trình thực hiện …") vào phần kết. Đoạn đó không được gửi trích quan hệ và không vào chunk. | Khoảng 49 văn bản trong mẫu | 681383, 671394, 669547 | LLM lập dàn ý (tầng 1) |
| 2 | Tầng trích cắt `noi_dung` của đơn vị ở 6.000 ký tự. Câu hành động ở sau đó bị mất. | Chưa đo | 669605 | Code (`extract.py`) |
| 3 | Danh sách đích dài trong Nghị quyết HĐND: sót hoặc `unresolved` | Chưa đo | 663479, 663380. 668634: cả 6 đích `unresolved`. | Chưa phân tích |
| 4 | Điều có phần đánh số La Mã I., II., III. bên trong: chỉ phần I vào chunk | Chưa đo | 672797: mất 13.843 ký tự (87% văn bản) | Parser |
| 5 | Đích trùng số hiệu sau sáp nhập tỉnh. Dòng phụ lục ghi văn bản của tỉnh cũ (Bình Phước). Resolver nối văn bản Đồng Nai cùng số, khác ngày. Câu trích là câu của khoản, không có ngày, nên resolver không so được ngày của dòng phụ lục. | Chưa đo | 679575: 16/2021/QĐ-UBND, 40/2023/QĐ-UBND | Resolver |
| 6 | Văn bản hợp nhất: chunk có dòng không có trong bản gốc | Chưa đo | 666444, 680269 | Chưa phân tích |

Lỗi phạm vi còn lại theo cơ chế. Nguồn: 9 bộ phân tích, 936 lỗi, code 26/10/2026, script `bernmark/fix3/pham_vi_tong_quan.py`.

| Cơ chế | Tỉ lệ | Nguồn lỗi |
| --- | --- | --- |
| Kéo theo từ lỗi phát hiện (sót hoặc sai quan hệ) | 37% | LLM: thủ tục hành chính, câu nêu nhiều văn bản, cặp hành động dễ nhầm |
| Ghi cả văn bản thay vì một phần | 28% | LLM không nêu phần (62%). Code: luật danh sách nhiều văn bản, quan hệ ở tên văn bản. |
| Danh sách vị trí thiếu, thừa hoặc khác mức chi tiết | 32% | LLM và nhánh quy tắc liệt kê vị trí không đủ |

- Hướng sửa: prompt bắt LLM chọn rõ cả văn bản hay một phần. Prompt định nghĩa thủ tục hành chính và các cặp hành động dễ nhầm.
- Đợt 20.000 (28/10/2026, không trọng số): 860 mục sót phát hiện. 563 mục sót đích, 167 mục có nhưng `unresolved`, 91 mục đúng đích khác hành động, 39 văn bản công cụ không ra quan hệ nào.
- Sửa prompt làm mọi câu trả lời LLM đã lưu hết hiệu lực. Công cụ phải hỏi lại LLM cho mọi đơn vị.
- Lỗi còn lại sau quy tắc 15–19 ở [08, mục 8.14](08-quan-he-4-tang-va-danh-gia.md#814-sửa-lỗi-sau-benchmark-500-văn-bản-22102026).

## 7.3. Chuỗi sửa đổi (V5, đã chốt)

Văn bản A sửa một chỗ trong văn bản gốc C. Văn bản B đã viết lại chỗ đó trước A. Quyết định: nối về văn bản câu nêu trực tiếp. Ghi chú "được sửa đổi tại B" không tạo quan hệ.

| A | Câu của A | Đích v3 |
| --- | --- | --- |
| TT 30/2018/TT-BTC (`378946`) | "Bỏ gạch đầu dòng thứ ba điểm b Khoản 3 Điều 17 Thông tư số 55/2016/TT-BTC được sửa đổi, bổ sung tại Điều 1 Thông tư số 75/2017/TT-BTC." | TT 55/2016/TT-BTC (`legal-docs/297312`), `378946_0` |
| TT 03/2024/TT-NHNN (`611245`) | "Sửa đổi, bổ sung khoản 1, khoản 2 Điều 47a (đã được bổ sung theo quy định tại khoản 33 Điều 1 của Thông tư số 14/2015/TT-NHNN …)" | TT 19/2013/TT-NHNN (`206663`), `611245_7`, `611245_8` |

## 7.4. Quyết định đã chốt

Nguyên tắc chung, chốt ngày 14/10/2026: **ES chỉ lưu tác động văn bản nêu trực tiếp. Không nội suy, không ngoại suy tác động văn bản không nói.**

Nhóm: V = cấp văn bản; C = Chương, Mục, phụ lục; D = Điều, khoản, điểm; E = dưới cấp điểm.

| # | Câu hỏi | Quyết định | Dữ liệu làm | Trạng thái |
| --- | --- | --- | --- | --- |
| V1 | Tiêu đề, lời dẫn và các Điều cùng nối tới một đích. Giữ cả hai không? | Giữ. Tiêu đề và lời dẫn có quan hệ riêng. | Bỏ quy tắc loại quan hệ lời dẫn trùng với Điều. | Thay bằng R6 (27/10/2026, code `3c26438`) |
| V2 | Ai tính trạng thái hiệu lực của văn bản đích? | Bên Graph tính. ES không tính. | Không đổi. | Đã chốt 14/10/2026 |
| V3 | Quan hệ hướng dẫn có cần vị trí cấp Điều không? | Mọi loại quan hệ chỉ lấy tác động trực tiếp. Vị trí có thể ở mọi cấp, miễn câu nêu trực tiếp. | Quan hệ hướng dẫn lấy điều khoản nêu trong tiêu đề hoặc lời dẫn. | Đã chốt 14/10/2026 |
| V4 | Văn bản đích hết hiệu lực thì văn bản quy định chi tiết nó có hết theo không? | Không suy ra. ES không ghi. | Không đổi. | Đã chốt 14/10/2026 |
| V5 | Chuỗi sửa đổi: cạnh của A nối về B hay C? | Nối về văn bản câu nêu trực tiếp. Ghi chú "được sửa đổi tại …" không tạo quan hệ. | Đơn vị nêu số hiệu ngay sau điều khoản thì văn bản đó là đích. | Đã chốt 14/10/2026 |
| V6 | Văn bản hợp nhất có sinh quan hệ không? | Có. | Quan hệ `hop-nhat` tới từng văn bản nêu ở phần đầu. | Đã chốt 14/10/2026 |
| V7 | Gia hạn đổi ngày hết hiệu lực của đích. Ai cập nhật? | Theo V2: bên Graph tính. ES lưu cạnh có `gia_han_den_ngay`. | Không đổi. | Đã chốt 14/10/2026 |
| V8 | Ý nghĩa thời gian của `dinh-chinh`, `ngung-hieu-luc`, `gia-han`. | `tu_dau`, `tam_ngung`, `ve_sau`. | Đã làm. | Đã chốt 13/10/2026 |
| V9 | "Sau N ngày kể từ ngày ký" tính thế nào? | Không chia nhỏ cách tính. Lưu ngày hiệu lực, mốc tính và số ngày. "Sau 45 ngày" lưu 45. | Gộp `sau_n_ngay_*` vào mốc. Thêm `ngay_hieu_luc_so_ngay`. | Đã chốt 14/10/2026 |
| C1 | Bên Graph có dựng node Chương, Mục của Luật không? | — | Không đổi. ES có `chuong`, `muc_lon` trên chunk. | Chưa chốt (Graph) |
| C2 | Vị trí thuộc Quyết định hay Quy định kèm theo? | Không suy ra. | Chỉ ghi `kem_theo` khi câu nguồn nói rõ. | Đã chốt 14/10/2026 |
| C3 | Mẫu biểu có thành node không? | Không. Mẫu để ở phụ lục chứa nó. | Vị trí `Mẫu số …` thành `Phụ lục <ký hiệu>` hoặc `Phụ lục`. | Đã chốt 14/10/2026 |
| C4 | Danh mục số thứ tự, bảng định mức, bảng giá | Chưa làm. | Không đổi. | Đã chốt 14/10/2026 |
| D1 | Sửa đổi cả Điều thì khoản, điểm cũ thế nào? | Chỉ nối vào Điều đó. Không xét khoản, điểm của Điều. | Không đổi. ES không lan tác động. | Đã chốt 14/10/2026 |
| D2 | "Sửa đổi, bổ sung" trên cùng vị trí: gộp không? | Không. Tách 2 quan hệ riêng. | Không đổi. | Đã chốt 14/10/2026 |
| D3 | Đơn vị mới (Điều 47a, khoản 2a) | ES lưu vị trí câu nêu. Bên Graph quyết định tạo node. | Không đổi. | Đã chốt phần ES |
| D4 | Mỗi vị trí cho một cạnh? | Có. Mỗi vị trí là một cạnh và là một quan hệ. Không gộp trùng. | Tách quan hệ nhiều vị trí. Đánh số lại `_id`. | Đã chốt 14/10/2026 |
| D5 | Ngày hiệu lực riêng cho từng điều khoản? | Có. Mở rộng xuống Điều, khoản, điểm. | Thêm `hieu_luc_rieng` ở văn bản, ngày hiệu lực ở mọi chunk, `source_ngay_hieu_luc` theo đơn vị nguồn. | Đã chốt 14/10/2026 |
| D6 | Bãi bỏ đơn vị con thì đơn vị cha thế nào? | Chỉ nối vào đơn vị bị bãi bỏ. Không xét cha, con. | Không đổi. | Đã chốt 14/10/2026 |
| E1 | Tiết, gạch đầu dòng, câu | Có tiểu điểm dưới điểm thì dùng tiểu điểm. Không có thì giữ nguyên ở đơn vị chứa nó. | Thêm chunk `tieu_diem` và vị trí `tiểu điểm <n> điểm …`. Gạch đầu dòng của khoản, câu, đoạn dừng ở khoản hoặc Điều. | Đã chốt 14/10/2026 |
| E2 | Thay cụm từ "trong toàn bộ Thông tư" | Toàn văn. | Vị trí `toàn bộ`. | Đã chốt 14/10/2026 |

Quy ước ngày 19–20/10/2026. Các quy ước này có trong `eval/rubric-gold.md` và trong prompt của tầng 2. Nhóm Q = cách nhận một quan hệ.

| # | Câu hỏi | Quy ước | Dữ liệu làm | Trạng thái |
| --- | --- | --- | --- | --- |
| Q1 | Luồng dò quan hệ nào là luồng sản phẩm? | Chế độ `llm` (luồng 4 tầng). | `RELATION_EXTRACTOR=llm` là mặc định. | Đã chốt 20/10/2026 |
| Q2 | Tên văn bản có quan hệ riêng khi nào? | Khi chính tên nêu văn bản đích (số hiệu hoặc tên luật). Không lấy số hiệu từ thân văn bản cho tên. | Quan hệ `intro_`. | Thay bằng R6 (27/10/2026, code `3c26438`) |
| Q3 | Câu chung "các quy định trái với văn bản này … bãi bỏ" | Không là quan hệ, kể cả khi câu nêu số hiệu. | Tầng 4 loại (`khong_co_van_ban_dich`). | Đã chốt 20/10/2026 |
| Q4 | Văn bản công bố danh mục văn bản hết hiệu lực (kết quả rà soát) | Không là hành động. Văn bản khác làm các văn bản đó hết hiệu lực. | Tầng 4 loại (`cong_bo_danh_muc`). | Đã chốt 19/10/2026 |
| Q5 | Dòng danh mục thủ tục hành chính | Quan hệ khi dòng hoặc đề mục nêu hành động, dòng nêu quyết định đã công bố thủ tục, và quyết định đó cùng cơ quan. | `source_path = Phụ lục <n> [Mục <m>] STT <k>`. | Đã chốt 19/10/2026 |
| Q6 | Dòng bảng chỉ nêu chi tiết hành động của một Điều | Quan hệ thuộc Điều đó. Dòng không có quan hệ riêng. | Gộp vào Điều. | Đã chốt 19/10/2026 |
| Q7 | Văn bản cấp dưới viết "sửa đổi Điều 12 Luật X" | Không là quan hệ. Chỉ Luật, Pháp lệnh, Nghị quyết của Quốc hội, Ủy ban Thường vụ Quốc hội tác động được lên Luật, Pháp lệnh. | Tầng 4 loại (`vuot_tham_quyen`). | Đã chốt 20/10/2026 |
| Q8 | "Đồng ý với đề nghị của …" | Là quan hệ khi chính câu nêu văn bản đích và nêu rõ thay đổi. Đồng ý một đề xuất sẽ làm bằng văn bản khác thì không. | Prompt tầng 2. | Đã chốt 20/10/2026 |
| Q9 | "Kết thúc", "chấm dứt" một văn bản | `bai-bo` khi chấm dứt hẳn. `ngung-hieu-luc` khi chỉ trong một thời gian. Không là hành động khi chỉ kết thúc chương trình, đề án không có số hiệu. | LLM phân loại theo định nghĩa. | Đã chốt 20/10/2026 |
| Q10 | Vị trí ngoài định dạng hợp đồng | Chuyển sang `doi_tuong`. Không để chờ duyệt. | [09, mục 9.5](09-hop-dong-du-lieu-v4.md#95-vị-trí). | Đã chốt 19/10/2026 |
| Q11 | Tên văn bản: dùng tên in trong văn bản hay tên lưu ở nguồn? | Tên in để dò quan hệ. Tên lưu (`title`) chỉ để tìm kiếm, đối chiếu. | `structure.printed_title` đọc tên in. Nhánh LLM, nhánh quy tắc, quan hệ hướng dẫn chỉ đọc tên in. Câu trích từ tên lưu bị tầng 4 loại. | Đã chốt 20/10/2026 (P0) |
| Q12 | Quan hệ của dòng bảng: giữ từng dòng hay tính là phụ lục chứa dòng? | Giữ từng dòng (cách A). Phân biệt quan hệ lên thủ tục và quan hệ lên văn bản. | Trường `doi_tuong_loai` (`van_ban`, `thu_tuc_hanh_chinh`) và `ma_thu_tuc` ([09, mục 9.10.6](09-hop-dong-du-lieu-v4.md#9106-tác-động)). | Đã chốt 20/10/2026 (P0) |

Quyết định ngày 26–27/10/2026 của người dùng. Q13–Q15 có trong code từ `8b023ca` và bộ chấm `eval/score.py`. Index `-v4` theo Q13, Q14 từ 28/10/2026 (code `1117e63`). Nhóm T = triển khai.

| # | Câu hỏi | Quyết định | Dữ liệu làm | Trạng thái |
| --- | --- | --- | --- | --- |
| Q13 | Vị trí không theo điều – khoản – điểm (Mục, Phần của phương án, dòng danh mục, văn bản kèm theo) nối vào đâu? | Quy ước phụ lục: vị trí đó tính là phụ lục chứa nó. Không xác định được điều – khoản – điểm trong phụ lục thì lưu chữ làm nội dung. Mở rộng C3 từ mẫu biểu sang mọi vị trí không theo điều – khoản – điểm. | `resolver.appendix_scope`: `Phụ lục <n>` khi chữ nêu đúng một số phụ lục, `Phụ lục` khi không nêu số. Ví dụ "Mục II Phần B Phụ lục I" → `Phụ lục I`. Phần nêu bằng tên giữ chữ ở `doi_tuong`. Vị trí gốc ("Mục IV") giữ chữ ở `chi_tiet_vi_tri`. `tên văn bản`, `tên Mục <n>`, Mục dưới Chương giữ nguyên. `Mục <n>` đứng một mình thành phụ lục. | Đã chốt 26/10/2026. Code làm đủ từ `8b023ca` (27/10/2026). |
| Q14 | Phần nêu bằng tên nào thành phụ lục? | Chỉ phần mà phụ lục chứa: danh mục, thủ tục hành chính, biểu mẫu, mẫu số, phương án, quy trình nội bộ, Mục hoặc Phần có số, số thứ tự. Phần khác giữ tên. | `resolver.appendix_like`. "một số điều của các Thông tư …" (`676559_0`) giữ `doi_tuong`, `vi_tri` rỗng. | Đã chốt 27/10/2026 |
| Q15 | Công cụ ghi cả "sửa đổi" và "bổ sung" mà nhãn chỉ có một vế: có tính là thừa không? | Không. Vế thừa không tính là sai khi vế kia đúng. | Chỉ ở bộ chấm (`score.extra_halves`). Dữ liệu không đổi. | Đã chốt 26/10/2026 |
| T1 | Phần nào thuộc luồng triển khai? | Chỉ luồng chính (`vbpl_v3`). `eval/` tách riêng, không thuộc image. | `Dockerfile` chỉ chép `requirements.txt` và `vbpl_v3/`. | Đã chốt 26–27/10/2026 |
| T2 | Đánh giá chất lượng khi thêm dữ liệu thế nào? | Cứ mỗi 10.000 văn bản mới, lấy mẫu 1.000 văn bản để gán nhãn và chấm. | `python -m eval.sample_batch`, chấm bằng `eval.strata` (`eval/README.md`). Đợt 20.000: mẫu 2.000 văn bản `eval/sets/dot-20000-20261028` (28/10/2026). | Đã chốt 26–27/10/2026. Đã làm cho đợt 20.000. |
| T3 | Ghi index nào? | Chỉ ghi `-v4`. Không ghi lại v3 khi bên Graph chưa duyệt v4. Hai ngoại lệ có người dùng duyệt: văn bản 132140 (15/10/2026), 32 văn bản của bộ 88 testcase (27/10/2026). | Script của lượt đặt `TARGET_*_INDEX` thành 3 index `-v4` (ví dụ `work/run-v4-next20000.sh`, `work/run-v4-2710.sh`). `.env` vẫn trỏ tới `-v3` (kiểm 28/10/2026): kiểm biến này trước mỗi lượt. 32 văn bản v3 gỡ được bằng `work/v3-32/manifest.json`. | Đã chốt |

Quyết định ngày 27/10/2026 của người dùng, khi làm sạch 32 văn bản của `loi_du_lieu_v4_32_van_ban.md`. Nhóm R = cách ghi một quan hệ cho đúng và sạch. Các quyết định đã làm có trong master `1117e63` (27/10/2026) ([08, mục 8.18](08-quan-he-4-tang-va-danh-gia.md#818-làm-sạch-dữ-liệu-32-văn-bản-27102026)). Index `-v4` theo các quyết định đã làm từ 28/10/2026. Bộ chấm áp R4–R6 cho nhãn (`3c26438`). Bộ chấm chưa áp R2. Hợp đồng ở [09](09-hop-dong-du-lieu-v4.md). 32 văn bản ghi vào v3 ngày 27/10/2026 được sửa tay theo cả R8–R11.

| # | Câu hỏi | Quyết định | Dữ liệu làm | Trạng thái |
| --- | --- | --- | --- | --- |
| R1 | Một thay đổi có ở cả đơn vị cha (khoản) và đơn vị con (điểm), cùng hành động, đích, vị trí, cụm từ | Giữ dòng của đơn vị con. Bỏ dòng của đơn vị cha. | `convert.distinct_edges`. Dòng cha chỉ bị bỏ khi dòng con là `validated`. Dòng lặp trong cùng một đơn vị giữ một lần. | Đã làm (commit `9dc5f55`) |
| R2 | Dòng của đơn vị cha chỉ có câu dẫn, không có vị trí, trong khi đơn vị con đã có vị trí | Bỏ dòng cha. | Bỏ khi có ít nhất một đơn vị con `validated`, cùng hành động và đích. Không có đơn vị con thì giữ dòng cha. | Đã làm (commit `b06a6d7`) |
| R3 | Câu dẫn viết "Sửa đổi, bổ sung một số khoản …", đơn vị con chỉ viết "Bổ sung khoản 9" hoặc "Sửa đổi điểm đ" | Hành động theo động từ của chính điều, khoản, điểm. Chỉ khi chính đơn vị viết "sửa đổi, bổ sung" mới tách thành 2 quan hệ. | Câu dẫn không áp cặp `sua-doi` + `bo-sung` xuống đơn vị con. Đơn vị không có động từ riêng thì theo câu dẫn. Làm rõ D2. Câu nêu vị trí là "Bãi bỏ …" thì quan hệ là `bai-bo` (`8b3e843`). | Đã làm (commit `3c8cef2`, `8b3e843`) |
| R4 | "Bỏ cụm từ X tại …" | `thay-cum-tu`, `cum_tu = {cu: X, moi: ""}`. | `cum_tu[].moi` rỗng nghĩa là bỏ cụm từ. Hợp đồng đổi: `moi` được rỗng. | Đã làm (commit `3c26438`) |
| R5 | "Bổ sung cụm từ Y vào trước (sau) cụm từ Z tại …" | Không tạo quan hệ. | Bỏ các dòng `bo-sung` không có cụm từ hiện có (ví dụ 131/2025, khoản 71). | Đã làm (commit `3c26438`) |
| R6 | Dòng cấp văn bản lấy từ tên và lời dẫn | Bỏ hết: cả dòng `intro_` (sửa đổi, bổ sung, thay thế, bãi bỏ) và dòng `hd_` (hướng dẫn, quy định chi tiết). | Quan hệ hướng dẫn chỉ còn khi một Điều (thường là Điều 1) nêu văn bản được hướng dẫn. Bộ chấm bỏ qua mục của tên và lời dẫn ở cả nhãn và công cụ. Thay V1, Q2 và phần tiêu đề, lời dẫn của V3. | Đã làm (commit `3c26438`). `-v4`: 0 quan hệ `source_path = intro` (28/10/2026). |
| R7 | "Văn bản X … hết hiệu lực kể từ ngày …" (không có chữ "bãi bỏ", "thay thế") | `bai-bo` toàn bộ. | `thay-the` chỉ khi văn bản viết "thay thế". | Đã chốt (code hiện tại đã làm như vậy) |
| R8 | Hết hiệu lực có ngoại lệ ("… hết hiệu lực, trừ Điều 7 và Phụ lục IV … hết hiệu lực từ ngày 01/7") | Tách dòng theo ngày. Dòng toàn bộ có trường mới `ngoai_tru`. | 143/2025, Điều 51 khoản 4: `bai-bo` toàn bộ 61/2020/QH14 với `ngoai_tru = ["Điều 7", "Phụ lục IV"]`; thêm 2 dòng `bai-bo` "Điều 7", "Phụ lục IV" với ngày riêng. Hợp đồng đổi: thêm `ngoai_tru`. | Chưa làm trong code (kiểm 28/10/2026: `vbpl_v3/` chưa có `ngoai_tru`) |
| R9 | Một phần của văn bản hết hiệu lực với ngày riêng; câu chuyển tiếp không có ngày riêng | Phần có ngày riêng: tách dòng với ngày đó. Câu chuyển tiếp: không ghi. | 109/2025: phần áp dụng từ kỳ tính thuế 2026 là dòng riêng. 95/2025: câu "dự toán 2025 đã giao" không ghi. | Chưa làm trong code |
| R10 | "Sửa đổi, bổ sung đoạn mở đầu của khoản 3 Điều 9" | `vi_tri = ["khoản 3 Điều 9"]`, `chi_tiet_vi_tri = "đoạn mở đầu"`. | Áp cho "đoạn mở đầu", "câu thứ …" của khoản hoặc Điều. Không thêm định dạng vị trí. | Chưa làm trong code |
| R11 | Vị trí nằm trong một mẫu của phụ lục ("khoản 2 Điều 1 Mẫu giấy phép 1c Phụ lục II.4") | `vi_tri` là phụ lục, chỗ trong mẫu ghi ở `chi_tiet_vi_tri`. | 15/2026, Điều 52 khoản 4: `vi_tri = ["Phụ lục II.4"]`, `chi_tiet_vi_tri = "khoản 2 Điều 1 Mẫu giấy phép 1c"`. Không ghi "Điều …" khi Điều đó thuộc một mẫu. Mở rộng Q13. | Chưa làm trong code |
| R12 | Evidence có được ghép nhiều đoạn bằng "…" không | Không. Evidence là một đoạn nguyên văn của chính đơn vị nguồn. | Đoạn phải chứa động từ và văn bản đích hoặc vị trí. | Đã làm (commit `24a8d57`) |
| R13 | `title` của nguồn là tên rút gọn ("Luật Quản lý nợ công sửa đổi 2025") | Giữ như nguồn. | Không thêm trường. Phát hiện về `title` không tính là lỗi. | Đã chốt |
| R14 | Văn bản gốc gõ nhầm số hiệu ("Nghị định số 62/2026/NĐ-CP (được bổ sung bởi Nghị định số 35/2023 …)") | Giữ đúng chữ. Để `unresolved`. | Không đoán đích. | Đã chốt (code hiện tại đã làm như vậy) |
| R15 | Chữ bị tách khi trích PDF ("QU ỐC HỘI", "Tr ần Thanh Mẫn") | Sửa khi nạp `full_content`. | Nối lại khi phần ghép là một âm tiết tiếng Việt hợp lệ. `content_sha256` đổi theo. | Đã làm (commit `c7930ea`) |

## 7.5. Việc còn lại ở bên dữ liệu

Cập nhật ngày 28/10/2026. Bảng đầu là việc chính, theo thứ tự người dùng chốt ngày 27/10/2026. Bảng thứ hai là việc mới sau đợt 20.000. Bảng thứ ba là việc đã có trước 27/10/2026. Bảng cuối là việc còn từ trước.

| # | Việc | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| A | Sửa hết lỗi của 32 văn bản trong `loi_du_lieu_v4_32_van_ban.md` (258 phát hiện), theo quyết định R1–R15 | Code: R1–R6, R12, R15 vào master `1117e63` (27/10/2026). R8–R11 chưa làm trong code. Dữ liệu: 32 văn bản sửa tay rồi ghi vào v3 (27/10/2026, người dùng duyệt). | [08, mục 8.18](08-quan-he-4-tang-va-danh-gia.md#818-làm-sạch-dữ-liệu-32-văn-bản-27102026). Số phát hiện code `1117e63` tự xử lý được: chưa đo. |
| B | Viết bộ eval chất lượng dữ liệu: kiểm từng dòng quan hệ, kiểm metadata, kiểm theo danh sách lỗi đã duyệt | Một phần | Ngày 28/10/2026 có kiểm tự động mẫu 2.000 văn bản và kiểm toàn bộ 75.506 quan hệ `-v4` ([05, mục 5.4.3](05-phien-ban-v2-v3-v4.md#543-chất-lượng-đo-được)). `eval/` chưa có lệnh riêng cho việc này (kiểm 28/10/2026). |
| C | Ghi lại toàn bộ `-v4` bằng code mới. Dùng lại vector `-v4` cho chunk không đổi chữ. | Đã làm 28/10/2026 | Lượt `v4-2710`, code `1117e63`, `EMBEDDING_REUSE=target`. 7 văn bản lỗi còn bản ghi 22/10 (mục 7.2). |
| D | Chạy văn bản mới bằng code mới, embedding API bge-m3 đủ độ dài | Đã làm 27–28/10/2026 với 20.000 văn bản | Lượt `v4-next20000`: 10.000 đầu của `work/v4-next10000b-ids.txt` (ban hành 25/06–08/10/2025) và 10.000 đầu của `work/v4-next10000c-ids.txt` (ban hành 12/03–25/06/2025). 19.988 văn bản ghi được. 10 văn bản lỗi (mục 7.2). |

Việc mới sau đợt 20.000 (28/10/2026). Mọi việc chờ người dùng quyết.

| # | Việc | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| E | Quyết sửa 6 lỗi thật tìm thấy khi chấm đợt 20.000 (mục 7.2) | Chờ người dùng | Sửa trước khi chạy đợt mới. Sửa dàn ý hoặc tách đơn vị thì phải hỏi lại LLM cho các đơn vị đổi. |
| F | Chạy lại 17 văn bản lỗi của đêm 27–28/10/2026 | Chưa làm | Chạy lại cùng lượt, **không** có `--redo` |
| G | Chạy đợt tiếp theo: ID sau 10.000 đầu của `v4-next10000b` và `v4-next10000c` | Chưa có lệnh chạy | Số ID còn lại: chưa đếm. Chạy hai lượt cùng lúc qua VPN `tun0` thì nhiều lỗi `ConnectionError`. |
| H | Người duyệt nhãn agent của đợt 20.000 (`eval/gold/dot-20000-20261028-g300`, `-r`) | Chờ người duyệt | Nhãn đã khóa. Agent gán không thống nhất R2 và "bỏ cụm từ". |
| I | Hợp đồng [09](09-hop-dong-du-lieu-v4.md) ghi đủ loại chunk `phu_luc_doan`, `muc_doan` và trường `loai_phan`, `muc_uid`, `phu_luc_uid`, `so_doan` | Cần cập nhật | Dữ liệu `-v4` đã có các trường này (28/10/2026) |

| # | Việc đã có trước 27/10/2026 | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| 1 | Người duyệt CSV của hold-out 300 (`bernmark/ho300/duyet_ho300.csv`, 1.431 dòng). Sau đó chấm lại. | Chờ người duyệt | Cho số đo độc lập có nhãn của người. Hiện nhãn do agent gán. |
| 2 | Quyết có ghi lại 11.000 văn bản `-v4` bằng code `8b023ca` hay không | Thay bằng việc C (27/10/2026) | Không phải hỏi lại LLM (thay đổi chỉ ở bước sau LLM). Dùng lại câu trả lời đã lưu, 10 luồng: khoảng 60 văn bản/phút, tức khoảng 3 giờ (22/10/2026). |
| 3 | Chạy đợt 10.000 văn bản tiếp theo: `work/v4-next10000b-ids.txt`, 10.200 ID (10.000 và 200 dự phòng), ban hành 25/06/2025–08/10/2025 | Thay bằng việc D (27/10/2026) | Có gọi LLM: 16,3 văn bản/phút ban ngày (3 lời gọi cùng lúc), 45,4 văn bản/phút sau 22:00 (10 lời gọi); khoảng 8,4 lời gọi mỗi văn bản (21–22/10/2026). Chạy lại văn bản lỗi: chạy lại cùng lượt **không** có `--redo`. |
| 4 | Sau đợt 3: lấy mẫu 1.000 văn bản (`python -m eval.sample_batch`), gán nhãn, chấm (`eval.strata`) | Đã làm 28/10/2026 cho đợt 20.000: mẫu 2.000 văn bản, nhãn agent | Quyết định T2. Số đo ở [05, mục 5.4.3](05-phien-ban-v2-v3-v4.md#543-chất-lượng-đo-được). |
| 5 | Sửa prompt: bắt chọn rõ cả văn bản hay một phần; thủ tục hành chính; cặp hành động dễ nhầm | Chưa làm | Mọi câu trả lời đã lưu hết hiệu lực: phải hỏi lại LLM cho mọi đơn vị. 9 bộ hiện có đã dùng để sửa (hold-out 300 còn độc lập), nên cần bộ mới để đo. Mẫu đợt 20.000 (28/10/2026) là bộ độc lập mới, nếu không dùng nó để sửa. Lỗi đọc nghĩa đã biết (`124929`: chọn sai đích, nhận câu đề nghị, giao nhiệm vụ là hành động) thuộc việc này. Không viết quy tắc riêng cho một văn bản. |
| 6 | Sửa parser: biểu mẫu trong phụ lục không tách thành Điều; bỏ Điều trùng nội dung | Biểu mẫu: đã làm (`c394162`, trong master `1117e63`), có trong `-v4` từ 28/10/2026. Điều trùng nội dung: chưa sửa. | [10, S8](10-khoang-trong-du-lieu.md#s8-điều-1-lặp-và-biểu-mẫu-tách-thành-điều). Đơn vị đổi thì phải hỏi lại LLM cho đơn vị đó. |
| 7 | Áp quy ước phụ lục cho vị trí tính từ `scope` và cho `cum_tu[].vi_tri`; chốt `tên văn bản`, `tên Mục <n>`, `Mục <n>` | Đã xong 27/10/2026 (`8b023ca`) | 0 vị trí lọt quy ước trên 876 văn bản (lượt `fix9-*`, 27/10/2026). `tên văn bản`, `tên Mục <n>` giữ nguyên; `Mục <n>` đứng một mình thành phụ lục. |
| 8 | Bên Graph trả lời câu hỏi ở [11](11-cau-hoi-graph.md), gồm cách nối `vi_tri = ["Phụ lục"]` không số | Chờ bên Graph | Mục 7.1 |
| 9 | Bên Graph duyệt `-v4` | Chờ bên Graph | Dashboard số liệu `-v4`: https://claude.ai/artifact/9sGL8D5ZSGcNLibgQwvMjQ (28/10/2026) |
| 10 | Sau khi duyệt: ghi lại v3 bằng luồng chốt | Chờ duyệt | Quyết định T3. Chỉ chạy `convert` thì mất sửa tay của 32 văn bản v3 (`work/v3-32/`). |

| Việc còn từ trước | Trạng thái |
| --- | --- |
| Ghi lại 3 index `-v4` bằng luồng chốt | Đã làm 22/10/2026 (11.000 văn bản, code `2911b77`, [08, mục 8.15](08-quan-he-4-tang-va-danh-gia.md#815-chốt-luồng-và-ghi-lại-v4-22102026)). Ghi lại lần nữa 28/10/2026 bằng code `1117e63` (việc C). |
| Đo thời gian và dung lượng trước khi chạy toàn kho | Đã đo trên 11.000 văn bản mới nhất (21/10/2026): 544 MB văn bản, 6,5 GB chunk, 20 MB quan hệ. Đo 28/10/2026 trên 30.988 văn bản: 1,4 GB văn bản, 33,9 GB chunk, 44,3 MB quan hệ. Chưa đo trên mẫu ngẫu nhiên. |
| Q11, Q12 | Đã có trong `-v4` từ 21/10/2026 |
| Văn bản có toàn văn tiếng Anh (`39074`) | Đã làm 20/10/2026: công cụ bỏ qua (`skipped = tieng_anh`) |
| Lỗi `n_table_rows` của `132723_pl0` | Chưa sửa |
| Danh mục số thứ tự, bảng định mức, mục `1.2.2` làm node (C4) | Chưa làm theo quyết định. Từ code 27/10/2026, vị trí là phụ lục chứa dòng (Q13). |
| Điền `signers`, `legal_sectors` còn thiếu bằng model, có dẫn chứng | Có từ 29/10/2026 (`metadata_fill`): code trước, model sau |
| Chuẩn hóa: số hiệu "không số" (846 văn bản) thành rỗng; gộp nhãn `legal_type` gần trùng (`Điều ước` / `Điều ước quốc tế`, `Văn bản WTO` / `WTO_Văn bản`) | Cần duyệt |
| Giới hạn 256 token của embedding: tăng `max_length` (đặt `EMBEDDING_REUSE=no`) hoặc thêm chunk con | Đã làm: vector đủ độ dài qua API bge-m3 kiểu OpenAI (`57b9033`), đoạn tìm kiếm cho phụ lục (300 từ) và đề mục (150 từ) (`c394162`, `57b9033`). Có trong `-v4` từ 28/10/2026. `.env` dùng chung vẫn để API cũ; lượt chạy đặt biến trong `work/.embedding.env` (kiểm 28/10/2026). |
| Báo bên đọc: ID chunk văn bản kèm theo đổi từ `_s<s>_` sang `_pl<i>_`; mỗi quan hệ chỉ còn một vị trí; chỉ dựng cạnh khi `resolution_status = validated`; từ code 27/10/2026 có vị trí `Phụ lục` không số; chunk `phu_luc_doan`, `muc_doan` là đoạn tìm kiếm, không là node | Cần báo |
| Ca parser sai đã biết (`315654`, `128228`) | Duyệt tay sau khi chuyển |
