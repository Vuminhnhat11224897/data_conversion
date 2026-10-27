# Đánh giá theo đợt

Thư mục `eval/` không thuộc luồng chạy. Image Docker chỉ chứa `vbpl_v3/` và `requirements.txt` (xem `Dockerfile`, `.dockerignore`).
Code ở đây chỉ đọc kết quả của luồng (`work/<lượt>/`) và nguồn ES.

Quy tắc: cứ mỗi đợt 10.000 văn bản mới chạy qua luồng, lấy mẫu 1.000 văn bản để gán nhãn và chấm.

## Các bước cho một đợt

1. Chạy luồng cho đợt, lưu cả kết quả để chấm:

   ```bash
   python -m vbpl_v3 convert --run <luot> --ids <ids.txt>          # ghi index
   python -m vbpl_v3 convert --run <luot> --ids <ids.txt> --dry-run  # hoặc chỉ ghi work/<luot>/dry-run
   ```

   Chấm cần `work/<luot>/dry-run/<id>.json`. Nếu lượt ghi thẳng index, chạy lại chặt để có dry-run, không gọi lại model:
   `python -m eval.replay <luot> <luot>-dry <ids.txt>`.

2. Lấy mẫu 1.000 văn bản, phân tầng theo độ dài và kết quả của lượt:

   ```bash
   python -m eval.sample_batch <bo> --run <luot> --size 1000
   ```

   Ra `eval/sets/<bo>.txt`, `eval/sets/<bo>.strata.json` và ghi vào `eval/sets/manifest.json`. Văn bản và nhóm văn bản đã có nhãn
   không bao giờ được lấy lại.

3. Tạo gói gán nhãn:

   ```bash
   python -m eval.packets <bo> <luot-dry> --batch-chars 150000 --full-text-limit 200000
   ```

4. Gán nhãn theo `eval/rubric-gold.md`, không xem kết quả công cụ. Người duyệt các dòng mà nhãn và công cụ lệch nhau. Khóa nhãn trước
   khi chấm: `eval/gold/<bo>/*.json` và `eval/gold/<bo>.lock.json`. Không sửa nhãn sau khi khóa.

5. Chấm:

   ```bash
   python -m eval.strata <bo> <luot-dry> --json work/<bo>-ket-qua.json
   ```

   Ra P/R phát hiện và phạm vi của từng tầng, ước tính cho cả đợt (trọng số N/n) và khoảng tin cậy 95%.

## Quy ước chấm (26/10/2026)

- **Phụ lục:** vị trí không theo điều – khoản – điểm (phần nêu bằng tên, Phần/Mục của phương án hay thông tư cũ, dòng danh mục,
  "Mục II Phần B Phụ lục I") được tính là phụ lục chứa nó: "Phụ lục II" khi chữ nêu số, "Phụ lục" khi không. Áp như nhau cho nhãn và
  công cụ (`score.place`).
- **Cặp sửa đổi, bổ sung:** "Sửa đổi, bổ sung X" cho hai quan hệ. Công cụ ghi thừa một vế của cặp mà vế kia đúng thì vế thừa không
  tính là sai (`score.extra_halves`).

## Bộ đo khác

- 6 bộ cũ (dev, H2, H3, H4, blind, review50): `python -m eval.round <ten> --without b2` đo một thay đổi code trên các bộ đã dùng để
  sửa; chỉ cho biết có làm hỏng gì không.
- Bộ dùng để sửa không còn độc lập. Số đo chất lượng lấy từ bộ của đợt mới, chưa ai xem để sửa.
