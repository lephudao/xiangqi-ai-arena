# Phase 5 — Người dùng tự nhập key, chạy công khai miễn phí, TTS Gemini

**Status:** Phase 5.0 XONG (vá lộ key) · 5.1-5.3 chưa bắt đầu | **Ngày:** 2026-07-31

## Bối cảnh

Ba yêu cầu:

1. **Elo từ trận đấu trên giao diện** — ✅ đã hoạt động, không cần làm gì (xem mục "Đã xong")
2. **Chia sẻ mã lên GitHub mà không lộ key + chạy online miễn phí cho người dùng tự nhập key**
3. **TTS dùng Gemini với key do người dùng cung cấp**

## Đã xong trước khi lập kế hoạch này

### Elo tự ghi khi đấu trên giao diện ✅

Kiểm chứng thật: trận mock đấu tới chiếu bí sau 310 nước → Elo cập nhật tự động, kỳ thủ
thắng +16, thua −16. Bạn chỉ cần đấu bình thường trên giao diện, không phải làm gì thêm.

Chỉ trận **kết thúc đúng luật cờ** mới tính Elo. Trận bạn bấm dừng giữa chừng sẽ nằm trong
danh sách xem lại nhưng không vào bảng xếp hạng.

### Vá lỗ hổng lộ key ✅ (commit riêng)

`/api/state` trả nguyên cấu hình kỳ thủ, trong đó có `api_key` người dùng gửi lên. Bất kỳ ai
đọc được trạng thái trận đều lấy được key. **Đây là lỗ hổng chặn đường toàn bộ ý tưởng cho
người dùng nhập key.**

Đã tách key khỏi cấu hình công khai, thêm 8 test canh giữ (quét phản hồi API, nhật ký trọng
tài, lịch sử nước đi, và quét thẳng file cơ sở dữ liệu ở mức byte).

### Lịch sử git sạch ✅

Quét toàn bộ commit: không có chuỗi nào giống API key. `.env.local`, `data/`, `engine/bin/`
đều đã bị chặn khỏi git.

## Các phase

| Phase | Nội dung | File | Ưu tiên | Est. |
|---|---|---|---|---|
| 5.1 | Giao diện nhập key an toàn (BYOK) | [phase-01-byok-nhap-key.md](phase-01-byok-nhap-key.md) | 🔴 Cần trước khi công khai | ~0.5 ngày |
| 5.2 | Triển khai công khai miễn phí | [phase-02-trien-khai-cong-khai.md](phase-02-trien-khai-cong-khai.md) | 🟠 | ~1 ngày |
| 5.3 | TTS Gemini bằng key người dùng | [phase-03-gemini-tts.md](phase-03-gemini-tts.md) | 🟡 Độc lập, làm lúc nào cũng được | ~0.5 ngày |

**Dependencies:** 5.2 phụ thuộc 5.1 (không được mở công khai khi chưa có luồng nhập key rõ
ràng). 5.3 độc lập hoàn toàn.

## Hai phát hiện kỹ thuật đã kiểm chứng

### Trình duyệt gọi thẳng Gemini API được (CORS cho phép)

Đã thử từ `http://localhost:5000`: nhận HTTP 400 "API key not valid" thay vì lỗi CORS.
Nghĩa là **key TTS không cần đi qua máy chủ** — ở lại hoàn toàn trong trình duyệt.

### Gemini TTS trả PCM thô, không phải WAV

`gemini-3.1-flash-tts-preview` trả `audio/l16; rate=24000; channels=1` dạng base64.
Trình duyệt phải tự bọc header WAV mới phát được — đây là chi tiết dễ bỏ sót.

## Khác biệt căn bản giữa hai loại key

Đây là điểm quyết định toàn bộ thiết kế:

| | Key cho AI đánh cờ | Key cho TTS |
|---|---|---|
| Ai gọi API | **Máy chủ** (vòng lặp trọng tài chạy ở máy chủ) | **Trình duyệt** |
| Key đi đâu | Phải gửi lên máy chủ | Không rời trình duyệt |
| Rủi ro | Người vận hành máy chủ về lý thuyết thấy được key | Không có |
| Cách giảm rủi ro | Mã nguồn mở để kiểm chứng + không lưu/log/echo + HTTPS | Không cần |

**Không thể** cho trình duyệt gọi thẳng API đánh cờ, vì trọng tài phải xác thực nước đi,
chấm điểm và giữ trạng thái ván — toàn bộ nằm ở máy chủ. Nói thẳng điều này với người dùng
là cách duy nhất giữ uy tín.

## Quyết định cần bạn chọn

1. **Nền tảng triển khai** — xem bảng so sánh trong [phase 5.2](phase-02-trien-khai-cong-khai.md).
   Đề xuất: Hugging Face Spaces (Docker, miễn phí thật, chạy được Pikafish).
2. **Bản công khai có bật chấm điểm Pikafish không?** Bật thì tốn CPU chung, nhiều người dùng
   cùng lúc sẽ chậm. Tắt thì mất phần hấp dẫn nhất.
3. **Có giới hạn số nước mỗi trận trên bản công khai không?** Đề xuất 60 nước để tránh một
   người chiếm máy quá lâu.

## Câu hỏi chưa giải quyết

1. Bản công khai có cần lưu trận của người dùng vào cơ sở dữ liệu không? Nếu có thì Elo của
   họ trộn với Elo của bạn — nên tách hai cơ sở dữ liệu.
2. Có muốn giữ bản công khai đồng bộ với bản local qua GitHub Actions, hay deploy thủ công?
