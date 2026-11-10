# Theo dõi 3 worker ban ngày

Ngày 09/11/2026, người dùng yêu cầu tăng riêng `vbpl-auto` lên 3 worker ban ngày, bắt đầu theo dõi và tránh ảnh hưởng các dịch vụ dùng chung. `.env` và môi trường container đã được đổi; image, volume `work`, 8 CPU/8 GiB RAM và 12 worker ban đêm được giữ nguyên. Không thay đổi cấu hình hoặc khởi động lại các container khác.

Lịch theo giờ Việt Nam: 06h–22h có 3 worker, mỗi lô tối đa 75 văn bản; 22h–06h có 12 worker như trước. Số worker ban ngày có thể được hạ về 1 bởi bộ theo dõi, không tự tăng lại.

## Bộ theo dõi

User service `vbpl-daytime-guard.service` chạy `ops/daytime_guard.py --monitor`, tự chạy lại nếu tiến trình theo dõi lỗi và tự khởi động cùng user manager. Tài khoản đã bật linger. Giới hạn riêng của bộ theo dõi: 0,05 CPU, 128 MiB RAM, ưu tiên CPU/I/O thấp. Mỗi 30 giây chỉ đọc HAProxy stats, ES node stats, embedding metrics và trạng thái/tài nguyên container `vbpl-auto`. Không gửi tin nhắn hoặc restart dịch vụ khác.

Trạng thái nằm trong `work/daytime-worker-control/`:

- `status.json`: giờ kiểm tra, số worker đã cấu hình, hàng đợi, lỗi dịch vụ và hành động hiện tại.
- `metrics.jsonl`, `metrics.previous.jsonl`: mẫu đo, xoay file khi quá 8 MiB.
- `backoff.json`: lý do hạ worker, nếu đã có; không đồng nghĩa luồng này gây ra lỗi của dịch vụ chung.
- `last-switch.json`, `switch-*/`: thời điểm chuyển, bản sao container và `.env` để phục hồi. Thư mục chứa bí mật, quyền 700; bản sao cấu hình quyền 600, không đưa vào git.

## Điều kiện hạ tải

Chỉ tự hạ khi ban ngày, bộ theo dõi đã được bật (`policy.json: armed=true`), `vbpl-auto` đang chạy và được cấu hình 3 worker ban ngày:

- Có thêm lỗi 5xx ở các backend LLM hoặc request ES bị từ chối: bắt đầu hạ tải ngay trong lần kiểm tra phát hiện.
- Một điều kiện kéo dài ít nhất 90 giây: hàng đợi LLM >4, độ trễ trung bình trượt HAProxy của một backend >15 giây, backend LLM mất kết nối, hàng đợi đọc/ghi ES >16, heap ES ≥92%, hàng đợi embedding >4, container dùng >6 GiB RAM, máy chủ còn <32 GiB RAM khả dụng, hoặc không đọc được probe dịch vụ.

Hạ tải bằng cách gửi SIGTERM cho **chỉ `vbpl-auto`**, đợi văn bản đang chạy kết thúc và tạo lại **chỉ container này** với `LLM_CONCURRENCY_DAY=1`; đồng thời cập nhật `.env`. Không ép SIGKILL. Image, giới hạn tài nguyên, volume, các biến môi trường khác và lịch 12 worker ban đêm được bảo toàn. Nếu tạo container mới lỗi, phục hồi container và `.env` trước thao tác. Không tự khởi động container đã bị người dùng dừng tay, và không tự giảm lịch ban đêm.

GPU của LLM là tài nguyên dùng chung và đã từng có OOM trước khi nâng worker. Bộ theo dõi dùng lỗi thực tế và hàng đợi làm tín hiệu giảm tải, không dùng riêng tỷ lệ VRAM đã cấp phát để kết luận. Cơ chế này giảm rủi ro nhưng không bảo đảm tuyệt đối không tác động đến request khác; phát hiện có độ trễ tối đa khoảng một chu kỳ kiểm tra, sau đó cần đợi các văn bản đang chạy dừng êm.

## Xem trạng thái

```bash
systemctl --user status vbpl-daytime-guard.service
journalctl --user -u vbpl-daytime-guard.service --since '30 minutes ago'
cat work/daytime-worker-control/status.json
python3 ops/daytime_guard.py --check    # chỉ đọc, không đổi worker
python3 -m unittest tests.test_daytime_guard -v
```

Không chạy `--switch 3` để tự tăng lại sau một sự cố nếu chưa xem nguyên nhân trong `backoff.json`. Service chỉ quản lý `vbpl-auto`; tên container đích được cố định trong mã.

## Cài lại bộ theo dõi từ Git

File service và policy trong thư mục này khớp cấu hình đang triển khai. Từ thư mục repo, sau khi điền .env và khởi động vbpl-auto:

```bash
mkdir -p work/daytime-worker-control ~/.config/systemd/user
install -m 600 ops/daytime-guard-policy.json work/daytime-worker-control/policy.json
install -m 644 ops/vbpl-daytime-guard.service ~/.config/systemd/user/vbpl-daytime-guard.service
systemctl --user daemon-reload
systemctl --user enable --now vbpl-daytime-guard.service
```

Service dùng đường dẫn /data/data_conversion; chỉnh WorkingDirectory và ExecStart nếu triển khai ở nơi khác. Policy bật giám sát 3 worker ngày, dự phòng 1 worker ngày và giữ 12 worker đêm. Không sao chép đè policy của một lượt đang vận hành nếu chưa chủ động muốn bật lại giám sát.

Sau khi xem nguyên nhân hạ tải, lệnh nâng lại theo yêu cầu người vận hành là `python3 ops/daytime_guard.py --switch 3`. Bộ giám sát vẫn tự hạ về 1 nếu vượt các ngưỡng ở trên. Ngày 10/11/2026 đã nâng lại lúc 15:21 giờ Việt Nam theo yêu cầu người dùng.
