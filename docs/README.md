# Tài liệu chuyển đổi VBPL: v2, v3, v4

Thư mục này mô tả công cụ `vbpl_v3` và dữ liệu nó tạo ra. Đọc [05](05-phien-ban-v2-v3-v4.md) trước để biết 3 phiên bản khác nhau thế nào. Sau đó đọc theo thứ tự dưới đây.

Trạng thái ngày 27/10/2026:

| Mục | Trạng thái |
| --- | --- |
| Luồng chốt | Chế độ `llm` (luồng 4 tầng), mặc định của `convert`. Code chốt: commit `8b023ca` (27/10/2026). |
| Index `-v4` | 11.000 văn bản, ban hành 08/10/2025–30/09/2026. Ghi lại ngày 22/10/2026 bằng code `2911b77`. Dữ liệu chưa có các thay đổi 26–27/10/2026 ([08, mục 8.16–8.18](08-quan-he-4-tang-va-danh-gia.md)). Quyết định làm sạch dữ liệu R1–R15 ở [07, mục 7.4](07-gioi-han-va-can-chot.md#74-quyết-định-đã-chốt). |
| Đợt tiếp theo | 10.000 văn bản ở `work/v4-next10000b-ids.txt`, ban hành 25/06/2025–08/10/2025. Chưa chạy, chờ người dùng quyết. |
| v3 | Không đổi. Ghi lại v3 cần bên Graph duyệt v4. |
| Đánh giá | Mỗi đợt 10.000 văn bản mới: lấy mẫu 1.000 văn bản để chấm ([`eval/README.md`](../eval/README.md)). |

| # | Tài liệu | Nội dung | Người đọc chính |
| --- | --- | --- | --- |
| 1 | [01-kien-truc.md](01-kien-truc.md) | Thành phần, 4 tầng, nguyên tắc thiết kế, an toàn dữ liệu, cấu hình, lưu trữ (`work/`, `bernmark/`), triển khai, mạng tới máy LLM | Bên dữ liệu |
| 2 | [02-luong-hoat-dong.md](02-luong-hoat-dong.md) | Luồng dữ liệu hiện hành: quy trình một đợt, ghi thử v4, giới hạn tải, lệnh, luồng một lượt, luồng một văn bản, luồng con của 4 tầng, làm tiếp và chạy lại, kiểm tra, thời gian | Bên dữ liệu |
| 3 | [03-hop-dong-du-lieu-v2.md](03-hop-dong-du-lieu-v2.md) | Dữ liệu nguồn v2 (chỉ đọc) và chất lượng đo được | Bên dữ liệu, bên Graph |
| 4 | [04-hop-dong-du-lieu-v3.md](04-hop-dong-du-lieu-v3.md) | Dữ liệu v3 đang có (đo 19/10/2026): trường, quy tắc, lỗi đã biết, cách nối cho đồ thị | Bên Graph, bên tìm kiếm |
| 5 | [05-phien-ban-v2-v3-v4.md](05-phien-ban-v2-v3-v4.md) | 3 phiên bản v2, v3, v4: bên ghi, luồng, cải tiến, chất lượng, trạng thái. Ánh xạ trường và ID. | Mọi bên |
| 6 | [06-bang-enum.md](06-bang-enum.md) | Mọi giá trị enum của v2 và v3, kèm nghĩa và ví dụ | Mọi bên |
| 7 | [07-gioi-han-va-can-chot.md](07-gioi-han-va-can-chot.md) | Giới hạn, lỗi đã biết, quyết định đã chốt, việc còn lại | Bên Graph, nghiệp vụ |
| 8 | [08-quan-he-4-tang-va-danh-gia.md](08-quan-he-4-tang-va-danh-gia.md) | Dò quan hệ 4 tầng, bộ đánh giá, chỉ số, kết quả từng vòng, các lần chốt luồng (20/10, 22/10, 26–27/10/2026) | Bên dữ liệu, bên Graph |
| 9 | [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md) | Hợp đồng v4 (dữ liệu của luồng chốt): trạng thái index `-v4`, luồng tạo dữ liệu, mọi trường, cách nối cho đồ thị, bất biến để kiểm | Bên Graph, bên tìm kiếm |
| 10 | [10-khoang-trong-du-lieu.md](10-khoang-trong-du-lieu.md) | Thành phần văn bản có mà dữ liệu chưa có: số lượng, ví dụ, thứ tự xử lý, cách đo lại | Bên dữ liệu, nghiệp vụ |
| 11 | [11-cau-hoi-graph.md](11-cau-hoi-graph.md) | Câu hỏi cho bên Graph về phạm vi của cạnh: quan hệ chưa rõ phạm vi, giới hạn trong node (`chi_tiet_vi_tri`), cạnh vào phụ lục không ký hiệu | Bên Graph |
| 12 | [12-logic-xu-ly-cau-hoi-llm-danh-gia.md](12-logic-xu-ly-cau-hoi-llm-danh-gia.md) | Quy tắc tạo từng trường: chuẩn hóa, tách Điều – khoản – điểm – phụ lục, metadata pháp lý và ngày hiệu lực, chunk, quan hệ. 6 câu hỏi gửi LLM (nguyên văn prompt, đầu vào, đầu ra, code kiểm). Bộ đánh giá, chỉ số, quy ước chấm. | Bên dữ liệu, nghiệp vụ |
| 13 | [13-phu-luc.md](13-phu-luc.md) | Phụ lục: dấu hiệu nhận ra, cách cắt, LLM kiểm bố cục, cách lưu ở văn bản và chunk, ba cách đánh số. Phụ lục ở vị trí của quan hệ. Số lượng và độ dài. | Bên dữ liệu, bên Graph |

Đánh giá theo đợt (lấy mẫu, gán nhãn, chấm, số đo mốc) ở [`eval/README.md`](../eval/README.md). Thư mục `eval/` không thuộc luồng chạy.

## Quy tắc viết

Tài liệu áp dụng nguyên tắc ASD-STE100 (Simplified Technical English) cho tiếng Việt:

1. Một câu nêu một ý. Câu mô tả tối đa 25 từ. Câu hướng dẫn tối đa 20 từ.
2. Câu hướng dẫn dùng thể mệnh lệnh. Ví dụ: "Chạy `check`."
3. Dùng thể chủ động. Nêu rõ ai làm. Ví dụ: "Công cụ ghi …", không viết "… được ghi".
4. Một thuật ngữ có một nghĩa. Chỉ dùng thuật ngữ ở bảng dưới. Không dùng từ đồng nghĩa.
5. Một đoạn tối đa 6 câu. Dùng bảng hoặc danh sách khi có nhiều mục.
6. Tên trường, giá trị, lệnh và đường dẫn viết trong `code`.
7. Ví dụ là bản ghi thật. Ví dụ ghi ID bản ghi.
8. Mọi số liệu ghi ngày đo.

## Thuật ngữ

| Thuật ngữ | Nghĩa |
| --- | --- |
| ES nguồn | Cụm Elasticsearch `10.1.10.10`. Chứa dữ liệu v2. Công cụ chỉ đọc cụm này. |
| ES đích | Cụm Elasticsearch `10.1.10.23`. Chứa 3 index v3 và 3 index `-v4`. Một lượt chạy chỉ ghi 3 index cấu hình (`TARGET_*_INDEX`). |
| Văn bản | Một bản ghi của `legal-docs` (v2), `legal-docs-v3` (v3) hoặc `legal-docs-v4` (v4). |
| Chunk | Một bản ghi của `legal-chunk-section-v2`, `-v3` hoặc `-v4`. Chunk là đơn vị tìm kiếm. |
| Quan hệ | Một bản ghi của `legal-changed-v2`, `-v3` hoặc `-v4`. Quan hệ là một tác động của văn bản này lên văn bản khác. |
| Văn bản nguồn | Văn bản thực hiện tác động. Trường `source_id`. |
| Văn bản đích | Văn bản chịu tác động. Trường `target_matched_id`. |
| Đơn vị nguồn | Phần của văn bản nguồn chứa câu tác động. Trường `source_path`. |
| Vị trí | Chuỗi chỉ một phần của văn bản đích. Trường `vi_tri`. Định dạng ở [09, mục 9.5](09-hop-dong-du-lieu-v4.md#95-vị-trí). Dữ liệu v3 hiện có ở [04, mục 4.3](04-hop-dong-du-lieu-v3.md#43-vị-trí). |
| Ứng viên | Quan hệ do quy tắc tìm ra, chưa qua QA. |
| Chế độ `rules` | Cách dò quan hệ của v3: regex tìm ứng viên, LLM kiểm (QA). |
| Chế độ `llm` | Cách dò quan hệ của hợp đồng v4: luồng 4 tầng. Mặc định từ 20/10/2026. |
| Luồng 4 tầng | Tầng 1 cấu trúc, tầng 2 LLM trích, tầng 3 code phân giải, tầng 4 code kiểm. Chi tiết ở [08](08-quan-he-4-tang-va-danh-gia.md). |
| Nhánh quy tắc | Regex và QA của chế độ `rules`. Nhánh này vẫn chạy trong chế độ `llm` để gộp. |
| Nhánh LLM | Tầng 2, 3, 4 của luồng 4 tầng. Chỉ có ở chế độ `llm`. |
| Hợp đồng v4 | Dữ liệu mà luồng chốt ghi. Mô tả ở [09](09-hop-dong-du-lieu-v4.md). |
| Index `-v4` | 3 index bản thử trên ES đích. Bên dữ liệu ghi các index này bằng luồng chốt trước khi ghi lại v3. Trạng thái ở [09, mục 9.1](09-hop-dong-du-lieu-v4.md#91-trạng-thái-v4). |
| Nhãn chuẩn | Quan hệ và metadata đúng, do agent LLM (Claude) gán theo `eval/rubric-gold.md`. Agent đọc toàn văn và không thấy kết quả của công cụ. Ngày 27/10/2026 chưa có bộ nhãn nào qua người duyệt. Nhãn hold-out 300 chờ duyệt ở `bernmark/ho300/duyet_ho300.csv`. |
| Hold-out | Bộ văn bản mới, nhãn khóa bằng hash trước khi chạy công cụ. Chỉ chấm một lần. Không xem lỗi để sửa. |
| Đợt | Một lần thêm 10.000 văn bản mới vào index `-v4`. Mỗi đợt có mẫu 1.000 văn bản để chấm ([`eval/README.md`](../eval/README.md)). |
| Chạy lại chặt | Lần chạy lại chỉ dùng câu trả lời model đã lưu, không gọi model (`LLM_REPLAY=strict`, `eval.replay`). Câu trả lời thiếu thì văn bản lỗi (`replay_misses`). Mức thay đổi đo được chỉ do code. |
| Ghi chú lịch sử | Đoạn kể lại tác động đã có: "… đã được sửa đổi, bổ sung bởi/theo/tại …". Văn bản chỉ có tên trong ghi chú lịch sử không là đích. |
| Quy ước phụ lục | Vị trí ngoài phần thân ghi thành "Phụ lục <n>" hoặc "Phụ lục". Phần thân là điều – khoản – điểm, Chương, "tên văn bản", "tên Mục <n>" (`resolver.body_place`). Phần nêu tên mà phụ lục chứa cũng vậy: danh mục, thủ tục, biểu mẫu, phương án, Mục, Phần, số thứ tự. Chữ gốc của vị trí đã đổi ghi ở `chi_tiet_vi_tri`. Công cụ áp quy ước này (`resolver.appendix_scope`). Bộ chấm áp cùng quy ước cho nhãn và kết quả công cụ (`eval/score.py`). Chi tiết ở [02, mục 2.5.8](02-luong-hoat-dong.md#258-nhánh-llm-4-tầng-và-gộp). |
| QA | Bước model LLM kiểm ứng viên của nhánh quy tắc. Chỉ ứng viên đạt QA thành quan hệ của nhánh này. |
| Lượt | Một lần chạy `convert` có tên (`--run`). Nhật ký nằm ở `work/<run>/`. |
| Server LLM | Server model trả lời theo API kiểu OpenAI, cấu hình bằng `LITELLM_BASE_URL`, `LITELLM_MODEL`. Ngày 27/10/2026: `qwen3.6-35b` chạy SGLang trên máy `dell-ai`. |
| Node | Một đơn vị trong đồ thị: văn bản, Điều, khoản, điểm, phụ lục, đề mục, nội dung. |
| Cạnh | Một liên kết giữa hai node. Một quan hệ có N vị trí cho N cạnh. |
| Bên dữ liệu | Nhóm chạy công cụ và ghi ES đích. |
| Bên Graph | Nhóm dựng đồ thị Neo4j từ ES đích. |
| Nghiệp vụ | Nhóm chuyên môn pháp lý. Nhóm này chốt ý nghĩa pháp lý. |

## Tài liệu cũ

Các tài liệu trước ngày 14/10/2026 nằm ở `archive/tai-lieu-cu/`. Bộ tài liệu này thay thế chúng:

| Tài liệu cũ | Nội dung chuyển sang |
| --- | --- |
| `data-contract-v3.md`, `hop-dong-du-lieu-v3.md` | 04, 06, 07, 09 |
| `lam-ro-quan-he.md` | 04 (mục 4.9), 07 |
| `ticket.md`, `phan-hoi-ticket.md` | 06, 07 |

Thư mục `archive/` không đưa vào git. Xóa thư mục này khi không cần tra lại.
