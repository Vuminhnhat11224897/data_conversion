# Báo cáo chuyển v2 → v4 qua Telegram

Bot theo dõi luồng chạy liên tục `python -m vbpl_v3 auto` và gửi báo cáo tiếng Việt mỗi 30 phút (mốc 00/30).
Bot chỉ đọc: `work/auto/` (nhật ký lô, hàng đợi, văn bản đã loại), thư mục từng lô `work/auto-*/` và số bản ghi của 3 index đích.

Báo cáo gồm:

- Trạng thái: đang chạy; hàng đợi trống; hoặc cảnh báo khi hàng đợi còn mà `auto` không ghi gì quá `BOT_STALE_MINUTES` phút.
- Trong khung: văn bản ghi `-v4`, chunk, quan hệ (tỉ lệ nối được đích), văn bản bị bỏ qua, văn bản lỗi,
  văn bản phải bóc lại metadata (`metadata_fill`), cảnh báo AI, tốc độ.
- Lũy kế: số bản ghi 3 index `-v4`, hàng đợi còn, văn bản đã loại theo lý do, ước tính số ngày còn lại theo tốc độ 24 giờ qua,
  lần quét v2 gần nhất.
- Phân loại lỗi trong khung (4 loại nhiều nhất) và cảnh báo lỗi hàng loạt (dịch vụ trục trặc).

Văn bản của một lô được tính vào khung có giờ lô kết thúc. Khung bị lỡ (bot dừng, chưa có token) được gộp vào một báo cáo.
Tin dài được chia nhiều phần; tiến độ gửi lưu ở `BOT_STATE_DIR`, khởi động lại không gửi lặp phần đã gửi.

Điền `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` vào `bot/.env` (đã tạo sẵn từ `bot/.env.example`, không đưa vào git).
Mở chat với bot Telegram và nhấn Start trước. Bot đọc lại `bot/.env` mỗi vòng: điền xong không cần khởi động lại.
Chưa có token thì bot chờ; `auto` vẫn chạy bình thường.

Chạy bằng image `vbpl-v3` (bot không nằm trong image, gắn vào chỉ đọc). Container không mở cổng nào:

```bash
cd /data/data_conversion
mkdir -p work/bot-state
docker run -d --name vbpl-bot --restart unless-stopped --network host --user "$(id -u):$(id -g)" --env-file .env \
  -e BOT_STATE_DIR=/app/state -v "$PWD/bot:/app/bot:ro" -v "$PWD/work:/app/work:ro" -v "$PWD/work/bot-state:/app/state" \
  --entrypoint python vbpl-v3 /app/bot/main.py
docker logs --tail 30 vbpl-bot
# Xem báo cáo của khung vừa xong mà không gửi Telegram:
docker run --rm --network host --env-file .env -v "$PWD/bot:/app/bot:ro" -v "$PWD/work:/app/work:ro" \
  --entrypoint python vbpl-v3 /app/bot/main.py --preview
```

Kiểm thử: `python -m unittest bot.test_bot -v`.
