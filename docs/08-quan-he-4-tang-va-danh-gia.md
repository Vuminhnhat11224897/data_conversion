# 8. Dò quan hệ 4 tầng và cách đánh giá

Tài liệu này mô tả chế độ `llm` (luồng 4 tầng) và bộ đánh giá `eval/`.

- 15/10/2026: thêm chế độ `llm`.
- 20/10/2026: chốt luồng. Chế độ `llm` là mặc định (mục 8.8.4). Kết quả độc lập ở mục 8.8.3.
- So sánh với v2 và v3 ở [05](05-phien-ban-v2-v3-v4.md).

## 8.1. Vì sao đổi

| Vấn đề của chế độ `rules` | Bằng chứng |
| --- | --- |
| Regex chỉ bắt các cách viết đã gặp. Mỗi bộ văn bản mới mang cách viết mới. | Vòng 5 đạt 93,7% / 90,0% trên 300 văn bản đã dùng để sửa lỗi. 29 văn bản mới chỉ đạt 66,1% / 53,6%. |
| Regex không phân biệt câu thực hiện với câu nhắc tới. | Tên danh mục ("Danh mục văn bản cần … bãi bỏ"), ghi chú lịch sử, câu dẫn chiếu đều có chữ "bãi bỏ", "hướng dẫn". |
| LLM chỉ kiểm. LLM không thêm được tác động regex bỏ sót. | Độ phủ trên bộ Dev: 56% tính theo văn bản (đo 15/10/2026). |

## 8.2. Bốn tầng

Mỗi tầng chịu một loại lỗi. Mỗi tầng kiểm thử riêng được.

| Tầng | Module | Làm gì | Loại lỗi tầng này chịu |
| --- | --- | --- | --- |
| 1. Cấu trúc | `structure.py`, `structure_ai.py` | Quy tắc tách Điều, khoản, điểm, mục, phụ lục. Ca quy tắc không chắc thì hỏi LLM bằng số dòng. | Tách sai, gộp sai |
| 2. Trích ngữ nghĩa | `extract.py` | LLM đọc từng đơn vị kèm ngữ cảnh. LLM trả JSON trung gian có câu trích nguyên văn. LLM không tạo ID. | Nhầm câu nhắc tới thành hành động; sai loại hành động |
| 3. Phân giải | `resolver.py` | Code đổi văn bản đích và vị trí nguyên văn sang định dạng hợp đồng (mục 4.3). Code không đoán. | Sai văn bản đích, sai vị trí, sai phần kèm theo |
| 4. Kiểm | `validate.py` | Quy tắc kiểm câu trích, văn bản đích và vị trí có trong nguồn. | Bịa, câu trong ngoặc kép, tên danh mục |

Regex của chế độ `rules` chạy song song để đối chiếu. Công cụ gộp hai đường theo bộ (đơn vị nguồn, hành động, văn bản đích):

| Ca | Kết quả | `extraction` |
| --- | --- | --- |
| Cả LLM và regex (đã qua QA) cùng thấy | Lấy câu trích của LLM. Lấy vị trí của regex khi regex nêu vị trí cụ thể (Dev 15/10/2026: vị trí regex đúng 97%, LLM 75%). Regex chỉ có `toàn bộ` hoặc không có vị trí: lấy cách đọc cụ thể nhất của LLM. | `llm+rules` |
| Chỉ regex thấy, QA giữ | Lấy quan hệ của regex | `rules` |
| Chỉ LLM thấy, qua tầng 4 | Lấy quan hệ của LLM | `llm` |

### 8.2.1. JSON trung gian của tầng 2

Mỗi trường có `description` trong schema (`extract.SCHEMA`). Code đưa các mô tả này vào prompt (`llm.describe`). Prompt ở `vbpl_v3/prompts/extract_quan_he.txt`.

| Trường | Nghĩa |
| --- | --- |
| `chu_the` | Ai làm hành động (từ 20/10/2026). `van_ban_nay`: chính văn bản này quyết định. `de_nghi`: đề nghị của cơ quan khác mà câu không quyết. `giao_nhiem_vu`: giao cơ quan khác làm sau. `ke_lai`: kể lại. `trich_dan`: ngoặc kép, căn cứ, dẫn chiếu. Tầng 4 chỉ giữ `van_ban_nay`. |
| `van_ban_chua_noi_dung` | Số hiệu văn bản chứa nội dung bị sửa, bỏ, thay (từ 20/10/2026). Văn bản chỉ được nhắc trong nội dung đó không tính. Tầng 3 lấy số hiệu này làm đích khi nó khác `target_document` và có trong nguồn. |
| `action` | Loại hành động (13 giá trị, mục 6). |
| `performed` | `true`: chính đơn vị thực hiện. `false`: chỉ nhắc tới. Công cụ bỏ hàng `false`. |
| `target_document` | Số hiệu văn bản đích như nguồn viết, hoặc `Luật <tên>`. |
| `target_from` | Nơi đọc được văn bản đích: đơn vị, câu dẫn, tên Điều, tên Chương, tên văn bản. |
| `target_section` | `quyet_dinh`, `kem_theo`, `khong_ro`, `khong_ap_dung`. |
| `target_text` | Vị trí nguyên văn, mỗi vị trí một phần tử. |
| `target_part` | Tên phần khi câu chỉ nêu bằng tên. |
| `evidence` | Câu trích nguyên văn. |

