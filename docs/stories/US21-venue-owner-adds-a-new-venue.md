# US21 - Venue owner adds a new venue

- **Issue:** #21
- **Priority:** P0
- **Points:** 5
- **Owner:** @PhunghoaAI
- **Screen:** `/owner/venues/new`

## User story

As a **chủ sân bóng (venue owner)**, I want **thêm một sân bóng mới vào hệ thống kèm đầy đủ thông tin (tên sân, địa chỉ, giá thuê, hình ảnh)** so that **khách hàng có thể tìm kiếm và đặt sân của tôi trên nền tảng**.

## Acceptance criteria

1. Given tôi đã đăng nhập với tài khoản chủ sân `owner@sanbong.com`, when tôi truy cập trang `/owner/venues/new`, nhập tên sân `Sân bóng Thống Nhất`, địa chỉ `123 Nguyễn Trãi, Quận 5, TP.HCM`, giá thuê theo giờ `250,000` VND, tải lên 1 hình ảnh (`san_thong_nhat.jpg`) rồi bấm nút **Thêm sân mới**, then hệ thống tạo thành công sân bóng mới, hiển thị đúng thông báo **"Thêm sân bóng thành công!"**, chuyển hướng sang `/owner/venues`, và sân **Sân bóng Thống Nhất** xuất hiện trên danh sách với giá `250,000` VND/giờ.

2. Given tôi đang ở trang thêm sân mới `/owner/venues/new`, when tôi nhập tên sân `Sân bóng Thống Nhất`, địa chỉ `123 Nguyễn Trãi, Quận 5, TP.HCM`, chọn ảnh nhưng **bỏ trống ô giá thuê** rồi bấm nút **Thêm sân mới**, then hệ thống từ chối submit, ô giá thuê được tô viền đỏ và hiển thị đúng câu thông báo lỗi **"Giá thuê không được để trống và phải là số lớn hơn 0"** (BR1).

3. Given tôi đang ở trang `/owner/venues/new`, when tôi nhập giá thuê là `0` VND hoặc `-50,000` VND rồi bấm **Thêm sân mới**, then hệ thống từ chối và hiển thị đúng câu thông báo lỗi **"Giá thuê phải lớn hơn hoặc bằng 1,000 VND/giờ"** (BR1).

4. Given tôi đang ở trang `/owner/venues/new`, when tôi nhập giá thuê `250,000` nhưng **bỏ trống ô tên sân** rồi bấm **Thêm sân mới**, then hệ thống từ chối và hiển thị đúng câu thông báo lỗi **"Vui lòng nhập tên sân bóng"** (BR2).

5. Given tôi đăng nhập với tài khoản khách hàng `customer@gmail.com` (role `customer`), when tôi cố gắng truy cập đường dẫn `/owner/venues/new`, then hệ thống từ chối truy cập, hiển thị đúng câu **"Bạn không có quyền truy cập trang này"** và chuyển hướng về trang chủ `/` (BR3).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR1 | Giá thuê theo giờ phải là số nguyên dương từ 1,000 VND đến 100,000,000 VND | Nhập `0` hoặc `-50,000` → từ chối, báo lỗi. Nhập `250,000` → chấp nhận. |
| BR2 | Tên sân và Địa chỉ là các trường bắt buộc; Tên sân từ 3 đến 100 ký tự | Bỏ trống Tên sân hoặc gõ `Sâ` (2 ký tự) → từ chối. Gõ `Sân bóng Thống Nhất` (19 ký tự) → chấp nhận. |
| BR3 | Chỉ người dùng có vai trò `venue_owner` mới được phép tạo sân mới | Tài khoản role `customer` truy cập `/owner/venues/new` → từ chối (403 Forbidden / Redirect về `/`). |
| BR4 | Mỗi sân bóng mới khởi tạo sẽ có trạng thái mặc định là `active` | Tạo sân thành công → sân hiển thị trong danh sách tìm kiếm với status = `active`. |

## Tasks

- [ ] Màn hình `/owner/venues/new` chứa form nhập thông tin: Tên sân, Địa chỉ, Giá/giờ, Upload hình ảnh - @PhunghoaAI
- [ ] Validation phía client cho các trường bắt buộc và định dạng giá thuê - @PhunghoaAI
- [ ] API backend `POST /api/venues` kiểm tra quyền `venue_owner` và lưu thông tin sân bóng - @PhunghoaAI
- [ ] Xử lý lưu trữ và hiển thị hình ảnh sân bóng - @PhunghoaAI
- [ ] Test tự động cho các trường hợp: Tạo sân thành công, Bỏ trống trường giá thuê, Báo lỗi phân quyền - @PhunghoaAI

## Ghi chú

Story này là điều kiện tiên quyết (P0) thuộc nhóm chức năng quản lý sân của chủ sân.
Nếu không có sân bóng trong hệ thống (#21), các chức năng Tìm kiếm sân (#16), Xem chi tiết sân (#17) và Đặt sân (#18) đều không thể thực hiện được.
