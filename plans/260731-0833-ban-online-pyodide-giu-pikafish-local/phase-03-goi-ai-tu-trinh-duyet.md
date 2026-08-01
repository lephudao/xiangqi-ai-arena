# Phase 6.3 — Gọi API AI từ trình duyệt

**Status: XONG phần mã (2026-08-01)** — 172 test xanh, kiểm chứng đường truyền tới cả 5 nhà
cung cấp trong Chrome. **Chưa gọi thử bằng key thật.** Xem "Kết quả".

## Mục tiêu

Trình duyệt gọi thẳng 5 nhà cung cấp bằng key người dùng nhập. **Key không đi qua máy chủ
nào của mình, kể cả ở chế độ local.**

## Đã kiểm chứng — CORS cho phép cả 5 (2026-07-31)

Preflight thật từ origin `https://example.github.io`:

| Nhà cung cấp | Endpoint | Header bắt buộc thêm |
|---|---|---|
| Gemini | `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | — |
| OpenAI | `api.openai.com/v1/chat/completions` | — |
| xAI | `api.x.ai/v1/chat/completions` | — |
| DeepSeek | `api.deepseek.com/chat/completions` | — |
| Anthropic | `api.anthropic.com/v1/messages` | `anthropic-dangerous-direct-browser-access: true` |

Tên header của Anthropic chính là cảnh báo của họ: key ở trình duyệt thì script nào trên
trang cũng đọc được. Phải nói thẳng điều này trong giao diện, không giấu.

## Files tạo

```
web/js/ai-providers/anthropic-client.js
web/js/ai-providers/gemini-client.js
web/js/ai-providers/openai-compatible-client.js   # dùng chung OpenAI + xAI + DeepSeek
web/js/ai-providers/provider-registry.js          # chọn client theo model_key
web/js/key-vault.js                               # localStorage, che khi hiển thị, nút xoá
```

OpenAI/xAI/DeepSeek chung một client vì cùng dạng API — giống cách
`engine/providers/openai_compatible_provider.py` đang làm ở phía Python.

## Điểm phải giữ đúng

### Prompt do Python dựng, không phải JS

`build_move_prompt` chạy trong Pyodide và trả prompt qua `beginTurn()`. JS **chỉ đóng gói và
gửi đi**. Nếu JS tự dựng prompt thì hai chế độ so sánh AI trên hai đề bài khác nhau, mọi số
liệu mất giá trị.

### Nước đi là chuỗi tự do

Giữ đúng luật thi đấu hiện có: không ép enum danh sách nước hợp lệ. Ép enum thì AI nào cũng
đi đúng 100% và mất hẳn tín hiệu "AI có đọc được bàn cờ không".

### Chi phí tính từ `model_registry`

Bảng giá đã có ở `engine/model_registry.py` và chạy được trong Pyodide. JS đọc số token từ
phản hồi API, đưa vào Python tính tiền. Đừng chép bảng giá sang JS — hai bảng lệch nhau là
báo sai chi phí.

## Việc phải làm

1. **5 client** — mỗi cái nhận `{prompt, apiKey, model}` trả `{moveUcci, taunt, thinking,
   tokensIn, tokensOut, latencyMs, error}`. Hình dạng trả về khớp `MoveDecision` của Python.
2. **Cờ năng lực model** — Haiku 4.5 **không** nhận `effort` và adaptive thinking (trả 400).
   `model_registry.py` đã có `supports_effort` / `supports_adaptive_thinking`; JS phải đọc và
   tuân theo, không gửi bừa.
3. **Kho key** — `localStorage` theo nhà cung cấp (một key dùng cho mọi model của họ). Ô nhập
   `type=password`; sau khi lưu chỉ hiện dạng che `sk-ant-…4f2a` để quay video không lộ.
4. **Xử lý lỗi** — hết hạn mức, key sai, `stop_reason: refusal` → ghi vào `decision.error`,
   trọng tài đã có sẵn đường xử lý (đếm `api_errors`, ghi nhật ký).
5. **Thông báo minh bạch** — ngay cạnh ô nhập key:
   > Key lưu trong trình duyệt của bạn và gửi **thẳng** tới nhà cung cấp AI.
   > Không đi qua máy chủ nào của dự án này.
   > Bạn tự trả tiền cho key của mình. Nên dùng key có giới hạn chi tiêu.
6. **Bộ đếm chi phí thời gian thực** + giới hạn số nước, để không ai bấm nhầm rồi cháy tiền.

## Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Hai bản provider (Python cho CLI, JS cho web) lệch nhau | Prompt và tính tiền đều ở Python; JS chỉ là ống dẫn. Chấp nhận phần đóng gói request khác nhau |
| Người dùng dán key vào ô tên kỳ thủ | Cảnh báo khi giá trị trông giống key (`sk-`, `AIza`) |
| Nhà cung cấp đổi CORS, bản online chết câm | Bắt lỗi mạng riêng, hiện thông báo rõ thay vì im lặng rơi về Mock |
| Quay video lộ key | Luôn `type=password`, sau khi lưu chỉ hiện dạng che |

## Tests

| Test | Nội dung |
|---|---|
| Thủ công | Nhập key thật từng nhà cung cấp, đi được ít nhất 1 nước hợp lệ |
| Thủ công | Tab Network: **không** có request nào chứa key đi tới máy chủ của dự án |
| Thủ công | Key sai → hiện lỗi rõ ràng, không im lặng |
| `tests/test_api_key_privacy.py` | Bổ sung: bundle web không nhúng key nào |

Không test tự động phần gọi API thật (tốn tiền, cần key). Kiểm thủ công một lần rồi ghi kết
quả vào báo cáo.

## Acceptance criteria

- [x] **4/5** nhà cung cấp gọi được từ trình duyệt (OpenAI cố ý chặn — xem dưới)
- [x] Prompt do Python dựng, JS không tự chế
- [x] Chi phí tính từ `model_registry`, không chép bảng giá sang JS
- [x] Key hiển thị dạng che, an toàn khi quay màn hình
- [ ] Thông báo minh bạch cạnh ô nhập key — **để phase 6.4** cùng lúc dựng giao diện
- [ ] Gọi thử bằng key thật — **chưa làm**, cần người dùng quyết

---

## Kết quả (2026-08-01)

### Phát hiện quan trọng: OpenAI KHÔNG gọi được từ trình duyệt

Kế hoạch gốc ghi cả 5 nhà cung cấp đều được, dựa trên preflight OPTIONS bằng curl.
**Kết luận đó sai.** Gọi thật từ Chrome mới lộ ra:

```
authorization + content-type  ->  CHẶN: Failed to fetch
chỉ content-type              ->  status 401
chỉ authorization             ->  CHẶN: Failed to fetch
không header nào              ->  status 401
```

Thu hẹp bằng curl: preflight OPTIONS trả 200 kèm `access-control-allow-headers: authorization`
với mọi origin (kể cả localhost). Nhưng phản hồi THẬT của `POST /chat/completions`:

| Request | `access-control-allow-origin` |
|---|---|
| có `Authorization` | **không có** |
| không `Authorization` | `*` |

Đây là chủ ý của OpenAI nhằm chặn dùng API key ở trình duyệt.

**Bài học:** preflight thông không có nghĩa là gọi được. Chỉ gọi thật từ trình duyệt thật mới
kết luận được. Đã ghi vào `model_registry` bằng cờ `browser_cors=False` — cùng chỗ với các dữ
kiện model khác, kèm test canh giữ.

ChatGPT vẫn đấu bình thường ở **bản local**. Bản online chặn từ đầu với lý do rõ ràng
("ChatGPT (GPT-5) chỉ chạy được ở bản local") thay vì để người dùng gặp "Failed to fetch".

### Kiểm chứng đường truyền — dùng key GIẢ cố ý

Lỗi xác thực trả về chính là bằng chứng request tới được nơi cần tới. Không tốn tiền:

| Nhà cung cấp | Lỗi nhận được |
|---|---|
| Anthropic | `invalid x-api-key` |
| Gemini | `API key not valid. Please pass a valid API key.` |
| DeepSeek | `Authentication Fails, Your api key: ****co-y is invalid` |
| xAI | `Incorrect API key provided. You can obtain an API key from https://console.x.ai.` |
| OpenAI | chặn từ đầu, không gửi request |