### 8.2.2. Trạng thái của quan hệ

| `resolution_status` | Nghĩa | Bên Graph |
| --- | --- | --- |
| `validated` | Đủ căn cứ | Dựng cạnh |
| `unresolved` | Có hành động thật nhưng chưa đủ căn cứ. `resolution_reason` nêu lý do. | Không dựng cạnh. Chờ duyệt. |

| `resolution_reason` | Nghĩa |
| --- | --- |
| `vi_tri_chua_xac_dinh` | Câu nêu tác động một phần nhưng không nêu vị trí. |
| `phan_kem_theo_chua_ro` | "khoản 7 Điều 3" có thể thuộc Quyết định hoặc Quy định kèm theo. Câu không nói rõ. |
| `van_ban_dich_khong_co_trong_nguon` | Văn bản đích không có trong đoạn nguồn LLM đọc. |
| `vi_tri_khong_co_trong_nguon` | Số của vị trí không có trong đoạn nguồn. |
| `khong_xac_dinh_van_ban_dich` | LLM không nêu được văn bản đích có số hiệu hoặc tên luật. |

Từ 19/10/2026, vị trí ngoài định dạng không còn là lý do chờ duyệt. Công cụ chuyển vị trí đó sang `doi_tuong` (lý do cũ `vi_tri_ngoai_dinh_dang`).

Tầng 4 loại hẳn (không ghi) các hàng ở bảng dưới. Lý do ở `work/<run>/extract/<id>/rejected.json`.

| Lý do loại | Nghĩa |
| --- | --- |
| `chu_the_de_nghi`, `chu_the_giao_nhiem_vu`, `chu_the_ke_lai`, `chu_the_trich_dan` | LLM nêu chủ thể không phải văn bản này (từ 20/10/2026). |
| `trich_dan_khong_co_trong_nguon` | Câu trích không có nguyên văn trong nguồn. Gồm câu trích lấy từ tên lưu ở nguồn (quy ước Q11). |
| `trong_noi_dung_moi` | Câu trích nằm trong ngoặc kép (nội dung mới). |
| `dong_bang_ke_hoach` | Dòng của danh sách việc cần làm (từ 21/10/2026). |
| `ten_danh_muc` | Câu trích là tên danh mục, bảng ("Danh mục văn bản cần … bãi bỏ"). |
| `ghi_chu_lich_su` | Câu trích chỉ là ghi chú "đã được sửa đổi tại …". |
| `cong_bo_danh_muc` | Văn bản chỉ công bố danh mục (thủ tục, văn bản hết hiệu lực). Câu không nêu văn bản đích bị tác động. |
| `trich_dan_khong_co_hanh_dong` | Câu trích không có động từ của hành động. |
| `khong_co_van_ban_dich` | Không có văn bản đích ("các quy định trái với …"). |
| `chinh_van_ban_nguon` | Đích là chính văn bản nguồn. |
| `vuot_tham_quyen` | Văn bản không phải Luật, Pháp lệnh, Nghị quyết của Quốc hội hoặc Ủy ban Thường vụ Quốc hội "sửa đổi, bãi bỏ, thay thế" một Luật, Pháp lệnh. Câu đó là đề xuất hoặc nhiệm vụ (từ 20/10/2026). |
| `dan_chieu_khong_phai_huong_dan` | Câu "theo quy định tại …" là dẫn chiếu, không phải hướng dẫn. |
| `dong_bang_khong_neu_van_ban` | Dòng bảng không nêu văn bản đích. |
| `dong_bang_khac_co_quan` | Dòng danh mục thủ tục nêu quyết định của cơ quan khác. |
| `dong_bang_khong_co_hanh_dong` | Dòng bảng, đề mục và tên phụ lục không nêu hành động. |

Văn bản hợp nhất không qua tầng 2. Văn bản hợp nhất chép lại câu của văn bản gốc. Quan hệ duy nhất của nó là `hop-nhat`, lấy bằng quy tắc.

## 8.3. Tầng cấu trúc: quy tắc và LLM

| Ca | Cách xử lý |
| --- | --- |
| Số chú thích dính nhãn ở văn bản hợp nhất: `4.[2]`, `4.8`, `46.`, `d4)`, `đ)5`, `Điều 32.` | Quy tắc. Dạng có ngoặc vuông: bỏ ở mọi văn bản. Dạng không ngoặc: chỉ ở văn bản hợp nhất, và chỉ khi khớp số đang chờ (sau khoản 3 thì chờ khoản 4). |
| Phần mở đầu của công văn, kế hoạch gộp vào Mục 1 | Quy tắc. Các dòng trước tiêu đề mục đầu tiên là phần đầu và lời dẫn. |
| `Điều thứ 1`, `Điêu 3`, `2 . `, `I-` | Quy tắc. |
| Câu "Nghị quyết này đã được … thông qua", khối "XÁC THỰC VĂN BẢN HỢP NHẤT" | Quy tắc. Các dòng này mở đầu phần cuối, không thuộc Điều nào. |
| Văn bản không chia Điều, bố cục nhiều cấp (I/II với 1/2, phần A/B), hoặc một mục chiếm phần lớn văn bản | LLM lập dàn ý (`prompts/dan_y_van_ban.txt`). LLM chỉ trả số dòng, nhãn và cấp. Code kiểm nhãn có ở đầu dòng rồi mới cắt chữ. Không đạt thì giữ quy tắc. |

