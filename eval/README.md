# Đánh giá theo đợt

Thư mục `eval/` không thuộc luồng chạy. Image Docker chỉ chứa `vbpl_v3/` và `requirements.txt` (xem `Dockerfile`, `.dockerignore`).
Code ở đây đọc kết quả của luồng (`work/<lượt>/`), ES nguồn và ES đích. Code không ghi ES.

Quy tắc (26–27/10/2026): mỗi **đợt** 10.000 văn bản mới chạy qua luồng thì lấy mẫu 1.000 văn bản để gán nhãn và chấm.

Chạy mọi lệnh trong `data_vbpl_v3/` bằng `.venv/bin/python -m eval.<lệnh>`. Lệnh đọc cấu hình ES từ `.env`.

## Các bước cho một đợt

1. Chạy luồng cho đợt và ghi index ([docs/02, "Ghi thử vào v4"](../docs/02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3)):

   ```bash
   python -m vbpl_v3 convert --run <lượt> --ids <ids.txt> --limit 10000
   python -m eval.check_contract v4
   ```

2. Lấy mẫu 1.000 văn bản, phân tầng theo độ dài và kết quả của lượt:

   ```bash
   python -m eval.sample_batch <bộ> --run <lượt> --size 1000
   ```

   - Lệnh đọc `work/<lượt>/documents.jsonl` và toàn văn ở ES nguồn. Lệnh bỏ văn bản dài hơn `--max-chars` (mặc định 200.000 ký tự) và văn bản bị bỏ qua.
   - Lệnh bỏ mọi văn bản và nhóm văn bản (cơ quan + mẫu tên) đã có trong `eval/sets/manifest.json` hoặc `eval/sets/*.txt`. Mỗi nhóm chỉ lấy một văn bản.
   - Tầng: độ dài (`ngan` ≤ 30.000 ký tự < `dai`) × kết quả của lượt (`khong_quan_he`, `kho`, `sua_doi`, `bai_bo`, `khac`). Tầng không có quan hệ nhận 1/4 phần của mình. Mỗi tầng có ít nhất `--floor` văn bản (mặc định 20).
   - Lệnh ghi `eval/sets/<bộ>.txt`, `eval/sets/<bộ>.strata.json` và thêm văn bản vào `eval/sets/manifest.json`.
   - Ngày 27/10/2026, hold-out 300 (`bernmark/ho300/`) chưa có trong `manifest.json`. Vì vậy lệnh chưa loại nhóm văn bản của hold-out 300.

3. Tạo kết quả để chấm bằng chạy lại chặt. Bộ chấm cần `work/<lượt>-dry/dry-run/<id>.json`:

   ```bash
   python -m eval.replay <lượt> <lượt>-dry eval/sets/<bộ>.txt
   ```

   - Lệnh chép `cache/`, `extract/`, `qa/` của lượt gốc sang lượt mới. Lượt 10.000 văn bản có khoảng 2,6 GB cache (ước theo `v4-2210`, đo 27/10/2026).
   - Lệnh chạy `convert --dry-run --redo` với `LLM_REPLAY=strict`. Lệnh không gọi model.
   - Kết quả ở `work/<lượt>-dry/replay.json`. Lượt hợp lệ khi `valid = true`: 0 văn bản lỗi, 0 `replay_misses`.
   - Code phải giống code của lượt gốc. Nếu không, kết quả chấm là kết quả của code mới.

4. Tạo gói gán nhãn:

   ```bash
   python -m eval.packets <bộ> <lượt>-dry --batch-chars 150000 --full-text-limit 200000
   ```

   Lệnh đọc cache cấu trúc `work/<lượt>-dry/cache/` và ghi `eval/packets/<bộ>/batch-<k>.json`. Gói không chứa kết quả của công cụ.

5. Gán nhãn theo `eval/rubric-gold.md`, không xem kết quả công cụ. Người duyệt các dòng mà nhãn và công cụ lệch nhau. Khóa nhãn trước
   khi chấm: `eval/gold/<bộ>/*.json` và `eval/gold/<bộ>.lock.json`. Không sửa nhãn sau khi khóa.

