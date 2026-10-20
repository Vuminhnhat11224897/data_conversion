# Tài liệu chuyển đổi VBPL v2 → v3

Thư mục này mô tả công cụ `vbpl_v3` và dữ liệu nó tạo ra. Đọc theo thứ tự dưới đây.

| # | Tài liệu | Nội dung | Người đọc chính |
| --- | --- | --- | --- |
| 1 | [01-kien-truc.md](01-kien-truc.md) | Thành phần, nguyên tắc thiết kế, an toàn dữ liệu, cấu hình, lưu trữ | Bên dữ liệu |
| 2 | [02-luong-hoat-dong.md](02-luong-hoat-dong.md) | Quy trình chạy, luồng một lượt, luồng một văn bản, kiểm tra sau chạy | Bên dữ liệu |
| 3 | [03-hop-dong-du-lieu-v2.md](03-hop-dong-du-lieu-v2.md) | Dữ liệu nguồn v2 (chỉ đọc) và chất lượng đo được | Bên dữ liệu, bên Graph |
| 4 | [04-hop-dong-du-lieu-v3.md](04-hop-dong-du-lieu-v3.md) | Dữ liệu v3 đang có (đo 19/10/2026): trường, quy tắc, lỗi đã biết, cách nối cho đồ thị | Bên Graph, bên tìm kiếm |
| 5 | [05-thay-doi-v2-v3.md](05-thay-doi-v2-v3.md) | Ánh xạ trường và ID từ v2 sang v3 | Bên đọc dữ liệu cũ |
| 6 | [06-bang-enum.md](06-bang-enum.md) | Mọi giá trị enum của v2 và v3, kèm nghĩa và ví dụ | Mọi bên |
| 7 | [07-gioi-han-va-can-chot.md](07-gioi-han-va-can-chot.md) | Giới hạn, lỗi đã biết, quyết định đã chốt ngày 14/10/2026 | Bên Graph, nghiệp vụ |
| 8 | [08-quan-he-4-tang-va-danh-gia.md](08-quan-he-4-tang-va-danh-gia.md) | Dò quan hệ 4 tầng (LLM trích, code phân giải và kiểm), bộ đánh giá Dev/Blind, chỉ số | Bên dữ liệu, bên Graph |
| 9 | [09-hop-dong-du-lieu-v4.md](09-hop-dong-du-lieu-v4.md) | Dữ liệu bản thử v4: trạng thái, khác với v3, mọi trường, cách nối, bất biến để kiểm | Bên Graph, bên tìm kiếm |
| 10 | [10-khoang-trong-du-lieu.md](10-khoang-trong-du-lieu.md) | Thành phần văn bản có mà dữ liệu chưa có: số lượng, ví dụ, thứ tự xử lý, cách đo lại | Bên dữ liệu, nghiệp vụ |

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
| ES đích | Cụm Elasticsearch `10.1.10.23`. Chứa 3 index v3. Công cụ chỉ ghi 3 index này. |
| Văn bản | Một bản ghi của `legal-docs` (v2) hoặc `legal-docs-v3` (v3). |
| Chunk | Một bản ghi của `legal-chunk-section-v2` hoặc `legal-chunk-section-v3`. Chunk là đơn vị tìm kiếm. |
| Quan hệ | Một bản ghi của `legal-changed-v2` hoặc `legal-changed-v3`. Quan hệ là một tác động của văn bản này lên văn bản khác. |
| Văn bản nguồn | Văn bản thực hiện tác động. Trường `source_id`. |
| Văn bản đích | Văn bản chịu tác động. Trường `target_matched_id`. |
| Đơn vị nguồn | Phần của văn bản nguồn chứa câu tác động. Trường `source_path`. |
| Vị trí | Chuỗi chỉ một phần của văn bản đích. Trường `vi_tri`. Định dạng ở [09, mục 9.5](09-hop-dong-du-lieu-v4.md#95-vị-trí). Dữ liệu v3 hiện có ở [04, mục 4.3](04-hop-dong-du-lieu-v3.md#43-vị-trí). |
| Ứng viên | Quan hệ do quy tắc tìm ra, chưa qua QA. |
| QA | Bước model LLM kiểm ứng viên. Chỉ ứng viên đạt QA thành quan hệ. |
| Lượt | Một lần chạy `convert` có tên (`--run`). Nhật ký nằm ở `work/<run>/`. |
| Node | Một đơn vị trong đồ thị: văn bản, Điều, khoản, điểm, phụ lục, đề mục, nội dung. |
| Cạnh | Một liên kết giữa hai node. Một quan hệ có N vị trí cho N cạnh. |
| Bên dữ liệu | Nhóm chạy công cụ và ghi ES đích. |
| Bên Graph | Nhóm dựng đồ thị Neo4j từ ES đích. |
| Nghiệp vụ | Nhóm chuyên môn pháp lý. Nhóm này chốt ý nghĩa pháp lý. |

## Tài liệu cũ

Các tài liệu trước ngày 14/10/2026 nằm ở `archive/tai-lieu-cu/`. Bộ tài liệu này thay thế chúng:

| Tài liệu cũ | Nội dung chuyển sang |
| --- | --- |
| `data-contract-v3.md`, `hop-dong-du-lieu-v3.md` | 04, 06, 07 |
| `lam-ro-quan-he.md` | 04 (mục 4.9), 07 |
| `ticket.md`, `phan-hoi-ticket.md` | 06, 07 |

Thư mục `archive/` không đưa vào git. Xóa thư mục này khi không cần tra lại.
