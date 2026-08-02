# Phase 5.3 — TTS Gemini bằng key người dùng

**Status: XONG phần mã (2026-08-01)** — 179 test xanh, bọc WAV kiểm chứng từng byte trong
Chrome. **Chưa gọi thử bằng key thật.** Xem "Kết quả".

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

- [x] Bọc WAV đúng, đọc `sampleRate` từ `mimeType` — kiểm từng byte header
- [x] Không có key hoặc lỗi API → tự chuyển Web Speech, có ghi chú
- [x] Đang đọc thì bỏ qua câu mới, không dồn hàng đợi
- [x] Chi phí TTS hiện riêng trên bộ đếm, giá lấy từ `model_registry`
- [x] Key TTS không đi qua máy chủ (gọi thẳng bằng `fetch` từ `gemini-tts.js`)
- [ ] Đọc được bằng giọng Gemini thật — **chưa**, cần key thật

---

## Kết quả (2026-08-01)

### Bọc WAV — phần khó nhất, kiểm từng byte

Gemini trả `audio/l16`: mẫu PCM trần, **không có header**. `new Audio()` với dữ liệu này chỉ
im lặng, không báo lỗi gì — kiểu hỏng khó lần ra nhất.

Dựng 100 mẫu PCM tổng hợp rồi soi header sinh ra trong Chrome:

| Trường | Giá trị | Đúng? |
|---|---|---|
| `RIFF` / `WAVE` / `fmt ` / `data` | đủ 4 dấu hiệu | ✅ |
| chunkSize | 236 = 36 + 200 | ✅ |
| audioFormat | 1 (PCM không nén) | ✅ |
| byteRate | 48000 = 24000 × 1 × 2 | ✅ |
| blockAlign | 2 | ✅ |
| dataSize | 200 | ✅ |
| PCM tại offset 44 | `[0,1,2,3]` nguyên vẹn | ✅ |

Header đúng chưa chắc trình duyệt giải mã được, nên kiểm thêm bằng dữ liệu thật: dựng 0,25
giây sóng sin 440Hz rồi cho `decodeAudioData` giải mã → **thời lượng đúng 0,25 giây**. Đây là
bằng chứng trường `sampleRate` được đọc đúng; sai tần số thì thời lượng lệch ngay.

`parseAudioMime` đọc động, không hardcode: thử `rate=48000; channels=2` ra đúng 48000/2. Đoán
sai tần số thì tiếng vẫn phát — chỉ là nhanh hoặc chậm bất thường như băng tua, không có
thông báo nào.

### Lỗi bắt được: trình duyệt tự bật lựa chọn TỐN TIỀN

Chrome khôi phục giá trị `<select>` giữa các tab cùng origin. Tab mới mở tự nhảy sang
"Gemini (tính phí)" dù HTML ghi `selected` ở "Web Speech" — người dùng không hề chọn mà vẫn
bị tính tiền.

Không phó mặc cho hành vi khôi phục của trình duyệt: đặt tường minh từ `localStorage`, mặc
định Web Speech. Lựa chọn Gemini chỉ được nhớ khi người dùng **tự bấm chọn**.

### Giá TTS lấy từ trang chính thức, không đoán

Lấy ngày 2026-08-01 từ ai.google.dev/gemini-api/docs/pricing:

| Model | Vào ($/1M) | Ra, âm thanh ($/1M) |
|---|---|---|
| `gemini-2.5-flash-preview-tts` | 0,50 | 10,00 |
| `gemini-3.1-flash-tts-preview` | 1,00 | 20,00 |
| `gemini-2.5-pro-preview-tts` | 1,00 | 20,00 |

Mặc định chọn bản 2.5 Flash — rẻ bằng nửa và đủ tốt cho lời bình.

TTS_MODELS nằm **ngoài** `ALL_MODELS` để không lọt vào danh sách chọn kỳ thủ, nhưng vẫn vào
`_BY_KEY` để `estimate_cost_usd` tra được giá.

Chi phí đọc hiện **riêng** trên bộ đếm, không cộng vào chi phí trận: tiếng đọc không thuộc
về bên Đỏ hay bên Đen nào, gộp vào là quy sai trách nhiệm chi phí.

### Files

| File | Việc |
|---|---|
| `web/js/gemini-tts.js` (mới) | Gọi API, bọc WAV, phát, đếm chi phí |
| `engine/model_registry.py` | `TTS_MODELS` + giá thật |
| `engine/browser_bridge.py` | `describe_tts_models`, `tts_cost_usd` |
| `server.py` | `/api/models` kèm `tts_models` |
| `web/app.js` | Định tuyến Web Speech / Gemini / Tắt, tự chuyển khi lỗi |
| `web/index.html` | Chọn chế độ đọc, model, giọng; ô chi phí đọc riêng |

### Kiểm thân request mà không tốn tiền (2026-08-02)

Phát hiện dùng được: **Google kiểm hình dạng JSON TRƯỚC khi kiểm API key.** Gửi trường bịa
đặt với key giả sẽ nhận `Invalid JSON payload received. Unknown name "..."`, còn thân request
đúng thì chỉ nhận `API key not valid`. Nhờ vậy kiểm được cấu trúc request miễn phí.

| Biến thể gửi thử | Kết quả |
|---|---|
| Thân request **đúng như mã đang gửi** | chỉ lỗi key → **cấu trúc đúng** |
| `responseModalities: ["KHONG_CO_THAT"]` | bị từ chối → `["AUDIO"]` là enum hợp lệ |
| `speechConfig: {voiceName: ...}` (phẳng) | bị từ chối → cách lồng hiện tại mới đúng |
| Tên giọng bịa đặt | **qua được** → không kiểm được tên giọng bằng cách này |
| Model ID bịa đặt | chỉ lỗi key → không kiểm được model ID bằng cách này |

### Còn thiếu

**Chưa gọi thử bằng key thật.** Đã kiểm chắc:

- Bọc WAV (từng byte header + `decodeAudioData` giải mã đúng thời lượng)
- Cấu trúc thân request TTS
- Định tuyến Web Speech / Gemini / Tắt, và đường tự chuyển khi lỗi

**Chưa kiểm được nếu không có key:**

- 3 model ID TTS có tồn tại không
- 8 tên giọng (`Kore`, `Puck`, …) có còn hiệu lực không
- Đường phản hồi `candidates[0].content.parts[].inlineData.{mimeType,data}` có đúng không
- `candidatesTokenCount` có phải token âm thanh để tính tiền không

Một lần gọi thật (~$0,002) là đủ để chốt cả bốn.