## 8.4. Model và tải

| Mục | Giá trị |
| --- | --- |
| Server | `http://100.91.202.88:8012/v1`, model `qwen3.6-35b`, không thinking |
| Lời gọi cùng lúc | 3 ban ngày, 10 từ 22h đến 6h (`LLM_CONCURRENCY_*`). Giới hạn chung cho mọi lời gọi trong một tiến trình. |
| Trần token | 4.000. Câu trả lời quá dài thì công cụ chia đôi đơn vị và hỏi lại. |
| Timeout | Kết nối 5 s. Đọc 30 s, dài hơn khi câu trả lời có thể dài. |
| Server từ chối kết nối | Chờ 10, 20, 40, 60, 90 s rồi thử lại. |
| Cache | Mỗi câu trả lời lưu kèm mã băm của prompt đầy đủ, gồm mô tả trường. Sửa prompt hoặc mô tả thì công cụ hỏi lại. |

## 8.5. Bộ đánh giá

| Bộ | Số văn bản | Dùng để | File |
| --- | --- | --- | --- |
| Regression | 532 | Kiểm không làm hỏng cái cũ. Đã dùng để sửa lỗi. | `eval/sets/regression.txt` |
| Dev | 150 | Xem lỗi và sửa | `eval/sets/dev.txt` |
| Blind | 250 | Chỉ chấm. Không xem lỗi để sửa. | `eval/sets/blind.txt` |
| Challenge | 40 | Ca khó: Quyết định và Quy định kèm theo, tên danh mục có từ hành động, thủ tục hành chính, ghi chú lịch sử, văn bản cũ | `eval/sets/challenge.txt` |
| `review50-20261019` | 50 | Hồi quy cho các lỗi đã rà ngày 19/10 | `eval/sets/review50-20261019.txt` |
| `holdout-20261019` | 122 | Hold-out 1 (văn bản đến 30.000 ký tự). Đã dùng một lần. | `eval/sets/holdout-20261019.txt` |
| `holdout-20261020` | 158 | Hold-out 2 (có văn bản dài). Từ 20/10 là bộ phân tích; nhãn phân xử ở `eval/gold/holdout-20261020-adj`. | `eval/sets/holdout-20261020.txt` |
| `holdout-20261021` | 158 | Hold-out 3. Kết quả độc lập của luồng chốt (mục 8.8.3). | `eval/sets/holdout-20261021.txt` |

- `eval/build_sets.py` chọn văn bản theo nhóm: 200 ngẫu nhiên, 200 theo loại tác động.
- Một nhóm (cơ quan ban hành + mẫu tên) chỉ nằm ở một bộ. Nhóm đã có trong Regression không vào bộ khác.
- Nhãn chuẩn do LLM (Claude) gán. Người gán không thấy kết quả của công cụ. Tiêu chí: `eval/rubric-gold.md` (quan hệ), `eval/rubric-metadata.md` (metadata). Gói đơn vị: `eval/packets.py`.
- `eval/build_holdout.py` tạo hold-out: văn bản mới, nhóm chưa dùng, mỗi nhóm một văn bản. Bên dữ liệu khóa nhãn bằng hash (`eval/gold/<bộ>.lock.json`) trước khi chạy công cụ.

### 8.5.1. Chỉ số

Chạy `python -m eval.score <bộ> <lượt>` (quan hệ) và `python -m eval.score_meta <bộ> <lượt>` (metadata). Lượt phải chạy `convert --dry-run`.

| Chỉ số | Đo gì |
| --- | --- |
| `document_precision`, `document_recall` | Đúng văn bản đích, bất kể đơn vị nguồn, hành động, vị trí (từ 19/10/2026). |
| `relation_precision`, `relation_recall` | Đúng đơn vị nguồn, hành động, văn bản đích. Chỉ tính quan hệ `validated`. Từ 20/10/2026, đơn vị nguồn cha hoặc con cũng tính là khớp. |
| `macro_precision`, `macro_recall` | Như trên, mỗi văn bản tính ngang nhau. Một văn bản 99 quan hệ không quyết định điểm. |
| `position_accuracy` | Trong các quan hệ khớp, vị trí đúng. |
| `e2e_precision`, `e2e_recall` | Đúng cả vị trí, mỗi vị trí một mục. |
| `unresolved_rate`, `unresolved_real` | Tỉ lệ quan hệ chờ duyệt; trong đó tỉ lệ là quan hệ thật. |
| `errors` | Số lỗi theo tầng: `structural`, `semantic`, `reference`, `scope`, `classification`, `graph_mapping`. |

### 8.5.2. Kết quả trên bộ Dev (đo 15/10/2026)

| Chế độ | P | R | P theo văn bản | R theo văn bản | Vị trí | Unresolved (thật) |
| --- | --- | --- | --- | --- | --- | --- |
| `rules`, parser cũ | 98,2% | 68,0% | 62,5% | 56,2% | 96,8% | 0% |
| `llm` (4 tầng), parser mới | 93,9% | 76,2% | 74,3% | 72,5% | 93,7% | 7,3% (95%) |

