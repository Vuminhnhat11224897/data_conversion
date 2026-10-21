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
| `trich_dan_khong_co_hanh_dong` | Câu trích không có động từ của hành động. Từ 21/10/2026 thay bằng `chua_co_cau_thuc_hien`: không có câu chi phối nêu hành động. |
| `dich_khong_phai_doi_tuong` | Mục của danh sách tác động lên văn bản mục nêu đầu tiên; đích LLM nêu chỉ nằm trong tên văn bản đó (từ 21/10/2026). |
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

## 8.10. Hold-out 4 (21/10/2026)

Bộ `holdout-20261022`: 158 văn bản mới, nhóm chưa dùng, văn bản đến 120.000 ký tự, 80 văn bản ngẫu nhiên. Nhãn do 10 agent độc lập gán, khóa hash trước khi chạy (`eval/gold/holdout-20261022.lock.json`): 302 quan hệ ở 71 văn bản. Code đo: commit `4e0a5c7` (`work/final-20261022-code.json`). Công cụ chạy một lần (lượt `h4-final`).

| Mức | P | R |
| --- | --- | --- |
| Văn bản | 92,2% | 67,1% |
| Quan hệ | 90,5% | 72,7% |
| Điều khoản | 65,3% | 51,8% |

Metadata: 98,0% theo trường, 92,4% văn bản đúng cả 6 trường. Quan hệ chờ duyệt: 18,2%, trong đó 50,9% là quan hệ thật.

75 quan hệ bị sót theo nguyên nhân:

| Nguyên nhân | Số | Văn bản |
| --- | --- | --- |
| Danh sách văn bản dưới câu dẫn ("Bãi bỏ … văn bản sau: 1. Quyết định …; 2. …") | 32 | `426243`, `389284`, `299860`, `658938` |
| — LLM ghép câu trích từ câu dẫn và mục danh sách, bỏ qua các mục ở giữa: câu trích không còn nguyên văn, tầng 4 loại (`trich_dan_khong_co_trong_nguon`) | 11 | |
| — Câu trích là mục danh sách, không có động từ; tầng 4 không đọc câu dẫn của Điều (`cau_dan_dieu`) cho khoản (`trich_dan_khong_co_hanh_dong`) | 7 | |
| — Nhánh quy tắc để mục danh sách chờ duyệt (`vi_tri_chua_xac_dinh`), không coi là toàn bộ văn bản | 12 | |
| — LLM không đọc ra | 2 | |
| Văn bản cũ cấu trúc hỏng (`257376`, 1998: parser nhận Điều của Quy định bị sửa là Điều của văn bản) | 16 | `257376` |
| LLM không đọc ra (tên văn bản, lời dẫn, công văn) | 13 | rải rác |
| Đơn vị nguồn khác nhãn (dòng bảng hay khoản) | 4 | `592133`, `482544`, `385433` |
| Khác | 10 | Số hiệu in sai "NQ-HDND" (`562142`), `phan_kem_theo_chua_ro` (`94678`), … |

- Nhóm danh sách văn bản dưới câu dẫn là lỗ hổng tổng quát, có từ trước P1. Hold-out 3 có ít văn bản dạng này. Văn bản bãi bỏ nhiều văn bản theo danh sách thường gặp trong kho.
- Sau khi xem lỗi, hold-out 4 không còn độc lập cho lần sửa sau.

## 8.11. Rule tổng quát: kiểm sự thật, không kiểm hình thức (21/10/2026)

### 8.11.1. Vấn đề

Sau mỗi hold-out mới, công cụ lại cần vá một cách viết mới. Nguyên nhân: tầng 4 và nhánh quy tắc xét lại câu trả lời của LLM bằng hình thức câu chữ. Ví dụ: câu trích phải liền một đoạn, phải chứa động từ, phải tìm được chuỗi vị trí. Văn bản thật viết một hành động theo nhiều hình thức: câu dẫn và danh sách, dòng bảng, đề mục, tên văn bản. Mỗi hình thức mới làm cổng chặn nhầm hành động thật.

