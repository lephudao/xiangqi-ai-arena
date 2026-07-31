# Phase 5.3 — TTS Gemini bằng key người dùng

**Status:** pending | **Est:** ~0.5 ngày | **Độc lập với 5.1 và 5.2**

## Vấn đề

TTS hiện dùng Web Speech `vi-VN` của trình duyệt: miễn phí nhưng **giọng máy móc**, ảnh
hưởng trực tiếp chất lượng video.

## Hai điều đã kiểm chứng

### Trình duyệt gọi thẳng Gemini API được

Thử từ `http://localhost:5000` với key sai cố ý: nhận HTTP 400 "API key not valid" chứ không
phải lỗi CORS. Nghĩa là **key TTS không cần đi qua máy chủ** — đây là điểm khác biệt lớn so
với key đánh cờ.

### Gemini TTS trả PCM thô, không phải WAV

```
gemini-3.1-flash-tts-preview  →  audio/l16; rate=24000; channels=1  (base64)
```

Trình duyệt **không phát trực tiếp được** dữ liệu này. Phải tự dựng header WAV 44 byte rồi
mới đưa vào `Audio` hoặc Web Audio API. Đây là chi tiết dễ bỏ sót nhất của phase này.

Model khả dụng (lấy từ API ngày 2026-07-31):

| Model | Ghi chú |
|---|---|
| `gemini-3.1-flash-tts-preview` | Mới nhất |
| `gemini-2.5-flash-preview-tts` | |
| `gemini-2.5-pro-preview-tts` | Có `batchGenerateContent` |

## Files sẽ tạo/sửa

```
web/js/gemini-tts.js       # gọi Gemini, bọc WAV, hàng đợi phát
```
Sửa: `web/app.js` (thay `speakMove`), `web/index.html` (chọn giọng, bật/tắt), `web/style.css`

## Implementation steps

### 1. `gemini-tts.js`

```
speak(text, { apiKey, model, voice })   # gọi API -> bọc WAV -> phát
stop()                                   # dừng câu đang đọc
isAvailable()                            # có key Gemini trong kho chưa
```

Bọc WAV: đọc `rate` từ `mimeType` (đừng hardcode 24000 — Google có thể đổi), dựng header
RIFF/WAVE 44 byte, nối với dữ liệu PCM, tạo `Blob` → `URL.createObjectURL` → `Audio`.

### 2. Hàng đợi, không cắt ngang

Bản Web Speech hiện tại gọi `synth.cancel()` nên câu trước bị cắt giữa chừng khi trận chạy
nhanh. Với Gemini còn tệ hơn vì mỗi câu tốn một lời gọi API.

Quy tắc: **đang đọc thì bỏ qua câu mới**, không xếp hàng dồn. Trận cờ chạy tiếp, đọc trễ 3-4
nước thì vô nghĩa.

### 3. Tự chuyển về Web Speech

Không có key Gemini, hoặc gọi lỗi, hoặc hết hạn mức → **tự dùng Web Speech** và ghi chú
trong giao diện. Không được im lặng mất tiếng.

### 4. Giao diện

Thay công tắc TTS hiện tại bằng:

```
🔊 Đọc tiếng:  [Tắt ▾] [Web Speech (miễn phí)] [Gemini (cần key)]
Giọng:         [Kore ▾]
```

Chỉ hiện lựa chọn Gemini khi kho key đã có key Gemini.

### 5. Nội dung đọc

Giữ nguyên như hiện tại: ký hiệu tiếng Việt + câu thoại.

```
"Pháo 2 bình 5. Pháo về giữa, mũi giáo chỉ thẳng tim địch!"
```

### 6. Chi phí

TTS tính theo token âm thanh đầu ra. Đo thật: câu 11 chữ ở trên tốn 190 token âm thanh.
Trận 100 nước ≈ 19.000 token âm thanh.

**Cần bổ sung giá TTS vào `model_registry` trước khi bật mặc định**, và cộng vào bộ đếm chi
phí — nếu không thì bộ đếm sẽ báo thiếu so với hoá đơn thật.

## Tests

| Test | Nội dung |
|---|---|
`tests/test_gemini_tts_wav.py` (Python, dựng lại logic) | Header WAV đúng 44 byte, `sampleRate` đọc từ mimeType chứ không hardcode |
Thủ công | Không key → dùng Web Speech; có key → giọng Gemini; lỗi API → tự chuyển về, có ghi chú |

Phần gọi API thật không test tự động (tốn tiền, cần key) — kiểm chứng thủ công một lần rồi ghi
kết quả vào báo cáo.

## Risks

| Risk | Xử lý |
|---|---|
| Độ trễ TTS cộng vào độ trễ AI | Đọc **không chặn** nước tiếp theo; trận chạy song song với tiếng |
| Google đổi định dạng trả về | Đọc `mimeType` động thay vì hardcode; lỗi thì tự chuyển về Web Speech |
| Người dùng bất ngờ vì tốn tiền | Ghi rõ "Gemini (cần key, có tính phí)" ngay trên lựa chọn |
| Key Gemini lộ qua devtools | Chấp nhận — key ở trình duyệt của chính người dùng, không gửi đi đâu khác |

## Acceptance criteria

- [ ] Đọc được bằng giọng Gemini với key người dùng nhập
- [ ] Key TTS **không** đi qua máy chủ (kiểm chứng bằng tab Network)
- [ ] Bọc WAV đúng, đọc `sampleRate` từ `mimeType`
- [ ] Không có key hoặc lỗi API → tự chuyển Web Speech, có ghi chú
- [ ] Đang đọc thì bỏ qua câu mới, không dồn hàng đợi
- [ ] Chi phí TTS cộng vào bộ đếm chi phí trận
