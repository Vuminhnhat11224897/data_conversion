# vbpl_v3: chuyển kho VBPL sang v3

Công cụ độc lập chuyển kho văn bản pháp luật từ v2 sang v3:

1. Đọc 3 index v2 trên ES nguồn (chỉ đọc).
2. Dựng lại Điều, khoản, điểm, phụ lục, chunk và metadata pháp lý bằng parser quy tắc. LLM chỉ trả lời ca quy tắc không chắc, bằng số dòng.
3. Dò quan hệ bằng luồng 4 tầng: LLM trích tác động, code phân giải và kiểm. Nhánh quy tắc chạy song song để gộp.
4. Ghi 3 index `-v4` để thử. Sau khi duyệt, ghi lại 3 index `-v3`.

Công cụ không dùng và không sửa luồng realtime.

| Phiên bản | Bên ghi | Trạng thái (27/10/2026) |
| --- | --- | --- |
| v2 | Luồng realtime | Nguồn, chỉ đọc |
| v3 | `vbpl_v3`, chế độ `rules` (09–13/10/2026) | 204 văn bản (đo 19/10/2026), không đổi. Ghi lại v3 theo hợp đồng v4 cần bên Graph duyệt v4. |
| v4 | `vbpl_v3`, chế độ `llm` (luồng 4 tầng) | Index `-v4` có 11.000 văn bản, ban hành 08/10/2025–30/09/2026. Ghi lại ngày 22/10/2026 bằng code `2911b77`. |

- Code chốt hiện tại: commit `8b023ca` (27/10/2026). Các thay đổi sau `2911b77` chỉ ở bước sau LLM. Dữ liệu `-v4` chưa có các thay đổi này.
- Đợt tiếp theo: 10.000 văn bản ở `work/v4-next10000b-ids.txt`. Chưa chạy, chờ người dùng quyết.
- Mỗi đợt 10.000 văn bản mới, bên dữ liệu lấy mẫu 1.000 văn bản để chấm ([eval/README.md](eval/README.md)).

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

Docker:

```bash
docker build -t vbpl-v3 .
docker run --rm --env-file .env -v "$PWD/work:/app/work" vbpl-v3 check
```

## Ghi thử vào v4

Khi đổi quy tắc, ghi thử vào 3 index `-v4` trước. Sau khi duyệt, xóa v4 và ghi lại v3. Các bước ở [docs/02-luong-hoat-dong.md](docs/02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3).

Lệnh cho đợt tiếp theo (chưa chạy). Tên lượt `v4-next10000b` là ví dụ:

```bash
export TARGET_DOCUMENT_INDEX=legal-docs-v4 TARGET_CHUNK_INDEX=legal-chunk-section-v4 TARGET_CHANGE_INDEX=legal-changed-v4
.venv/bin/python -m vbpl_v3 init
.venv/bin/python -m vbpl_v3 convert --run v4-next10000b --ids work/v4-next10000b-ids.txt --limit 10000 --workers 10
.venv/bin/python -m vbpl_v3 convert --run v4-next10000b --limit <số văn bản lỗi> --workers 3   # chạy lại văn bản lỗi, không --redo
.venv/bin/python -m eval.check_contract v4
```

- Danh sách có 10.200 ID: 10.000 ID chính, 200 ID dự phòng ở cuối.
- Chạy đợt lớn sau 22h: server LLM nhận 10 lời gọi cùng lúc ban đêm, 3 ban ngày.

## Tài liệu

| Tài liệu | Nội dung |
| --- | --- |
| [docs/README.md](docs/README.md) | Mục lục, trạng thái, quy tắc viết, thuật ngữ |
| [docs/01-kien-truc.md](docs/01-kien-truc.md) | Thành phần, an toàn dữ liệu, cấu hình, lưu trữ, triển khai, mạng |
| [docs/02-luong-hoat-dong.md](docs/02-luong-hoat-dong.md) | Luồng dữ liệu v4: quy trình một đợt, lệnh, luồng một văn bản, luồng 4 tầng, làm tiếp, kiểm tra, thời gian |
| [docs/03-hop-dong-du-lieu-v2.md](docs/03-hop-dong-du-lieu-v2.md) | Dữ liệu nguồn v2 |
| [docs/04-hop-dong-du-lieu-v3.md](docs/04-hop-dong-du-lieu-v3.md) | Dữ liệu v3 đang có, lỗi đã biết, cách nối cho đồ thị |
| [docs/05-phien-ban-v2-v3-v4.md](docs/05-phien-ban-v2-v3-v4.md) | 3 phiên bản: luồng, cải tiến, chất lượng, ánh xạ trường |
| [docs/06-bang-enum.md](docs/06-bang-enum.md) | Bảng enum |
| [docs/07-gioi-han-va-can-chot.md](docs/07-gioi-han-va-can-chot.md) | Lỗi đã biết, quyết định đã chốt, việc còn lại |
| [docs/08-quan-he-4-tang-va-danh-gia.md](docs/08-quan-he-4-tang-va-danh-gia.md) | Luồng 4 tầng, bộ đánh giá, kết quả từng vòng, chốt luồng (đến 27/10/2026) |
| [docs/09-hop-dong-du-lieu-v4.md](docs/09-hop-dong-du-lieu-v4.md) | Hợp đồng v4: mọi trường, cách nối cho đồ thị, bất biến để kiểm |
| [docs/10-khoang-trong-du-lieu.md](docs/10-khoang-trong-du-lieu.md) | Khoảng trống dữ liệu, thứ tự xử lý |
| [docs/11-cau-hoi-graph.md](docs/11-cau-hoi-graph.md) | Câu hỏi cho bên Graph: phạm vi của cạnh, phụ lục không ký hiệu |
| [eval/README.md](eval/README.md) | Đánh giá theo đợt: các bước, quy ước chấm, số đo mốc |

## Dữ liệu nhạy cảm

- `.env` chứa `LITELLM_API_KEY`. Không đưa vào git, không đưa vào image.
- `work/` chứa toàn văn gửi model và câu trả lời model (`llm_response.json`). Không đưa vào git, không đưa vào image.
- `bernmark/` chứa cache model của các lượt cũ, cùng loại dữ liệu với `work/`. Không đưa vào git, không đưa vào image.
- Chỉ `.env.example` (không có giá trị bí mật) được đưa vào git.