6. Chấm:

   ```bash
   python -m eval.strata <bộ> <lượt>-dry --json work/<bộ>-ket-qua.json
   ```

   Lệnh ra P/R phát hiện và phạm vi của từng tầng. Lệnh ước tính cho cả đợt bằng trọng số N/n. Khoảng tin cậy 95% lấy từ bootstrap 2.000 lần.

## Quy ước chấm (27/10/2026)

Bộ chấm chính thức từ ngày 27/10/2026 là `eval/score.py` của commit `8b023ca`. Mọi lệnh chấm (`eval.score`, `eval.compare`, `eval.strata`,
`eval.round`) dùng các hàm của file này.

| Quy ước | Cách áp | Hàm |
| --- | --- | --- |
| Phát hiện | Đúng văn bản nguồn, hành động, văn bản đích. | `eval.compare` |
| Phạm vi | Phát hiện, cộng vị trí hoặc phần nêu tên. `toàn bộ` và không có vị trí là một. | `score.place` |
| Quan hệ chờ duyệt | Quan hệ `unresolved` không là cạnh. Bộ chấm không tính quan hệ này. | `compare`, `strata` |
| Phụ lục: vị trí | Vị trí ngoài phần thân tính là phụ lục chứa nó. Bộ chấm dùng cùng phép thử với công cụ: `resolver.body_place`. Phần thân là vị trí có "điểm", "khoản", "Điều", "Chương", và "tên văn bản", "tên Mục <n>". "Mục <n>" đứng một mình là phụ lục. "Phụ lục <n>" khi chữ nêu đúng một số phụ lục; "Phụ lục" khi không nêu số hoặc nêu nhiều số. Bộ chấm bỏ số 0 đầu: "Phụ lục 06" là "Phụ lục 6". | `score.place`, `score.appendix`, `resolver.body_place` |
| Phụ lục: phần nêu tên | Bộ chấm dùng cùng phép thử với công cụ: `resolver.appendix_like`. Đúng thì phần nêu tên tính là phụ lục chứa nó. Sai thì mọi phần nêu tên so như nhau (`#`), chữ không cần khớp. | `score.place` |
| Cặp sửa đổi, bổ sung | "Sửa đổi, bổ sung X" cho hai quan hệ. Công cụ ghi thừa một vế của cặp mà vế kia đúng thì vế thừa không tính là sai. | `score.extra_halves` |
| Văn bản hợp nhất | Nhãn chỉ giữ một quan hệ `hop-nhat`, tới văn bản gốc. | `score.normalize_gold` |
| Dòng bảng | "Phụ lục 2 Mục I STT 01" và "Phụ lục 2 STT 1" là một đơn vị nguồn. | `score.row_path` |

- Quy ước áp như nhau cho nhãn và công cụ.
- Số đo trước ngày 27/10/2026 (docs/08 mục 8.16) dùng quy ước phụ lục rộng hơn: mọi phần nêu tên tính là phụ lục. Không so trực tiếp
  số đó với số dưới đây.
- `appendix_like` đúng khi chữ có: "phụ lục", "danh mục", "thủ tục", "TTHC", "biểu mẫu", "mẫu (số) …", "phương án", "quy trình nội bộ",
  "Mục <số>", "Phần <số hoặc chữ>", "số thứ tự", "STT".

## Số đo mốc của code `8b023ca` (27/10/2026)

Cách đo: chạy lại chặt (`eval.replay`, `LLM_REPLAY=strict`) cùng câu trả lời model đã lưu, lượt `fix9-*`, 0 câu trả lời thiếu. Chấm theo
quy ước ở trên. Hold-out 300 bỏ văn bản 675259 (nhãn sinh bằng script).

