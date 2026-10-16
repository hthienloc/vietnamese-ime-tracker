# Vietnamese IME Tracker

Hệ thống tổng hợp, phân loại và tự động theo dõi trạng thái các bộ gõ tiếng Việt mã nguồn mở trên Linux, macOS và Windows.

[![Sync Status](https://github.com/hthienloc/vietnamese-ime-tracker/actions/workflows/sync-and-deploy.yml/badge.svg)](https://github.com/hthienloc/vietnamese-ime-tracker/actions/workflows/sync-and-deploy.yml)
[![Live Site](https://img.shields.io/badge/Web-Live_Dashboard-blue)](https://hthienloc.github.io/vietnamese-ime-tracker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-gray.svg)](https://opensource.org/licenses/MIT)

---

## Bảng điều khiển trực tuyến

Truy cập, tra cứu và lọc dữ liệu đầy đủ tại:

**[https://hthienloc.github.io/vietnamese-ime-tracker/](https://hthienloc.github.io/vietnamese-ime-tracker/)**

### Tính năng bảng điều khiển
- Tìm kiếm tức thì theo tên bộ gõ, tác giả, ngôn ngữ lập trình hoặc framework.
- Lọc đa chiều trực tiếp trên tiêu đề bảng: Trạng thái (Status), Framework, Tác giả, Ngôn ngữ, Giấy phép (License).
- Sắp xếp linh hoạt theo số sao GitHub (Stars), ngày commit gần nhất hoặc ngày tạo dự án.
- Chuyển đổi giữa chế độ xem Bảng dữ liệu và Biểu đồ thống kê phân tích trực quan (8 biểu đồ phân tích).
- Giao diện tối giản tông màu Zinc, hỗ trợ Dark mode mặc định.

---

## Tiêu chí phân loại trạng thái

Trạng thái hoạt động của từng dự án được tính toán tự động dựa trên các chỉ số từ GitHub REST API trong mỗi chu kỳ đồng bộ:

| Trạng thái | Định nghĩa | Tiêu chí kỹ thuật |
| :--- | :--- | :--- |
| **Active** | Đang duy trì tích cực hoặc ổn định với cập nhật gần đây. | Repository chưa bị lưu trữ (archived), commit gần nhất trong vòng 180 ngày (<= 6 tháng). |
| **Inactive** | Tạm ngưng phát triển hoặc đã hoàn thiện tính năng, chưa có cập nhật mới. | Repository chưa bị lưu trữ, commit gần nhất từ 181 đến 365 ngày (6 - 12 tháng). |
| **Dead** | Dừng phát triển, bỏ hoang hoặc không còn truy cập được. | Repository đã bị lưu trữ bởi tác giả, trả về HTTP 404 (được lưu cache lịch sử), hoặc không có commit mới quá 365 ngày (> 1 năm). |

---

## Tự động hóa và Luồng xử lý dữ liệu

- **Chu kỳ chạy**: GitHub Actions thực thi tập lệnh `sync.py` định kỳ vào 00:00 UTC thứ Hai hàng tuần (07:00 sáng Thứ Hai giờ Việt Nam) hoặc kích hoạt thủ công.
- **Thu thập dữ liệu**: Truy vấn GitHub REST API để cập nhật số sao, ngôn ngữ chính, giấy phép và thời điểm commit gần nhất.
- **Tạo tệp dữ liệu**: Xuất tệp `data.json` phục vụ giao diện web và cập nhật `bo-go-tieng-viet.csv` làm nguồn dữ liệu bảng.
- **Triển khai**: Tự động build và deploy trang tĩnh lên GitHub Pages sau khi đồng bộ thành công.

---

## Kế hoạch phát triển

- [x] **Linux**: Hỗ trợ đầy đủ các bộ gõ Standalone Wayland, Fcitx5 và IBus.
- [x] **macOS**: Hỗ trợ các bộ gõ trên macOS (OpenKey, Gõ Nhanh...).
- [x] **Windows**: Hỗ trợ các bộ gõ trên Windows (OpenKey, Gõ Nhanh...).

---

## Đóng góp dữ liệu

Bạn có thể đề xuất bổ sung bộ gõ mới hoặc cập nhật thông tin hiện có theo hai cách:

### Cách 1: Mở Issue (Không cần sử dụng Git)
Điền thông tin bộ gõ vào biểu mẫu có sẵn tại: [Đề xuất bộ gõ tiếng Việt](https://github.com/hthienloc/vietnamese-ime-tracker/issues/new?template=add_ime.yml).

### Cách 2: Gửi Pull Request
1. Fork repository này về tài khoản của bạn.
2. Thêm bản ghi mới vào tệp [`repos.yml`](./repos.yml):
   ```yaml
   - name: Tên bộ gõ
     url: https://github.com/owner/repo
     framework: Fcitx5  # Fcitx5, IBus, hoặc Standalone (Wayland)
     maintainer: Tên tác giả
     os: Linux          # Linux, macOS, hoặc Windows
   ```
   *(Các thông số như Stars, License, Ngôn ngữ, Ngày cập nhật sẽ được bot tự động đồng bộ khi merge).*
3. Tạo và gửi Pull Request.

---

## Giấy phép

Mã nguồn dự án và các tập lệnh tự động hóa được phát hành theo [Giấy phép MIT](LICENSE).
