# US02 - User login

- **Issue:** #15
- **Priority:** P0
- **Points:** 3
- **Owner:** @thunopro
- **Screen:** `/login`

## User story

As a **người dùng đã có tài khoản (khách hàng hoặc chủ sân)**, I want **đăng nhập bằng
email và mật khẩu** so that **tôi vào được khu vực của mình và thấy các lịch đặt sân
của riêng tôi**.

## Acceptance criteria

1. Given tài khoản `hoa.nguyen@gmail.com` đã xác thực email và mật khẩu là `sanbong2026`,
   when tôi nhập đúng cả hai và bấm Đăng nhập, then tôi được chuyển tới `/dashboard`
   và thấy tên `Nguyễn Thị Hoa` ở góc trên bên phải.

2. Given tôi nhập sai mật khẩu **4 lần liên tiếp**, when tôi nhập sai **lần thứ 5**,
   then tài khoản bị khoá **15 phút** và hệ thống hiện đúng câu
   **"Tài khoản tạm khoá. Thử lại sau 15 phút"** (BR5).

3. Given tài khoản đang bị khoá và đã trôi qua **15 phút** kể từ lần sai thứ 5, when tôi
   nhập đúng mật khẩu, then tôi đăng nhập thành công và bộ đếm sai được **đặt lại về 0**
   (BR5).

4. Given tôi nhập sai mật khẩu, when hệ thống báo lỗi, then thông báo là đúng câu
   **"Email hoặc mật khẩu không đúng"** - **không** nói riêng cái nào sai, để người lạ
   không dò được email nào đang tồn tại trong hệ thống (BR6).

5. Given tài khoản là **chủ sân**, when đăng nhập thành công, then tôi vào
   `/owner/venues` chứ không phải `/dashboard` của khách hàng; given tài khoản là
   **khách hàng**, then vào `/dashboard` (BR7).

6. Given tôi đã đăng nhập và không thao tác gì trong **30 phút**, when tôi bấm vào bất
   kỳ trang nào cần đăng nhập, then phiên hết hạn và tôi bị đưa về `/login` kèm câu
   **"Phiên đăng nhập đã hết hạn"** (BR8).

## Business rules liên quan

| ID | Rule | Ví dụ với số thật |
|----|------|-------------------|
| BR5 | Sai mật khẩu 5 lần liên tiếp thì khoá tài khoản 15 phút; đăng nhập đúng sẽ đặt bộ đếm về 0 | Sai lúc 20:00, 20:01, 20:02, 20:03, 20:04 → khoá tới 20:19. Vào lúc 20:10 dù đúng mật khẩu vẫn bị từ chối. Vào lúc 20:20 đúng mật khẩu → thành công, bộ đếm về 0. |
| BR6 | Thông báo lỗi đăng nhập không được tiết lộ email có tồn tại hay không | Email không tồn tại → "Email hoặc mật khẩu không đúng". Email tồn tại nhưng sai mật khẩu → **cũng** đúng câu đó. |
| BR7 | Đích đến sau đăng nhập phụ thuộc vai trò | Khách hàng → `/dashboard`. Chủ sân → `/owner/venues`. Quản trị → `/admin`. |
| BR8 | Phiên đăng nhập hết hạn sau 30 phút không hoạt động | Đăng nhập 19:00, thao tác cuối 19:10 → phiên hết hạn 19:40. Bấm vào `/my-bookings` lúc 19:45 → bị đưa về `/login`. |

## Tasks

- [ ] Màn hình `/login` với 2 ô email, mật khẩu và link "Quên mật khẩu" - @thunopro
- [ ] Đếm số lần sai và khoá 15 phút theo BR5 - @thunopro
- [ ] Điều hướng theo vai trò sau khi đăng nhập theo BR7 - @thunopro
- [ ] Hết hạn phiên sau 30 phút không hoạt động theo BR8 - @thunopro
- [ ] Test tự động: sai lần thứ 5 bị khoá, sau 15 phút vào được, thông báo lỗi giống nhau ở cả 2 trường hợp của BR6 - @thunopro

## Ghi chú

Acceptance criterion số 4 là thứ dễ bị bỏ sót nhất khi làm: phản xạ tự nhiên là báo
"Email không tồn tại" cho thân thiện, nhưng như thế là để lộ danh sách email. Ghi rõ
vào đây để người review bắt được nếu làm sai ở Sprint 3.
