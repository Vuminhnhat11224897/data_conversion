# vbpl_v3: chuyển kho VBPL sang v3

Công cụ độc lập chuyển kho văn bản pháp luật từ v2 sang v3:

1. Đọc 3 index v2 trên ES nguồn (chỉ đọc).
2. Dựng lại Điều, khoản, điểm, phụ lục, chunk, quan hệ và metadata pháp lý bằng parser quy tắc. Model LLM chỉ xử lý ca quy tắc không chắc.
3. Ghi 3 index `*-v3` trên ES đích.

Công cụ không dùng và không sửa luồng realtime.

## Cấu trúc thư mục

```
data_vbpl_v3/
├── README.md            tài liệu này
├── docs/                kiến trúc, luồng, hợp đồng dữ liệu v2 và v3, bảng enum
├── vbpl_v3/             code (python -m vbpl_v3)
│   └── mappings/        settings + mapping 3 index v3
├── tests/               unittest, không gọi dịch vụ ngoài
├── eval/                bộ chấm, rubric, danh sách bộ và nhãn đã khóa (không cần cho luồng sản phẩm)
├── .env.example         mẫu cấu hình
├── requirements.txt
├── Dockerfile
├── work/                nhật ký và cache từng lượt (tự tạo, không đưa vào git)
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
.venv/bin/python -m vbpl_v3 convert --run thu --sample 20 --dry-run
```

Docker:

```bash
docker build -t vbpl-v3 .
docker run --rm --env-file .env -v "$PWD/work:/app/work" vbpl-v3 check
```

## Ghi thử vào v4

Khi đổi quy tắc, ghi thử vào 3 index `-v4` trước. Sau khi duyệt, xóa v4 và ghi lại v3. Các bước ở [docs/02-luong-hoat-dong.md](docs/02-luong-hoat-dong.md#ghi-thử-vào-v4-trước-khi-ghi-lại-v3).

```bash
export TARGET_DOCUMENT_INDEX=legal-docs-v4 TARGET_CHUNK_INDEX=legal-chunk-section-v4 TARGET_CHANGE_INDEX=legal-changed-v4
.venv/bin/python -m vbpl_v3 init
.venv/bin/python -m vbpl_v3 convert --run v4-pilot --ids work/v4-ids.txt
```

## Tài liệu

| Tài liệu | Nội dung |
| --- | --- |
| [docs/README.md](docs/README.md) | Mục lục, quy tắc viết, thuật ngữ |
| [docs/01-kien-truc.md](docs/01-kien-truc.md) | Thành phần, an toàn dữ liệu, cấu hình, lưu trữ |
| [docs/02-luong-hoat-dong.md](docs/02-luong-hoat-dong.md) | Quy trình chạy, lệnh, luồng một văn bản, kiểm tra |
| [docs/03-hop-dong-du-lieu-v2.md](docs/03-hop-dong-du-lieu-v2.md) | Dữ liệu nguồn v2 |
| [docs/04-hop-dong-du-lieu-v3.md](docs/04-hop-dong-du-lieu-v3.md) | Dữ liệu v3 đang có, lỗi đã biết, cách nối cho đồ thị |
| [docs/05-thay-doi-v2-v3.md](docs/05-thay-doi-v2-v3.md) | Ánh xạ v2 → v3 |
| [docs/06-bang-enum.md](docs/06-bang-enum.md) | Bảng enum |
| [docs/07-gioi-han-va-can-chot.md](docs/07-gioi-han-va-can-chot.md) | Lỗi đã biết, quyết định đã chốt |

## Dữ liệu nhạy cảm

- `.env` chứa `LITELLM_API_KEY`. Không đưa vào git, không đưa vào image.
- `work/` chứa toàn văn gửi model và câu trả lời model (`llm_response.json`). Không đưa vào git, không đưa vào image.
- Chỉ `.env.example` (không có giá trị bí mật) được đưa vào git.
