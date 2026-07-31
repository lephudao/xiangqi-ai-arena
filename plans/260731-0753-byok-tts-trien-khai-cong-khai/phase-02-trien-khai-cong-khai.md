# Phase 5.2 — Triển khai công khai miễn phí

**Status: HOÃN (2026-07-31)** — chốt hướng chỉ chạy local, chia sẻ mã nguồn qua GitHub.
Giữ tài liệu này vì phần khảo sát nền tảng và các vấn đề đa người dùng vẫn đúng nếu sau này
muốn mở lại. Xem [plan.md](plan.md) mục "Quyết định: chỉ chạy local" trước khi dùng lại.

**Est:** ~1 ngày | **Depends:** 5.1

## Chọn nền tảng

Ràng buộc thật của hệ thống:

- Pikafish là **binary gốc** (632KB) + bảng NNUE **51MB** → cần Docker hoặc ổ đĩa ghi được
- Trận đấu **có trạng thái trong bộ nhớ**, chạy 10-60 phút → không hợp serverless
- SQLite cần **ổ đĩa ghi được**

| Nền tảng | Miễn phí thật | Chạy Pikafish | Nhược điểm |
|---|---|---|---|
| **Hugging Face Spaces (Docker)** | ✅ CPU basic, 16GB RAM | ✅ | Space công khai, mọi người chung một máy |
| Render (free web service) | ✅ | ✅ Docker | Ngủ sau 15 phút không dùng, ổ đĩa tạm → mất cơ sở dữ liệu |
| Fly.io | Hạn mức nhỏ | ✅ | Cần thẻ tín dụng |
| Railway | Chỉ tín dụng dùng thử | ✅ | Hết tín dụng là dừng |
| Vercel / Netlify | ✅ | ❌ | Serverless, không chạy được binary lâu dài |

**Đề xuất: Hugging Face Spaces.** Miễn phí thật, chạy Docker, không ngủ, đủ RAM cho Pikafish.

## Vấn đề phải giải trước khi mở công khai

### 1. Trạng thái toàn cục bị chia sẻ giữa mọi người dùng — CHẶN ĐƯỜNG

`server.py` giữ một `manager` toàn cục, và các route không có `match_id` (`/api/state`,
`/api/step`, `/api/reset`) tác động lên **"trận đang xem"** dùng chung.

Trên bản công khai, hai người vào cùng lúc sẽ **đá nhau ra khỏi trận của nhau**.

Hạ tầng đã sẵn (`/api/matches/<id>/…`), chỉ cần:
- Giao diện tạo `match_id` riêng khi vào trang, lưu `sessionStorage`
- Mọi lời gọi dùng route theo `match_id`
- Route không có id chỉ giữ cho chế độ local một người

### 2. Giới hạn tài nguyên

| Hạng mục | Hiện tại | Cần cho bản công khai |
|---|---|---|
| Số trận trong bộ nhớ | 20 | Giữ 20, nhưng dọn theo thời gian không hoạt động |
| Số nước mỗi trận | không giới hạn ở giao diện | Giới hạn 60 (biến môi trường) |
| Thời gian phân tích engine | 300ms/nước | Giảm còn 150ms, hoặc tắt hẳn |
| Tần suất gọi API | không giới hạn | Giới hạn theo IP cho `/api/*/step` |

### 3. Cơ sở dữ liệu tách riêng

Trận của người lạ **không được trộn vào bảng Elo của bạn**, nếu không thì bảng xếp hạng dùng
cho video sẽ bị nhiễu.

Thêm biến `ARENA_DB_PATH`; bản công khai dùng cơ sở dữ liệu riêng, hoặc đặt
`ARENA_PUBLIC_MODE=1` để không ghi Elo.

### 4. Chế độ công khai

Thêm `ARENA_PUBLIC_MODE=1` bật một loạt hành vi:

- Ẩn nút xoá trận, ẩn danh sách trận của người khác
- Bắt buộc mỗi phiên một `match_id`
- Áp giới hạn số nước và tần suất
- Hiện thông báo BYOK ngay lần đầu vào

## Files sẽ tạo/sửa

```
Dockerfile              # dựng ảnh, cài Pikafish trong lúc build
.dockerignore
docs/deployment-guide.md   # bổ sung mục triển khai công khai
```
Sửa: `server.py` (chế độ công khai, giới hạn tần suất), `web/app.js` (mỗi phiên một trận),
`engine/match_manager.py` (dọn theo thời gian không hoạt động)

## Implementation steps

1. **Dockerfile** — Python 3.13 slim, cài phụ thuộc, chạy `install-pikafish.sh` trong lúc
   build (ảnh có sẵn engine, khởi động không phải tải 51MB).
2. **Mỗi phiên một trận** — giao diện gọi `POST /api/matches` khi vào trang, lưu id vào
   `sessionStorage`, mọi lời gọi sau dùng id đó.
3. **Giới hạn tần suất** — đếm theo IP trong bộ nhớ cho `/api/*/step` và `/api/*/human-move`.
   Không cần thư viện ngoài, một dict với cửa sổ trượt là đủ.
4. **Dọn trận cũ** — loại trận không hoạt động quá 30 phút, thay vì chỉ dọn khi vượt số lượng.
5. **Biến môi trường mới** — `ARENA_PUBLIC_MODE`, `ARENA_DB_PATH`, `ARENA_MAX_PLIES`,
   `ARENA_RATE_LIMIT_PER_MIN`.
6. **Trang giới thiệu** — lần đầu vào hiện hộp thoại giải thích BYOK và cách lấy key miễn phí
   của Google.

## Tests

| Test | Nội dung |
|---|---|
`tests/test_public_mode.py` | Hai phiên khác nhau không đá nhau; giới hạn số nước có hiệu lực; vượt tần suất trả 429 |
`tests/test_match_manager.py` | Bổ sung: dọn trận theo thời gian không hoạt động |
Thủ công | Mở hai trình duyệt khác nhau, đấu song song, không ảnh hưởng nhau |

## Risks

| Risk | Xử lý |
|---|---|
| Người dùng nghi ngờ máy chủ ăn cắp key | Mã nguồn mở + test canh giữ + thông báo thẳng thắn; không hứa điều không đúng |
| Một người chiếm hết CPU | Giới hạn số nước + giới hạn tần suất + giảm thời gian phân tích engine |
| Cơ sở dữ liệu phình to | Dọn trận cũ hơn N ngày; hoặc bản công khai không ghi cơ sở dữ liệu |
| Space bị lạm dụng để gọi API chùa | Không thể — người dùng dùng key của chính họ, bạn không trả tiền LLM |
| Mất cơ sở dữ liệu khi Space khởi động lại | Chấp nhận; bản công khai là để thử, không phải lưu trữ |

## Acceptance criteria

- [ ] Dockerfile dựng được ảnh chạy đủ cả Pikafish
- [ ] Hai người dùng đồng thời không đá nhau ra khỏi trận
- [ ] `ARENA_PUBLIC_MODE=1` áp giới hạn số nước và tần suất
- [ ] Cơ sở dữ liệu công khai tách khỏi cơ sở dữ liệu cá nhân
- [ ] Trang đầu giải thích rõ BYOK trước khi người dùng nhập key
- [ ] Không có key nào xuất hiện trong nhật ký máy chủ khi chạy công khai