Bộ Dev đã dùng để sửa lỗi. Con số khách quan lấy từ bộ Blind. Nhóm yếu nhất: văn bản trước năm 2000 (25% / 25%), công bố thủ tục hành chính (75% / 55%).

### 8.5.3. Kết quả trên bộ Blind và Challenge (đo 15/10/2026)

Bộ Blind chưa dùng để sửa lỗi. Đây là con số khách quan. Parser mới ở cả hai chế độ.

| Bộ | Chế độ | P | R | P theo văn bản | R theo văn bản | Vị trí | Unresolved (thật) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Blind (250) | `rules` | 94,5% | 35,0% | 62,1% | 46,4% | 85,4% | 14,3% (90%) |
| Blind (250) | `llm` | 90,5% | 48,3% | **77,7%** | **67,6%** | 77,7% | 13,7% (83%) |
| Challenge (40) | `rules` | 64,4% | 41,4% | 76,0% | 50,0% | 80,4% | 4,4% |
| Challenge (40) | `llm` | 64,1% | 52,0% | **85,3%** | **69,0%** | 75,1% | 4,0% |

- 88% văn bản Blind không có lỗi cấu trúc (người gán xét parser mới). Parser cũ trên Dev: 72,7%.
- Ca B (tên danh mục có từ hành động): `llm` đạt 100% / 96%. Ca A (Quyết định và Quy định kèm theo): 98,1% / 73,5%.
- `llm` chưa đạt mục tiêu 85%. Lỗi lớn nhất: danh sách văn bản trong phụ lục, danh mục chưa được đọc; vị trí do LLM đọc kém hơn regex; văn bản không chia Điều có sửa đổi (0%).
- Thời gian: `llm` khoảng 12 giây mỗi văn bản (290 văn bản trong 57 phút, CCU 3). `rules` khoảng 1,4 giây khi dùng lại cache QA.

## 8.6. Vòng sửa ngày 19/10/2026

### 8.6.1. Thay đổi

Lỗi gốc ở báo cáo rà soát `work/review50-20261019/README.md`. Chỉ xem lỗi của bộ Dev và `review50` để sửa.

| Lớp | Thay đổi | Ví dụ |
| --- | --- | --- |
| Cấu trúc | Dòng bảng của phụ lục không chia Điều là một đơn vị (`Phụ lục <n> [Mục <m>] STT <k>`). Cột căn cứ pháp lý bị bỏ. Đơn vị mang câu của Điều nói về phụ lục đó. | `587301`: 0 → 17 quan hệ |
| Vị trí | "điểm a, khoản 16 Điều 2" là một vị trí. Danh sách ngăn bằng `;` được đọc đủ. | `661129`, `628717` |
| Prompt (LLM) | Định nghĩa từng hành động, "thực hiện", dòng bảng, danh mục chỉ công bố, cả văn bản và một phần văn bản. Không thêm regex cho ca khó nhận diện. | `634166`, `542598` |
| Kiểm | Dòng bảng phải nêu văn bản đích. "Công bố … danh mục" không nêu đích bị loại. Ghi chú lịch sử bị loại. Chữ hành động ở câu dẫn của danh sách được chấp nhận. "Sửa đổi, bổ sung" cho 2 quan hệ. | `664270` |
| Gộp | Không giữ cả vị trí cha và con của cùng đơn vị, hành động, văn bản đích. "toàn bộ" bên cạnh vị trí cụ thể thì giữ vị trí cụ thể. Vị trí ngoài định dạng thành `doi_tuong`. Phụ lục chỉ chi tiết lệnh của một Điều thì quan hệ thuộc Điều. | `634166`, `417402` |
| Metadata | `noi_nhan` bỏ khối chữ ký cùng dòng bảng. `hieu_luc_rieng` đọc danh sách ngăn bằng `;`. | `10377`, `628717` |

### 8.6.2. Bộ hold-out mới

`holdout-20261019`: 122 văn bản (60 ngẫu nhiên, 62 theo loại tác động). Nhóm (cơ quan + mẫu tên) không có ở bộ nào khác. Mỗi văn bản dài tối đa 30.000 ký tự, người gán đọc toàn văn kể cả bảng. Nhãn quan hệ và metadata do 7 agent Claude độc lập gán, không thấy kết quả công cụ. Nhãn được khóa bằng hash (`eval/gold/holdout-20261019.lock.json`) trước khi chấm. Rubric sửa một lần trước khi khóa: danh mục văn bản hết hiệu lực chỉ được công bố không là hành động (4 văn bản, 105 quan hệ bị bỏ).

Lệnh: `python -m eval.build_holdout <tên>`, `python -m eval.packets <tên> <lượt>`, `python -m eval.score <tên> <lượt>`, `python -m eval.score_meta <tên> <lượt>`. Tiêu chí metadata: `eval/rubric-metadata.md`.

### 8.6.3. Kết quả (code chốt ngày 19/10/2026, hash ở `work/final-20261019-code.json`)

Quan hệ, chế độ `llm`. P và R tính trên (đơn vị nguồn, hành động, văn bản đích), chỉ quan hệ `validated`. "e2e" tính thêm vị trí.

