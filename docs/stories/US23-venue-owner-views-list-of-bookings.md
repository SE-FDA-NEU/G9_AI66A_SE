# US23 - Venue owner views list of bookings

- **Issue:** #23
- **Priority:** P1
- **Points:** 3
- **Owner:** @lequangk2006-sys
- **Screen:** `/owner/bookings`

## User story

As a **chủ sân**, I want **xem danh sách mọi lịch đặt của các sân tôi quản lý theo từng ngày**
so that **tôi biết hôm nay có bao nhiêu lượt, ai đến giờ nào, để chuẩn bị sân và người trực**.

## Acceptance criteria

1. Given hôm nay là **20/09/2026** và các sân của tôi có **7 lịch đặt** trong ngày,
   when tôi mở `/owner/bookings`, then trang mặc định hiện ngày **20/09/2026** với đúng
   **7 dòng**, xếp theo giờ bắt đầu tăng dần, và tiêu đề hiện đúng câu
   **"7 lịch đặt ngày 20/09/2026"** (BR16).

2. Given tôi đang xem ngày 20/09/2026, when tôi chọn **22/09/2026** trên ô chọn ngày,
   then danh sách đổi sang đúng các lịch đặt của ngày 22/09/2026 **trong vòng 2 giây**
   và URL đổi thành `/owner/bookings?date=2026-09-22` (BR16).

3. Given một lịch đặt trong danh sách, when tôi nhìn một dòng, then dòng đó hiện đủ
   **6 cột**: mã đặt (`BK-000148`), tên sân (`Sân số 2`), khung giờ (`19:00-20:00`),
   tên khách (`Nguyễn Thị Hoa`), số điện thoại (`0912345678`), trạng thái
   (`Đã xác nhận` / `Đã huỷ` / `Đã hoàn thành`) (BR17).

4. Given ngày **28/09/2026** không có lịch đặt nào, when tôi chọn ngày đó, then danh sách
   hiện đúng câu **"Không có lịch đặt ngày 28/09/2026"** - **không** hiện bảng rỗng
   và **không** hiện lỗi.

5. Given tôi quản lý **Sân số 1, Sân số 2, Sân số 3** và ngày 20/09/2026 có 7 lịch đặt
   trong đó **3 lịch thuộc Sân số 2**, when tôi lọc theo `Sân số 2`, then danh sách còn
   đúng **3 dòng** và tiêu đề hiện **"3 lịch đặt ngày 20/09/2026 - Sân số 2"**.

6. Given tài khoản chủ sân khác (`@owner-b`) cũng có lịch đặt trong ngày 20/09/2026,
   when tôi mở `/owner/bookings`, then danh sách của tôi **không** chứa bất kỳ dòng nào
   của `@owner-b`; và khi tôi mở thẳng URL `/owner/bookings/BK-000901` (lịch đặt của
   `@owner-b`), then hệ thống trả về **403** kèm câu
   **"Bạn không có quyền xem lịch đặt này"** (BR18).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR16 | Danh sách lịch đặt luôn gắn với đúng một ngày; mặc định là ngày hôm nay, đổi ngày phải phản ánh trong URL và tải xong trong 2 giây | Mở `/owner/bookings` lúc 08:00 ngày 20/09/2026 → hiện ngày 20/09. Chọn 22/09 → URL thành `/owner/bookings?date=2026-09-22`, danh sách xong trước 08:00:02. |
| BR17 | Mỗi dòng lịch đặt phải hiện đủ 6 trường để chủ sân liên lạc được với khách mà không phải bấm vào từng dòng | `BK-000148 · Sân số 2 · 19:00-20:00 · Nguyễn Thị Hoa · 0912345678 · Đã xác nhận` |
| BR18 | Chủ sân chỉ xem được lịch đặt của sân do chính mình sở hữu | Tôi sở hữu Sân 1, 2, 3. `BK-000901` thuộc sân của `@owner-b` → mở trực tiếp trả về 403, và không xuất hiện trong danh sách của tôi. |

## Tasks

- [ ] Màn hình `/owner/bookings` với ô chọn ngày, mặc định hôm nay - @lequangk2006-sys
- [ ] Truy vấn lịch đặt theo ngày + theo chủ sở hữu, xếp theo giờ bắt đầu - @lequangk2006-sys
- [ ] Bộ lọc theo từng sân, cập nhật cả tiêu đề đếm số - @lequangk2006-sys
- [ ] Chặn truy cập chéo chủ sân, trả 403 theo BR18 - @lequangk2006-sys
- [ ] Trạng thái rỗng đúng câu "Không có lịch đặt ngày <dd/mm/yyyy>" - @lequangk2006-sys
- [ ] Test tự động: đếm đúng 7 dòng, lọc còn 3 dòng, ngày rỗng, và 403 khi xem lịch của chủ sân khác - @lequangk2006-sys

## Ghi chú

BR18 là criterion dễ bị bỏ sót nhất: lọc đúng trên màn hình danh sách nhưng quên kiểm tra
quyền ở trang chi tiết, dẫn tới ai đoán đúng mã `BK-xxxxxx` cũng xem được số điện thoại
khách của sân người khác. Phải test cả hai đường.

Số BR (BR16-BR18) là **số tạm** trong phạm vi story này. PO (@thunopro) sẽ đánh số lại
toàn bộ khi gộp vào `docs/requirements.md` mục 5.
