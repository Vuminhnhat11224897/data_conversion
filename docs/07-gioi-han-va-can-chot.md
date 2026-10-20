# 7. Giới hạn, lỗi đã biết và quyết định đã chốt

Số liệu đo trên bản thử `-v4` ngày 14/10/2026: 203 văn bản, 6.610 chunk, 969 quan hệ. v3 sẽ có cùng số sau khi ghi lại.

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
| Dịch vụ embedding cắt đầu vào ở 256 token. | Phần đuôi chunk dài không tìm được bằng vector. | — |
| `signers` (447 văn bản), `legal_sectors` (4 văn bản) còn thiếu ở nguồn. | v3 chép nguyên. Chưa có lệnh điền. | — |

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
| V1 | Tiêu đề, lời dẫn và các Điều cùng nối tới một đích. Giữ cả hai không? | Giữ. Tiêu đề và lời dẫn có quan hệ riêng. | Bỏ quy tắc loại quan hệ lời dẫn trùng với Điều. | Đã chốt 14/10/2026 |
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

## 7.5. Việc còn lại ở bên dữ liệu

| Việc | Trạng thái |
| --- | --- |
| Bên Graph duyệt bản thử `-v4` | Chờ duyệt |
| Sau khi duyệt: xóa 3 index `-v4`, ghi lại v3 bằng quy tắc mới (`init`, rồi `convert --redo`) | Chờ duyệt |
| Sửa các lỗi còn lại ở mục 7.2 | Chưa làm |
| Danh mục số thứ tự, bảng định mức, mục `1.2.2` (C4) | Chưa làm theo quyết định |
| Điền `signers`, `legal_sectors` còn thiếu bằng model, có dẫn chứng | Chưa có lệnh |
| Chuẩn hóa: số hiệu "không số" (846 văn bản) thành rỗng; gộp nhãn `legal_type` gần trùng (`Điều ước` / `Điều ước quốc tế`, `Văn bản WTO` / `WTO_Văn bản`) | Cần duyệt |
| Giới hạn 256 token của embedding: tăng `max_length` (đặt `EMBEDDING_REUSE=no`) hoặc thêm chunk con | Cần chốt |
| Báo bên đọc: ID chunk văn bản kèm theo đổi từ `_s<s>_` sang `_pl<i>_`; mỗi quan hệ chỉ còn một vị trí | Cần báo |
| Ca parser sai đã biết (`315654`, `128228`) | Duyệt tay sau khi chuyển |