| Bộ | Vai trò | Văn bản | P | R | e2e P / R | Ngày 15/10 (P / R) |
| --- | --- | --- | --- | --- | --- | --- |
| `holdout-20261019` | Độc lập, nhãn mới | 122 | **93,4%** | **75,7%** | 78,4% / 64,2% | — |
| Blind trừ `review50` | Đã xem lỗi ngày 20/10 (không còn độc lập), nhãn 15/10 | 205 | 87,5% | 60,2% | 78,0% / 52,9% | 92,2% / 52,2% |
| `review50-20261019` | Đã dùng để sửa | 50 | 94,7% | 81,6% | 87,7% / 76,3% | 88,2% / 51,7% |
| Dev | Đã dùng để sửa | 147 | 92,5% | 86,4% | 75,3% / 76,3% | 93,8% / 74,8% |

Metadata, 6 trường (`la_vbqppl`, `cap_hieu_luc`, `ngay_hieu_luc`, `ngay_het_hieu_luc`, `ngay_hoi_to`, `hieu_luc_rieng`):

| Bộ | Văn bản | Đúng theo trường | Văn bản đúng cả 6 trường | Bỏ trường người gán chưa chắc |
| --- | --- | --- | --- | --- |
| `holdout-20261019` | 122 | **97,7%** | 91,0% | 99,3% |
| `review50-20261019` | 50 | 98,3% | 94,0% | 100% |

Trên Blind, theo việc người gán có toàn văn hay không:

| Nhóm | Văn bản | P | R |
| --- | --- | --- | --- |
| Có toàn văn (≤ 30.000 ký tự) | 172 | 90,1% | 57,8% |
| Văn bản dài, chỉ có đơn vị | 33 | 64,9% | 45,3% |

- Hold-out đạt mục tiêu: R ≥ 65%, P ≥ 70%, metadata ≥ 90%. Riêng e2e R (64,2%) sát dưới 65%.
- Số liệu chấm lại ngày 20/10/2026 sau khi sửa `eval.score`: `align()` đã gán quan hệ trùng khớp chính xác về đơn vị cha khi nhãn có cả hai cấp (`692795`: 6 quan hệ ở `Điều 10 Khoản 1–3` bị tính là sót). Mọi lượt được chấm lại bằng cùng bộ chấm.
- Blind chưa đạt R 65%. Phân tích ngày 20/10 (171 quan hệ bị sót, 82% ở 12 văn bản):

| Nguyên nhân | Quan hệ | Văn bản |
| --- | --- | --- |
| Nhãn theo quy ước khác rubric hiện hành: tên văn bản không nêu số hiệu nhưng người gán lấy số hiệu từ Điều 1 (18); "các TTHC tại 8 Quyết định trái với Quyết định này được sửa đổi, thay thế hoặc bãi bỏ" ghi 24 quan hệ (24). | 42 | `636935`, `668142` |
| Điều bãi bỏ các văn bản trong danh mục kèm theo: câu hành động nằm ở tên Điều; nhãn "Danh mục II", "Danh mục đính kèm" không khớp phụ lục. | 38 | `683636`, `336452` |
| Câu tác động lên một phần ("Hủy bỏ 44 công trình, dự án … tại các Nghị quyết") nhưng LLM không nêu tên phần: quan hệ chờ duyệt. | 17 | `636935` |
| Rải rác ở các văn bản khác | 74 | — |

Bỏ 42 quan hệ theo quy ước khác thì R của Blind là 66,8%.
- `macro_precision` của `eval.score` tính 0 cho văn bản mà công cụ bỏ sót hết quan hệ. Chỉ số này phạt cả độ bao phủ. Dùng P theo quan hệ làm độ chính xác.

## 8.7. Vòng phân tích và sửa ngày 20/10/2026

### 8.7.1. Vì sao Blind thấp hơn hold-out

| Yếu tố | Đo | Kết luận |
| --- | --- | --- |
| Bộ chấm | `align()` gán quan hệ trùng khớp về đơn vị cha; thứ tự duyệt `set` làm điểm đổi giữa các lần chấm. Đã sửa: đơn vị nguồn khớp khi bằng nhau hoặc là cha/con (cùng hành động, cùng văn bản đích), duyệt có thứ tự. | Blind 56,3% → 64,2% (code 19/10) |
| Văn bản không có toàn văn khi gán nhãn | Có toàn văn: R 62,3%. Không có (33 văn bản): R 45,3%. | Ảnh hưởng nhỏ: 29/171 quan hệ bị sót |
| Rubric cũ | 208 điểm bất đồng được 5 agent phân xử lại với toàn văn, không biết nguồn của quan hệ: 119 nhãn đúng, 19 nhãn sai, 33 không chắc; 8/37 quan hệ thừa của công cụ thật ra đúng. | R chuẩn hóa 64,1–69,2% (code 19/10) |

Sau khi chuẩn hóa, recall vẫn thấp hơn hold-out. Blind thành bộ phân tích lỗi (`eval/gold/blind-adj`, không còn độc lập). Lỗi bị sót theo nhóm văn bản (code 19/10): có bảng phụ lục 49% (không có: 88%); không chia Điều 40%; Nghị quyết 53%; Thông tư liên tịch 38%. Theo bước: chờ duyệt vì thiếu vị trí 37, model không thấy đích 34, sai hành động 25, sai đích 18.