Đo trên 5 bộ (`holdout-20261020-adj`, `holdout-20261021`, `holdout-20261022`, Blind, Dev): 197 quan hệ bị sót. Trong đó 96 (49%) là hành động hệ thống đã tìm ra nhưng code chặn. Tỉ lệ chặn đúng = số ứng viên sai bị chặn / số ứng viên bị chặn. Khoảng tin cậy 95% theo Wilson. Mỗi cổng tính theo lý do chặn đầu tiên, nên cổng sau chỉ được đánh giá trên phần còn lại.

| Cổng | Sai bị chặn | Thật bị chặn nhầm | Chặn đúng | Khoảng 95% |
| --- | --- | --- | --- | --- |
| `trich_dan_khong_co_trong_nguon` (hình thức) | 26 | 88 | 23% | 16%–31% |
| chờ duyệt `vi_tri_chua_xac_dinh` (hình thức) | 19 | 53 | 26% | 18%–38% |
| `trong_noi_dung_moi` (hình thức) | 0 | 6 | 0% | 0%–39% |
| `trich_dan_khong_co_hanh_dong` (hình thức) | 117 | 44 | 73% | 65%–79% |
| `khong_co_van_ban_dich` (sự thật) | 98 | 0 | 100% | 96%–100% |
| `vuot_tham_quyen` (sự thật) | 62 | 0 | 100% | 94%–100% |
| `chinh_van_ban_nguon` (sự thật) | 27 | 0 | 100% | 88%–100% |
| `dong_bang_ke_hoach` (sự thật) | 12 | 0 | 100% | 76%–100% |

### 8.11.2. Phân công

| Thành phần | Trách nhiệm |
| --- | --- |
| Parser cấu trúc | Đơn vị, phần cha, danh sách, bảng, ranh giới nội dung mới |
| LLM | Đọc nghĩa: ai thực hiện, hành động nào, đích nào, phạm vi nào |
| Code (`governance.py`, `validate.py`, `resolver.py`) | Kiểm vị trí bằng chứng, phân giải ID, chuẩn hóa vị trí, kiểm tính nhất quán. Code không đọc nghĩa. |
| Quy tắc nghiệp vụ | Điều kiện để quan hệ được dùng trong Graph. Bảng thẩm quyền cần nghiệp vụ duyệt. |

### 8.11.3. Quy tắc

1. **Câu thực hiện do cấu trúc xác định** (`governance.governing`). Câu thực hiện của một đơn vị là chính đơn vị, hoặc câu dẫn mở danh sách chứa đơn vị:
   - câu dẫn của khoản, cho các điểm;
   - câu dẫn hoặc tên Điều, cho các khoản;
   - đề mục của danh mục thủ tục hành chính, hoặc tên cột nêu hành động, cho các dòng bảng;
   - Điều tác động lên các văn bản của phần kèm theo, cho các dòng của phần đó.
