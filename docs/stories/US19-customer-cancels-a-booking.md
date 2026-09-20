# US19 - Customer cancels a booking

- **Issue:** #19
- **Priority:** P1
- **Points:** 3
- **Owner:** @PhunghoaAI
- **Screen:** `/my-bookings`

## User story

As a **khách hàng (customer)**, I want **hủy một đơn đặt sân sắp tới (cancel an upcoming booking)** so that **tôi không bị mất tiền nếu kế hoạch thay đổi (avoid being charged if my plans change)**.


## Acceptance criteria

1. Given tôi có một đơn đặt sân sắp tới mã `BK-1002` trị giá `300,000` VND vào lúc **18:00 - 19:00 ngày 25/09/2026**, when tôi bấm nút **Hủy đặt sân** trước giờ bắt đầu ít nhất **24 giờ** (vào lúc 15:00 ngày 24/09/2026, trước 27 giờ) và xác nhận, then đơn đặt sân được hủy thành công, trạng thái chuyển sang **"Cancelled"**, tôi nhận lại đủ **100% tiền hoàn (300,000 VND)**, hệ thống hiện đúng câu thông báo **"Hủy đơn đặt sân thành công! Bạn được hoàn lại 100% số tiền (300,000 VND)"**, và khung giờ 18:00 - 19:00 ngày 25/09/2026 được mở lại trên hệ thống để khách khác có thể đặt (BR1).

2. Given tôi có một đơn đặt sân sắp tới mã `BK-1003` bắt đầu lúc **17:00 hôm nay**, when tôi cố gắng hủy đơn lúc **16:00** (còn 1 giờ trước giờ bắt đầu, **dưới 2 giờ**), then hệ thống **không cho phép hủy**, nút Hủy đặt sân bị vô hiệu hóa (disabled) hoặc khi gửi yêu cầu hệ thống từ chối và hiện đúng câu thông báo lỗi **"Không thể hủy đơn đặt sân trước giờ chơi dưới 2 giờ"** (BR2).

3. Given tôi có một đơn đặt sân sắp tới mã `BK-1004` trị giá `400,000` VND bắt đầu lúc **18:00 hôm nay**, when tôi thực hiện hủy đơn lúc **10:00 cùng ngày** (trước giờ chơi 8 giờ, **trong khoảng từ 2 giờ đến 24 giờ**), then hệ thống cho phép hủy, cập nhật trạng thái đơn thành **"Cancelled"**, hoàn lại 50% số tiền (`200,000` VND) và hiện đúng thông báo **"Đơn đặt sân đã được hủy. Bạn được hoàn lại 50% chi phí (200,000 VND) theo chính sách hủy sân."** (BR3).

4. Given đơn đặt sân `BK-1001` có trạng thái **"Completed"** (đã qua giờ chơi) hoặc **"Cancelled"** (đã hủy trước đó), when tôi xem chi tiết đơn tại trang `/my-bookings`, then nút **Hủy đặt sân** không xuất hiện trên giao diện (BR4).

5. Given tôi đăng nhập tài khoản `userB@gmail.com`, when tôi cố gắng gửi yêu cầu hủy đơn `BK-1002` thuộc sở hữu của tài khoản `customer@gmail.com`, then hệ thống từ chối với mã lỗi 403 và hiển thị đúng thông báo **"Bạn không có quyền hủy đơn đặt sân này"** (BR5).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR1 | Hủy trước giờ bắt đầu ≥ 24 giờ → Được hủy và hoàn tiền 100% | Đơn 300,000 VND chơi lúc 18:00 ngày 25/09. Hủy lúc 15:00 ngày 24/09 (trước 27 giờ) → Hoàn 300,000 VND. |
| BR2 | Hủy trước giờ bắt đầu < 2 giờ → Hệ thống không cho phép hủy | Chơi lúc 17:00. Thử hủy lúc 16:00 (trước 1 giờ) → Từ chối hủy, báo lỗi. |
| BR3 | Hủy trong khoảng từ 2 giờ đến 24 giờ trước giờ bắt đầu → Hoàn tiền 50% | Đơn 400,000 VND chơi lúc 18:00. Hủy lúc 10:00 cùng ngày (trước 8 giờ) → Hoàn 200,000 VND. |
| BR4 | Chỉ các đơn ở trạng thái sắp tới (`Pending` hoặc `Confirmed`) mới có thể hủy | Đơn ở trạng thái `Completed` hoặc `Cancelled` → Nút Hủy bị ẩn/disabled. |
| BR5 | Người dùng chỉ được quyền hủy các đơn đặt sân do chính tài khoản của mình tạo | `userB` hủy đơn của `userA` → Báo lỗi 403 Forbidden. |

## Tasks

- [ ] Màn hình `/my-bookings` hiển thị danh sách đơn đặt sân kèm nút "Hủy đặt sân" cho các đơn đủ điều kiện 
- [ ] Modal xác nhận hủy sân hiển thị lý do hủy và số tiền hoàn dự kiến (100%, 50% hoặc 0%) 
- [ ] API backend `POST /api/bookings/:id/cancel` kiểm tra thời gian chơi, tính toán tiền hoàn và cập nhật trạng thái đơn 
- [ ] Xử lý giải phóng khung giờ chơi trên lịch đặt sân ngay sau khi hủy thành công 
- [ ] Test tự động cho các trường hợp: Hủy trước 24h (hoàn 100%), Hủy từ 2h-24h (hoàn 50%), Hủy dưới 2h (từ chối) 

## Ghi chú

Story này thuộc ưu tiên P1 (3 điểm).
Mặc dù không nằm trong luồng chính P0 (tạo sân -> tìm sân -> đặt sân), chức năng hủy đặt sân rất cần thiết để nâng cao trải nghiệm khách hàng và giải phóng khung giờ trống cho chủ sân.
