# Product Backlog - Sprint 1

Chốt tại buổi Backlog Refinement (issue #12). Product Owner: @thunopro.

Thang điểm: Fibonacci (1, 2, 3, 5, 8, 13). Điểm là **độ phức tạp tương đối**,
không phải số giờ.

Ưu tiên: **P0** = không có thì sản phẩm vô nghĩa · **P1** = nên có · **P2** = có thì tốt.

## Sprint 1 backlog

| Issue | Story | Priority | Points | Owner |
|-------|-------|----------|--------|-------|
| #14 | Customer registration | P0 | 3 | @thunopro |
| #15 | User login | P0 | 3 | @thunopro |
| #16 | Customer searches for venues | P0 | 5 | @peng543 |
| #17 | Customer views venue details and availability | P0 | 5 | @peng543 |
| #18 | Customer books a venue | P0 | 8 | @peng543 |
| #21 | Venue owner adds a new venue | P0 | 5 | @PhunghoaAI |
| #19 | Customer cancels a booking | P1 | 3 | @PhunghoaAI |
| #20 | Customer views booking history | P1 | 3 | @PhunghoaAI |
| #22 | Venue owner manages venue availability schedule | P1 | 5 | @lequangk2006-sys |
| #23 | Venue owner views list of bookings | P1 | 3 | @lequangk2006-sys |
| #24 | Venue owner sets peak-hour pricing | P2 | 5 | @htngochan2802 |
| #25 | Customer leaves a review and rating | P2 | 3 | @htngochan2802 |

**Tổng: 51 điểm · 6 story P0** (khung yêu cầu là 4-6 P0).

## Lý do xếp ưu tiên

- **#14 → #18 là đường đi ngắn nhất để một khách hàng đặt được sân.** Bỏ bất kỳ
  cái nào trong chuỗi này thì không ai đặt được sân, nên cả năm đều P0.
- **#21 là P0** vì không có sân trong hệ thống thì không có gì để tìm và để đặt.
  Đây là điều kiện để #16, #17, #18 có ý nghĩa.
- **#19, #20, #22, #23 là P1.** Hệ thống vẫn chạy được nếu huỷ đặt phải gọi điện
  và chủ sân phải xem lịch bằng tay, chỉ là khó chịu. Không phải điều kiện sống còn.
- **#24, #25 là P2.** Giá giờ cao điểm và đánh giá là thứ làm sản phẩm tốt hơn,
  không phải thứ làm sản phẩm hoạt động.

## Lý do ước lượng điểm

| Points | Story | Vì sao |
|--------|-------|--------|
| 3 | #14, #15, #19, #20, #23, #25 | Một form hoặc một danh sách, luật đơn giản, ít trạng thái |
| 5 | #16, #17, #21, #22, #24 | Có truy vấn theo điều kiện, hoặc quản lý lịch/khung giờ |
| 8 | #18 | Việc phức tạp nhất: kiểm tra chỗ trống, tránh đặt trùng, tính tiền, xác nhận |

## Ghi chú về velocity

Sprint 1 là **sprint yêu cầu** (requirements sprint): sản phẩm giao ra là
`docs/requirements.md` chứ không phải code chạy được. Vì vậy điểm trong bảng trên
là **ước lượng để lập kế hoạch cho Sprint 2-3**, và Sprint 1 ghi nhận
`Committed 0 - Completed 0 - Velocity: không áp dụng` trong `docs/sprint-log.md`.
