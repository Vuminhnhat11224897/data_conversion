# Đánh giá theo đợt

Thư mục `eval/` không thuộc luồng chạy. Image Docker chỉ chứa `vbpl_v3/` và `requirements.txt` (xem `Dockerfile`, `.dockerignore`).
Code ở đây đọc kết quả của luồng (`work/<lượt>/`), ES nguồn và ES đích. Code không ghi ES.

Quy tắc (26–27/10/2026): mỗi **đợt** 10.000 văn bản mới chạy qua luồng thì lấy mẫu 1.000 văn bản để gán nhãn và chấm.
Đợt 20.000 ngày 28/10/2026 lấy mẫu 2.000 văn bản, cùng tỉ lệ (mục "Đợt 20.000" ở dưới).

Code chạy hiện hành (28/10/2026): master `1117e63`. Bộ chấm hiện hành: `eval/score.py` của commit `3c26438`; commit sau không đổi file này.

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
   - Ngày 28/10/2026, hold-out 300 (`bernmark/ho300/`) vẫn chưa có trong `manifest.json`. Vì vậy lệnh chưa loại nhóm văn bản của hold-out 300.
   - `statistic/` và `toan-kho-1100` (`eval/sets/toan-kho-1100-*`, `eval/gold/toan-kho-1100-*`, `work/toan-kho-1100`) là thống kê toàn kho. Chúng không phải bộ đánh giá, không có trong `manifest.json` và bị `.gitignore`.

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

   - Nhiều bộ nhãn lấy từ một khung thì chấm gộp bằng dấu `+`: `dot-20000-20261028-g300+dot-20000-20261028-r`. Các bộ phải cùng N ở mỗi tầng.
   - File `--json` ghi số đếm đúng / sai / sót của từng tầng. Cộng số đếm của mọi tầng thì ra P/R không trọng số.

## Quy ước chấm (27–28/10/2026)

Bộ chấm chính thức từ ngày 27/10/2026 là `eval/score.py` của commit `8b023ca`. Commit `3c26438` (27/10/2026) thêm ba quy ước R4–R6 (ba dòng cuối của bảng).
Mọi lệnh chấm (`eval.score`, `eval.compare`, `eval.strata`, `eval.round`) dùng các hàm của file này.

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
| Tên và lời dẫn (R6, từ `3c26438`) | Bộ chấm bỏ quan hệ có nguồn "Phần đầu", trừ `hop-nhat`, ở cả nhãn và công cụ. | `score.tool_items`, `score.normalize_gold` |
| Bỏ cụm từ (R4, từ `3c26438`) | Nhãn `bai-bo` có evidence "bỏ cụm từ …" đổi thành `thay-cum-tu`. | `score.normalize_gold` |
| Bổ sung cụm từ (R5, từ `3c26438`) | Bộ chấm bỏ nhãn `bo-sung`, `sua-doi`, `thay-cum-tu` có evidence "bổ sung cụm từ …". | `score.normalize_gold` |

- Quy ước áp như nhau cho nhãn và công cụ, trừ R4 và R5: hai quy ước này chỉ sửa nhãn cũ cho khớp quyết định mới.
- Bộ chấm chưa xử lý R2 (dòng câu dẫn của đơn vị cha).
- Số đo trước ngày 27/10/2026 (docs/08 mục 8.16) dùng quy ước phụ lục rộng hơn: mọi phần nêu tên tính là phụ lục. Không so trực tiếp
  số đó với số dưới đây.
- `appendix_like` đúng khi chữ có: "phụ lục", "danh mục", "thủ tục", "TTHC", "biểu mẫu", "mẫu (số) …", "phương án", "quy trình nội bộ",
  "Mục <số>", "Phần <số hoặc chữ>", "số thứ tự", "STT".

## Đợt 20.000 (28/10/2026): số đo mốc của code `1117e63`

Lượt `v4-next20000` ghi 20.000 văn bản mới vào `-v4` bằng code `1117e63` (docs/08 mục 8.19). Chi tiết chấm ở docs/08 mục 8.20.

**Mẫu.** Lệnh `eval.sample_batch dot-20000-20261028 --run v4-next20000 --size 2000` (seed mặc định 20261026):

- Khung: 12.195 văn bản của lượt, dài tối đa 200.000 ký tự, trừ văn bản và nhóm văn bản của mọi bộ có nhãn.
- 10 tầng như bước 2. Tầng `dai_sua_doi` nhận đúng mức sàn 20 văn bản.
- File: `eval/sets/dot-20000-20261028.txt`, `eval/sets/dot-20000-20261028.strata.json`. 2.000 văn bản đã vào `manifest.json`.
- Chạy lại lệnh này không ra cùng mẫu, vì lệnh loại văn bản đã có trong `manifest.json`.

