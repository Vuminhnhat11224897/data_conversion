# vbpl_v3: chuyển kho VBPL sang v3

Công cụ độc lập chuyển kho văn bản pháp luật từ v2 sang v3:

1. Đọc 3 index v2 trên ES nguồn (chỉ đọc).
2. Dựng lại Điều, khoản, điểm, phụ lục, chunk và metadata pháp lý bằng parser quy tắc. LLM chỉ trả lời ca quy tắc không chắc, bằng số dòng.
3. Dò quan hệ bằng luồng 4 tầng: LLM trích tác động, code phân giải và kiểm. Nhánh quy tắc chạy song song để gộp.
4. Ghi 3 index `-v4` để thử. Sau khi duyệt, ghi lại 3 index `-v3`.

Công cụ không dùng và không sửa luồng realtime.

| Phiên bản | Bên ghi | Trạng thái (28/10/2026) |
| --- | --- | --- |
| v2 | Luồng realtime | Nguồn, chỉ đọc |
| v3 | `vbpl_v3`, chế độ `rules` (09–13/10/2026) | 236 văn bản (đo 28/10/2026). Không ghi lại toàn bộ. Hai ngoại lệ có người dùng duyệt: văn bản 132140 (15/10/2026) và 32 văn bản của bộ 88 testcase (27/10/2026). Ghi lại toàn bộ v3 cần bên Graph duyệt v4. |
| v4 | `vbpl_v3`, chế độ `llm` (luồng 4 tầng) | Index `-v4` có 30.988 văn bản, ban hành 12/03/2025–30/09/2026 (đo 28/10/2026). Code `1117e63` ghi 30.981 văn bản ngày 27–28/10/2026. 7 văn bản còn bản ghi ngày 22/10/2026 (code `2911b77`). |