2. **Câu mở danh sách** (`governance.opens_list`): câu kết thúc bằng dấu hai chấm, nêu một tập ("các văn bản", "15 văn bản", "một số điều", "sau đây"), và không nêu một vị trí cụ thể. Câu "Sửa đổi khoản 2 Điều 3 như sau:" không mở danh sách: các mục dưới nó là nội dung mới.
3. **Bằng chứng nhiều đoạn nguyên văn** (`governance.pieces`). Mỗi đoạn dài từ 12 ký tự, nằm nguyên văn trong một trường của khung đơn vị. Các đoạn phải phủ ít nhất 90% câu trích. Câu trích không khớp thì code tự lấy câu thực hiện, và lấy thêm mục nêu đích khi câu thực hiện là câu dẫn. Không tìm được câu thực hiện thì loại (`chua_co_cau_thuc_hien`), không chuyển thành `validated`. Từng đoạn, trường và vai trò được ghi ở `work/<run>/extract/<id>/evidence.json`. ES vẫn lưu `evidence` là một chuỗi.
4. **Ngoặc kép theo vai trò** (`governance.quotes`). `noi_dung_moi`: nội dung chèn vào văn bản đích. `cum_tu`: cụm từ của `thay-cum-tu`, tên văn bản. `trich`: câu kể lại. Chỉ `noi_dung_moi` và `trich` không chứa hành động của văn bản này.
5. **Đối tượng của mục** (`governance.heads`, `item_object`). Một mục của danh sách tác động lên văn bản mục nêu đầu tiên. Mục cũng tác động lên các văn bản nối với văn bản đó bằng ngày, cơ quan ban hành, "và", dấu phẩy hoặc dấu chấm phẩy ("1307/QĐ-BXD ngày 29/10/2008 và 91/QĐ-BXD …"). Vị trí nêu trước số hiệu ("Khoản 2 Điều 3 Quyết định số X") là phạm vi. Phần sau số hiệu là tên văn bản ("Quyết định X về việc sửa đổi khoản 2 Điều 3 …"), không phải phạm vi, không phải đích (`dich_khong_phai_doi_tuong`). Văn bản đứng sau từ mở đầu tên ("về việc", "quy định", "sửa đổi" …), ở ô khác của dòng bảng hoặc ở dòng khác thuộc tên văn bản.
6. **Phạm vi theo đối tượng.** Mục nêu cả văn bản với hành động bãi bỏ, thay thế, hủy bỏ: `toàn bộ`. Bỏ quy tắc "một phần thắng toàn bộ" trong `tidy_positions`.
7. **Giữ giới hạn trong node.** Phần không có node (mẫu biểu, đoạn, câu, gạch đầu dòng của khoản, tiết, dòng số thứ tự) có vị trí là node chứa nó. Phần đó ghi ở trường mới `chi_tiet_vi_tri`. Ví dụ: `vi_tri = ["Phụ lục I"]`, `chi_tiet_vi_tri = "Mẫu số 01"`.
8. **Đích chỉ nằm trong ghi chú lịch sử** ("… đã được sửa đổi tại Quyết định Y"): loại (`ghi_chu_lich_su`). Cặp "sửa đổi, bổ sung" trong ghi chú lịch sử không tạo cặp quan hệ.
9. **Thẩm quyền theo hành động.** Chỉ áp cho 6 hành động thay đổi nội dung hoặc hiệu lực. Không biết loại văn bản nguồn thì không kết luận mâu thuẫn.
10. **B2: chọn đơn vị theo cấu trúc** (`extract.units`). Mục do câu mở danh sách chi phối được gửi cho LLM, kể cả khi mục không có từ chỉ hành động. Đây là thay đổi duy nhất làm đổi đầu vào của LLM; thay đổi này được đo riêng.
11. **Một hàm kiểm "đoạn văn nêu đích"** (`governance.spans`, `names`, `first_is`, `listed`). Mọi phép kiểm "đoạn này nêu văn bản đích" dùng cùng một hàm. Hàm nhận số hiệu in có dấu cách bên trong ("32/2012/QĐ- U BND", "96 /QĐ-UBND"), chữ "Ð" thay "Đ", gạch ngang dài, số 0 ở đầu. Hàm không nhận số hiệu dài hơn có chứa số hiệu đích ("132/2012/QĐ-UBND", "32/2012/QĐ-UBND-VX").
12. **Chữ thuộc động từ của hành động khác không được tính** (`validate.VERBS`). "Bỏ" trong "hủy bỏ" không phải động từ của `bai-bo`. "Sửa" trong "sửa đổi" không phải động từ của `dinh-chinh`. "Thay" trong "thay đổi" không phải động từ của `thay-the` và `thay-cum-tu`.
13. **Bản ghi chờ duyệt không che bản ghi đã kiểm** (`convert.rows_into_articles`, `validate.distinct`). Hai bản ghi trùng đơn vị, hành động, đích, vị trí: giữ bản `validated`. Dòng của phần kèm theo là chi tiết của hành động do Điều nêu. Nếu hành động của Điều là `unresolved` và một dòng đã kiểm (`validated`) cùng hành động, cùng đích, thì hành động của Điều nhận kết quả của dòng đó. Ví dụ: Điều chỉ nêu "các Quyết định … (có danh sách kèm theo)"; dòng có cột "Thu hồi, hủy bỏ Quyết định số:" nêu đích.
14. **Văn bản nguồn không bao giờ là đích** (`resolver`, `validate`). Phần kèm theo của văn bản nguồn là nội dung của chính văn bản đó. LLM có thể ghi "văn bản chứa nội dung" là văn bản nguồn ("Kèm theo Quyết định số …"). Khi đó code giữ đích LLM nêu. Phép kiểm `chinh_van_ban_nguon` dùng cả đích sau phân giải.

