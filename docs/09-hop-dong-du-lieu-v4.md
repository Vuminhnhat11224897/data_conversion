# 9. Hợp đồng dữ liệu v4

Tài liệu này mô tả 3 index v4 trên ES đích `10.1.10.23`. Bên dữ liệu ghi các index này. Bên Graph và bên tìm kiếm đọc.

- v4 là bản thử. Bên Graph duyệt v4. Sau khi duyệt, công cụ ghi lại v3 theo đúng hợp đồng này, chỉ đổi hậu tố `-v4` thành `-v3`.
- Hợp đồng là dữ liệu mà `convert` ghi bằng luồng chốt ngày 20/10/2026 (chế độ `llm`, mặc định). Công cụ ghi bản ghi v4 hiện có ngày 14/10/2026 bằng code cũ hơn. Một số trường mới chưa có trong các bản ghi đó (mục 9.1).
- So sánh v2, v3, v4 ở [05](05-phien-ban-v2-v3-v4.md). Chất lượng đo được của luồng chốt ở [08, mục 8.8](08-quan-he-4-tang-va-danh-gia.md#88-vòng-3-20102026-và-hold-out-3).
- Số liệu đo ngày 16/10/2026 trên v4: 532 văn bản, 22.825 chunk, 2.009 quan hệ. Số liệu của luồng 4 tầng lấy từ lượt chạy thử `eval-llm-blind` (290 văn bản, 15/10/2026).
- Ví dụ viết dạng `<index>/<_id>`. Ví dụ chỉ có trong lượt chạy thử thì ghi tên lượt.
- Giá trị enum giải thích ở [06-bang-enum.md](06-bang-enum.md). Quyết định đã chốt ở [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt). Luồng 4 tầng ở [08](08-quan-he-4-tang-va-danh-gia.md).
- Nguyên tắc chung: **chỉ lưu tác động văn bản nêu trực tiếp. Không suy diễn tác động mà văn bản không nói.**

## 9.1. Trạng thái v4

### 9.1.1. Bản ghi hiện có

| Index | Số bản ghi | `ingest_job_id` |
| --- | --- | --- |
| `legal-docs-v4` | 532 | `v3:20261014T064855Z` (503), `v3:20261014T100709Z` (29) |
| `legal-chunk-section-v4` | 22.825 | Như trên |
| `legal-changed-v4` | 2.009 | Như trên |

Tiền tố `v3:` là tên công cụ. Tiền tố này không chỉ tên index.

### 9.1.2. Thay đổi sau ngày 14/10/2026 chưa có trong bản ghi v4

| Ngày | Thay đổi | Ảnh hưởng tới bản ghi |
| --- | --- | --- |
| 15/10 | 5 trường mới của quan hệ: `resolution_status`, `resolution_reason`, `extraction`, `evidence`, `target_section`. | Mapping v4 chưa có 5 trường này. Bản ghi v4 chưa có. |
| 15/10 | Tầng cấu trúc mới: số chú thích dính nhãn, phần mở đầu của công văn, câu kết của Nghị quyết, `Điều thứ`, `Điêu`, nhãn `I-`, dàn ý do LLM lập ([08, mục 8.3](08-quan-he-4-tang-va-danh-gia.md#83-tầng-cấu-trúc-quy-tắc-và-llm)). | Ranh giới và nội dung chunk của một số văn bản đổi. |
| 15/10 | `noi_nhan` rỗng khi văn bản không có mục "Nơi nhận". Trước đó công cụ ghi dòng chữ ký vào `noi_nhan`. | 18/532 văn bản v4 có dòng chữ ký trong `noi_nhan`. |
| 15/10 | Chế độ dò quan hệ 4 tầng (`--extractor llm`). Từ 20/10 đây là chế độ mặc định. | Quan hệ có `detection_mode = llm`. |
| 16/10 | Quan hệ có `cap_quan_he = chua_xac_dinh` luôn có `resolution_status = unresolved`, ở cả hai chế độ. | Không có cạnh nào thiếu node đích. |
| 19/10 | Dòng bảng của phụ lục không chia Điều được đọc. `source_path` mới `Phụ lục <n> [Mục <m>] STT <k>` (mục 9.6). | Thêm quan hệ từ danh mục thủ tục hành chính và danh sách văn bản. |
| 19/10 | Vị trí ngoài định dạng chuyển sang `doi_tuong`. Cùng đơn vị nguồn, hành động, văn bản đích thì không có cả vị trí cha lẫn vị trí con. "toàn bộ" bên cạnh vị trí cụ thể thì chỉ giữ vị trí cụ thể. | Hết cạnh thừa lên khoản cha (`661129`) và cạnh "toàn bộ" sai (`634166`). |
| 19/10 | Câu "… hết hiệu lực": mỗi văn bản đích có phạm vi riêng, đọc qua danh sách ngăn bằng `;`. Dòng "số thứ tự" cho phụ lục chứa dòng. | `634166`: 3 văn bản, mỗi văn bản một phụ lục, không còn "toàn bộ 1659". |
| 19/10 | `hieu_luc_rieng[].vi_tri` đọc đủ danh sách ngăn bằng `;`. | `628717`: 10 vị trí, trước là 3. |
| 19/10 | `noi_nhan` không còn khối chữ ký nằm cùng dòng bảng ("Lưu: VT. \| TM. …"). | 338/532 văn bản v4 có lỗi này. Hết sau khi ghi lại. |
| 19/10 | "Sửa đổi, bổ sung X" luôn cho 2 quan hệ, kể cả khi LLM chỉ nêu một. | — |
| 20/10 | Điều thực hiện hành động lên "các văn bản tại Phụ lục/Danh mục/Danh sách kèm theo" cho một quan hệ với mỗi văn bản của danh sách. `source_path` là Điều đó. | Thêm quan hệ từ danh sách văn bản bãi bỏ, hủy bỏ (`226447`). |
| 20/10 | Phụ lục viết thành đoạn văn: đơn vị nguồn `Phụ lục <n> Mục <m>` (mục 9.6). | Thêm quan hệ từ phụ lục văn xuôi. |
| 20/10 | Hành động ở tên văn bản có quan hệ `intro_` khi tên nêu số hiệu văn bản đích. | Thêm quan hệ cấp văn bản. |
| 20/10 | Q11: công cụ chỉ đọc tên in trong văn bản để dò quan hệ (nhánh LLM, nhánh quy tắc, quan hệ hướng dẫn). Tên lưu ở nguồn (`title`) chỉ dùng cho tìm kiếm, đối chiếu và trường `source_title`. | Hết quan hệ do tên lưu tự thêm (`144450`, `628298`). Số hiệu đích theo chữ in: `31/CP`, không phải `31/CP-1996` (`40110`). |
| 20/10 | Q12: trường mới `doi_tuong_loai`, `ma_thu_tuc` (mục 9.10.6). Mapping thêm 2 trường; chạy `init` trước khi ghi. | Tách quan hệ lên thủ tục hành chính khỏi quan hệ lên văn bản. |
| 20/10 | Văn bản có toàn văn tiếng Anh được bỏ qua (`skipped = tieng_anh`). | `39074` không có bản ghi. |
| 20/10 | Văn bản không phải Luật, Pháp lệnh, Nghị quyết của Quốc hội, Ủy ban Thường vụ Quốc hội không có quan hệ sửa đổi, bãi bỏ, thay thế lên Luật, Pháp lệnh. | Bớt quan hệ thừa từ câu đề xuất sửa Luật. |
| 20/10 | Danh sách vị trí lẫn cấp được tách đúng ("khoản 1 và điểm c, điểm đ khoản 3 Điều 15"). | Vị trí đúng hơn (`609183`). |
| 20/10 | Số hiệu có gạch ("38-HD/BTCTW", "481-TTg") được khớp. "Phụ lục số 07" thành "Phụ lục 07". | — |

### 9.1.3. Cách đưa v4 về đúng hợp đồng

Bên dữ liệu làm các bước này. Bước chi tiết ở [02, "Ghi thử vào v4"](02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3).

1. Đặt 3 biến `TARGET_*_INDEX` sang tên `-v4`.
2. Chạy `init`. Lệnh thêm 5 trường mới vào mapping v4.
3. Chạy `convert --run <lượt> --ids <file> --redo`.

Trong lúc chờ ghi lại, bên Graph dùng `cap_quan_he` khác `chua_xac_dinh` thay cho `resolution_status = validated`.

## 9.2. Khác với v3 hiện có

v3 hiện có 204 văn bản. Công cụ ghi v3 bằng quy tắc ngày 13/10/2026. v4 áp dụng các quyết định ngày 14/10/2026 và các thay đổi ở mục 9.1.2.

| Phần | v3 hiện có | v4 |
| --- | --- | --- |
| Văn bản | Không có `hieu_luc_rieng`, `ngay_hieu_luc_so_ngay`. | Có. |
| Chunk | Không có `diem_uid`, `so_tieu_diem`, loại `tieu_diem`, ngày hiệu lực của đơn vị (`ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_so_ngay`, `ngay_hieu_luc_rieng`, `ngay_hoi_to`). | Có. |
| Một quan hệ có mấy vị trí | Có thể nhiều. 68/733 quan hệ có từ 2 vị trí. | Đúng một vị trí, hoặc rỗng. |
| Mẫu biểu | `Mẫu số 01 Phụ lục I` (`legal-changed-v3/602450_4`) | Phụ lục chứa mẫu: `Phụ lục I` |
| Hợp nhất | Không có quan hệ `hop-nhat`. | Văn bản hợp nhất có quan hệ `hop-nhat` (`hn_`). |
| Tác động suy ra | Có một số tác động lên đơn vị cha, con. | Chỉ tác động văn bản nêu trực tiếp. |
| Trạng thái cạnh | Không có. | `resolution_status`, `resolution_reason`, `extraction`. |

## 9.3. Phạm vi và quy tắc chung

| Index | Một bản ghi là | Số bản ghi | Mẫu `_id` |
| --- | --- | --- | --- |
| `legal-docs-v4` | Một văn bản | 532 | `<doc>`, bằng `_id` ở `legal-docs` nguồn |
| `legal-chunk-section-v4` | Một chunk | 22.825 | `<doc>_<đơn vị>`, ví dụ `602450_d1_k1_pa` |
| `legal-changed-v4` | Một quan hệ | 2.009 | `[<tiền tố>]<source_id>_<n>`, ví dụ `602450_1` |

Quy tắc chung:

1. Mọi trường trong bảng đều có, trừ trường ghi "Có khi …".
2. Trường không có trong hợp đồng thì không thuộc hợp đồng. Không dùng trường đó.
3. Mapping `legal-changed-v4` có `inherited_from_v1`. Dữ liệu v4 không có trường này. Không dùng.
4. Vector có 1.024 chiều (`BAAI/bge-m3`). `legal-changed-v4` không có vector.
5. Mapping cho phép ES tự thêm trường. Công cụ không ghi trường ngoài hợp đồng. Bên đọc không dựa vào trường ngoài hợp đồng.

| Ký hiệu | Nghĩa |
| --- | --- |
| Có khi X | Trường có khi X đúng. Trường thiếu khi X sai. |
| `null` | Trường có, giá trị là `null`. |
| Rỗng | Giá trị là `""` hoặc `[]`. |
| Ngày | Chuỗi `YYYY-MM-DD` hợp lệ. |
| Thời điểm | Chuỗi ISO 8601 có múi giờ. |

## 9.4. Khóa nối

| Từ | Đến | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| chunk `doc_id` | văn bản `_id` | Mọi chunk thuộc một văn bản có trong `legal-docs-v4`. Mọi văn bản có ít nhất một chunk. Đo 16/10: đúng cả hai. | `602450_d1_k1_pa` → `602450` |
| chunk `dieu_uid`, `khoan_uid`, `diem_uid` | node Điều, khoản, điểm | Gom chunk con với đơn vị chứa nó. `_id` của chunk bắt đầu bằng `dieu_uid`. | `602450_d1_k1_pa`: `dieu_uid = 602450_d1`, `khoan_uid = 602450_d1_k1` |
| quan hệ `source_id` | văn bản `_id` | Văn bản nguồn luôn có trong `legal-docs-v4`. `source_id` là số nguyên. `_id` là chuỗi. | `602450_1` → `602450` |
| quan hệ `target_matched_id` | `legal-docs._id` (nguồn) | Văn bản đích có trong v4 chỉ khi văn bản đó đã chuyển. Đo 16/10: 339/1.922 đích đã nối có trong v4. | `602450_1` → `legal-docs/133717` |
| chunk `dan_chieu[].target_id` | `legal-docs._id` (nguồn) | Như `target_matched_id`. `null` khi chưa nối được (71/3.660 chunk có dẫn chiếu). | `602450_d2_full` → `legal-docs/315420` |

## 9.5. Vị trí

`vi_tri`, `cum_tu[].vi_tri`, `dan_chieu[].vi_tri`, `hoi_to_vi_tri` và `hieu_luc_rieng[].vi_tri` dùng định dạng này. Vị trí thuộc văn bản đích, văn bản được dẫn chiếu, hoặc chính văn bản (`hoi_to_vi_tri`, `hieu_luc_rieng`).

| Dạng | Nghĩa | Ví dụ |
| --- | --- | --- |
| `Điều <x>` | Cả Điều | `Điều 11`, `Điều 47a` |
| `khoản <y> Điều <x>` | Cả khoản | `khoản 1 Điều 6` |
| `điểm <z> khoản <y> Điều <x>` | Cả điểm | `điểm a khoản 3 Điều 2` (`legal-changed-v4/602450_1`), `điểm đ1 khoản 2 Điều 19` (`588810_12`) |
| `tiểu điểm <n> điểm <z> khoản <y> Điều <x>` | Mục gạch đầu dòng thứ `n` của một điểm | `tiểu điểm 3 điểm b khoản 3 Điều 17` (`legal-changed-v4/378946_0`) |
| `tên Điều <x>` | Chỉ tên Điều. Nội dung giữ nguyên. | `tên Điều 42` |
| `tên Chương <c>` | Chỉ tên Chương | `tên Chương IV` (`legal-changed-v4/288269_27`) |
| `tên Mục <n> Chương <c>`, `tên Mục <n>` | Chỉ tên Mục | `tên Mục 2 Chương II` |
| `Chương <c>`, `Mục <n>`, `Mục <n> Chương <c>` | Cả Chương, cả Mục | `Chương III` ("Bãi bỏ Chương III"), `Mục 8 Chương 1` (`662238_18`) |
| `Phụ lục`, `Phụ lục <ký hiệu>` | Phụ lục. Không có ký hiệu khi câu nguồn không nêu. | `Phụ lục 03` (`legal-changed-v4/192512_0`) |
| `Mục <ký hiệu> Phụ lục <ký hiệu>`, `Mục <ký hiệu> Phần <ký hiệu> Phụ lục` | Mục, Phần của một phụ lục | `Mục D.2 Phụ lục I`, `Mục 6 Phụ lục III` |
| `tên văn bản` | Chỉ tên văn bản | — |
| `toàn bộ` | Cả văn bản | `legal-changed-v4/hn_589448_0` |

Thành phần:

- `<x>`, `<y>`: số, có thể kèm một chữ thường. Ví dụ: `47a`, `1a`.
- `<z>`: chữ cái, có thể kèm số (`a`, `đ`, `đ1`), hoặc số thập phân (`1.2`).
- `<c>`: số La Mã hoặc số (`IV`, `1`). Công cụ ghi đúng như văn bản đích viết.
- `tiểu điểm`, `khoản`, `điểm`, `tên` viết thường. `Điều`, `Chương`, `Mục`, `Phụ lục` viết hoa chữ đầu.

Quy tắc:

- Gạch đầu dòng của khoản hoặc Điều, câu, đoạn không có node. Vị trí dừng ở khoản hoặc Điều chứa nó. Câu "đoạn 3, điểm a, khoản 2, Điều 4" cho `điểm a khoản 2 Điều 4`.
- Tiết hoặc mục số La Mã bên trong một Điều không có node. Câu "điểm b tiết 3.5, mục III, Điều 1" cho `Điều 1`.
- Mẫu biểu nằm ở phụ lục chứa nó. Câu "Mẫu số 04 Phụ lục I" cho `Phụ lục I`.
- Một dòng "số thứ tự N" của danh mục hoặc bảng không có node (C4). Vị trí là phụ lục chứa danh mục, ví dụ `Phụ lục V`. Câu chỉ nêu danh mục bằng tên thì `vi_tri` rỗng và `doi_tuong` là tên danh mục.
- Câu nêu Mục mà câu dẫn nêu đúng một phụ lục ("Sửa đổi, bổ sung Phụ lục III …: 2. Bổ sung Mục 6") cho `Mục 6 Phụ lục III`.
- Vị trí nằm sau số hiệu văn bản đích là một phần tên văn bản đó. Câu "thay thế Quyết định số 42/2018/QĐ-UBND … sửa đổi Điểm a, Khoản 2 Điều 3 …" cho `toàn bộ`.
- Mỗi quan hệ có một vị trí. Câu "khoản 2, 3, 4 Điều 7" cho 3 quan hệ: `khoản 2 Điều 7`, `khoản 3 Điều 7`, `khoản 4 Điều 7`.
- Câu "điểm a và điểm b khoản 2 Điều 11" cho `điểm a khoản 2 Điều 11` và `điểm b khoản 2 Điều 11`. Điểm trước nhận khoản và Điều của điểm sau.

Đo 16/10/2026: 14/2.009 quan hệ v4 có vị trí ngoài định dạng. Ví dụ: `Tên Điều 23` (`660522_65`, chữ "T" viết hoa), `tên Phụ lục I` (`691249_9`), `Phụ lục 04, dòng “Điểm thành tích”` (`588531_13`). Luồng 4 tầng có 17/759 vị trí ngoài định dạng, phần lớn là dòng danh mục: `Phụ lục I Mục III số 2, 3` (lượt chạy thử `eval-llm-blind`, `600990_2`). Bên Graph bỏ qua cạnh có vị trí ngoài định dạng. Từ ngày 19/10/2026, công cụ chuyển vị trí ngoài định dạng sang `doi_tuong`. Ví dụ: `Mục Thời gian thực hiện đối với 11 thủ tục hành chính` (`542598`, Điều 2) thành `doi_tuong`, `cap_quan_he = van_ban_kem_theo`. Chữ `Tên Điều` viết hoa được đổi thành `tên Điều`.

## 9.6. Đơn vị nguồn

`source_path` chỉ đơn vị của văn bản nguồn chứa câu tác động. `source_path` không dùng định dạng Vị trí: `Khoản` viết hoa, thứ tự từ Điều xuống điểm. Không so sánh trực tiếp `source_path` với `vi_tri`.

| Dạng | Nghĩa | Chunk tương ứng | Ví dụ |
| --- | --- | --- | --- |
| `Điều <x>` | Cả Điều của văn bản nguồn | `<doc>_d<x>` hoặc `<doc>_d<x>_full` | `Điều 3` (`legal-changed-v4/hidden_394837_0`) |
| `Điều <x> Khoản <y>` | Khoản | `<doc>_d<x>_k<y>` hoặc `…_full` | `Điều 1 Khoản 22` → `288269_d1_k22` |
| `Điều <x> Khoản <y> điểm <z>` | Điểm | `<doc>_d<x>_k<y>_p<z>` | `Điều 1 Khoản 1 điểm a` → `602450_d1_k1_pa` |
| `Phụ lục <n> ` + một dạng ở trên | Điều trong phụ lục thứ `n`, đếm từ 1 | `<doc>_pl<n−1>_d<x>…` | 1 quan hệ v4 |
| `… Văn bản kèm theo <s> …` | Điều thuộc chuỗi Điều kèm theo thứ `s` | `…_s<s>_d<x>…` | — |
| `intro` | Lời dẫn. Chế độ `llm`: lời dẫn hoặc tên in trong văn bản (quy ước Q11). Tên lưu ở nguồn (`title`) không tạo quan hệ. | Node văn bản | `legal-changed-v4/intro_318496_0` |
| `Tiêu đề`, `Lời dẫn` | Chỉ có ở quan hệ hướng dẫn | Node văn bản | `legal-changed-v4/hd_356281_0` |
| `Phần đầu` | Phần đầu của văn bản hợp nhất. Phần này nêu văn bản được hợp nhất. | Node văn bản | `legal-changed-v4/hn_589448_0` |
| `Mục <n>` | Đề mục của văn bản không chia Điều. `<n>` là nhãn như văn bản viết (`1`, `IX`, `PHẦN I`). | `<doc>_m<n>` | `Mục 1` → `318496_m1` |
| `Nội dung` | Văn bản không chia Điều, không có đề mục | `<doc>_nd` hoặc `<doc>_nd_full` | Lượt chạy thử `eval-llm-blind` |
| `Phụ lục <n> Mục <m>`, `Phụ lục <n>` | Đề mục `<m>` (`1`, `II`) của phụ lục thứ `n` viết thành đoạn văn, không chia Điều, không phải bảng. `Phụ lục <n>` khi phụ lục không có đề mục. Từ 20/10/2026. | Không có chunk riêng. Node nguồn là phụ lục `<doc>_pl<n−1>`. | `Phụ lục 1 Mục 2` (`124929`, lượt `r3-holdout2`) |
| `Phụ lục <n> STT <k>`, `Phụ lục <n> Mục <m> STT <k>` | Một dòng bảng của phụ lục thứ `n` (đếm từ 1) không chia Điều. `<m>` là ký hiệu đề mục chứa bảng (`A`, `II`). `<k>` là số ở cột "TT"/"STT", hoặc thứ tự dòng khi cột không có số. Từ 19/10/2026. | Không có chunk riêng. Node nguồn là phụ lục `<doc>_pl<n−1>`. | `Phụ lục 1 Mục A STT 1` (lượt `trace4-fix1`, `587301`) |

Quy tắc của dòng bảng:

- Dòng có quan hệ khi dòng nêu số hiệu văn bản đích, và chữ chỉ hành động nằm ở dòng hoặc ở đề mục của danh sách thủ tục hành chính chứa dòng.
- Văn bản ở cột căn cứ pháp lý không phải đích. Công cụ bỏ cột này trước khi đọc.
- Một Điều đã nêu cùng hành động lên cùng văn bản đích ("Điều 2. Bãi bỏ 107 thủ tục … tại Quyết định số 158/…") thì dòng của phụ lục chỉ là chi tiết: quan hệ thuộc Điều đó, dòng không có quan hệ riêng.
- Danh mục văn bản hết hiệu lực mà văn bản chỉ "công bố" (kết quả rà soát) không có quan hệ.
- Thủ tục nêu bằng tên: `vi_tri` rỗng, `doi_tuong` là tên thủ tục, `kem_theo = true`.

## 9.7. Trường truy vết

Cả 3 index có 5 trường này.

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `origin` | keyword | `legacy` hoặc `user_upload`. Chép từ nguồn. Nguồn thiếu thì `legacy`. | `legacy` (531), `user_upload` (1) |
| `ingest_job_id` | keyword | `v3:<run_id>`, `run_id` dạng `YYYYMMDDTHHMMSSZ`. Lượt đã ghi bản ghi. | `v3:20261014T064855Z` |
| `ingest_revision` | integer | Luôn bằng `1`. | `1` |
| `ingested_at` | date | Thời điểm ghi (UTC). | `2026-10-14T09:23:31.227560+00:00` |
| `uploaded_by` | keyword | Luôn bằng `migration-v3`. | `migration-v3` |

Chunk có 5 trường bằng giá trị của văn bản. Quan hệ có 5 trường bằng giá trị của văn bản nguồn.

## 9.8. `legal-docs-v4`

### 9.8.1. Ví dụ: `legal-docs-v4/602450`

Chuỗi dài giữ câu đầu và "…". Mảng dài giữ 1–2 phần tử đầu. `embedding` giữ 3 số đầu.

```json
{
  "_index": "legal-docs-v4",
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
    "noi_nhan": ["Ban Bí thư Trung ương Đảng", "… (19 phần tử)"],
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
    "ngay_hieu_luc_so_ngay": 0,
    "ngay_hieu_luc_trich": "Nghị định này có hiệu lực thi hành kể từ ngày ký ban hành.",
    "hieu_luc_rieng": [],
    "ngay_het_hieu_luc": null,
    "ngay_het_hieu_luc_cach": "khong_ghi",
    "ngay_het_hieu_luc_trich": null,
    "hoi_to": false,
    "ngay_hoi_to": null,
    "ngay_hoi_to_trich": null,
    "hoi_to_vi_tri": [],
    "origin": "legacy",
    "ingest_job_id": "v3:20261014T064855Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-14T09:23:31.227560+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 9.8.2. Định danh và metadata

Công cụ chép các trường này từ `legal-docs` nguồn. Công cụ không sửa giá trị.

| Trường | Kiểu | Có | Quy tắc | Đo 16/10 |
| --- | --- | --- | --- | --- |
| `_id` | chuỗi | Mọi văn bản | Chỉ có chữ số. Bằng `_id` nguồn. | 532 |
| `document_number` | keyword | Mọi văn bản | Khác rỗng. Không duy nhất. | 532 |
| `title` | text | Mọi văn bản | Khác rỗng. | 532 |
| `legal_type` | keyword | Mọi văn bản | Khác rỗng. | 18 giá trị. Nhiều nhất: Quyết định 261, Thông tư 58, Công văn 53. |
| `legal_sectors` | mảng keyword | Có khi nguồn có | Mỗi phần tử khác rỗng. | 532 |
| `issuing_authority` | keyword | Mọi văn bản | Khác rỗng. | 532 |
| `issuance_date` | date | Mọi văn bản | Là Ngày. | 532 |
| `signers` | keyword, không index | Có khi nguồn có | Dạng `Tên:mã`. Nhiều người cách nhau bằng dấu phẩy. Văn bản tải lên chỉ có tên. | 532 |
| `tom_tat` | text | Mọi văn bản | Khác rỗng. | 532 |
| `action` | keyword | Mọi văn bản | Phân loại văn bản ở nguồn. **Không phải** hành động của quan hệ. | 532 |
| `url` | keyword, không index | Mọi văn bản | `legacy`: bắt đầu bằng `https://thuvienphapluat.vn/`. `user_upload`: `upload://<_id>`. | 532 |
| `pdf_minio_path` | keyword | Có khi nguồn có | `tvpl-pdf/…_<_id>.pdf` hoặc `legal-upload/pdf/<sha256>.pdf`. | 395 |
| `pdf_vbpl_id` | keyword | Có khi nguồn có | Chỉ có chữ số. | 138 |
| `embedding` | dense_vector 1.024 | Mọi văn bản | Chép từ nguồn. Nguồn thiếu thì công cụ tạo vector của `title`. | 532 |

### 9.8.3. Nội dung và cấu trúc

Công cụ tính lại các trường này từ toàn văn.

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `full_content` | text | Mọi văn bản | Toàn văn nguồn, chuẩn hóa NFC. Khác rỗng. |
| `content_sha256` | keyword | Mọi văn bản | SHA-256 (hex) của `full_content` mã hóa UTF-8. |
| `text_source` | keyword | Mọi văn bản | Nơi lấy chữ. `legacy` luôn là `source_full_content`. Đo 16/10: 1 văn bản `ocr`. |
| `can_cu` | mảng chuỗi, không index | Mọi văn bản | Mỗi phần tử là một dòng bắt đầu bằng "Căn cứ". Rỗng khi không có căn cứ. |
| `can_cu_refs` | mảng keyword | Mọi văn bản | Số hiệu nêu trong `can_cu`. Rỗng ở 134/532 văn bản. |
| `intro` | text | Mọi văn bản | Lời dẫn sau căn cứ, trước Điều đầu tiên. Công văn: phần trước đề mục đầu tiên. Rỗng khi không có. |
| `noi_nhan` | mảng chuỗi, không index | Mọi văn bản | Mỗi dòng sau "Nơi nhận" là một phần tử. Rỗng khi văn bản không có mục "Nơi nhận". Dòng chữ ký không phải nơi nhận. |
| `phu_luc` | mảng object, `enabled: false` | Mọi văn bản | Phụ lục và văn bản kèm theo. ES không tìm kiếm được trường này. Mục 9.8.4. |
| `has_tail` | boolean | Mọi văn bản | `true` khi văn bản có chữ ký hoặc Nơi nhận. Đo 16/10: 488 `true`. |
| `n_dieu` | integer | Mọi văn bản | Số Điều của văn bản chính. Không tính Điều trong phụ lục và chuỗi Điều kèm theo. |
| `grade` | keyword | Mọi văn bản | Chất lượng tách cấu trúc: `full` (440), `partial` (45), `minimal` (47). Không đo giá trị pháp lý. |

### 9.8.4. `phu_luc[]`

- Mỗi phần tử là một phụ lục có nhãn, hoặc một văn bản kèm theo không nhãn.
- Thứ tự phần tử là thứ tự trong văn bản.
- Phần tử thứ `i` (đếm từ 0) có chunk ID bắt đầu bằng `<doc>_pl<i>`.
- Phụ lục không chia Điều có một chunk `phu_luc` chứa toàn bộ phụ lục. Bảng, danh mục, biểu mẫu nằm trong chunk đó. Công cụ không tách theo dòng (C4).

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `loai` | chuỗi | `labeled` hoặc `unlabeled`. | `labeled` |
| `ky_hieu` | chuỗi \| `null` | Ký hiệu trong nhãn. `null` khi `unlabeled` hoặc nhãn không có ký hiệu. Không duy nhất trong một văn bản. | `I`; `01` |
| `tieu_de` | chuỗi | Tiêu đề đầy đủ, gồm ghi chú "(Kèm theo …)". Khác rỗng. | `PHỤ LỤC I (Kèm theo Nghị định số 31/2024/NĐ-CP …)` |
| `noi_dung` | chuỗi | Nội dung sau tiêu đề. Bảng ở dạng dòng `\| … \|`. Có thể rỗng. | `\| Mẫu số 01 \| …` |
| `has_table` | boolean | `true` khi `n_table_rows ≥ 2`. | `true` |
| `n_tables` | integer | Số bảng. | `2` |
| `n_table_rows` | integer | Số dòng bắt đầu bằng `\|`. | `10` |
| `dieu_luat` | mảng object | Các Điều của phần này. Rỗng khi phần không chia Điều. Mục 9.8.5. | `[]` |

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
| `chuong` | chuỗi | Có khi Điều nằm trong một Chương | Tên Chương. |
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

| Trường | Kiểu | Quy tắc | Đo 16/10 |
| --- | --- | --- | --- |
| `la_vbqppl` | boolean \| `null` | `true`: văn bản quy phạm pháp luật. `null` khi và chỉ khi `la_vbqppl_cach = can_kiem`. | `true` 210, `false` 316, `null` 6 |
| `la_vbqppl_cach` | keyword | Căn cứ phân loại. | `theo_loai` 189, `so_hieu_co_nam` 114, `so_hieu_khong_nam` 101, `tieu_de_ca_biet` 66, khác 62 |
| `cap_hieu_luc` | integer \| `null` | 1..15 theo Luật 87/2025/QH15. `null` khi `la_vbqppl` khác `true`. | Có giá trị: 207 |
| `cap_hieu_luc_nhan` | keyword \| `null` | Nhãn của `cap_hieu_luc`. `null` khi và chỉ khi `cap_hieu_luc = null`. | `UBND_TINH` 75, `THONG_TU` 64, `HDND_TINH` 24 |
| `cap_hieu_luc_ghi_chu` | keyword \| `null` | `hinh_thuc_cu`, `cap_huyen`, `khong_xac_dinh` hoặc `null`. `cap_huyen`, `khong_xac_dinh` đi với `cap_hieu_luc = null`. | `hinh_thuc_cu` 15, `cap_huyen` 3 |

`la_vbqppl` chỉ có ở văn bản. Chunk và quan hệ không có trường này. Muốn lọc theo `la_vbqppl` thì nối qua `doc_id` hoặc `source_id`.

### 9.8.7. Thời điểm hiệu lực

Công cụ chỉ đọc câu của chính văn bản. Công cụ bỏ câu nằm trong ngoặc kép. Chủ ngữ của câu phải đúng loại văn bản ("Thông tư này" với Thông tư).

| Trường | Kiểu | Quy tắc | Ví dụ |
| --- | --- | --- | --- |
| `ngay_hieu_luc` | date \| `null` | Ngày có hiệu lực. `null` khi cách đọc không cho ngày. Đo 16/10: 68 `null`. | `2024-03-15` |
| `ngay_hieu_luc_cach` | keyword | Mốc tính ngày, hoặc lý do không có ngày. Bảng dưới. | `ngay_ky` |
| `ngay_hieu_luc_so_ngay` | integer \| `null` | Số ngày sau mốc mà câu nêu. "sau 45 ngày kể từ ngày ký" cho `45`. "kể từ ngày ký" cho `0`. `null` khi câu ghi ngày cụ thể hoặc không có câu. | `0` |
| `ngay_hieu_luc_trich` | keyword, không index \| `null` | Câu gốc, tối đa 300 ký tự. `null` khi và chỉ khi cách đọc là `mac_dinh_ngay_ban_hanh`, `khong_tim_thay` hoặc `van_ban_hop_nhat`. | `Nghị định này có hiệu lực thi hành kể từ ngày ký ban hành.` |
| `ngay_het_hieu_luc` | date \| `null` | Ngày hết hiệu lực do chính văn bản ghi. `null` khi và chỉ khi `ngay_het_hieu_luc_cach = khong_ghi`. | `2013-12-31` (`legal-docs-v4/163439`) |
| `ngay_het_hieu_luc_cach` | keyword | `ngay_cu_the`, `het_nam`, `khong_ghi`. | `khong_ghi` (526), `ngay_cu_the` (6) |
| `ngay_het_hieu_luc_trich` | keyword, không index \| `null` | Câu gốc. `null` khi và chỉ khi `khong_ghi`. | `Quyết định này có hiệu lực kể từ ngày 01/01/2013 đến hết ngày 31/12/2013` |
| `hoi_to` | boolean | `true`: văn bản áp dụng từ một ngày trước `issuance_date`. `true` khi và chỉ khi `ngay_hoi_to` khác `null`. | `true` ở 20 văn bản (`legal-docs-v4/509618`) |
| `ngay_hoi_to` | date \| `null` | Ngày bắt đầu áp dụng hồi tố. Trước `issuance_date`. | `2019-01-01` |
| `ngay_hoi_to_trich` | keyword, không index \| `null` | Câu gốc. `null` khi và chỉ khi `hoi_to = false`. | `Quy định tại khoản 8 Điều 1 và khoản 3 Điều 2 Nghị định này được áp dụng từ ngày 01 tháng 01 năm 2019` |
| `hoi_to_vi_tri` | mảng keyword | Vị trí hồi tố trong chính văn bản. Rỗng là cả văn bản. | `["khoản 8 Điều 1", "khoản 3 Điều 2"]` |
| `hieu_luc_rieng` | mảng object | Ngày hiệu lực văn bản nêu riêng cho một số Điều, khoản, điểm của chính nó. Rỗng khi không có. Đo 16/10: 7 văn bản. | `legal-docs-v4/509618` |

| `ngay_hieu_luc_cach` | `ngay_hieu_luc` | Đo 16/10 |
| --- | --- | --- |
| `ngay_ky` | Ngày ký cộng `ngay_hieu_luc_so_ngay` | 208 |
| `ngay_cu_the` | Ngày câu ghi | 135 |
| `mac_dinh_ngay_ban_hanh` | `issuance_date`. Giá trị suy ra. Chỉ khi `la_vbqppl = false`. | 112 |
| `khong_tim_thay` | `null` | 30 |
| `van_ban_hop_nhat` | `null`. Văn bản hợp nhất không có ngày hiệu lực riêng. | 18 |
| `ngay_dang_cong_bao` | `null`. Công cụ không biết ngày đăng Công báo. | 15 |
| `ngay_thong_qua` | Ngày thông qua | 9 |
| `khong_doc_duoc` | `null`. Câu có nhưng công cụ không đọc được ngày. | 5 |

`hieu_luc_rieng[]` có các trường `vi_tri` (mảng Vị trí), `ngay_hieu_luc`, `ngay_hieu_luc_cach`, `ngay_hieu_luc_so_ngay`, `ngay_hieu_luc_trich`. Ví dụ `legal-docs-v4/509618`: câu "Quy định tại khoản 1, các điểm a và b khoản 2, các khoản 3, 4, 5 và 6 Điều 1 Nghị định này được áp dụng từ ngày 19 tháng 10 năm 2023" cho một phần tử có 7 vị trí, `ngay_hieu_luc = 2023-10-19`. Công cụ bỏ câu nêu điều khoản của văn bản khác.

**`ngay_het_hieu_luc = null` không có nghĩa là văn bản còn hiệu lực.** Văn bản khác có thể thay thế, bãi bỏ, hủy bỏ văn bản này. Thông tin đó nằm ở `legal-changed-v4`: quan hệ có `target_matched_id` là văn bản này và `vi_tri = ["toàn bộ"]`.

## 9.9. `legal-chunk-section-v4`

- Một chunk là một đơn vị nội dung để tìm kiếm.
- Chunk có `is_full = true` chứa trọn một Điều, một khoản hoặc toàn bộ nội dung.
- Đơn vị có chunk con thì chunk `is_full` lặp lại nội dung của chunk con. Khi gộp kết quả tìm kiếm, bỏ trùng theo `dieu_uid` và `khoan_uid`.
- Vector tạo từ `tieu_de + " " + noi_dung` sau khi gộp khoảng trắng. Dịch vụ embedding cắt đầu vào ở 256 token. Phần sau token 256 không có trong vector.
- Chunk `phu_luc` thường dài hơn giới hạn này. Vector chỉ đại diện cho phần đầu của phụ lục. Tìm nội dung phụ lục bằng truy vấn chữ trên `noi_dung`.

### 9.9.1. Ví dụ: `legal-chunk-section-v4/602450_d1_k1_pa`

Chunk này chứa câu tạo ra quan hệ `legal-changed-v4/602450_1`.

```json
{
  "_index": "legal-chunk-section-v4",
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
    "diem_uid": "602450_d1_k1_pa",
    "ngay_hieu_luc": "2024-03-15",
    "ngay_hieu_luc_cach": "ngay_ky",
    "ngay_hieu_luc_so_ngay": 0,
    "ngay_hieu_luc_rieng": false,
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
    "ingest_job_id": "v3:20261014T064855Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-14T09:23:31.227560+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 9.9.2. Loại chunk và ID

| `chunk_type` | Mẫu `_id` | Nội dung | Đo 16/10 | Ví dụ |
| --- | --- | --- | --- | --- |
| `dieu` | `<doc>_d<x>` | Trọn một Điều không có khoản | 1.595 | `611245_d3` |
| `dieu_full` | `<doc>_d<x>_full` | Trọn một Điều có khoản | 2.218 | `602450_d1_full` |
| `dieu_mo_dau` | `<doc>_d<x>_md` | Phần trước khoản đầu. Có khi phần này dài từ 40 ký tự. | 308 | `108505_pl0_d2_md` |
| `khoan` | `<doc>_d<x>_k<y>` | Trọn một khoản không có điểm | 7.086 | `602450_d2_k1` |
| `khoan_full` | `<doc>_d<x>_k<y>_full` | Trọn một khoản có điểm | 1.709 | `509618_d1_k5_full` |
| `khoan_mo_dau` | `<doc>_d<x>_k<y>_md` | Phần trước điểm đầu. Có khi phần này dài từ 40 ký tự. | 1.313 | `602450_d1_k1_md` |
| `diem` | `<doc>_d<x>_k<y>_p<z>` | Trọn một điểm, gồm các tiểu điểm | 6.402 | `602450_d1_k1_pa` |
| `tieu_diem` | `<doc>_d<x>_k<y>_p<z>_t<n>` | Mục gạch đầu dòng thứ `n` của một điểm. Có khi điểm có từ 2 dòng gạch đầu dòng. | 926 | `104217_d1_k2_pa_t1` |
| `phu_luc` | `<doc>_pl<i>` | Phần thứ `i` (từ 0) của `phu_luc[]`. Có khi phần đó không chia Điều. | 550 | `602450_pl0` |
| `muc` | `<doc>_m<n>` | Một đề mục của văn bản không chia Điều | 432 | `10377_m2` |
| `noi_dung` | `<doc>_nd`, `<doc>_nd<k>` | Văn bản không chia Điều, không có đề mục. `_nd`: nội dung ngắn. `_nd<k>`: đoạn thứ `k` của nội dung dài. | 240 | `119430_nd1` |
| `noi_dung_full` | `<doc>_nd_full` | Trọn nội dung dài (trên 200 âm tiết). | 46 | `35961_nd_full` |

Quy tắc ID:

1. Điều trong phụ lục có thêm `_pl<i>` sau `<doc>`. Ví dụ: `108505_pl0_d1`.
2. Điều thuộc chuỗi Điều kèm theo thứ `s` có thêm `_s<s>` trước `_d`. Ví dụ: `346282_pl1_s1_d2_k1`.
3. `_pl<i>` luôn có số. `_pl` ở cuối ID là điểm `l`. Ví dụ: `66935_d9_k2_pl`.
4. `_t<n>` sau `_p<z>` là tiểu điểm thứ `n`, đếm từ 1.
5. Hai chunk trùng ID thì chunk sau có thêm `_2`, `_3`…

### 9.9.3. Trường

"Chunk thuộc Điều" là 8 loại: `dieu`, `dieu_full`, `dieu_mo_dau`, `khoan`, `khoan_full`, `khoan_mo_dau`, `diem`, `tieu_diem`.

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `_id` | chuỗi | Mọi chunk | Bắt đầu bằng `<doc_id>_`. Khớp mẫu của `chunk_type`. |
| `doc_id` | keyword | Mọi chunk | Bằng `_id` của văn bản. |
| `chunk_type` | keyword | Mọi chunk | 12 giá trị ở mục 9.9.2. |
| `tieu_de` | text | Mọi chunk | Tên Điều với chunk thuộc Điều. Tiêu đề phụ lục với `phu_luc`. Rỗng với `muc`, `noi_dung`, `noi_dung_full` và Điều không tên. |
| `noi_dung` | text | Mọi chunk | `tieu_de + noi_dung` khác rỗng. Đo 16/10: đúng ở mọi chunk. |
| `so_van_ban_refs` | mảng keyword | Mọi chunk | Số hiệu nêu trong chunk. Chunk `_md` luôn rỗng. |
| `embedding` | dense_vector 1.024 | Mọi chunk | Vector của `tieu_de + " " + noi_dung`. |
| `document_number`, `title`, `action`, `legal_type`, `issuing_authority`, `issuance_date`, `url`, `signers` | như văn bản | Có khi văn bản có | Bằng trường cùng tên của văn bản. |
| `legal_sectors` | keyword (chuỗi) | Có khi văn bản có | Chuỗi, không phải mảng. Các phần tử nối bằng `", "`. |
| `dieu_uid` | keyword | Chunk thuộc Điều | Phần đầu `_id` đến hết `_d<x>`. ID node Điều. |
| `segment` | integer | Chunk thuộc Điều | `0`: chuỗi Điều đầu. `s ≥ 1`: chuỗi Điều kèm theo thứ `s`. `segment > 0` khi và chỉ khi `_id` có `_s<s>`. Đo 16/10: 346 chunk có `segment > 0`. |
| `so_dieu`, `ky_hieu_dieu` | integer, keyword | Chunk thuộc Điều | Phần số và ký hiệu đầy đủ. `dieu_uid` kết thúc bằng `_d<ky_hieu_dieu>`. |
| `chuong` | text | Có khi Điều nằm trong Chương | Tên Chương. |
| `muc_lon` | text | Có khi Điều nằm trong Mục của Chương | Tên Mục. |
| `khoan_uid` | keyword | `khoan`, `khoan_full`, `khoan_mo_dau`, `diem`, `tieu_diem` | Phần đầu `_id` đến hết `_k<y>`. ID node khoản. |
| `so_khoan`, `ky_hieu_khoan` | integer, keyword | Cùng `khoan_uid` | Phần số và ký hiệu đầy đủ. |
| `so_diem` | keyword | `diem`, `tieu_diem` | Ký hiệu điểm. |
| `diem_uid` | keyword | `diem`, `tieu_diem` | `_id` của chunk `diem`. ID node điểm. |
| `so_tieu_diem` | integer | `tieu_diem` | Thứ tự tiểu điểm, từ 1. |
| `is_full` | boolean | `dieu`, `dieu_full`, `khoan`, `khoan_full`, `noi_dung_full` | Chỉ có giá trị `true`. |
| `in_phu_luc` | boolean | Có khi `_id` có `_pl<i>` | Chỉ có giá trị `true`. Đo 16/10: 6.146 chunk, khớp `_id` ở mọi chunk. |
| `phu_luc_tieu_de` | text | Cùng `in_phu_luc` | 500 ký tự đầu của `phu_luc[i].tieu_de`. |
| `has_table` | boolean | Cùng `in_phu_luc` | Bằng `phu_luc[i].has_table`. |
| `so_muc` | keyword | `muc` | Ký hiệu đề mục: `2`, `II`. |
| `so_doan` | integer | `<doc>_nd<k>` | Bằng `k`. Đánh số liên tục từ 1. Văn bản có đoạn thì có đúng một `noi_dung_full`. |
| `dan_chieu` | mảng object | Có khi chunk có dẫn chiếu | Khác rỗng khi có. Mục 9.9.4. Đo 16/10: 3.660 chunk. |
| `ngay_hieu_luc` | date \| `null` | Mọi chunk | Ngày hiệu lực của chính đơn vị. Văn bản nêu ngày riêng cho đơn vị (hoặc đơn vị cha) thì dùng ngày đó. Không nêu thì bằng ngày của văn bản. |
| `ngay_hieu_luc_cach` | keyword | Mọi chunk | Cách đọc của ngày trên, cùng giá trị với văn bản (mục 9.8.7). |
| `ngay_hieu_luc_so_ngay` | integer \| `null` | Mọi chunk | Như trường cùng tên của văn bản. |
| `ngay_hieu_luc_rieng` | boolean | Mọi chunk | `true` khi ngày hiệu lực lấy từ `hieu_luc_rieng`. Đo 16/10: 90 chunk `true` (`509618_d1_k5_full`). |
| `ngay_hoi_to` | date | Có khi đơn vị nằm trong phạm vi hồi tố | Bằng `ngay_hoi_to` của văn bản. Đo 16/10: 464 chunk (`149606_d1_k2_full`). |
| 5 trường truy vết | | Mọi chunk | Mục 9.7. |

Đo 16/10: 4.170/22.825 chunk có `ngay_hieu_luc = null`. Lý do: `van_ban_hop_nhat` 3.445, `khong_tim_thay` 346, `ngay_dang_cong_bao` 335, `khong_doc_duoc` 44.

### 9.9.4. `dan_chieu[]`

| Trường | Kiểu | Quy tắc | Ví dụ (`602450_d2_full`) |
| --- | --- | --- | --- |
| `loai` | keyword | `noi_bo` (2.461 chunk), `noi_bo_ngam` (1.533), `ngoai` (1.057), `van_ban_bi_sua` (149). | `van_ban_bi_sua` |
| `vi_tri` | keyword | Là Vị trí (mục 9.5). | `Điều 5` |
| `van_ban` | keyword \| `null` | Số hiệu hoặc tên văn bản được dẫn. `null` khi `loai` là `noi_bo`, `noi_bo_ngam`. | `61/2016/NĐ-CP` |
| `target_id` | integer \| `null` | `_id` văn bản được dẫn ở `legal-docs`. Bằng `doc_id` khi `loai` là `noi_bo`, `noi_bo_ngam`. `null` khi chưa nối được. | `315420` |
| `trich` | keyword, không index | Câu chữ gốc, tối đa 200 ký tự. | `Điều 5 Nghị định này` |

Dẫn chiếu không phải quan hệ. Số hiệu văn bản trong bảng, danh mục chỉ là dẫn chiếu hoặc `so_van_ban_refs`. Ví dụ: chunk `132140_pl0` của bảng thủ tục hành chính có `03/2009/TT-BXD` trong `so_van_ban_refs`. Văn bản 132140 không sửa Thông tư đó.

## 9.10. `legal-changed-v4`

- Một quan hệ là một tác động của một đơn vị nguồn lên **một** vị trí của văn bản đích. Một vị trí là một cạnh và là một quan hệ.
- Câu nguồn nêu N vị trí thì công cụ ghi N quan hệ. Các quan hệ này có cùng `scope` (chữ của câu nguồn) và khác `vi_tri`.
- "Sửa đổi, bổ sung" trên một vị trí cho 2 quan hệ riêng: `sua-doi` và `bo-sung`. Công cụ không gộp.
- Tiêu đề, lời dẫn và từng Điều có quan hệ riêng, kể cả khi cùng văn bản đích.
- Quan hệ có trong câu chữ và là tác động trực tiếp. Công cụ không suy ra tác động lên đơn vị cha, đơn vị con hay văn bản khác.
- Công cụ có 2 chế độ dò: `rules` (mặc định) và `llm` (4 tầng). Trường `extraction` ghi đường nào đọc được quan hệ. Mục 9.10.6.
- Model LLM: `qwen-legal` đến 14/10/2026, `qwen3.6-35b` từ 15/10/2026. Quan hệ hướng dẫn (`hd_`) và hợp nhất (`hn_`) lấy bằng quy tắc, không qua model.
- Khi ghi lại một văn bản, công cụ xóa mọi quan hệ có `source_id` của văn bản đó rồi ghi lại.

### 9.10.1. Ví dụ: `legal-changed-v4/602450_1`

Bản ghi ghi ngày 14/10/2026. Bản ghi chưa có các trường mới ở mục 9.1.2. Sau khi ghi lại ở chế độ `rules`, bản ghi có thêm `"extraction": "rules"`, `"resolution_status": "validated"`, `"resolution_reason": null`.

```json
{
  "_index": "legal-changed-v4",
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
    "ingest_job_id": "v3:20261014T064855Z",
    "ingest_revision": 1,
    "ingested_at": "2026-10-14T09:23:31.227560+00:00",
    "uploaded_by": "migration-v3"
  }
}
```

### 9.10.2. Ví dụ ở chế độ `llm`

Hai quan hệ của lượt chạy thử `eval-llm-blind` (15/10/2026). Chỉ nêu các trường khác ví dụ trên.

`274123_0`: cả LLM và regex cùng thấy. Vị trí lấy từ regex. Câu trích lấy từ LLM.

```json
{
  "source_id": 274123,
  "source_path": "Điều 1",
  "action": "sua-doi",
  "target_doc": "31/2011/QĐ-UBND",
  "target_matched_id": 131565,
  "vi_tri": ["khoản 1 Điều 7"],
  "cap_quan_he": "vi_tri",
  "extraction": "llm+rules",
  "resolution_status": "validated",
  "resolution_reason": null,
  "target_section": "quyet_dinh",
  "evidence": "Sửa đổi Khoản 1 Điều 7 Quy định ban hành kèm theo Quyết định số 31/2011/QĐ-UBND …"
}
```

`intro_372651_1`: chỉ LLM thấy. Câu không nói "Điều 6" thuộc Quyết định hay Quy định kèm theo. Quan hệ chờ duyệt.

```json
{
  "source_path": "intro",
  "action": "sua-doi",
  "target_doc": "50/2014/QĐ-TTg",
  "vi_tri": ["điểm b khoản 3 Điều 6"],
  "cap_quan_he": "vi_tri",
  "unresolved": false,
  "detection_mode": "llm",
  "extraction": "llm",
  "resolution_status": "unresolved",
  "resolution_reason": "phan_kem_theo_chua_ro",
  "target_section": "khong_ro",
  "evidence": "… hướng dẫn Điểm b, Khoản 3, Điều 6, Quyết định 50/2014/QĐ-TTg"
}
```

### 9.10.3. ID

`_id` có dạng `<tiền tố><source_id>_<n>`.

| Tiền tố | `detection_mode` | Nơi có câu tác động | Đo 16/10 | Ví dụ |
| --- | --- | --- | --- | --- |
| không có | thiếu, hoặc `llm` | Điều, khoản, điểm, đề mục | 1.848 | `602450_1` |
| `hidden_` | `hidden` | Tiêu đề văn bản nguồn không nêu hành động. Câu tác động nằm trong một Điều. | 47 | `hidden_394837_0` |
| `intro_` | `intro`, hoặc `llm` | Lời dẫn | 37 | `intro_318496_0` |
| `hhl_` | `het_hieu_luc` | Câu "… hết hiệu lực kể từ ngày …" trong văn bản nguồn. Hành động `bai-bo`, vị trí `toàn bộ`. Không qua QA. | 24 | `hhl_19070_0` |
| `hd_` | `title_guidance` | Tiêu đề, lời dẫn hướng dẫn | 35 | `hd_356281_0` |
| `hn_` | `hop_nhat` | Phần đầu văn bản hợp nhất | 18 | `hn_589448_0` |

- `n` đếm từ 0 trong mỗi tiền tố của một văn bản nguồn. Công cụ đánh số sau khi tách theo vị trí. Dãy số không bị khuyết.
- `n` đổi khi chạy lại văn bản nguồn. **Không dùng `_id` quan hệ làm khóa lâu dài.**
- `detection_mode` có kiểu text. Lọc bằng `detection_mode.keyword`.
- `detection_mode = title_guidance` khi và chỉ khi `action` là `huong-dan` hoặc `quy-dinh-chi-tiet` và quan hệ lấy bằng quy tắc.
- `detection_mode = hop_nhat` khi và chỉ khi `action = hop-nhat`.
- `detection_mode = llm` khi và chỉ khi `extraction = llm`.

### 9.10.4. Văn bản nguồn

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `source_id` | integer | Luôn | Bằng `_id` của một văn bản. |
| `source_document_number`, `source_title`, `source_action`, `source_issuing_authority`, `source_issuance_date`, `source_legal_type`, `source_url` | như văn bản | Luôn | Bằng trường cùng tên (bỏ `source_`) của văn bản nguồn. |
| `source_legal_sectors` | keyword (chuỗi) | Luôn | Lĩnh vực của văn bản nguồn nối bằng `", "`. |
| `source_path` | keyword | Luôn | Đơn vị nguồn (mục 9.6). |
| `source_in_phu_luc` | boolean | Luôn | `true` khi và chỉ khi `source_path` bắt đầu bằng "Phụ lục". Đo 16/10: 1 quan hệ `true`. |
| `source_ngay_hieu_luc` | date \| `null` | Luôn | Ngày hiệu lực của đơn vị nguồn: ngày văn bản nêu riêng cho đơn vị đó (`hieu_luc_rieng`), hoặc `ngay_hieu_luc` của văn bản nguồn. |
| `source_ngay_hoi_to` | date | Có khi `hieu_luc_tac_dong = ve_truoc` | Bằng `ngay_hoi_to` của văn bản nguồn. Đo 16/10: 44 quan hệ. |

### 9.10.5. Văn bản đích

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `target_doc` | keyword | Luôn | Số hiệu đích theo câu nguồn, không có khoảng trắng. Câu nêu luật bằng tên mà dòng căn cứ không có số hiệu thì là tên luật: `Luật Thủy lợi` (`hd_356281_0`). |
| `target_matched_id` | integer \| `null` | Luôn | `_id` đích ở `legal-docs`. `null` khi chưa nối được (87/2.009). Khác `null` thì: khác `source_id`; ngày ban hành đích không sau `source_issuance_date`. |
| `target_candidates_count` | integer | Luôn | Số văn bản có cùng số hiệu, gồm dạng bỏ năm. Từ 1 khi `target_matched_id` khác `null`. |
| `target_issuance_date` | date | Có khi câu trích có ngày | Ngày ban hành đích theo câu trích. Đích đã nối thì bằng `issuance_date` của đích, trừ khi có `target_match_note`. |
| `target_issuing_authority` | keyword | Có khi câu trích nêu cơ quan | Cơ quan ban hành đích theo câu trích. |
| `target_match_note` | keyword | Có khi ngày lệch | Chỉ có `lech_ngay_trich_dan` (25 quan hệ). |
| `target_section` | keyword | Có khi `extraction` có `llm` | Phần của văn bản đích mà LLM đọc được: `quyet_dinh` (văn bản chính), `kem_theo` (văn bản ban hành kèm theo), `khong_ro`, `khong_ap_dung` (tác động lên cả văn bản). |

### 9.10.6. Tác động

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `action` | keyword | Luôn | 13 giá trị. Đo 16/10: `bo-sung` 648, `sua-doi` 571, `thay-cum-tu` 378, `bai-bo` 246, `thay-the` 64, `huong-dan` 28, `dinh-chinh` 21, `hop-nhat` 18, `ngung-hieu-luc` 12, `huy-bo` 11, `quy-dinh-chi-tiet` 7, `dinh-chi` 3, `gia-han` 2. |
| `scope` | text + keyword | Luôn | Phạm vi theo câu nguồn. Khác rỗng. Không có định dạng cố định. Có thể nêu nhiều vị trí. **Dùng `vi_tri` để nối, không dùng `scope`.** |
| `vi_tri` | mảng keyword | Luôn | Một Vị trí trong văn bản đích (mục 9.5), hoặc rỗng. Mảng không có quá một phần tử. `scope = toàn bộ` khi và chỉ khi `vi_tri = ["toàn bộ"]`. Đo 16/10: 141 rỗng, 159 `toàn bộ`. |
| `cap_quan_he` | keyword | Luôn | Mức chi tiết của quan hệ (mục 9.10.8). |
| `hieu_luc_tac_dong` | keyword | Luôn | Ý nghĩa thời gian. Tính từ `action` và hồi tố: `ve_sau` 1.865, `khong_ap_dung` 53, `ve_truoc` 44, `tu_dau` 32, `tam_ngung` 15. |
| `unresolved` | boolean | Luôn | Trường của QA phạm vi. `true`: phạm vi chưa được xác nhận. `scope = chưa xác định` thì `true`. **Không dùng trường này để quyết định cạnh.** Dùng `resolution_status`. |
| `doi_tuong` | keyword | Có khi câu nguồn nêu phần bị tác động bằng tên, không có số | Tên phần bị tác động. Thường đi với `vi_tri` rỗng. Câu nêu cả phụ lục chứa phần đó ("mẫu Bản cáo bạch tại Phụ lục số 03") thì `vi_tri` là phụ lục đó (`192512_0`). `dinh-chinh` có thể có `phần căn cứ`, `phần Nơi nhận`. |
| `doi_tuong_loai` | keyword | Luôn (từ 20/10/2026) | Loại đối tượng bị tác động (quy ước Q12). `van_ban`: văn bản đích hoặc một phần của nó. `thu_tuc_hanh_chinh`: một hoặc nhiều thủ tục hành chính do văn bản đích công bố; `doi_tuong` là tên thủ tục. Công cụ gán `thu_tuc_hanh_chinh` khi phần bị tác động có tên là thủ tục ("107 thủ tục hành chính", "Thủ tục thẩm định …"), hoặc khi quan hệ là dòng của danh mục thủ tục (tên phụ lục hoặc đề mục nêu thủ tục). Lượt `q11q12-check`: `587301_0` (`Phụ lục 1 Mục B STT 1`, `bai-bo` lên `3443/QĐ-UBND`). |
| `ma_thu_tuc` | keyword | Có khi `doi_tuong_loai = thu_tuc_hanh_chinh` và dòng có mã | Mã thủ tục quốc gia như dòng ghi, dạng `<d>.<6 chữ số>`. Ví dụ `2.000164` (`587301`). |
| `kem_theo` | boolean | Cùng `doi_tuong` | `true`: phần đó ban hành kèm theo văn bản đích (21 quan hệ). `false`: 11 quan hệ. |
| `cum_tu` | mảng object | Có khi `action = thay-cum-tu` | Khác rỗng. |
| `cum_tu[].cu`, `cum_tu[].moi` | keyword | Cùng `cum_tu` | Cụm từ cũ, cụm từ mới. Khác rỗng. |
| `cum_tu[].vi_tri` | mảng keyword | Cùng `cum_tu` | Bằng `vi_tri` của quan hệ. Quan hệ chỉ giữ các cặp áp dụng tại vị trí của nó (`488371_49`). |
| `dinh_chi_tu_ngay` | date \| `null` | Có khi `action` là `dinh-chi`, `ngung-hieu-luc` | Ngày bắt đầu. Câu không ghi ngày thì bằng `source_ngay_hieu_luc`. |
| `dinh_chi_den_ngay` | date \| `null` | Như trên | Ngày kết thúc. |
| `dinh_chi_den_khi` | keyword \| `null` | Như trên | Điều kiện kết thúc, ghi bằng lời. Câu "… cho đến khi có kết luận thanh tra" cho `có kết luận thanh tra`. |
| `gia_han_den_ngay` | date \| `null` | Có khi `action = gia-han` | Ngày hết hiệu lực mới. "đến hết tháng 12 năm 2016" → `2016-12-31` (`318496_0`). |
| `gia_han_den_khi` | keyword \| `null` | Như trên | Điều kiện ("có văn bản thay thế") hoặc thời hạn thêm ("thêm 06 tháng"). |
| `detection_mode` | text + keyword | Có khi `_id` có tiền tố, hoặc `extraction = llm` | Mục 9.10.3. |

### 9.10.7. Trạng thái cạnh và đường dò

Ba trường này có ở mọi quan hệ từ ngày 15/10/2026. Bản ghi v4 hiện có chưa có (mục 9.1.2).

| Trường | Kiểu | Có | Quy tắc |
| --- | --- | --- | --- |
| `extraction` | keyword | Luôn | `rules`: chỉ regex thấy, QA giữ. `llm`: chỉ LLM thấy, qua tầng kiểm. `llm+rules`: cả hai cùng thấy. Chế độ `rules` chỉ có `rules`. |
| `resolution_status` | keyword | Luôn | `validated`: đủ căn cứ, bên Graph dựng cạnh. `unresolved`: hành động có thật nhưng chưa đủ căn cứ, chờ duyệt, không dựng cạnh. |
| `resolution_reason` | keyword \| `null` | Luôn | `null` khi và chỉ khi `validated`. Giá trị ở bảng dưới. |
| `evidence` | text | Có khi `extraction` có `llm` | Câu trích nguyên văn thực hiện hành động. Tầng kiểm đã xác nhận câu này có trong văn bản nguồn. |

| `resolution_reason` | Nghĩa |
| --- | --- |
| `vi_tri_chua_xac_dinh` | Câu nêu tác động một phần nhưng không nêu vị trí. Mọi quan hệ có `cap_quan_he = chua_xac_dinh` có lý do này hoặc một lý do cụ thể hơn. |
| `vi_tri_ngoai_dinh_dang` | Vị trí không đổi được sang định dạng mục 9.5. Code không sinh lý do này từ 19/10/2026: vị trí ngoài định dạng chuyển sang `doi_tuong`. |
| `phan_kem_theo_chua_ro` | "khoản 7 Điều 3" có thể thuộc Quyết định hoặc Quy định kèm theo. Câu không nói rõ. |
| `van_ban_dich_khong_co_trong_nguon` | Văn bản đích không có trong đoạn nguồn LLM đọc. |
| `vi_tri_khong_co_trong_nguon` | Số của vị trí không có trong đoạn nguồn. |
| `khong_xac_dinh_van_ban_dich` | LLM không nêu được văn bản đích. |

Quy tắc:

1. `cap_quan_he = chua_xac_dinh` thì `resolution_status = unresolved`, ở cả hai chế độ.
2. Chế độ `rules`: các quan hệ khác là `validated`.
3. Chế độ `llm`: tầng phân giải và tầng kiểm quyết định (mục 8.2.2). Quan hệ `llm+rules` là `validated`.
4. `resolution_status` và `unresolved` là hai trường khác nhau. Một quan hệ có thể có `unresolved = false` và `resolution_status = unresolved` (`intro_372651_1`).

Đo trên lượt chạy thử `eval-llm-blind` (290 văn bản, 759 quan hệ, 15/10/2026):

| Chỉ số | Giá trị |
| --- | --- |
| `extraction` | `llm+rules` 412, `llm` 264, `rules` 83 |
| `resolution_status` | `validated` 688, `unresolved` 71. Sau khi sửa quy tắc 1 ngày 16/10: thêm 29 quan hệ `unresolved`. |
| `resolution_reason` | `vi_tri_chua_xac_dinh` 64, `vi_tri_khong_co_trong_nguon` 4, `phan_kem_theo_chua_ro` 3 |
| `target_section` | `quyet_dinh` 401, `khong_ro` 108, `kem_theo` 91, `khong_ap_dung` 76 |

### 9.10.8. Cấp quan hệ

Công cụ xét các dòng từ trên xuống. Công cụ chọn dòng đầu tiên có điều kiện đúng.

| # | `cap_quan_he` | Điều kiện | `vi_tri` | Đo 16/10 |
| --- | --- | --- | --- | --- |
| 1 | `vi_tri` | `vi_tri` có một Vị trí khác `toàn bộ`. Câu nằm ở đâu cũng vậy: Điều, lời dẫn, tiêu đề. | Một phần tử | 1.709 |
| 2 | `van_ban_kem_theo` | Có `doi_tuong` và `kem_theo = true`. | Rỗng | 19 |
| 3 | `noi_dung` | Có `doi_tuong` và `kem_theo = false`. | Rỗng | 11 |
| 4 | `van_ban` | `vi_tri = ["toàn bộ"]`; hoặc `detection_mode` là `intro`, `title_guidance`, `het_hieu_luc`, `hop_nhat`; hoặc `source_path` là `intro`, `Tiêu đề`, `Lời dẫn`, `Phần đầu`; hoặc `scope` là `một số điều`, `một số cụm từ`. | `["toàn bộ"]` hoặc rỗng | 197 |
| 5 | `chua_xac_dinh` | Không đúng dòng nào ở trên. Công cụ ghi thêm vào `work/<run>/review.jsonl`. | Rỗng | 73 |

### 9.10.9. QA phạm vi

Các trường này chỉ có ở quan hệ đi qua QA của regex (`extraction` là `rules` hoặc `llm+rules`).

| Trường | Kiểu | Có | Quy tắc | Đo 16/10 |
| --- | --- | --- | --- | --- |
| `scope_resolution_method` | keyword | Có khi quy tắc xác nhận phạm vi | `explicit_declaration` hoặc `liet_ke_vi_tri`. Khi có, `scope_grounding_correct = true`. | 1.160 và 393 |
| `scope_grounding_checked` | boolean | Có khi đã kiểm phạm vi | Chỉ có giá trị `true`. | 1.758 |
| `scope_grounding_correct` | boolean | Cùng `scope_grounding_checked` | `true`: dẫn chứng hỗ trợ phạm vi. `false` thì `unresolved = true`. | `false` 34 |
| `scope_grounding_suggestion` | text + keyword | Có khi model đề xuất mà công cụ không áp dụng | Phạm vi do model LLM đề xuất. Chỉ để tham khảo. | 141 |
| `llm_refined` | boolean | Có khi công cụ áp dụng đề xuất | Chỉ có giá trị `true`. Khi có, `scope_grounding_correct = true`, `unresolved = false`. | 38 |
| `llm_hallucination_rejected` | boolean | Có khi QA phạm vi không đạt | `true`: dẫn chứng của model không có trong văn bản nguồn. `false`: dẫn chứng có trong nguồn, nhưng model trả `correct = false`. | `true` 28, `false` 6 |

## 9.11. Cách nối cho đồ thị

ES chỉ lưu tác động trực tiếp. Bên Graph tính trạng thái hiệu lực từ các cạnh.

### 9.11.1. Node

| Node | ID | Lấy từ |
| --- | --- | --- |
| Văn bản | `<doc>` | `legal-docs-v4/<doc>` |
| Chương, Mục của Luật | — | Trường `chuong`, `muc_lon` trên chunk. Không có chunk riêng. |
| Điều | `dieu_uid` | Chunk `dieu`, `dieu_full`, `dieu_mo_dau` |
| Khoản | `khoan_uid` | Chunk `khoan`, `khoan_full`, `khoan_mo_dau` |
| Điểm | `diem_uid` | Chunk `diem` |
| Tiểu điểm | `_id` của chunk `tieu_diem` | Chunk `tieu_diem` |
| Phụ lục | `<doc>_pl<i>` | Chunk `phu_luc`, hoặc Điều trong phụ lục |
| Đề mục, nội dung | `_id` của chunk `muc`, `noi_dung`, `noi_dung_full` | Chunk tương ứng |

Dựng một node cho mỗi `dieu_uid`, `khoan_uid` và `diem_uid`. Không dựng một node cho mỗi chunk: chunk `_full` và `_md` cùng thuộc một node.

### 9.11.2. Từ vị trí sang node

| Vị trí | ID node | Ví dụ |
| --- | --- | --- |
| `Điều <x>` | `<doc>_d<x>` | `Điều 47` (`314836_10`) → `206663_d47` (chunk `206663_d47_full`) |
| `khoản <y> Điều <x>` | `<doc>_d<x>_k<y>` | `khoản 6 Điều 3` (`611245_14`) → `206663_d3_k6` |
| `điểm <z> khoản <y> Điều <x>` | `<doc>_d<x>_k<y>_p<z>` | `điểm a khoản 1 Điều 43` (`288269_32`) → `206663_d43_k1_pa` |
| `tiểu điểm <n> điểm <z> khoản <y> Điều <x>` | `<doc>_d<x>_k<y>_p<z>_t<n>`. Văn bản đích không có tiểu điểm đó thì dùng node điểm. | `tiểu điểm 3 điểm b khoản 3 Điều 17` (`378946_0`) → `297312_d17_k3_pb_t3`. Văn bản 297312 chưa có trong v4. |
| `tên Điều <x>` | `<doc>_d<x>`. Cạnh tác động lên tên, không lên nội dung. | `tên Điều 42` → `206663_d42` |
| `Chương <c>`, `Mục <n>`, `tên Chương <c>`, `tên Mục <n>` (của Luật) | Chưa chốt. Chương và Mục không có node riêng (mục 9.11.1). | `tên Chương IV` (`288269_27`) |
| `Phụ lục <ký hiệu>` | `<doc>_pl<i>` với `phu_luc[i].ky_hieu` bằng ký hiệu | `legal-docs-v4/602450`: `phu_luc[1].ky_hieu = II` → `602450_pl1` |
| `Mục <x> Phụ lục <ký hiệu>`, `Mục <x> Phần <y> Phụ lục` | Node phụ lục. Mục, Phần của phụ lục không có node riêng. | `Mục D.2 Phụ lục I` → `<doc>_pl0` khi `phu_luc[0].ky_hieu = I` |
| `toàn bộ` | Node văn bản | `hn_589448_0` → `legal-docs/457744` |

- Vị trí thuộc văn bản kèm theo thì ID có thêm `_pl<i>`. Ví dụ dạng ID: `366183_pl0_d3_k7_pb`. Dữ liệu chỉ đánh dấu khi câu nguồn nói rõ (`kem_theo`, `target_section = kem_theo`). Công cụ không suy ra (C2).
- Node đích chỉ có chunk khi văn bản đích đã chuyển sang v4. Đo 16/10: 339/1.922 đích đã nối có trong v4.

### 9.11.3. Cạnh

1. Mỗi quan hệ có `resolution_status = validated` cho một cạnh chi tiết. Quan hệ `unresolved` không có cạnh.
2. Bỏ qua quan hệ có vị trí ngoài định dạng (mục 9.5).
3. Phía nguồn: node theo `source_path`. `source_path` là `intro`, `Tiêu đề`, `Lời dẫn`, `Phần đầu` thì phía nguồn là node văn bản.
4. Phía đích: node theo `vi_tri`. `vi_tri = ["toàn bộ"]` hoặc rỗng ở quan hệ cấp văn bản thì phía đích là node văn bản.
5. Cạnh tổng hợp nối văn bản nguồn với văn bản đích. Bên Graph dựng cạnh này từ `source_id` và `target_matched_id`. Quan hệ có `target_matched_id = null` không có cạnh tổng hợp.

### 9.11.4. Không lan tác động

| Ca | ES lưu | ES không lưu |
| --- | --- | --- |
| Sửa đổi, thay thế, bãi bỏ cả Điều | Một quan hệ vào node Điều | Quan hệ vào khoản, điểm của Điều đó |
| Bãi bỏ một khoản | Một quan hệ vào node khoản | Trạng thái của Điều chứa khoản |
| Bổ sung đơn vị mới (Điều 47a, khoản 2a) | Một quan hệ có vị trí của đơn vị mới | Node mới. Bên Graph tạo node nếu cần. |
| Chuỗi sửa đổi: câu nêu "khoản 3 Điều 17 Thông tư A, được sửa đổi tại Thông tư B" | Một quan hệ vào Thông tư A | Quan hệ vào Thông tư B (ghi chú lịch sử) |
| Văn bản hết hiệu lực | Quan hệ vào văn bản đó | Hết hiệu lực của văn bản quy định chi tiết nó |
| Thay cụm từ "trong toàn bộ Thông tư" | Một quan hệ có `vi_tri = ["toàn bộ"]` | Danh sách khoản có cụm từ |
| Công bố thủ tục hành chính | Không có quan hệ | Quan hệ tới văn bản nêu trong bảng thủ tục (`132140`) |
| Dòng danh mục thủ tục bị sửa đổi, thay thế, bãi bỏ | Mỗi dòng một quan hệ tới quyết định đã công bố thủ tục, `doi_tuong_loai = thu_tuc_hanh_chinh`, `doi_tuong` là tên thủ tục | Quan hệ "sửa đổi, bãi bỏ" lên nội dung của quyết định đó. Cạnh này nói về thủ tục, không về Điều, khoản của quyết định. |

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

Bên đọc dùng bảng này để kiểm dữ liệu. Cột cuối là kết quả đo trên v4 ngày 16/10/2026.

| # | Bất biến | Kết quả |
| --- | --- | --- |
| 1 | Mọi chunk có `doc_id` trong `legal-docs-v4`. Mọi văn bản có ít nhất một chunk. | Đạt |
| 2 | `tieu_de + noi_dung` của chunk khác rỗng. | Đạt |
| 3 | `_id` chunk bắt đầu bằng `dieu_uid`. `in_phu_luc` khi và chỉ khi `_id` có `_pl<i>`. | Đạt |
| 4 | `vi_tri` có tối đa một phần tử. | Đạt |
| 5 | `scope = toàn bộ` khi và chỉ khi `vi_tri = ["toàn bộ"]`. `scope = chưa xác định` thì `unresolved = true`. | Đạt |
| 6 | `source_in_phu_luc` khi và chỉ khi `source_path` bắt đầu bằng "Phụ lục". | Đạt |
| 7 | `target_matched_id` khác `source_id`. Có `target_matched_id` thì `target_candidates_count ≥ 1`. | Đạt |
| 8 | `la_vbqppl = null` khi và chỉ khi `la_vbqppl_cach = can_kiem`. | Đạt (6 và 6) |
| 9 | `ngay_het_hieu_luc = null` khi và chỉ khi `khong_ghi`. `hoi_to` khi và chỉ khi có `ngay_hoi_to`. | Đạt |
| 10 | Vị trí đúng định dạng mục 9.5. | Không đạt: 14 quan hệ (đo `python -m eval.check_contract v4` ngày 19/10: 18 vị trí). Code 19/10 chuyển vị trí sai dạng sang `doi_tuong`. Hết sau khi ghi lại. |
| 11 | `noi_nhan` không có dòng chữ ký. | Không đạt: 338/532 văn bản (đo 19/10). Code 19/10 đã sửa. Hết sau khi ghi lại. |
| 12 | Mọi quan hệ có `resolution_status` và `extraction`. `cap_quan_he = chua_xac_dinh` thì `unresolved`. | Chưa có trường. Có sau khi ghi lại. |

## 9.13. Giới hạn đã biết

| Giới hạn | Ảnh hưởng | Chi tiết |
| --- | --- | --- |
| Phụ lục không chia Điều là một chunk. | Vector chỉ đại diện phần đầu phụ lục. Đo trên mẫu 10.000 văn bản nguồn (15/10): 42% tổng chữ nằm trong các chunk này. | C4 |
| Dòng bảng chỉ được đọc ở chế độ `llm`. Chế độ `rules` không đọc. | Chế độ `rules` thiếu quan hệ từ danh mục trong phụ lục. | Mục 9.6 |
| Thủ tục hành chính không có node. | Quan hệ lên thủ tục trỏ vào văn bản đã công bố thủ tục, tên thủ tục ở `doi_tuong`, `doi_tuong_loai = thu_tuc_hanh_chinh`. Bên Graph dùng trường này để tách cạnh lên thủ tục. | Mục 9.6, 9.10.6, 9.11.4 |
| Quan hệ từ lời dẫn khác nhau giữa hai chế độ. Chế độ `rules` cho `van_ban` và `validated`. Chế độ `llm` cho `unresolved` khi câu không nêu vị trí. | 24 quan hệ của lượt chạy thử `eval-llm-blind`. | Chờ chốt |
| `la_vbqppl` chỉ có ở văn bản. | Lọc chunk, quan hệ phải nối qua văn bản. | Mục 9.8.6 |
| Nhãn chuẩn do LLM gán, chưa có nhãn của người. | Chỉ số quan hệ và metadata có thể lệch. | [08, mục 8.5](08-quan-he-4-tang-va-danh-gia.md) |
| Kết quả LLM đổi giữa các lượt chạy, kể cả khi temperature bằng 0. | Cùng code, hai lượt lệch 2–4 điểm ở mức quan hệ. Một dòng bảng có thể có quan hệ ở lượt này, không có ở lượt khác. | [08, mục 8.8.4](08-quan-he-4-tang-va-danh-gia.md#884-chốt-luồng-20102026) |
| Công văn điều chỉnh phương án đơn giản hóa thủ tục (`124929`) và câu đề nghị, giao nhiệm vụ | LLM chọn sai văn bản đích: lấy văn bản nêu trong nội dung thay cho Nghị quyết chứa phương án. LLM nhận câu đề nghị, giao nhiệm vụ là hành động. | Đang sửa (P1): cải thiện phân loại, không viết quy tắc riêng cho một văn bản |
| Văn bản có toàn văn tiếng Anh (`39074`: bản dịch của Nghị định 12/CP lưu làm toàn văn) | Công cụ bỏ qua, không ghi văn bản, chunk, quan hệ. Nhật ký ghi `skipped = tieng_anh`. Văn bản đã có ở index đích từ lượt cũ thì vẫn còn. | Đã làm 20/10/2026 |

Các giới hạn khác và quyết định đã chốt ở [07-gioi-han-va-can-chot.md](07-gioi-han-va-can-chot.md).
