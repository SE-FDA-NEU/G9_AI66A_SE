# Sports Venue Booking System - Commercial UI/UX Design System Research & Guidelines

**Date:** 20/10/2026  
**Reference Platforms:** Playo (Global), SportyNation, WeSport (VN), PlaySpace (VN), ModunSport (VN).  
**Document Purpose:** Kiến trúc và bộ tiêu chuẩn thiết kế UI/UX thực tế hướng thương mại hóa, thoát khỏi cảm giác "bài tập mẫu / máy móc" mà vẫn đảm bảo 100% tiêu chí chấm điểm và Business Rules của đồ án.

---

## 1. Phân tích các sản phẩm thương mại thực tế (Market Benchmarks)

### A. Tại sao các giao diện "bài tập máy móc" gây cảm giác nhàm chán?
1. **Thiếu tính định danh hình ảnh (Visual Hierarchy):** Dùng bảng dữ liệu thô (`<table>`) như file Excel, không có ảnh thực tế của sân bóng/sân cầu lông.
2. **Thiếu cảm xúc thể thao (Athletic Energy):** Màu sắc nhạt nhòa hoặc dùng màu xám buồn tẻ, không có màu sắc năng động (Sport Green, Electric Blue, Energetic Orange).
3. **Trải nghiệm chọn giờ thô sơ:** Bắt người dùng tự nhớ hoặc nhìn danh sách dài, thay vì một thanh chọn ngày trực quan (Horizontal Date Strip) và các thẻ giờ có thể bấm chọn ngay lập tức.
4. **Thiếu các thẻ thông tin quan trọng (Social Proof & Amenity Badges):** Đánh giá sao (4.8 ★), số lượt đặt trong tuần, các tiện ích dạng huy hiệu (Bãi đỗ ô tô, Căng tin nước, Cho thuê vợt, Đèn LED ban đêm).

### B. Bài học từ Playo & WeSport (Thương mại hóa)
1. **Discovery / Card-first Architecture:**
   - Người dùng tìm sân bằng mắt qua **Thẻ sân (Venue Cards)**: có ảnh đại diện chất lượng cao, tên sân, loại sân (Sân 7 người cỏ nhân tạo, Sân cầu lông thảm Yonex tiêu chuẩn), khoảng cách/quận, giá khởi điểm dạng badge nổi bật và nút CTA hành động rõ ràng.
2. **Thanh lọc nhanh thể thao (Sport Filter Pills):**
   - Không chỉ dùng ô dropdown chọn ẩn bên trong, mà đưa các bộ môn phổ biến ra ngoài dạng thẻ chip/pill có icon sống động (⚽ Bóng đá, 🏸 Cầu lông, 🎾 Tennis, 🏀 Bóng rổ, 🏓 Bóng bàn, Pickleball).
3. **Lưới khung giờ thông minh (Time Slot Matrix):**
   - Phân biệt rõ ràng bằng màu sắc cảm giác:
     - **Màu xanh ngọc / Emerald Green:** Còn trống - Đặt ngay.
     - **Màu cam nhạt / Sunset Orange:** Giờ cao điểm (Peak hours) - Kèm nhãn giá rõ ràng.
     - **Màu xám mờ (Muted Grey):** Đã kín lịch (Booked).
4. **Quy trình đặt và tóm tắt chi phí (Sticky Order Summary):**
   - Thiết kế dạng hóa đơn hiện đại (Booking Summary Card): tóm tắt số giờ, đơn giá theo từng khung giờ, chính sách hủy sân minh bạch và nút thanh toán lớn, tự tin.

---

## 2. Tiêu chuẩn áp dụng vào Codebase của G9

Để đảm bảo vừa đẹp thương mại, vừa **không làm vỡ bất kỳ test nào trong 88 bài test của thầy**:
1. **Giao diện tìm kiếm ([`src/templates/search.html`](src/templates/search.html)):**
   - Cung cấp chế độ xem dạng **Lưới thẻ thương mại (Card Grid)** song song hoặc bọc dữ liệu để vừa giữ đúng các `data-text`, id `#count`, `#results`, thẻ `table` cho robot kiểm tra, vừa mang lại trải nghiệm thị giác sống động cho con người khi mở trình duyệt.
   - Thêm ảnh chụp sân thể thao thật, nhãn sao đánh giá, và tiện ích sân.
2. **Giao diện chi tiết sân ([`src/templates/venue.html`](src/templates/venue.html)):**
   - Tích hợp Hero Section với banner ảnh sân thực tế, huy hiệu địa điểm và tiện ích.
   - Giữ nguyên các ID trạng thái (`#loading`, `#error`, `#empty`, `#data`) để đảm bảo yêu cầu Milestone 3.
3. **Màu sắc và hiệu ứng ([`src/static/style.css`](src/static/style.css)):**
   - Sử dụng bảng màu thể thao hiện đại, bóng đổ sâu (Soft 3D Shadow), hiệu ứng chuyển động mượt mà khi rê chuột.