Kiểm thử theo họ cách viết: `tests/test_behavior.py`. Mã kiểm thử không chứa ID văn bản trong điều kiện xử lý.

### 8.11.4. Quy tắc đã đo và không dùng

Trước khi thêm một quy tắc, đo quy tắc đó trên 6 bộ. Quy tắc chặn nhiều quan hệ đúng hơn quan hệ sai thì không dùng. Lỗi còn lại được ghi là lỗi đọc nghĩa của LLM.

| Quy tắc thử | Quan hệ đúng bị chặn | Quan hệ sai bị chặn | Kết luận |
| --- | --- | --- | --- |
| Động từ phải đứng trước số hiệu đầu tiên của câu | 70 | 19 | Không dùng. Câu bị động ("Quyết định X … hết hiệu lực") và tên văn bản ("THÔNG TƯ … SỬA ĐỔI …") đặt động từ sau số hiệu. |
| Câu trích của LLM có động từ của hành động khác, không có động từ của hành động này | 35 | 2 | Không dùng. Ví dụ ca sai còn lại: LLM đọc thêm `bo-sung` từ tên văn bản đích ("… công bố Danh mục thủ tục hành chính mới ban hành, sửa đổi, bổ sung"). |
| Đơn vị dưới câu dẫn nội dung mới ("Sửa đổi Điều 6 … như sau:") là nội dung, động từ trong đơn vị không tính | 23 | 1 | Không dùng. Các khoản dưới "Sửa đổi, bổ sung Điều 5 … như sau:" thường tự nêu hành động ("Khoản 1 Điều 5 được sửa đổi như sau:"). |
| Câu nêu đề nghị, kế hoạch (`PLANNED`) áp cho mọi đơn vị, không chỉ dòng bảng | 1 | 0 | Không dùng. Đề nghị không theo một mẫu câu cố định; `chu_the` do LLM đọc. |
| "Bỏ" sau "hủy" không tính cho `bai-bo` (quy tắc 12) | 0 | 7 | Dùng. |

### 8.11.5. Kết quả đo C′ (21/10/2026)

Một vòng đo trên 6 bộ là một lệnh:

```bash
.venv/bin/python -m eval.round <tên lượt> --without b2   # chạy lại chặt, 6 bộ song song, khoảng 2 phút
.venv/bin/python -m eval.round <tên lượt> --allow-new    # có B2, cho gọi LLM, chạy lần lượt từng bộ
```

Lệnh in bảng chỉ số và bảng thay đổi so với A. Bộ nào không hợp lệ (có câu trả lời thiếu hoặc văn bản lỗi) thì lệnh báo và trả mã lỗi. Trước ngày 21/10/2026, một vòng đo mất khoảng 15 phút; thời gian chủ yếu là chờ ES tra số hiệu (mục 2.5.3 ở docs 02).

C′ là code mới (quy tắc 1–9, 11–14), chạy lại chặt trên đúng các câu trả lời LLM của lượt A. Lượt chạy lại chặt không gọi LLM mới. Mọi thay đổi trong bảng do code tạo ra. B2 (quy tắc 10) chưa bật trong C′; B2 được đo riêng ở lượt C. A là baseline (commit 4e0a5c7). Bản chụp code: `work/C-code-1336.tgz`. 6 bộ đều hợp lệ: 0 câu trả lời thiếu, 0 văn bản lỗi.

Ô ghi "P / R (đúng, sai, sót)". Phát hiện: đúng văn bản nguồn, đích và hành động. Phạm vi: đúng thêm vị trí hoặc phần bị tác động. Quan hệ `unresolved` không tính là cạnh.

