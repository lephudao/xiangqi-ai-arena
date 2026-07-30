# Phase 4 — Chế độ Người vs AI

**Status:** pending | **Est:** ~0.5 ngày | **Depends:** Phase 2 (chấm điểm), Phase 3 (persist)

## Vì sao cần

Content mới hoàn toàn khác AI vs AI: *"Tôi thách đấu Claude — và đây là kết quả"*. Người xem
đồng cảm với người thật hơn nhiều so với hai bot đánh nhau. Ngoài ra bạn tự đánh sẽ cảm nhận
trực tiếp AI mạnh/yếu ở đâu — thông tin không con số nào thay được.

Kỹ thuật rẻ vì hạ tầng đã có: trọng tài đã xác thực nước đi, engine đã chấm điểm, chỉ cần
thêm một "provider" nhận nước đi từ chuột thay vì từ API.

## Files sẽ tạo/sửa

```
engine/providers/human_provider.py   # chờ nước đi do người nhập, không gọi API
web/js/human-input.js                # chọn quân -> hiện ô đi được -> gửi nước
```
Sửa: `engine/referee.py` (biết lượt nào là người), `server.py` (`POST /api/matches/<id>/human-move`),
`web/index.html` (chọn "Người chơi" trong dropdown provider), `web/js/board-renderer.js`
(highlight ô hợp lệ)

## Implementation steps

1. **`human_provider.py`** — provider đặc biệt: `decide()` trả về nước đi đã được nạp sẵn từ
   API, hoặc báo "đang chờ người chơi". Không có timeout API, không có retry.
2. **API nhận nước người đi** — `POST /api/matches/<id>/human-move {"ucci": "h2e2"}`.
   Trọng tài xác thực y như với AI (dùng chung `explain_illegal_move`), nước sai trả lỗi
   để UI hiện lý do tiếng Việt thay vì im lặng.
3. **Trạng thái chờ** — thêm `waiting_for_human: bool` vào state; auto-play phải TẠM DỪNG
   khi tới lượt người, không được tự đi thay.
4. **Tương tác bàn cờ** — click quân của mình → gọi `GET /api/matches/<id>/legal-moves?from=h2`
   → highlight các ô đi được → click ô đích để đi. Cho phép click lại để bỏ chọn.
   Lấy danh sách nước hợp lệ từ backend (không nhân bản luật cờ sang JS — tránh 2 nguồn sự thật).
5. **Chấm điểm cho người** — dùng đúng `score_move` như với AI, nên có ngay accuracy % của
   BẠN so với AI. Đây là số liệu hấp dẫn nhất của chế độ này.
6. **Gợi ý (tuỳ chọn)** — nút "Engine khuyên gì?" hiện bestmove. Phải ghi cờ `used_hint`
   vào trận để không làm bẩn số liệu so sánh.

## Tests

| Test | Nội dung |
|------|----------|
`tests/test_human_provider.py` | Nước người đi hợp lệ được nhận; nước sai trả lý do tiếng Việt và KHÔNG được ghi vào lịch sử |
`tests/test_human_match_flow.py` | Lượt người: `waiting_for_human=True`, `step()` không tự đi thay; sau khi nhận nước thì AI đi tiếp bình thường |
Smoke | Trận Người vs mock: đi 5 nước qua API, accuracy của người được tính |

## Risks

| Risk | Xử lý |
|------|-------|
| Auto-play tự đi thay người | Test riêng cho `waiting_for_human`; chặn ở cả backend và frontend |
| Nhân bản luật cờ sang JS gây lệch với backend | Luôn lấy nước hợp lệ từ API, JS chỉ hiển thị |
| Người dùng dùng hint rồi số liệu accuracy mất ý nghĩa | Ghi cờ `used_hint` và loại các nước đó khỏi thống kê so sánh |

## Acceptance criteria

- [ ] Chọn "Người chơi" cho bên Đỏ hoặc Đen trong hộp thoại cấu hình
- [ ] Click quân hiện đúng các ô đi được (lấy từ backend)
- [ ] Nước sai luật hiện lý do tiếng Việt, không đi được
- [ ] Auto-play dừng đúng ở lượt người
- [ ] Accuracy % của người được chấm và so sánh trực tiếp với AI
- [ ] Nước dùng hint bị đánh dấu riêng
