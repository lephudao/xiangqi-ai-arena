# Phase 6 — Bản online chạy trình duyệt, bản local giữ Pikafish thật

**Status:** chưa bắt đầu | **Ngày:** 2026-07-31 | **Est: 2,5–3 ngày**

Thay thế [phase 5.2](../260731-0753-byok-tts-trien-khai-cong-khai/phase-02-trien-khai-cong-khai.md)
(đã hoãn — hướng Docker/máy chủ công khai).

## Mục tiêu

Một mã nguồn, hai chế độ:

| | Bản online (GitHub Pages) | Bản local (máy bạn) |
|---|---|---|
| Ai chạy luật cờ | Pyodide trong trình duyệt | Pyodide trong trình duyệt |
| Ai gọi API AI | Trình duyệt | Trình duyệt |
| Chấm điểm | ❌ không có | ✅ **Pikafish thật** qua máy chủ local |
| Lưu trận / Elo | IndexedDB | ✅ SQLite |
| Máy chủ | không có | Flask trên máy bạn |
| Key đi đâu | thẳng tới nhà cung cấp AI | thẳng tới nhà cung cấp AI |

Bản local là **studio quay video** (đủ tính năng). Bản online là **bản demo** cho người xem
tự thử bằng key của họ.

## Nguyên tắc thiết kế: Python = logic thuần, JS = vào/ra

Đây là điều giữ cho hai chế độ không lệch nhau.

**Lõi Python chạy ở cả hai nơi (1.087 dòng, một bản duy nhất):**

| Module | Dòng | Vì sao chạy được trong trình duyệt |
|---|---|---|
| `engine/xiangqi/` | 759 | chỉ import thư viện chuẩn |
| `engine/prompt_builder.py` | 147 | chỉ import `engine.xiangqi.notation` |
| `engine/analysis/move_quality_scorer.py` | 135 | chỉ `math` + `dataclasses` |
| `engine/storage/elo_rating.py` | 46 | không import gì |

`engine/referee.py` (463) cũng chạy cả hai nơi **sau khi tách phần gọi mạng ra** (phase 6.1).

**Chỉ ở máy chủ:** `engine/analysis/pikafish_engine.py` (249, `subprocess`+`threading`),
`engine/storage/match_repository.py` (SQLite), `engine/providers/*` bản SDK (cho CLI).

**Chỉ ở trình duyệt (viết mới):** nạp Pyodide, 5 provider gọi API bằng `fetch`, IndexedDB.

### Vì sao không port luật cờ sang JS

Chân mã, mắt tượng, ngòi pháo, tướng đối mặt, binh qua hà — hai bản luật lệch nhau một chỗ là
AI đi được nước phi pháp mà **không ai phát hiện**, và mọi số liệu Elo/độ chính xác thành vô
nghĩa. Pyodide đắt hơn (~10MB tải lần đầu) nhưng loại bỏ hẳn rủi ro này.

## Các phase

| Phase | Nội dung | File | Est. |
|---|---|---|---|
| 6.1 | Tách phần gọi mạng khỏi trọng tài | [phase-01-tach-io-khoi-trong-tai.md](phase-01-tach-io-khoi-trong-tai.md) | ~0,5 ngày |
| 6.2 | Chạy lõi Python trong trình duyệt (Pyodide) | [phase-02-pyodide-trong-trinh-duyet.md](phase-02-pyodide-trong-trinh-duyet.md) | ~0,75 ngày |
| 6.3 | Gọi API AI từ trình duyệt (5 nhà cung cấp) | [phase-03-goi-ai-tu-trinh-duyet.md](phase-03-goi-ai-tu-trinh-duyet.md) | ~0,75 ngày |
| 6.4 | Hai chế độ, lưu trữ, triển khai | [phase-04-hai-che-do-va-trien-khai.md](phase-04-hai-che-do-va-trien-khai.md) | ~0,5–1 ngày |

**Thứ tự bắt buộc:** 6.1 → 6.2 → 6.3 → 6.4. Không rút ngắn được vì mỗi phase là tiền đề của
phase sau.

## Đã kiểm chứng (2026-07-31)

### Cả 5 nhà cung cấp cho trình duyệt gọi thẳng

Test preflight CORS thật từ origin `https://example.github.io`:

| Nhà cung cấp | Kết quả | Điều kiện |
|---|---|---|
| Gemini | ✅ | |
| OpenAI | ✅ | |
| xAI (Grok) | ✅ `allow-origin: *` | |
| DeepSeek | ✅ | |
| Anthropic | ✅ | bắt buộc header `anthropic-dangerous-direct-browser-access: true` |

Key đi thẳng từ trình duyệt tới nhà cung cấp, **không qua máy chủ nào của mình** — kể cả ở
chế độ local.

### Pikafish không có bản WASM

npm không có `pikafish` lẫn `pikafish.wasm`. Bản online **không chấm điểm** — đây là lý do
chính để giữ bản local.

## Rủi ro chính

| Rủi ro | Xử lý |
|---|---|
| Pyodide nặng, tải lâu lần đầu | Hiện tiến trình nạp; cache trình duyệt lo lần sau; bàn cờ vẽ trước khi Pyodide sẵn sàng |
| Refactor trọng tài làm hỏng bản local đang chạy tốt | 151 test hiện có là lưới an toàn; phase 6.1 **không được** để test nào đỏ |
| Hai chế độ lệch hành vi | Cùng một `referee.py` chạy cả hai nơi; khác biệt duy nhất là provider và có/không Pikafish |
| Tên header `anthropic-dangerous-direct-browser-access` làm người dùng lo | Nói thẳng trong giao diện: key nằm ở trình duyệt của chính họ |
| Người dùng hết tiền vì bấm nhầm | Hiện chi phí luỹ kế theo thời gian thực; có giới hạn số nước |

## Câu hỏi chưa giải quyết

1. Bản online có cần chế độ Người vs AI không, hay chỉ AI vs AI cho gọn?
2. Bản online có cần xem lại (replay) từ IndexedDB không, hay bỏ luôn?
3. Repo công khai ngay hay chờ quay xong loạt video đầu?