| Bộ | A phát hiện | C′ phát hiện | A phạm vi | C′ phạm vi |
| --- | --- | --- | --- | --- |
| dev | 0,837 / 0,798 (87, 17, 22) | 0,847 / 0,862 (94, 17, 15) | 0,849 / 0,773 (214, 38, 63) | 0,853 / 0,798 (221, 38, 56) |
| H2 | 0,930 / 0,820 (132, 10, 29) | 0,944 / 0,839 (135, 8, 26) | 0,791 / 0,543 (170, 45, 143) | 0,781 / 0,546 (171, 48, 142) |
| H3 | 0,982 / 0,794 (108, 2, 28) | 0,976 / 0,897 (122, 3, 14) | 0,882 / 0,735 (172, 23, 62) | 0,880 / 0,782 (183, 25, 51) |
| H4 | 0,928 / 0,703 (116, 9, 49) | 0,932 / 0,830 (137, 10, 28) | 0,737 / 0,556 (140, 50, 112) | 0,732 / 0,619 (156, 57, 96) |
| Blind | 0,894 / 0,910 (193, 23, 19) | 0,902 / 0,910 (193, 21, 19) | 0,812 / 0,732 (273, 63, 100) | 0,815 / 0,732 (273, 62, 100) |
| review50 | 0,957 / 0,957 (45, 2, 2) | 0,957 / 0,957 (45, 2, 2) | 0,829 / 0,818 (63, 13, 14) | 0,829 / 0,818 (63, 13, 14) |

Thay đổi từ A sang C′, đếm theo cặp hành động và đích trong từng văn bản:

| Bộ | Đúng phục hồi | Đúng bị mất | Sai mới | Sai được loại |
| --- | --- | --- | --- | --- |
| dev | 7 | 0 | 0 | 0 |
| H2 | 4 | 1 | 1 | 3 |
| H3 | 14 | 0 | 1 | 0 |
| H4 | 21 | 0 | 1 | 0 |
| Blind | 0 | 0 | 1 | 3 |
| review50 | 0 | 0 | 0 | 0 |

Đọc kết quả:

1. Trên 5 bộ hold-out: 39 quan hệ đúng được phục hồi, 1 quan hệ đúng bị mất, 4 quan hệ sai mới, 6 quan hệ sai được loại.
2. Phạm vi: R tăng ở H3 và H4. P giảm 0,002–0,010 ở H2, H3, H4. Lý do: một phần quan hệ mới tìm ra có vị trí sai (H4: thêm 7 lỗi vị trí).
3. 4 quan hệ sai mới là lỗi đọc nghĩa của LLM. Code cũ chặn được các quan hệ này nhờ cổng hình thức, không nhờ một sự thật:
   - LLM đọc động từ từ tên văn bản đích (638463);
   - LLM đọc động từ từ nội dung mới (47544);
   - LLM đọc đề nghị thành hành động (579076);
   - một quan hệ trong văn bản 124929.
4. Quan hệ đúng bị mất (41783) có câu thực hiện không nêu đích. Đích nằm ở câu trước ("… Mục II Thông tư số 163/NG/TT …. Đoạn đầu điểm (1)(a) Mục II được sửa lại như sau:"). Code không gắn được đích theo cấu trúc, nên quan hệ ở `unresolved`.

### 8.11.6. Kết quả đo C, có B2 (21/10/2026)

C là C′ cộng B2 (quy tắc 10). B2 đổi đầu vào của LLM, nên lượt này gọi LLM cho các Điều có thêm đơn vị: 245 lời gọi mới trên 6 bộ. Các câu trả lời khác dùng lại câu trả lời đã lưu. Lệnh: `.venv/bin/python -m eval.round C --allow-new`, tổng thời gian 7 phút 24 giây. Bản chụp code: `work/C-code-1423.tgz`. 6 bộ đều hợp lệ.