- Code chạy hiện hành: commit `1117e63` (27/10/2026). Các commit sau `1117e63` chỉ thêm tài liệu và bộ chấm, không đổi code.
- Lượt gần nhất (đêm 27/10/2026): `v4-next20000` thêm 19.988 văn bản mới, `v4-2710` ghi lại 11.000 văn bản cũ. Còn 17 văn bản lỗi ([docs/02, mục 2.1.2](docs/02-luong-hoat-dong.md#212-quy-trình-một-đợt-chuyển-đổi)).
- Đợt tiếp theo: chưa có lệnh chạy. Người dùng quyết trước có sửa các lỗi tìm thấy khi chấm đợt 20.000 hay không.
- Mỗi 10.000 văn bản mới, bên dữ liệu lấy mẫu 1.000 văn bản để chấm ([eval/README.md](eval/README.md)).
- Chấm đợt 20.000 (28/10/2026): mẫu 2.000 văn bản, nhãn agent chưa qua người duyệt. Ước tính cho cả đợt: phát hiện P 0,901, R 0,804; phạm vi P 0,785, R 0,695. Chi tiết ở [eval/README.md](eval/README.md) và [docs/08, mục 8.20](docs/08-quan-he-4-tang-va-danh-gia.md#820-chấm-đợt-20000-28102026).
- Số liệu toàn `-v4` (28/10/2026): dashboard https://claude.ai/artifact/9sGL8D5ZSGcNLibgQwvMjQ.

Khác biệt và cải tiến của 3 phiên bản: [docs/05-phien-ban-v2-v3-v4.md](docs/05-phien-ban-v2-v3-v4.md).

## Cấu trúc thư mục

```
data_vbpl_v3/
├── README.md            tài liệu này
├── docs/                kiến trúc, luồng, 3 phiên bản, hợp đồng dữ liệu v2, v3, v4, bảng enum, đánh giá
├── vbpl_v3/             code (python -m vbpl_v3)
│   └── mappings/        settings + mapping 3 index (dùng cho -v3 và -v4)
├── tests/               unittest, không gọi dịch vụ ngoài
├── eval/                đánh giá theo đợt: lấy mẫu, chấm, chạy lại chặt (không thuộc luồng, không vào image)
├── .env.example         mẫu cấu hình
├── requirements.txt
├── Dockerfile           image chỉ chứa vbpl_v3/ và thư viện
├── .dockerignore        danh sách cho phép: requirements.txt, vbpl_v3/
├── work/                nhật ký và cache từng lượt (tự tạo, không đưa vào git)
├── bernmark/            kết quả benchmark, cache lượt cũ (không đưa vào git)
├── frontend/            trang đánh giá thủ công -v4, không thuộc luồng (không đưa vào git)
├── statistic/           thống kê toàn kho, không thuộc luồng (không đưa vào git)
└── archive/             tài liệu cũ, dữ liệu mẫu (không đưa vào git)
```

## Bắt đầu nhanh

```bash
cd data_vbpl_v3
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env      # điền .env
.venv/bin/python -m unittest discover -s tests -t .
.venv/bin/python -m vbpl_v3 check
.venv/bin/python -m vbpl_v3 convert --run thu --sample 20 --dry-run   # chế độ llm (mặc định)
```

- `check` kiểm cả dịch vụ embedding. API kiểu OpenAI cần `EMBEDDING_URL` kết thúc bằng `/v1` và `EMBEDDING_KEY` ([docs/01, mục 1.6](docs/01-kien-truc.md#16-cấu-hình-env)).
- Mã nguồn ở GitHub: `origin` = https://github.com/Vuminhnhat11224897/data_conversion. Nhánh cục bộ `master` đẩy lên `origin/main`: `git push origin master:main`.

Docker:

```bash
docker build -t vbpl-v3 .
docker run --rm --env-file .env -v "$PWD/work:/app/work" vbpl-v3 check
```

## Ghi thử vào v4

Khi đổi quy tắc, ghi thử vào 3 index `-v4` trước. Sau khi duyệt, xóa v4 và ghi lại v3. Các bước ở [docs/02-luong-hoat-dong.md](docs/02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3).

Ví dụ hiện hành: hai lượt đêm 27/10/2026, script `work/run-v4-next20000.sh` và `work/run-v4-2710.sh`. Lệnh chính:

```bash
source work/.embedding.env    # EMBEDDING_URL=http://10.1.10.22:9999/v1, EMBEDDING_KEY
export TARGET_DOCUMENT_INDEX=legal-docs-v4 TARGET_CHUNK_INDEX=legal-chunk-section-v4 TARGET_CHANGE_INDEX=legal-changed-v4

# Văn bản mới: không dùng lại vector v2 (cắt 256 token)
export EMBEDDING_REUSE=no LLM_CONCURRENCY_NIGHT=20
.venv/bin/python -m vbpl_v3 init
.venv/bin/python -m vbpl_v3 convert --run v4-next20000 --ids work/v4-next20000-ids.txt --limit 20000 --workers 20
.venv/bin/python -m vbpl_v3 convert --run v4-next20000 --ids work/v4-next20000-ids.txt --limit <số văn bản lỗi> --workers 3

# Ghi lại văn bản đã có trong -v4: dùng lại vector đủ độ dài của -v4
export EMBEDDING_REUSE=target LLM_CONCURRENCY_DAY=2 LLM_CONCURRENCY_NIGHT=8
.venv/bin/python -m vbpl_v3 convert --run v4-2710 --ids work/v4-2210-ids.txt --workers 8
.venv/bin/python -m vbpl_v3 convert --run v4-2710 --workers 3
```

- Trước lần chạy lại văn bản lỗi, đổi tên `failures.jsonl` thành `failures-1.jsonl`. Không dùng `--redo`.
- Lượt ghi lại chép trước `cache/`, `extract/`, `qa/` của lượt cũ (`bernmark/cache/v4-2210`) vào thư mục lượt mới.
- Chạy đợt lớn sau 22h. Server LLM nhận 10 lời gọi cùng lúc ban đêm, 3 ban ngày (`.env.example`). Đêm 27/10/2026, người dùng cho mở 20.
- Chạy một lượt một lúc. ES đích, ES nguồn và máy embedding đều đi qua VPN `tun0` (khoảng 2,5 MB/s, đo 27/10/2026).

## Chạy liên tục v2 → v4 (`auto`, 29/10/2026)

Lệnh `auto` chạy mãi: chuyển văn bản nguồn chưa có ở đích, từng lô nhỏ. Chi tiết trong docstring `vbpl_v3/auto.py`.

- Mỗi `AUTO_RESCAN_HOURS` giờ (24) quét toàn bộ nguồn, lập hàng đợi = nguồn − đích − văn bản đã loại. Văn bản mới từ lần quét trước đứng đầu, rồi theo `issuance_date` mới → cũ.
- Trước mỗi lô tra lại đích theo `_id`: văn bản đã có ở đích không bao giờ chạy lại.
- Số luồng = số lời gọi LLM cùng lúc: `LLM_CONCURRENCY_DAY=1` (6h–22h), `LLM_CONCURRENCY_NIGHT=12` (22h–6h). Lô = 25 văn bản mỗi luồng.
- Văn bản bị bỏ qua (`skipped`) thì loại hẳn; văn bản lỗi xuống cuối hàng đợi, lỗi 3 lần thì loại. Danh sách loại: `work/auto/excluded.json`.
- Trạng thái và nhật ký từng lô: `work/auto/` (`queue.json`, `history.jsonl`). Mỗi lô là một lượt `work/auto-<giờ>/`.
- Chỉ một tiến trình `auto` chạy được một lúc (khóa `work/auto/lock`). Muốn chạy `convert` tay thì dừng `auto` trước.

```bash
docker run --rm --network host --user "$(id -u):$(id -g)" --env-file .env -v "$PWD/work:/app/work" vbpl-v3 auto --scan-only  # chỉ lập hàng đợi
docker run -d --name vbpl-auto --restart unless-stopped --stop-timeout 600 --network host --user "$(id -u):$(id -g)" \
  --env-file .env -v "$PWD/work:/app/work" vbpl-v3 auto
docker logs -f vbpl-auto      # theo dõi
docker stop vbpl-auto         # dừng êm: văn bản đang chạy làm xong, văn bản chưa bắt đầu ở lại hàng đợi
```

## Tài liệu

| Tài liệu | Nội dung |
| --- | --- |
| [docs/README.md](docs/README.md) | Mục lục, trạng thái, quy tắc viết, thuật ngữ |
| [docs/01-kien-truc.md](docs/01-kien-truc.md) | Thành phần, an toàn dữ liệu, cấu hình, embedding, lưu trữ, triển khai, mạng |
| [docs/02-luong-hoat-dong.md](docs/02-luong-hoat-dong.md) | Luồng dữ liệu v4: quy trình một đợt (ví dụ lượt 27/10/2026), lệnh, luồng một văn bản, luồng 4 tầng, làm tiếp, kiểm tra, thời gian |
| [docs/03-hop-dong-du-lieu-v2.md](docs/03-hop-dong-du-lieu-v2.md) | Dữ liệu nguồn v2 |
| [docs/04-hop-dong-du-lieu-v3.md](docs/04-hop-dong-du-lieu-v3.md) | Dữ liệu v3 đang có, lỗi đã biết, cách nối cho đồ thị |
| [docs/05-phien-ban-v2-v3-v4.md](docs/05-phien-ban-v2-v3-v4.md) | 3 phiên bản: luồng, cải tiến, chất lượng, ánh xạ trường |
| [docs/06-bang-enum.md](docs/06-bang-enum.md) | Bảng enum |
| [docs/07-gioi-han-va-can-chot.md](docs/07-gioi-han-va-can-chot.md) | Lỗi đã biết, quyết định đã chốt, việc còn lại |
| [docs/08-quan-he-4-tang-va-danh-gia.md](docs/08-quan-he-4-tang-va-danh-gia.md) | Luồng 4 tầng, bộ đánh giá, kết quả từng vòng, chốt luồng, chấm đợt 20.000 (đến 28/10/2026) |
| [docs/09-hop-dong-du-lieu-v4.md](docs/09-hop-dong-du-lieu-v4.md) | Hợp đồng v4: mọi trường, cách nối cho đồ thị, bất biến để kiểm |
| [docs/10-khoang-trong-du-lieu.md](docs/10-khoang-trong-du-lieu.md) | Khoảng trống dữ liệu, thứ tự xử lý |
| [docs/11-cau-hoi-graph.md](docs/11-cau-hoi-graph.md) | Câu hỏi cho bên Graph: phạm vi của cạnh, phụ lục không ký hiệu |
| [docs/12-logic-xu-ly-cau-hoi-llm-danh-gia.md](docs/12-logic-xu-ly-cau-hoi-llm-danh-gia.md) | Quy tắc tạo từng trường, câu hỏi gửi LLM, bộ đánh giá |
| [docs/13-phu-luc.md](docs/13-phu-luc.md) | Phụ lục: nhận ra, cắt, lưu, đánh số, vị trí của quan hệ |
| [eval/README.md](eval/README.md) | Đánh giá theo đợt: các bước, quy ước chấm, số đo mốc |

## Dữ liệu nhạy cảm

- `.env` chứa `LITELLM_API_KEY`. Không đưa vào git, không đưa vào image.
- `work/` chứa toàn văn gửi model và câu trả lời model (`llm_response.json`). Không đưa vào git, không đưa vào image.
- `bernmark/` chứa cache model của các lượt cũ, cùng loại dữ liệu với `work/`. Không đưa vào git, không đưa vào image.
- `work/.embedding.env` chứa `EMBEDDING_KEY`. File nằm trong `work/`, nên không vào git.
- `frontend/data/` chứa toàn văn chụp từ ES. Không đưa vào git.
- Chỉ `.env.example` (không có giá trị bí mật) được đưa vào git.
