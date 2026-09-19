# US01 - Customer registration

- **Issue:** #14
- **Priority:** P0
- **Points:** 3
- **Owner:** @thunopro
- **Screen:** `/register`

## User story

As a **khách hàng muốn thuê sân**, I want **tự tạo một tài khoản bằng email và mật khẩu**
so that **tôi giữ được lịch đặt sân của mình và không phải nhắn tin cho chủ sân mỗi lần muốn chơi**.

## Acceptance criteria

1. Given tôi đang ở trang `/register` và email `hoa.nguyen@gmail.com` chưa có trong hệ
   thống, when tôi nhập email đó cùng mật khẩu `sanbong2026` (11 ký tự) và họ tên
   `Nguyễn Thị Hoa` rồi bấm Đăng ký, then tài khoản được tạo, tôi được chuyển sang
   `/login`, và một email xác thực được gửi tới `hoa.nguyen@gmail.com`.

2. Given email `hoa.nguyen@gmail.com` **đã** tồn tại, when tôi đăng ký lại bằng chính
   email đó, then hệ thống từ chối và hiện đúng câu **"Email này đã được sử dụng"**,
   đồng thời **không** tạo tài khoản thứ hai (BR1).

3. Given tôi nhập mật khẩu `sanbong` (**7 ký tự**), when tôi bấm Đăng ký, then hệ thống
   từ chối và hiện đúng câu **"Mật khẩu phải có ít nhất 8 ký tự"**, ô mật khẩu được
   tô viền đỏ, và các ô khác vẫn giữ nguyên nội dung tôi đã gõ (BR2).

4. Given tôi nhập số điện thoại `0912345678` (**10 chữ số, bắt đầu bằng 0**), when tôi
   bấm Đăng ký, then số được chấp nhận; given tôi nhập `091234567` (**9 chữ số**), then
   hệ thống hiện đúng câu **"Số điện thoại phải có 10 chữ số"** (BR3).

5. Given tài khoản vừa tạo và tôi chưa bấm link trong email xác thực, when tôi thử đặt
   sân, then bị từ chối với câu **"Vui lòng xác thực email trước khi đặt sân"**; link
   xác thực hết hạn sau **24 giờ** kể từ lúc gửi (BR4).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR1 | Mỗi email chỉ gắn với đúng một tài khoản | `hoa.nguyen@gmail.com` đăng ký lúc 09:00 ngày 19/09 thành công. Lúc 14:00 cùng ngày đăng ký lại bằng email đó → từ chối, hệ thống vẫn chỉ có 1 tài khoản. |
| BR2 | Mật khẩu tối thiểu 8 ký tự, phải có ít nhất 1 chữ cái và 1 chữ số | `sanbong` (7 ký tự) → từ chối. `sanbong1` (8 ký tự, có số) → chấp nhận. `12345678` (8 ký tự, không có chữ) → từ chối. |
| BR3 | Số điện thoại phải đúng 10 chữ số và bắt đầu bằng số 0 | `0912345678` → chấp nhận. `091234567` (9 số) → từ chối. `1912345678` (không bắt đầu bằng 0) → từ chối. |
| BR4 | Tài khoản chưa xác thực email không được đặt sân; link xác thực hết hạn sau 24 giờ | Đăng ký lúc 10:00 ngày 19/09 → link hết hạn 10:00 ngày 20/09. Bấm link lúc 11:00 ngày 20/09 → hết hạn, phải yêu cầu gửi lại. |

## Tasks

- [ ] Màn hình `/register` với 4 ô: họ tên, email, số điện thoại, mật khẩu - @thunopro
- [ ] Kiểm tra dữ liệu phía client theo BR2 và BR3, hiện lỗi ngay dưới từng ô - @thunopro
- [ ] Kiểm tra email trùng phía server theo BR1 - @thunopro
- [ ] Gửi email xác thực, token hết hạn 24 giờ theo BR4 - @thunopro
- [ ] Test tự động cho 3 trường hợp bị từ chối: email trùng, mật khẩu 7 ký tự, SĐT 9 số - @thunopro

## Ghi chú

Story này là cửa vào của toàn bộ sản phẩm, nên để P0. Không có tài khoản thì
US02 (đăng nhập), US05 (đặt sân) và US07 (lịch sử đặt) đều không chạy được.