| Bộ | A phát hiện | C phát hiện | A phạm vi | C phạm vi | LLM mới |
| --- | --- | --- | --- | --- | --- |
| dev | 0,837 / 0,798 (87, 17, 22) | 0,847 / 0,862 (94, 17, 15) | 0,849 / 0,773 (214, 38, 63) | 0,853 / 0,798 (221, 38, 56) | 24 |
| H2 | 0,930 / 0,820 (132, 10, 29) | 0,944 / 0,839 (135, 8, 26) | 0,791 / 0,543 (170, 45, 143) | 0,781 / 0,546 (171, 48, 142) | 53 |
| H3 | 0,982 / 0,794 (108, 2, 28) | 0,976 / 0,912 (124, 3, 12) | 0,882 / 0,735 (172, 23, 62) | 0,881 / 0,791 (185, 25, 49) | 43 |
| H4 | 0,928 / 0,703 (116, 9, 49) | 0,938 / 0,909 (150, 10, 15) | 0,737 / 0,556 (140, 50, 112) | 0,748 / 0,671 (169, 57, 83) | 44 |
| Blind | 0,894 / 0,910 (193, 23, 19) | 0,903 / 0,925 (196, 21, 16) | 0,812 / 0,732 (273, 63, 100) | 0,808 / 0,732 (273, 65, 100) | 67 |
| review50 | 0,957 / 0,957 (45, 2, 2) | 0,957 / 0,957 (45, 2, 2) | 0,829 / 0,818 (63, 13, 14) | 0,829 / 0,818 (63, 13, 14) | 14 |

| Bộ | Đúng phục hồi | Đúng bị mất | Sai mới | Sai được loại |
| --- | --- | --- | --- | --- |
| dev | 7 | 0 | 0 | 0 |
| H2 | 4 | 1 | 1 | 3 |
| H3 | 16 | 0 | 1 | 0 |
| H4 | 34 | 0 | 1 | 0 |
| Blind | 3 | 0 | 1 | 3 |
| review50 | 0 | 0 | 0 | 0 |

Đọc kết quả:

1. Trên 5 bộ hold-out, so với A: 57 quan hệ đúng được phục hồi, 1 quan hệ đúng bị mất, 4 quan hệ sai mới, 6 quan hệ sai được loại.
2. B2 thêm 18 quan hệ đúng so với C′ (H3: 2, H4: 13, Blind: 3). B2 không thêm quan hệ sai ở nhóm phát hiện.
3. Phạm vi ở Blind: thêm 2 lỗi vị trí, nên P giảm 0,004.
4. Câu trả lời mới của LLM có thể dao động giữa các lượt (mục 8.8.4). Phần tăng của B2 cần được xác nhận lại ở H5.

### 8.11.7. Ghi thử v4 (21/10/2026)

Theo yêu cầu người dùng, 3 index `-v4` được xóa tay và ghi lại bằng code mới nhất (đến commit `013e897`). Phạm vi: 1000 văn bản mới nhất theo ngày ban hành, lấy từ 2026 lùi về 1980. Kết quả là các văn bản ban hành từ 30/01/2026 đến 30/09/2026. Danh sách ở `work/v4-newest-ids.txt`. Lệnh ở docs 02, mục "Ghi thử vào v4".

| Bước | Thời gian | Kết quả |
| --- | --- | --- |
| Ghi lần đầu (lượt `v4-1000`, có gọi LLM) | 71 phút, 7.958 lời gọi LLM | 994/1000 văn bản; 4 văn bản lỗi `IndexError`, 2 văn bản hết thời gian kết nối |
| Sửa lỗi "Phần I Phụ lục" (commit `fb1b206`), chạy lại 6 văn bản | 43 giây | 6/6 |
| Kiểm hợp đồng v4 lần 1 | | 237 luật, 8 luật có lỗi |
| Sửa 3 lỗi dữ liệu và 2 luật kiểm lỗi thời (commit `aaf27a2`), ghi lại 1000 văn bản bằng câu trả lời đã lưu (`LLM_REPLAY=strict`) | 19 phút | 993/1000; 7 văn bản rất lớn hết thời gian kết nối, chạy lại với 3 luồng thì đạt |
| Sửa cặp cụm từ (commit `013e897`), ghi lại 27 văn bản có `thay-cum-tu` | 3 phút | 27/27 |

