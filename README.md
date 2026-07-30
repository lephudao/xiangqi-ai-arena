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
  match_manager.py        Nhiều trận song song, dùng chung một tiến trình engine
  providers/              Kỳ thủ: Claude (SDK), Gemini (SDK), OpenAI-compatible, Mock, Pikafish
  analysis/               Pikafish chấm điểm: centipawn loss, nhãn chất lượng, accuracy %
  storage/                SQLite: lưu trận, nước đi, Elo — nền cho xem lại và xếp hạng
  reporting/              Sinh báo cáo trận làm khung script video
  xiangqi/
    board.py              Trạng thái bàn cờ, FEN, thực hiện nước đi, bộ đếm luật hoà
    move_generation.py    Sinh nước đi 7 loại quân + lọc nước hợp lệ
    attack_detection.py   Phát hiện ô bị tấn công, chiếu tướng, lộ mặt tướng
    game_rules.py         Chiếu bí / hết nước / mất tướng / các luật hoà
    notation.py           UCCI ↔ toạ độ, ký hiệu cờ tướng tiếng Việt
web/                      Giao diện studio (vanilla JS + SVG bàn cờ + TTS)
scripts/                  install-pikafish.sh, run_matches.py (chạy trận/giải đấu),
                          import_match_json.py, build_match_report.py
tests/                    pytest — luật cờ, vòng đời trận, provider, quản lý trận
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

## Chơi thử với AI

Vào ⚙️ Cấu Hình, chọn **Người chơi (bạn)** cho bên Đỏ hoặc Đen, rồi bấm 🔄 Trận Mới.

- Bấm vào quân của mình → hiện chấm gợi ý các ô đi được (danh sách lấy từ máy chủ, không
  nhân bản luật cờ sang trình duyệt)
- Nước sai luật bị từ chối kèm lý do tiếng Việt, y như khi AI đi sai
- Tự động đấu **dừng lại** ở lượt bạn, không tự đi thay
- 💡 Gợi Ý cho biết engine khuyên nước nào; nước dùng gợi ý bị **đánh dấu riêng** để độ
  chính xác của bạn không bị thổi phồng khi so với AI

## Xem lại, giải đấu và overlay

```bash
# Giải vòng tròn: mọi cặp đánh cả hai màu, ghi thẳng vào cơ sở dữ liệu
scripts/run_matches.py --round-robin claude-haiku-4-5,gemini-3.6-flash,pikafish \
    --max-moves 140 --max-cost-usd 5.00

# Nhập các file JSON chạy từ trước khi có cơ sở dữ liệu
scripts/import_match_json.py --all

# Xuất báo cáo trận làm khung script video
scripts/build_match_report.py --list
scripts/build_match_report.py <match_id> -o plans/reports/tran.md
```

- **Xem lại** — bấm 📼 Xem Lại trên giao diện. Đọc từ cơ sở dữ liệu nên **không tốn tiền API**;
  có kéo thanh thời gian, phát tự động, và nút nhảy tới nước sai nặng nhất.
- **Elo** — chỉ tính trận kết thúc đúng luật cờ. Trận dừng vì hết giới hạn nước hoặc hết
  ngân sách không được tính, vì không phản ánh sức mạnh.
- **Overlay OBS** — mở `http://localhost:5000/?overlay=1&transparent=1` làm browser source.
  Không có nút bấm, nền trong suốt; điều khiển trận từ tab khác để tay không lọt vào khung hình.

## Test

```bash
venv/bin/python3 -m pytest tests/ -q
```
Mốc kiểm chứng chính: thế khai cuộc có đúng **44 nước đi hợp lệ**.

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [docs/project-overview-pdr.md](docs/project-overview-pdr.md) | Mục tiêu, **luật thi đấu** đảm bảo công bằng, cách đo chất lượng nước đi, chi phí |
| [docs/system-architecture.md](docs/system-architecture.md) | Kiến trúc, luồng một nước đi, các quyết định thiết kế và lý do |
| [docs/codebase-summary.md](docs/codebase-summary.md) | Bản đồ mã nguồn, sửa gì thì mở file nào, nợ kỹ thuật |
| [docs/deployment-guide.md](docs/deployment-guide.md) | Cài đặt, an toàn vận hành, chặn chi phí, quay video, xử lý sự cố |

## Lộ trình

Xem [plans/260730-0811-xiangqi-ai-arena-upgrade/plan.md](plans/260730-0811-xiangqi-ai-arena-upgrade/plan.md):

- **Phase 1** (xong) — sửa tính đúng đắn luật cờ + an toàn vận hành
- **Phase 2** (xong) — Pikafish chấm điểm, tầng provider dùng SDK, prompt đầy đủ ngữ cảnh, nhiều trận song song
- **Phase 3** (xong) — lưu SQLite, xem lại miễn phí, giải vòng tròn, Elo, overlay OBS, báo cáo trận
- **Phase 4** (xong) — chế độ Người vs AI