### 8.7.2. Thay đổi

- Điều thực hiện hành động lên "các văn bản tại Phụ lục/Danh mục" nhận danh sách dòng của phụ lục đó (`danh_sach_kem_theo`). Khớp phụ lục theo nhãn ("Danh mục II") và tên Điều; nhận "đính kèm".
- Danh sách dài (từ 8 văn bản) được hỏi theo phần, mỗi phần 5 văn bản. Một lời gọi lỗi không làm mất quan hệ của cả văn bản. Câu trích và tên phần có `maxLength` trong schema.
- Gộp: vị trí của quy tắc chỉ thắng khi cụ thể; các act trích cùng một câu biểu quyết "một phần" hay "toàn bộ"; "một phần" bên cạnh "toàn bộ" thì giữ "một phần".
- Vị trí ngoài định dạng do LLM đọc ("khoản 2 mục II") thành `doi_tuong`, không để chờ duyệt.
- Dòng của danh sách thủ tục chỉ tác động lên quyết định của cùng cơ quan (`dong_bang_khac_co_quan`). Dòng bảng mà một Điều đã nêu cùng hành động, cùng văn bản đích thì thuộc Điều đó, kể cả khi model không đọc ra quan hệ của Điều.
- Prompt: định nghĩa danh sách kèm theo, "toàn bộ" cho mỗi văn bản của danh sách bãi bỏ. Quy ước bổ sung của rubric (tên văn bản; câu chung "trái với").

### 8.7.3. Kết quả (code chốt 20/10/2026, hash ở `work/final-20261020-code.json`)

Ba mức recall: **văn bản** (đúng văn bản đích), **quan hệ** (thêm hành động và đơn vị nguồn cùng nhánh), **điều khoản** (thêm vị trí Điều/khoản/điểm).

| Bộ | Vai trò | Văn bản P / R | Quan hệ P / R | Điều khoản P / R |
| --- | --- | --- | --- | --- |
| `holdout-20261020` (158) | **Độc lập, có văn bản dài** | 88,9% / **56,7%** | 86,1% / **53,8%** | 78,3% / 37,0% |
| `holdout-20261020` trừ `124929` (157) | Bỏ một Công văn có 80 quan hệ | 88,9% / 67,3% | 86,1% / 62,9% | 78,3% / 51,2% |
| `holdout-20261019` (122) | Chưa xem lỗi | 92,9% / 79,0% | 92,0% / 77,7% | 76,1% / 64,7% |
| Blind chuẩn hóa (205) | Bộ phân tích | 95,7% / 90,7% | 94,2% / 89,1% | 75,1% / 65,8% |
| Dev (147) | Đã dùng để sửa | — / 89,9% | 94,6% / 87,2% | 76,8% / 78,1% |

Metadata `holdout-20261020`: 97,3% theo trường, 90,5% văn bản đúng cả 6 trường.

Trên `holdout-20261020` trừ `124929`, theo nhóm (quan hệ R): văn bản có phụ lục không chia Điều 36%, không có 79%; dài trên 30.000 ký tự 75%, ngắn hơn 62%. Quan hệ bị sót theo nơi đặt: Điều/khoản/mục 38, tên văn bản 19, dòng bảng 15, chờ duyệt 7.

- Mục tiêu R ≥ 65% chưa đạt trên hold-out mới. Nhóm văn bản có phụ lục, danh sách là nguyên nhân chính.
- LLM không ổn định với dòng bảng: cùng dòng, `performed` đổi giữa các lần chạy (`587301`, `review50`).
- Không ghi ES.

## 8.8. Vòng 3 (20/10/2026) và hold-out 3

### 8.8.1. Rà soát hold-out 2 trước khi sửa

- Bộ chấm: dòng bảng viết khác nhau ("Phụ lục 2 Mục I STT 01" và "Phụ lục 2 STT 1") là một dòng (`row_path`). Ca `510508`, `667513` là lỗi bộ chấm, không dùng để sửa model.
- Nhãn: 123 điểm bất đồng được phân xử lại (không biết nguồn): 104 nhãn đúng, 2 sai, 2 không chắc; 13/15 quan hệ thừa của công cụ là sai. Nhãn của `124929` đúng, phạm vi là một phần. Nhãn đã phân xử: `eval/gold/holdout-20261020-adj`. Từ đây hold-out 2 là bộ phân tích.
- Chẩn đoán cũ "tên văn bản trong ES bị cắt" là sai: tên trong ES đủ (11/13). Nguyên nhân thật là prompt thiếu định nghĩa hành động ở tên văn bản.

### 8.8.2. Thay đổi (code chốt, hash ở `work/final-20261021-code.json`)

| Lỗi | Sửa |
| --- | --- |
| "Danh sách kèm theo", "đính kèm" không được nhận | Nhận các cách viết; danh sách gắn vào Điều nêu hành động |
| Phụ lục viết thành đoạn văn | Đơn vị `Phụ lục <n> Mục <m>` cho LLM; rubric thêm đường dẫn này |
| Hành động ở tên văn bản | Prompt định nghĩa TÊN VĂN BẢN; tên in trong văn bản đưa vào `Phần đầu` |
| Cột "Áp dụng thay thế" | Prompt: `thay-the` lên quy trình của dòng, không phải cả văn bản |
| "Kết thúc", "chấm dứt" | Prompt định nghĩa; LLM phân loại, không ép thành `bai-bo` |
| Số hiệu kiểu "38-HD/BTCTW", "481-TTg" | Resolver nhận số có gạch |
| Văn bản cấp dưới "sửa đổi Luật" | Lý do loại `vuot_tham_quyen` (rubric đã có quy ước) |
| Văn bản tiếng Anh (`39074`) | Ghi `ngon_ngu` trong thống kê. Từ 20/10/2026, công cụ bỏ qua văn bản có toàn văn tiếng Anh (`skipped = tieng_anh`). |