Trạng thái cuối:

| Index | Số bản ghi |
| --- | --- |
| `legal-docs-v4` | 1.000 |
| `legal-chunk-section-v4` | 61.674 |
| `legal-changed-v4` | 3.570 (3.380 `validated`, 190 `unresolved`) |

- Lý do `unresolved`: `vi_tri_chua_xac_dinh` 78, `dich_chua_gan_cau_thuc_hien` 59, `phan_kem_theo_chua_ro` 48, `van_ban_dich_khong_co_trong_nguon` 4, `vi_tri_khong_co_trong_nguon` 1.
- 3.193 quan hệ có `target_matched_id`. 182 quan hệ có `doi_tuong_loai = thu_tuc_hanh_chinh`. 41 quan hệ có `chi_tiet_vi_tri`.
- Kiểm hợp đồng v4 lần cuối: 237 luật, 3 luật có lỗi. Cả 3 là lỗi đọc cấu trúc có từ trước: vị trí "Mục I" đứng một mình (9/3.128), nơi nhận có dòng chữ ký (9/1.000), số dòng bảng (1/965).
- Văn bản rất lớn (tới 2.940 chunk) có thể hết thời gian chờ embedding hoặc ES khi chạy 10 luồng. Chạy lại các văn bản lỗi với ít luồng hơn.

### 8.11.8. Ghi thêm 10.000 văn bản vào v4 (21–22/10/2026)

Lượt `v4-10000` ghi 10.000 văn bản mới nhất tiếp theo (ban hành từ 08/10/2025 đến 30/01/2026), bằng code đến commit `013e897`. Danh sách ở `work/v4-next10000-ids.txt` (thêm 200 ID dự phòng). Script: `work/run-v4-10000.sh`. Script chạy lại một lần các văn bản lỗi với 3 luồng.

| Chỉ số | Kết quả |
| --- | --- |
| Thời gian | 17:15 → 23:58 (6 giờ 43 phút) |
| Tốc độ | 16,3 văn bản/phút ban ngày (3 lời gọi LLM cùng lúc); 45,4 văn bản/phút sau 22:00 (10 lời gọi) |
| Lời gọi LLM | 83.593 (khoảng 8,4 lời gọi mỗi văn bản) |
| Lỗi | 5 văn bản hết thời gian kết nối ở lượt chính; chạy lại đạt cả 5 |

Trạng thái `-v4` sau lượt này:

| Index | Số bản ghi | Dung lượng |
| --- | --- | --- |
| `legal-docs-v4` | 11.000 | 544 MB |
| `legal-chunk-section-v4` | 447.589 | 6,5 GB |
| `legal-changed-v4` | 42.718 (40.428 `validated`, 2.290 `unresolved`) | 20 MB |

- 37.243 quan hệ (87%) có `target_matched_id`. 1.730 quan hệ có `doi_tuong_loai = thu_tuc_hanh_chinh`. 274 quan hệ có `chi_tiet_vi_tri`.
- Lý do `unresolved`: `vi_tri_chua_xac_dinh` 736, `dich_chua_gan_cau_thuc_hien` 585, `phan_kem_theo_chua_ro` 528, `vi_tri_khong_co_trong_nguon` 325, `van_ban_dich_khong_co_trong_nguon` 116.
- Kiểm hợp đồng v4 (27 phút): 237 luật, 5 luật có lỗi, mỗi luật dưới 1% số bản ghi:
  - vị trí ngoài định dạng 198/38.357; 196 trường hợp là "Mục" hoặc "Phần" đứng một mình (ví dụ `Mục IV`);
  - nơi nhận có dòng chữ ký 48/11.000;
  - số dòng bảng 3/11.789;
  - ký hiệu Điều không bắt đầu bằng số Điều 1/20.660;
  - `scope_grounding_correct = false` mà quan hệ `validated` 1/258 (`677855_0`: quan hệ chỉ do quy tắc đọc, phạm vi là danh sách số thứ tự).
