# US20 - Customer views booking history

- **Issue:** #20
- **Priority:** P1
- **Points:** 3
- **Owner:** @PhunghoaAI
- **Screen:** `/my-bookings`

## User story

As a **khách hàng (customer)**, I want **xem lại lịch sử đặt sân của mình (view my booking history)** so that **tôi có thể theo dõi các hoạt động đặt sân trong quá khứ và các lịch sắp tới (track my past activities and upcoming bookings)**.


## Acceptance criteria

1. Given tôi đã đăng nhập với tài khoản `customer@gmail.com` và có 3 đơn đặt sân trong hệ thống (`BK-1001` ngày 15/09/2026 trạng thái `Completed`, `BK-1002` ngày 25/09/2026 trạng thái `Confirmed`, và `BK-1003` ngày 01/10/2026 trạng thái `Pending`), when tôi điều hướng vào mục "My Bookings" tại đường dẫn `/my-bookings`, then hệ thống hiển thị danh sách 3 đơn đặt sân được sắp xếp theo thứ tự thời gian mới nhất lên đầu (`BK-1003` nằm trên cùng, tiếp theo là `BK-1002` và `BK-1001`), mỗi đơn hiển thị đầy đủ: Mã đơn, Tên sân bóng, Khung giờ chơi, Tổng tiền và Trạng thái đơn (BR1).

2. Given tôi đang ở danh sách lịch sử đặt sân tại `/my-bookings`, when tôi bấm vào đơn đặt sân quá khứ mã `BK-1001`, then hệ thống mở xem chi tiết đơn với đầy đủ thông tin: Tên sân **"Sân bóng Thống Nhất"**, Địa chỉ **"123 Nguyễn Trãi, Quận 5, TP.HCM"**, Khung giờ chơi **"18:00 - 19:00 ngày 15/09/2026"**, Tổng số tiền đã thanh toán **"250,000 VND"**, Phương thức thanh toán **"Chuyển khoản VNPAY"**, và Trạng thái **"Đã hoàn thành"** (BR2).

3. Given tôi đăng nhập bằng tài khoản mới tạo `newuser@gmail.com` (chưa từng đặt sân nào), when tôi truy cập trang `/my-bookings`, then hệ thống hiển thị danh sách trống kèm đúng câu thông báo **"Bạn chưa có đơn đặt sân nào"** và hiển thị nút **"Tìm sân ngay"** dẫn về trang chủ `/` (BR3).

4. Given tôi có 5 đơn đặt sân với các trạng thái khác nhau (`2 Confirmed`, `2 Completed`, `1 Cancelled`), when tôi chọn bộ lọc trạng thái **"Đã hủy" (Cancelled)**, then danh sách chỉ hiển thị đúng **1 đơn** có trạng thái Cancelled và ẩn toàn bộ các đơn khác (BR4).

5. Given tôi đăng nhập tài khoản `customerA@gmail.com`, when tôi cố gắng truy cập chi tiết đơn `BK-2001` của `customerB@gmail.com`, then hệ thống từ chối truy cập với mã lỗi 403 và hiển thị đúng thông báo lỗi **"Bạn không có quyền xem thông tin đơn đặt sân này"** (BR5).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR1 | Danh sách đơn đặt sân mặc định được sắp xếp theo thời gian tạo mới nhất lên đầu | Đơn đặt ngày 20/09 hiển thị trước đơn đặt ngày 15/09. |
| BR2 | Chi tiết đơn phải hiển thị đầy đủ thông tin sân, thời gian và tổng tiền đã thanh toán chính xác theo VNĐ | Hiển thị rõ tổng tiền `250,000 VND`, tên sân `Sân bóng Thống Nhất`. |
| BR3 | Khi tài khoản chưa có đơn đặt sân nào, hệ thống phải hiển thị trạng thái trống (empty state) thân thiện | 0 đơn đặt sân → Hiện thông báo "Bạn chưa có đơn đặt sân nào". |
| BR4 | Hỗ trợ lọc đơn theo trạng thái (Tất cả, Đang chờ, Đã xác nhận, Đã hoàn thành, Đã hủy) | Chọn lọc `Cancelled` → Chỉ hiển thị các đơn có trạng thái đã hủy. |
| BR5 | Người dùng chỉ được phép xem lịch sử và chi tiết đơn đặt sân của chính tài khoản mình | Customer A không thể xem thông tin đơn của Customer B (báo lỗi 403). |

## Tasks

- [ ] Màn hình `/my-bookings` hiển thị danh sách lịch sử đặt sân (sắp xếp theo thời gian mới nhất) 
- [ ] Bộ lọc trạng thái đơn: Tất cả, Đang chờ, Đã xác nhận, Đã hoàn thành, Đã hủy 
- [ ] Màn hình chi tiết đơn đặt sân hiển thị thông tin sân, địa chỉ và tổng số tiền thanh toán 
- [ ] API backend `GET /api/bookings/my-history` phân trang và lọc theo tài khoản người dùng 
- [ ] Test tự động cho các trường hợp: Hiển thị đúng thứ tự thời gian, Xem chi tiết đơn thành công, Khách hàng không xem được đơn của người khác 

## Ghi chú

Story này thuộc ưu tiên P1 (3 điểm).
Chức năng này giúp khách hàng quản lý và theo dõi toàn bộ lịch sử sử dụng dịch vụ trên nền tảng, làm cơ sở để thực hiện các chức năng tiếp theo như Hủy đặt sân (#19) hoặc Đánh giá sân sau khi chơi (#25).
