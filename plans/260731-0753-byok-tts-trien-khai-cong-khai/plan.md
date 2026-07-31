# Phase 5 — Người dùng tự nhập key, chạy công khai miễn phí, TTS Gemini

**Status:** 5.0 XONG (vá lộ key) · **5.2 HOÃN** (chốt chỉ chạy local) · 5.1 và 5.3 chưa bắt
đầu | **Ngày:** 2026-07-31

## Quyết định: chỉ chạy local (2026-07-31)

Chốt **không dựng bản online**. Hệ thống chạy local để quay video, chia sẻ mã nguồn qua
GitHub cho người xem tự clone và chạy bằng key của họ.

Ghi lại lý do và các dữ kiện đã kiểm chứng, để nếu sau này đổi ý thì không phải khảo sát lại:

### Bản online là khả thi và miễn phí — cái tốn là công, không phải tiền

Đã kiểm preflight CORS thật (2026-07-31): **cả 5 nhà cung cấp đều cho trình duyệt gọi thẳng**,
nghĩa là key có thể đi từ trình duyệt người dùng tới thẳng máy chủ AI, không qua máy chủ nào
của mình.

| Nhà cung cấp | Kết quả | Điều kiện |
|---|---|---|
| Gemini | ✅ | |
| OpenAI | ✅ | |
| xAI (Grok) | ✅ `allow-origin: *` | |
| DeepSeek | ✅ | |
| Anthropic | ✅ | bắt buộc header `anthropic-dangerous-direct-browser-access: true` |

Host tĩnh (GitHub Pages / Cloudflare Pages) **miễn phí, không cần Docker, không cần máy chủ**.
Chi phí LLM do người dùng tự trả bằng key của họ.

### Cái chặn thật: luật cờ đang nằm ở máy chủ

`engine/xiangqi/` (759 dòng) chạy server-side. Bỏ máy chủ thì phần này phải vào trình duyệt.

**Pyodide là đường đi tốt nhất nếu mở lại:** đã kiểm — `engine/xiangqi/` chỉ import thư viện
chuẩn, **không phụ thuộc ngoài**, nên chạy nguyên xi trong Pyodide không sửa dòng nào. JS chỉ
lo vòng lặp và gọi API. Tránh được cái bẫy lớn nhất là **nhân đôi luật cờ** — hai bản luật
lệch nhau (chân mã, mắt tượng, ngòi pháo, lộ mặt tướng) thì AI đi được nước phi pháp mà
không ai biết. Giá: tải ~10MB lần đầu.

### Pikafish không lên web được

Không có bản WASM chính thức (npm không có `pikafish` lẫn `pikafish.wasm`). Thay thế khả dĩ:
`fairy-stockfish-nnue.wasm` (npm, 1.7MB, Fairy-Stockfish có hỗ trợ cờ tướng) — **yếu hơn
Pikafish**, và **chưa kiểm chứng** bản WASM có bật biến thể xiangqi hay không.

### Hệ quả cho các phase còn lại

- **5.1 (BYOK)** vẫn còn giá trị nhưng **thu hẹp**: chỉ cần lưu key vào `localStorage` để đỡ
  gõ lại mỗi lần mở trang, cộng nút xoá. Không cần thông báo minh bạch dài dòng nữa vì người
  dùng tự chạy máy chủ trên máy của chính họ.
- **5.3 (TTS Gemini)** không đổi gì — vẫn gọi thẳng từ trình duyệt.
- **5.2** hoãn.

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
| 5.1 | Nhớ key trong trình duyệt (thu hẹp) | [phase-01-byok-nhap-key.md](phase-01-byok-nhap-key.md) | 🟡 Tiện lợi, không gấp | ~0.25 ngày |
| 5.2 | Triển khai công khai miễn phí | [phase-02-trien-khai-cong-khai.md](phase-02-trien-khai-cong-khai.md) | ⬜ **HOÃN** | — |
| 5.3 | TTS Gemini bằng key người dùng | [phase-03-gemini-tts.md](phase-03-gemini-tts.md) | 🟠 Ảnh hưởng trực tiếp chất lượng video | ~0.5 ngày |

**Dependencies:** không còn phụ thuộc nào — 5.1 và 5.3 độc lập, làm cái nào trước cũng được.
Ưu tiên 5.3 vì giọng đọc ảnh hưởng thẳng tới video.

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

## Đã làm cho hướng chia sẻ mã nguồn

- `.env.example` — README bảo người xem copy file này nhưng nó **chưa tồn tại**; ai clone về
  là tắc ngay bước đầu. Đã tạo, kèm giải thích từng biến và cảnh báo về `HOST=0.0.0.0`.
- README thêm mục "An toàn key khi chia sẻ mã nguồn".

## Câu hỏi chưa giải quyết

1. Repo có công khai ngay không, hay để private tới khi quay xong loạt video đầu?
2. Có cần thêm LICENSE không? Pikafish là GPL nhưng dự án chỉ **tải về lúc cài**, không kèm
   binary trong repo, nên không bị ràng buộc lây.
