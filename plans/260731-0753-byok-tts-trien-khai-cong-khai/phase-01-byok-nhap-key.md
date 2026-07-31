# Phase 5.1 — Giao diện nhập key an toàn (BYOK)

**Status:** pending | **Est:** ~0.5 ngày | **Blocks:** 5.2

## Vấn đề

Hộp thoại cấu hình hiện có ô nhập API key, nhưng:

- Key gõ vào **không được lưu**, mở lại trang là mất → người dùng phải gõ lại mỗi lần
- Key **gửi kèm mọi lần `/api/reset`** dù trận không đổi model
- Không nói gì với người dùng về việc key đi đâu, có bị lưu không
- Không có cách xoá key đã nhập
- Không phân biệt "chạy local với key của mình trong `.env.local`" và "chạy công khai, người
  dùng tự nhập"

## Nguyên tắc

1. **Key sống trong `localStorage` của trình duyệt**, không nằm trong mã nguồn, không nằm
   trong cơ sở dữ liệu máy chủ.
2. **Chỉ gửi lên máy chủ khi bắt đầu/lập lại trận** — không đính kèm vào mọi lời gọi.
3. **Nói thẳng với người dùng** key đi đâu. Không hứa "key không rời máy bạn" vì với AI đánh
   cờ điều đó không đúng.
4. **Xoá được** bằng một nút.

## Files sẽ tạo/sửa

```
web/js/key-vault.js        # đọc/ghi/xoá key trong localStorage, che khi hiển thị
```
Sửa: `web/index.html` (hộp thoại cấu hình), `web/app.js`, `web/style.css`,
`engine/model_registry.py` (báo model nào cần key nào)

## Implementation steps

### 1. `key-vault.js` — kho key phía trình duyệt

```
saveKey(providerKey, value)     # lưu vào localStorage
getKey(providerKey)             # đọc
clearKey(providerKey)           # xoá một key
clearAll()                      # xoá tất cả
maskKey(value)                  # "sk-ant-…4f2a" để hiển thị lại mà không lộ toàn bộ
listStoredProviders()           # provider nào đã có key
```

Lưu theo **provider** (`anthropic`, `gemini`, `openai`, `xai`, `deepseek`) chứ không theo
model, vì một key dùng chung cho mọi model của nhà cung cấp đó.

### 2. Hộp thoại cấu hình: một khu vực quản lý key riêng

Tách khỏi phần chọn kỳ thủ. Mỗi nhà cung cấp một dòng:

```
Anthropic   [••••••••4f2a]  ✅ đã lưu    [Xoá]
Google      [nhập key...]   ⚠️ chưa có   [Lưu]
OpenAI      [nhập key...]   ⚠️ chưa có   [Lưu]
```

Trạng thái lấy từ `key-vault`, không hỏi máy chủ.

### 3. Thông báo minh bạch — bắt buộc

Đặt ngay trong khu vực nhập key, không giấu trong tài liệu:

> **Key của bạn đi đâu?**
> Key được lưu trong trình duyệt của bạn (localStorage), không gửi đi đâu khác ngoài lúc
> bắt đầu trận.
> Khi AI đánh cờ, key **được gửi tới máy chủ này** để máy chủ gọi API — vì vòng lặp trọng
> tài chạy ở máy chủ. Máy chủ **giữ key trong bộ nhớ tạm cho trận đó, không ghi ra đĩa,
> không ghi vào nhật ký, không trả lại trong bất kỳ phản hồi nào**.
> Mã nguồn mở, bạn kiểm chứng được: `engine/referee.py`, `tests/test_api_key_privacy.py`.
> Riêng phần đọc tiếng (TTS) gọi thẳng từ trình duyệt — key không đi qua máy chủ.

### 4. Cảnh báo khi chọn model chưa có key

Khi chọn kỳ thủ mà chưa có key tương ứng, hiện cảnh báo ngay trong hộp thoại thay vì để
người dùng bắt đầu trận rồi mới thấy nó rơi về Mock.

`/api/models` bổ sung trường `api_key_env` để giao diện biết model nào cần key nào.

### 5. Chế độ máy chủ có sẵn key

Khi chạy local với `.env.local`, người dùng không cần nhập gì. Thêm vào `/api/models`:

```json
{ "server_has_keys": ["anthropic", "gemini"] }
```

Giao diện thấy nhà cung cấp nào máy chủ đã có key thì hiện "✅ máy chủ đã cấu hình" và
không đòi nhập. **Chỉ trả tên nhà cung cấp, tuyệt đối không trả giá trị key.**

## Tests

| Test | Nội dung |
|---|---|
`tests/test_api_key_privacy.py` | Đã có 8 test; bổ sung: `/api/models` không lộ giá trị key, chỉ lộ tên nhà cung cấp |
Thủ công | Nhập key → tải lại trang → key vẫn còn; bấm Xoá → mất; chọn model chưa có key → hiện cảnh báo |

## Risks

| Risk | Xử lý |
|---|---|
| `localStorage` bị mã độc trên cùng tên miền đọc được | Không tránh được về mặt kỹ thuật; nói rõ trong thông báo và khuyến nghị dùng key có giới hạn chi tiêu |
| Người dùng dán nhầm key vào ô tên kỳ thủ | Ô tên kỳ thủ cảnh báo nếu giá trị trông giống key (bắt đầu bằng `sk-`, `AIza`) |
| Quay video lộ key trên màn hình | Ô nhập luôn là `type=password`; sau khi lưu chỉ hiện dạng che |

## Acceptance criteria

- [ ] Key lưu trong `localStorage`, còn sau khi tải lại trang
- [ ] Có nút xoá từng key và xoá tất cả
- [ ] Thông báo minh bạch hiển thị ngay cạnh ô nhập, nói rõ key đi tới máy chủ
- [ ] Chọn model chưa có key thì cảnh báo trước khi bắt đầu trận
- [ ] `/api/models` báo được nhà cung cấp nào máy chủ đã có key, không lộ giá trị
- [ ] Key hiển thị lại dưới dạng che, an toàn khi quay màn hình