### 8.8.3. Kết quả

Hold-out 3 (`holdout-20261021`): 158 văn bản mới, nhóm chưa dùng, văn bản đến 120.000 ký tự, 80 văn bản lấy ngẫu nhiên. Nhãn do 10 agent độc lập gán theo rubric, khóa hash trước khi chạy công cụ (`eval/gold/holdout-20261021.lock.json`): 215 quan hệ ở 59 văn bản.

| Bộ | Vai trò | Văn bản P / R | Quan hệ P / R | Điều khoản P / R |
| --- | --- | --- | --- | --- |
| **`holdout-20261021` (158)** | **Độc lập, chạy một lần** | **97,4% / 92,6%** | **96,9% / 93,1%** | **84,1% / 73,7%** |
| `holdout-20261020-adj` (158) | Bộ phân tích | 83,0% / 92,1% | 85,6% / 89,0% | 71,2% / 54,7% |
| `holdout-20261020-adj` trừ `124929` | Bộ phân tích | 94,4% / 95,3% | 95,0% / 92,5% | 87,1% / 74,7% |
| Blind chuẩn hóa | Bộ phân tích | 93,6% / 94,2% | 90,8% / 93,5% | 73,5% / 69,1% |
| Dev | Đã dùng để sửa | 95,2% / 89,9% | 90,1% / 86,4% | 73,1% / 77,1% |
| `review50-20261019` | Hồi quy | 96,9% / 91,2% | 94,4% / 78,2% | 78,2% / 65,6% |

Metadata `holdout-20261021`: 98,0% theo trường, 91,8% văn bản đúng cả 6 trường. `review50`: 98,3%.

Lưu ý khi đọc hold-out 3:
- Hold-out 3 có ít quan hệ hơn hold-out 2 (215 so với 298) và không có văn bản kiểu `124929` (một Công văn 80 quan hệ trong phụ lục văn xuôi). Điểm cao một phần do mẫu dễ hơn.
- Lỗi còn lại trên hold-out 3, theo nguyên nhân:
  - Vị trí: nhánh quy tắc đọc sai danh sách vị trí lẫn cấp ("khoản 1 và điểm c, điểm đ khoản 3 Điều 15" thành "điểm c khoản 1 Điều 15") và ghi đè vị trí đúng của LLM (`609183`, 15 vị trí).
  - Vị trí ngoài định dạng hợp đồng ("khoản 2.1 Điều 2", "Mục II" trong văn bản chia Mục): nhãn có, hợp đồng 9.5 không cho phép.
  - Tên văn bản lưu trong ES (không phải tên in): sinh 3 quan hệ `Phần đầu` thừa và số hiệu "31/CP-1996" thay cho "31/CP".
  - Chờ duyệt đúng thiết kế: `phan_kem_theo_chua_ro` (2), danh sách "thay thế các Nghị quyết sau:" bị để `vi_tri_chua_xac_dinh` (3).
- Không ghi ES.

### 8.8.4. Chốt luồng (20/10/2026)

Luồng được chốt với code hiện tại: code vòng 3 cộng 3 sửa lỗi nhỏ.

| Sửa | Từ bộ | Kiểm |
| --- | --- | --- |
| Danh sách vị trí lẫn cấp ở nhánh quy tắc: "khoản 1 và điểm c, điểm đ khoản 3 Điều 15" không còn thành "điểm c khoản 1 Điều 15"; nhóm sau dấu ";" không nêu Điều thì lấy Điều của nhóm sau | hold-out 3 (`609183`) | unittest |
| Văn bản đích là văn bản chứa nội dung bị tác động, không phải văn bản được nhắc trong nội dung (prompt); "Phụ lục số 07" thành "Phụ lục 07" | hold-out 2 | không đổi điểm `124929` |
| Số hiệu Luật kiểu "40/QH12/2009" được nhận là Luật (quy tắc thẩm quyền) | hold-out 2 | unittest |

Độ dao động của LLM (cùng code, 2 lượt chạy, `holdout-20261020-adj` trừ `124929`):

| Lượt | Văn bản P / R | Quan hệ P / R | Điều khoản P / R |
| --- | --- | --- | --- |
| Vòng 3 | 94,4% / 95,3% | 95,0% / 92,5% | 87,1% / 74,7% |
| Code chốt, lượt a | 94,4% / 95,3% | 95,4% / 91,0% | 87,5% / 74,3% |
| Code chốt, lượt b | 92,7% / 95,3% | 92,0% / 88,7% | 82,0% / 70,6% |