| Bộ | Code 26/10 (`fix5-*`), bộ chấm `8ccb1da`: phát hiện F1 / phạm vi F1 | Code `8b023ca` (`fix9-*`): phát hiện P / R / F1 | Code `8b023ca`: phạm vi P / R / F1 |
| --- | --- | --- | --- |
| 7 bộ cũ (dev, H1–H4, blind, review50) | 0,905 / 0,809 | 0,923 / 0,888 / 0,905 | 0,861 / 0,792 / 0,825 |
| H5 + H6 (500 văn bản) | 0,884 / 0,801 | 0,895 / 0,873 / 0,884 | 0,833 / 0,773 / 0,801 |
| Hold-out 300 | 0,876 / 0,683 | 0,900 / 0,861 / 0,880 | 0,711 / 0,673 / 0,691 |
| Stress C4/B8c (57 văn bản + 18 đối chứng) | 0,751 / 0,654 | 0,915 / 0,909 / 0,912 | 0,677 / 0,794 / 0,731 |

- So với code `8ccb1da` (lượt `fix7-*`), chỉ phạm vi của hold-out 300 đổi: P / R / F1 từ 0,710 / 0,672 / 0,690 lên 0,711 / 0,673 / 0,691.

Độ tin của từng bộ:

| Bộ | Độc lập? | Ghi chú |
| --- | --- | --- |
| 7 bộ cũ, H5 + H6 | Không | Đã dùng để sửa lỗi. Chỉ cho biết thay đổi code có làm hỏng gì không. |
| Hold-out 300 | Có | Nhãn do agent gán, **chưa qua người duyệt**. File duyệt: `bernmark/ho300/duyet_ho300.csv` (1.431 dòng). Khi người duyệt xong, chấm lại để có số chính thức. |
| Stress C4/B8c | Một phần | Văn bản 675210 đã dùng để dò lỗi ngày 27/10/2026. |

- Giữa code 26/10 và 27/10, phát hiện ở 7 bộ cũ và H5 + H6 không đổi.
- Luật ghi chú lịch sử 27/10 (`8ccb1da`) bỏ 101 quan hệ, không thêm quan hệ nào. 101 quan hệ nằm ở 10 văn bản: 8 văn bản của bộ stress và 2 văn bản
  của hold-out 300 (658530, 687890). Recall của mọi bộ không đổi.
- Lượt `fix9-ho` (cũng như `fix7-ho`) gồm hold-out 300 và bộ stress (375 văn bản).
- Dữ liệu `-v4` hiện có (code `2911b77`) đo trên H5 + H6 ngày 22/10/2026 theo bộ chấm cũ: phát hiện P / R 0,890 / 0,873; phạm vi P / R
  0,785 / 0,743 (docs/08 mục 8.14–8.15).
- Script chấm của các lượt `fix*`: `bernmark/fix3/score_phuluc.py` (dùng `eval/score.py`). Bảng đầy đủ của `fix7-*`: `bernmark/fix3/ket_qua_fix7.txt`.

## Đo một thay đổi code trên các bộ cũ

`eval.round` chạy lại chặt 6 bộ cũ (dev, H2, H3, H4, blind, review50) bằng code hiện tại. Lệnh so kết quả với lượt gốc A của từng bộ:

```bash
python -m eval.round <tên> --from D             # dùng câu trả lời đã lưu của các lượt D-<bộ>, không gọi model
python -m eval.round <tên> --from D --allow-new # cho gọi model khi đầu vào của model đổi; chạy từng bộ một
python -m eval.round <tên> --sets dev,h2        # chỉ một số bộ
```

- Các lượt `D-<bộ>` chứa câu trả lời cho đầu vào hiện tại, kể cả B2 (docs/08 mục 8.11.3, quy tắc 10). Ngày 27/10/2026, lượt `fix9-*` chạy lại chặt từ `D-*` với 0 câu trả lời thiếu.
- Lệnh báo "KHÔNG HỢP LỆ" và trả mã lỗi khi một bộ có văn bản lỗi hoặc câu trả lời thiếu.
- Bộ H1, H5 + H6 và hold-out 300 không có trong `eval.round`. Chạy lại chặt bằng `eval.replay` với lượt gốc `E-h1`, `H56-C`, `ho-A3`.
- Bộ dùng để sửa không còn độc lập. Số đo chất lượng lấy từ bộ của đợt mới, chưa ai xem để sửa.
