# vbpl_v3: chuyển kho VBPL sang v3

Công cụ độc lập chuyển kho văn bản pháp luật từ v2 sang v3:

1. Đọc 3 index v2 trên ES nguồn (chỉ đọc).
2. Dựng lại Điều, khoản, điểm, phụ lục, chunk và metadata pháp lý bằng parser quy tắc. LLM chỉ trả lời ca quy tắc không chắc, bằng số dòng.
3. Dò quan hệ bằng luồng 4 tầng: LLM trích tác động, code phân giải và kiểm. Nhánh quy tắc chạy song song để gộp.
4. Ghi 3 index `-v4` để thử. Sau khi duyệt, ghi lại 3 index `-v3`.

Công cụ không dùng và không sửa luồng realtime.

| Phiên bản | Bên ghi | Trạng thái (20/10/2026) |
| --- | --- | --- |
| v2 | Luồng realtime | Nguồn, chỉ đọc |
| v3 | `vbpl_v3`, chế độ `rules` (09–13/10/2026) | 204 văn bản. Chờ ghi lại theo hợp đồng v4. |
| v4 | `vbpl_v3`, chế độ `llm` (luồng chốt 20/10/2026) | Index `-v4` là bản thử ngày 14/10. Ghi lại bằng luồng chốt cần duyệt. |

Khác biệt và cải tiến của 3 phiên bản: [docs/05-phien-ban-v2-v3-v4.md](docs/05-phien-ban-v2-v3-v4.md).

## Cấu trúc thư mục

```
data_vbpl_v3/
├── README.md            tài liệu này
├── docs/                kiến trúc, luồng, 3 phiên bản, hợp đồng dữ liệu v2, v3, v4, bảng enum, đánh giá
├── vbpl_v3/             code (python -m vbpl_v3)
│   └── mappings/        settings + mapping 3 index (dùng cho -v3 và -v4)
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
.venv/bin/python -m vbpl_v3 convert --run thu --sample 20 --dry-run   # chế độ llm (mặc định)
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
| [docs/05-phien-ban-v2-v3-v4.md](docs/05-phien-ban-v2-v3-v4.md) | 3 phiên bản: luồng, cải tiến, chất lượng, ánh xạ trường |
| [docs/06-bang-enum.md](docs/06-bang-enum.md) | Bảng enum |
| [docs/07-gioi-han-va-can-chot.md](docs/07-gioi-han-va-can-chot.md) | Lỗi đã biết, quyết định đã chốt, việc còn lại |
| [docs/08-quan-he-4-tang-va-danh-gia.md](docs/08-quan-he-4-tang-va-danh-gia.md) | Luồng 4 tầng, bộ đánh giá, kết quả, chốt luồng |
| [docs/09-hop-dong-du-lieu-v4.md](docs/09-hop-dong-du-lieu-v4.md) | Hợp đồng v4: dữ liệu của luồng chốt |
| [docs/10-khoang-trong-du-lieu.md](docs/10-khoang-trong-du-lieu.md) | Khoảng trống dữ liệu, thứ tự xử lý |

## Dữ liệu nhạy cảm

- `.env` chứa `LITELLM_API_KEY`. Không đưa vào git, không đưa vào image.
- `work/` chứa toàn văn gửi model và câu trả lời model (`llm_response.json`). Không đưa vào git, không đưa vào image.
- Chỉ `.env.example` (không có giá trị bí mật) được đưa vào git.
