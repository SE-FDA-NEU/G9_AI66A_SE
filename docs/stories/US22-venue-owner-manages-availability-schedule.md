# US22 - Venue owner manages venue availability schedule

- **Issue:** #22
- **Priority:** P1
- **Points:** 5
- **Owner:** @lequangk2006-sys
- **Screen:** `/owner/venues/{id}/schedule`

## User story

As a **chủ sân**, I want **tự chặn và mở lại các khung giờ trên lịch sân của mình**
so that **tôi giữ được giờ để bảo trì, và khách không đặt trúng lúc sân không dùng được**.

## Acceptance criteria

1. Given sân `Sân bóng đá mini Thanh Xuân - Sân số 2` đang trống khung **18:00-19:00
   ngày 25/09/2026**, when tôi chặn đúng khung đó với lý do `Bảo trì mặt cỏ`,
   then khung 18:00-19:00 ngày 25/09 **biến mất** khỏi danh sách giờ trống ở `/venues/2`,
   và trên lịch của tôi ô đó hiện nền xám kèm chữ **"Đã chặn - Bảo trì mặt cỏ"** (BR13).

2. Given khung **18:00-19:00 ngày 25/09/2026** đang bị chặn, when tôi bấm Mở lại,
   then trong vòng **5 giây** khung đó xuất hiện trở lại trong danh sách giờ trống ở
   `/venues/2` mà không cần khách tải lại trang thủ công (BR13).

3. Given khung **19:00-20:00 ngày 25/09/2026** **đã có khách đặt** (mã đặt `BK-000148`),
   when tôi thử chặn khung đó, then hệ thống từ chối và hiện đúng câu
   **"Không thể chặn: khung giờ này đã có 1 lịch đặt (BK-000148). Huỷ lịch đặt trước."**
   - khung giờ **vẫn giữ nguyên trạng thái đã đặt**, không có lịch nào bị xoá ngầm (BR14).

4. Given hôm nay là **20/09/2026** và bây giờ là **14:30**, when tôi chọn chặn khung
   **14:00-15:00 ngày 20/09/2026** (đã bắt đầu), then hệ thống từ chối và hiện đúng câu
   **"Chỉ được chặn khung giờ bắt đầu sau thời điểm hiện tại"** (BR15).

5. Given tôi chọn chặn hàng loạt từ **ngày 01/10/2026 đến 05/10/2026, khung 06:00-08:00**,
   when tôi xác nhận, then **5 khung** (mỗi ngày 1 khung) được chặn cùng lúc và hệ thống
   báo đúng câu **"Đã chặn 5 khung giờ"**; nếu ngày 03/10 khung đó đã có khách đặt thì
   **4 khung** được chặn và hệ thống báo
   **"Đã chặn 4 khung giờ. Bỏ qua 1 khung đã có lịch đặt: 03/10/2026 06:00-08:00"** (BR14).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR13 | Khung giờ bị chủ sân chặn không xuất hiện trong kết quả tìm kiếm và không đặt được; mở lại thì có hiệu lực trong 5 giây | Chặn 18:00-19:00 ngày 25/09 lúc 09:00 → khách vào `/venues/2` lúc 09:01 không thấy khung này. Mở lại lúc 10:00 → khách tải trang lúc 10:00:05 thấy lại khung này. |
| BR14 | Không được chặn khung giờ đã có lịch đặt chưa huỷ | Khung 19:00-20:00 ngày 25/09 có `BK-000148` trạng thái Đã xác nhận → chặn bị từ chối. Sau khi khách huỷ `BK-000148` lúc 11:00 → chặn lúc 11:01 thành công. |
| BR15 | Chỉ được chặn khung giờ bắt đầu sau thời điểm hiện tại | Bây giờ 20/09/2026 14:30. Chặn khung 14:00-15:00 ngày 20/09 → từ chối. Chặn khung 15:00-16:00 ngày 20/09 → chấp nhận. Chặn khung 06:00-07:00 ngày 21/09 → chấp nhận. |

## Tasks

- [ ] Màn hình lịch `/owner/venues/{id}/schedule` dạng lưới 7 ngày x khung giờ - @lequangk2006-sys
- [ ] Chặn / mở lại một khung giờ, lưu lý do chặn - @lequangk2006-sys
- [ ] Chặn hàng loạt theo khoảng ngày + khung giờ, báo số khung bị bỏ qua theo BR14 - @lequangk2006-sys
- [ ] Chặn khung đã chặn khỏi kết quả tìm kiếm và trang chi tiết sân theo BR13 - @lequangk2006-sys
- [ ] Test tự động cho 3 trường hợp từ chối: khung đã có lịch đặt (BR14), khung trong quá khứ (BR15), và trường hợp chặn hàng loạt bỏ qua đúng 1 khung - @lequangk2006-sys

## Ghi chú

Điểm dễ làm sai nhất là BR14: phản xạ tự nhiên khi code là cứ ghi đè trạng thái ô lịch
thành "blocked", làm lịch đặt của khách biến mất im lặng mà không ai báo. Ghi rõ vào đây
để người review Sprint 3 bắt được.

Số BR (BR13-BR15) là **số tạm** trong phạm vi story này. PO (@thunopro) sẽ đánh số lại
toàn bộ khi gộp vào `docs/requirements.md` mục 5.