### Lỗi thứ hai: xAI trả `error` là chuỗi

Các hãng khác dùng `{error: {message}}`, xAI dùng `{error: "chuỗi"}`. Code ban đầu chỉ đọc
`error.message` nên lỗi của xAI biến thành `HTTP 400` trống rỗng — người dùng không biết phải
sửa gì. Thêm `errorMessage()` dùng chung, xử cả hai hình dạng.

### Kiến trúc: JS không giữ bản sao nào của bảng model

`describe_models()` phía Python cung cấp model ID, base URL, `MOVE_SCHEMA` và cờ năng lực
(`supports_effort`, `supports_adaptive_thinking`). Chép sang JS thì hai bảng sẽ lệch, và biểu
hiện ra ngoài là lỗi 400 khó hiểu — ví dụ gửi `effort` cho Haiku 4.5.

Tương tự với tiền: JS chỉ báo số token, `decision_from_payload` tra bảng giá và tính.

### `ExternalProvider` — chỗ suýt sai âm thầm

Ở bản trình duyệt, trọng tài vẫn cần đối tượng kỳ thủ để biết danh tính và "có phải người
chơi không", nhưng không được tự gọi mạng. Nếu để `create_provider` chạy như thường thì nó đi
tìm API key trong biến môi trường, không thấy, rồi **âm thầm rơi về Mock**: người xem tưởng
đang xem Claude đánh cờ mà thật ra là đi ngẫu nhiên.

Thêm `external=True` và `ExternalProvider`. Gọi `decide()` trên nó sẽ báo lỗi thẳng.

### Files

| File | Việc |
|---|---|
| `web/js/key-vault.js` | localStorage theo nhà cung cấp, che key khi hiển thị |
| `web/js/ai-providers/response-shape.js` | Hình dạng quyết định + đọc lỗi + parse JSON |
| `web/js/ai-providers/anthropic-client.js` | Claude, kèm header direct-browser-access |
| `web/js/ai-providers/gemini-client.js` | Gemini, cộng `thoughtsTokenCount` vào token ra |
| `web/js/ai-providers/openai-compatible-client.js` | Grok + DeepSeek (OpenAI bị chặn) |
| `web/js/ai-providers/provider-registry.js` | Chọn client, kiểm key, `checkReady()` |
| `engine/providers/external_provider.py` | Kỳ thủ do bên ngoài quyết định |
| `engine/browser_bridge.py` | `describe_models()`, tính tiền phía Python |
| `engine/model_registry.py` | Cờ `browser_cors` |

### Còn thiếu

**Chưa gọi thử bằng key thật** — nghĩa là đường thành công (parse JSON nước đi từ phản hồi
200) chưa được kiểm trực tiếp ở JS. Code là bản sao của provider Python đã kiểm chứng, nhưng
đó là suy luận chứ không phải bằng chứng.