| Tầng | N | n |
| --- | --- | --- |
| `ngan_khong_quan_he` | 6.579 | 513 |
| `ngan_bai_bo` | 1.789 | 558 |
| `dai_khong_quan_he` | 1.129 | 88 |
| `ngan_kho` | 1.074 | 334 |
| `dai_bai_bo` | 571 | 178 |
| `dai_kho` | 412 | 128 |
| `ngan_sua_doi` | 376 | 117 |
| `dai_khac` | 136 | 42 |
| `ngan_khac` | 71 | 22 |
| `dai_sua_doi` | 58 | 20 |

**Nhãn.** Mẫu chia thành hai bộ. Mỗi bộ có file `.strata.json` riêng, cùng tầng và cùng N với mẫu:

| Bộ | Văn bản | Người gán | Quan hệ nhãn | Khóa (UTC) |
| --- | --- | --- | --- | --- |
| `dot-20000-20261028-g300` | 312, lấy phân tầng từ mẫu 2.000 (seed 20261028) | 10 agent | 1.448 | 28/10/2026 02:08 |
| `dot-20000-20261028-r` | 1.688 văn bản còn lại | 60 agent | 7.689 | 28/10/2026 03:27 |

- Agent gán theo `eval/rubric-gold.md`, không xem kết quả công cụ. Nhãn chuẩn hóa NFC trước khi khóa.
- File khóa `eval/gold/<bộ>.lock.json` ghi mã băm SHA-256 của từng gói nhãn. Không sửa nhãn sau khi khóa.
- **Chưa người duyệt** các dòng lệch giữa nhãn và công cụ (bước 5). Số đo dưới đây là số tạm.

**Chấm lại.** `work/v4-next20000-dry` là lượt chạy lại chặt của 2.000 văn bản (0 lỗi, 0 câu trả lời thiếu, `valid = true`). Lượt gốc `dot20k-base` đã xóa. Chạy:

```bash
python -m eval.strata dot-20000-20261028-g300+dot-20000-20261028-r v4-next20000-dry --json work/dot-20000-20261028-2000-ket-qua.json
python -m eval.strata dot-20000-20261028-g300 v4-next20000-dry --json work/dot-20000-20261028-g300-ket-qua.json
```

Đo một thay đổi code trên mẫu này:

```bash
python -m eval.replay v4-next20000-dry <lượt mới> eval/sets/dot-20000-20261028.txt
python -m eval.compare dot-20000-20261028-g300 v4-next20000-dry <lượt mới>
```

- `eval.compare` nhận một bộ nhãn. Chạy riêng cho `-g300` và `-r`.
- Mẫu đã dùng để tìm lỗi (docs/08 mục 8.20). Sau khi sửa các lỗi đó, mẫu không còn độc lập.

**Kết quả** (28/10/2026; khoảng tin cậy 95%):

| Phép đo | Phát hiện P | Phát hiện R | Phạm vi P | Phạm vi R |
| --- | --- | --- | --- | --- |
| Có trọng số N/n, ước tính cho cả đợt | 0,901 [0,873–0,922] | 0,804 [0,750–0,852] | 0,785 [0,713–0,842] | 0,695 [0,630–0,752] |
| Không trọng số, 2.000 văn bản | 0,900 | 0,819 | 0,785 | 0,702 |

- F1 không trọng số: phát hiện 0,858, phạm vi 0,741.
- Sót phát hiện (860 quan hệ nhãn, không trọng số): 563 công cụ không có đích, 167 có nhưng `unresolved`, 91 đúng đích khác hành động, 39 thuộc văn bản mà công cụ không ra quan hệ nào.
- Kiểm tự động trên 2.000 văn bản: metadata 99,1%; 9.550 quan hệ; `unresolved = true` 3,6%; evidence nguyên văn 99,5%; nối được đích 85%.

**Giới hạn của nhãn:**

- Agent gán không thống nhất R2 (câu dẫn của đơn vị cha) và "bỏ cụm từ".
- Agent ghi `doi_tuong` không đều. Số đo liên quan tới `doi_tuong` chỉ để tham khảo.

## Số đo mốc của code `8b023ca` (27/10/2026)

Code hiện hành `1117e63` chưa đo trên các bộ dưới đây. Số đo độc lập của `1117e63` là đợt 20.000 (mục trên).

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
- Dữ liệu `-v4` ngày 22/10/2026 (code `2911b77`) đo trên H5 + H6 theo bộ chấm cũ: phát hiện P / R 0,890 / 0,873; phạm vi P / R
  0,785 / 0,743 (docs/08 mục 8.14–8.15). Đêm 27/10/2026, `-v4` được ghi lại bằng `1117e63`; còn 7 văn bản là bản 22/10 (docs/08 mục 8.19).
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
