# Phase 6.3 — Gọi API AI từ trình duyệt

**Status:** pending | **Est:** ~0,75 ngày | **Phụ thuộc:** 6.2

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

- [ ] Cả 5 nhà cung cấp gọi được từ trình duyệt bằng key người dùng
- [ ] Tab Network xác nhận key **không** tới máy chủ dự án, kể cả chế độ local
- [ ] Prompt do Python dựng, JS không tự chế
- [ ] Chi phí tính từ `model_registry`, không chép bảng giá sang JS
- [ ] Key hiển thị dạng che, an toàn khi quay màn hình
- [ ] Thông báo minh bạch hiện ngay cạnh ô nhập key