- Cùng code, hai lượt lệch 2–4 điểm ở mức quan hệ, 4–5 điểm ở mức điều khoản. Recall mức văn bản ổn định. Một lượt đo là một mẫu, không phải giá trị chắc chắn.
- Code chốt nằm trong khoảng dao động của vòng 3.
- Hold-out 3 không đo lại với code chốt: sửa lỗi vị trí lấy từ hold-out 3.
- Còn mở: `124929` (Công văn điều chỉnh phương án đơn giản hóa: model chọn sai văn bản đích, nhận câu đề nghị, giao nhiệm vụ là hành động); quan hệ `Phần đầu` lấy từ tên lưu trong ES thay cho tên in.
- Chưa ghi ES.

## 8.9. Quyết định P0, P1 (20/10/2026)

### 8.9.1. Thay đổi

| Mức | Việc | Code |
| --- | --- | --- |
| P0 | Q11: dò quan hệ chỉ từ tên in trong văn bản. Tên lưu ở nguồn chỉ để tìm kiếm, đối chiếu. | `structure.printed_title`, `sentence_case`; `extract.opening`, `relations.detect`, `references.guidance` |
| P0 | Q12: giữ từng dòng bảng. Trường `doi_tuong_loai` (`van_ban`, `thu_tuc_hanh_chinh`) và `ma_thu_tuc`. | `resolver.object_kind`, mapping `changes.json` |
| — | Bỏ qua văn bản có toàn văn tiếng Anh (`skipped = tieng_anh`). | `convert.convert_document` |
| P1 | LLM nêu `chu_the` và `van_ban_chua_noi_dung` trước hành động. Tầng 4 loại act không do văn bản này thực hiện. Tầng 3 lấy văn bản chứa nội dung làm đích. Không có quy tắc riêng cho một văn bản. | `extract.SCHEMA`, prompt, `validate`, `resolver` |
| P1 | Thủ tục hành chính: văn bản chứa thủ tục là quyết định công bố thủ tục, không phải văn bản ở cột căn cứ pháp lý (prompt). | `prompts/extract_quan_he.txt` |
| P1 | Dòng của danh sách việc cần làm ("Danh mục văn bản cần sửa đổi, ban hành mới", cột "Thời hạn thực hiện", "Cơ quan chủ trì") không có act (`dong_bang_ke_hoach`). | `validate.PLANNED` |
| — | Tên phần chỉ là loại văn bản ("Quyết định") không là tên phần. Dòng của danh sách văn bản bị bãi bỏ, thay thế cả văn bản không lấy ô đầu làm tên phần. | `resolver.TYPE_ONLY` |

### 8.9.2. Kết quả (bộ phân tích, quan hệ P / R)

| Bộ | Code chốt (2 lượt, hoặc r3 và r4) | Code mới |
| --- | --- | --- |
| `holdout-20261020-adj` | 84,7–87,7% / 85,4–86,6% | 85,4% / 85,4% |
| `holdout-20261020-adj` trừ `124929` | 92,0–95,4% / 88,7–91,0% | 87,4% / 91,0% |
| `124929` (số quan hệ thừa / bị sót) | 21–22 / 15–17 | 10 / 20 |
| Dev | 87,7–90,1% / 86,4–88,4% | 85,1% / 84,7% |
| Blind chuẩn hóa | 90,8% / 91,5–93,5% | 90,5% / 91,2% |
| Blind, mức Điều khoản P / R | 73,5–74,2% / 68,9–69,1% | 73,3% / 67,7% |
| `review50-20261019` | 94,3–94,4% / 75,9–78,2% | 94,7% / 81,6% |

Sau 2 sửa cuối (lượt `r7`, 21/10/2026):

| Bộ | Quan hệ P / R | Văn bản P / R |
| --- | --- | --- |
| `holdout-20261020-adj` | 94,4% / 84,1% | 93,3% / 88,2% |
| `holdout-20261020-adj` trừ `124929` | 94,4% / 90,0% | 93,5% / 94,3% |
| Dev | 86,9% / 85,1% | 94,2% / 91,0% |

- `dong_bang_ke_hoach` chỉ loại 12 dòng, cả 12 ở `684851`. Không văn bản nào khác bị ảnh hưởng.
- `179298` hết quan hệ thừa từ cột căn cứ pháp lý.
- P của Dev còn thấp hơn khoảng cũ 1 điểm, do `11019` ("Xóa bỏ các khoản …" bị đọc là `bo-sung`). Lỗi này có từ lượt `r3`.

- P1 giảm một nửa quan hệ thừa ở `124929`. Ngoài văn bản này, kết quả nằm trong khoảng dao động của LLM, trừ P của hold-out 2 trừ `124929`.
- P của hold-out 2 trừ `124929` giảm chủ yếu do `684851` (Nghị quyết 247/2025/QH15, phụ lục là danh sách việc sẽ làm): 13 quan hệ thừa. Lượt `r4` có cùng lỗi, lượt `r5a`, `r5b` không có. Đây là ca LLM không ổn định.
- Dev: mọi quan hệ thừa của lượt mới đã có ở lượt `r3` hoặc `r4`. Không có loại lỗi mới.
- Các ca LLM còn không ổn định: danh sách nhiệm vụ (`684851`), câu "công bố" có kèm hành động (`616667`), "kết thúc" (`676752`).
- Chưa có hold-out độc lập cho code mới. Hold-out 3 đã dùng để sửa vị trí.
