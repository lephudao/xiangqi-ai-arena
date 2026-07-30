# Đại Chiến AI Cờ Tướng (Xiangqi AI Arena)

Đấu trường cờ tướng giữa các LLM (Gemini, ChatGPT, Claude, Grok, …) — đo sức mạnh tính toán
thật của từng AI và làm nguồn nội dung cho kênh YouTube.

## Chạy nhanh

```bash
./run.sh                      # tạo venv, cài deps, chạy server
# hoặc
venv/bin/python3 server.py
```
Mở http://localhost:5000

Không cần API key: mặc định cả hai bên chạy chế độ **Mock** (chọn nước hợp lệ ngẫu nhiên)
để thử giao diện và quy trình quay video.

## Cấu hình

Copy `.env.example` → `.env.local` (file này đã được gitignore, an toàn để chứa key thật):

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `ANTHROPIC_API_KEY` | rỗng | Cho Claude. Không có key → tự động dùng Mock và ghi rõ lý do vào log |
| `GEMINI_API_KEY` | rỗng | Cho Gemini |
| `OPENAI_API_KEY` / `XAI_API_KEY` / `DEEPSEEK_API_KEY` | rỗng | ChatGPT / Grok / DeepSeek (code đã viết, **chưa kiểm chứng** bằng key thật) |
| `PIKAFISH_PATH` | engine/bin/pikafish | Engine chấm điểm; cài bằng `./scripts/install-pikafish.sh` |
| `PIKAFISH_MOVETIME_MS` | 300 | Thời gian engine phân tích mỗi thế cờ |
| `PORT` | 5000 | Cổng server |
| `HOST` | 127.0.0.1 | Chỉ nghe local. **Chỉ mở ra ngoài sau khi đã thêm xác thực** |
| `FLASK_DEBUG` | 0 | Bật debugger Werkzeug (nguy hiểm nếu mở ra mạng ngoài) |
| `ALLOWED_ORIGINS` | localhost:5000 | Danh sách origin được phép gọi API |

API key cũng có thể nhập trực tiếp trong hộp thoại ⚙️ Cấu Hình của giao diện.

## Kiến trúc

```
server.py                 Flask API + phục vụ file tĩnh
engine/
  referee.py              Trọng tài: phân lượt, xác thực nước đi, đếm vi phạm, kết luận trận
  model_registry.py       Danh mục model + bảng giá token (một chỗ duy nhất để cập nhật)
  prompt_builder.py       Dựng prompt: bàn cờ ASCII, lịch sử, kiểm kê quân, cảnh báo chiếu
  providers/              Kỳ thủ: Claude (SDK), Gemini (SDK), OpenAI-compatible, Mock, Pikafish
  analysis/               Pikafish chấm điểm: centipawn loss, nhãn chất lượng, accuracy %
  xiangqi/
    board.py              Trạng thái bàn cờ, FEN, thực hiện nước đi, bộ đếm luật hoà
    move_generation.py    Sinh nước đi 7 loại quân + lọc nước hợp lệ
    attack_detection.py   Phát hiện ô bị tấn công, chiếu tướng, lộ mặt tướng
    game_rules.py         Chiếu bí / hết nước / mất tướng / các luật hoà
    notation.py           UCCI ↔ toạ độ, ký hiệu cờ tướng tiếng Việt
web/                      Giao diện studio (vanilla JS + SVG bàn cờ + TTS)
tests/                    pytest — luật cờ và vòng đời trận đấu
plans/                    Kế hoạch nâng cấp theo phase
```

## Luật thi đấu (đảm bảo công bằng khi so sánh AI)

- **Trọng tài là bên duy nhất xác thực nước đi.** Agent AI không bao giờ được tự sửa nước
  đi sai của mình thành nước hợp lệ.
- AI đi sai luật được **cho đi lại tối đa 3 lần** kèm lý do cụ thể ("Pháo cần ngòi để ăn quân").
  Mọi lần sai đều được **đếm và hiển thị** — đây là một thước đo sức mạnh.
- Chỉ khi AI không đưa được nước hợp lệ sau cả 3 lần, trọng tài mới chọn thay và ghi rõ vào log.
- Cùng một template prompt cho mọi nhà cung cấp; chỉ khác cách gói request theo từng API.
- Nước đi trả về là **string tự do**, không dùng enum giới hạn danh sách. Ép enum sẽ khiến
  mọi AI đi hợp lệ 100% và mất tín hiệu "AI có thật sự đọc được bàn cờ không".
- Pikafish chỉ **chấm điểm sau khi AI đã quyết định**, không gợi ý nước đi cho AI.
- Đỏ đi trước nên có lợi thế → khi chạy giải đấu phải cho mỗi cặp đánh cả hai màu.

## Luật cờ đã cài đặt

Đúng luật: chân mã, mắt tượng, ngòi pháo, binh qua hà mới đi ngang, tượng không qua hà,
sĩ/tướng trong cung, **cấm lộ mặt tướng**, **cấm đi nước để tướng mình bị chiếu**.

Kết cục: chiếu bí (thua), **hết nước đi (thua — khác cờ vua)**, hoà khi 60 nước đôi không ăn
quân, hoà khi lặp lại thế cờ 3 lần.

Đơn giản hoá hiện tại: luật xử phạt chiếu tướng liên tục / vây bắt liên tục theo chuẩn Á Châu
chưa cài, các thế này được xử **hoà** kèm cờ cảnh báo `draw_perpetual_check`.

## Test

```bash
venv/bin/python3 -m pytest tests/ -q
```
Mốc kiểm chứng chính: thế khai cuộc có đúng **44 nước đi hợp lệ**.

## Lộ trình

Xem [plans/260730-0811-xiangqi-ai-arena-upgrade/plan.md](plans/260730-0811-xiangqi-ai-arena-upgrade/plan.md):

- **Phase 1** (xong) — sửa tính đúng đắn luật cờ + an toàn vận hành
- **Phase 2** (gần xong) — Pikafish chấm điểm ✅, provider layer ✅, prompt nghiêm túc ✅; còn match_manager
- **Phase 3** — lưu trận vào SQLite, replay không tốn API, giải đấu headless, Elo, overlay OBS
