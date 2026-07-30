# Hướng dẫn cài đặt và vận hành

**Cập nhật:** 2026-07-30 · **Chế độ hiện tại:** chạy local, quay màn hình

## 1. Cài đặt

```bash
./run.sh                       # tạo venv, cài phụ thuộc, chạy máy chủ
```

Mở http://localhost:5000

Không cần API key: mặc định cả hai bên chạy chế độ **Mock** (đi ngẫu nhiên hợp lệ) để thử
giao diện và quy trình quay video.

### Cài engine chấm điểm (nên làm)

```bash
./scripts/install-pikafish.sh
```

Pikafish là engine cờ tướng mã nguồn mở (GPL), chạy local, **chi phí 0đ**. Script tải bản
phát hành mới nhất, kiểm tra engine trả `uciok`, và tự chuyển sang build từ mã nguồn nếu bản
phát hành không có binary cho kiến trúc máy.

Cần `7z`: `brew install p7zip`

Không cài cũng chạy được, nhưng mất toàn bộ phần chấm điểm chất lượng nước đi.

## 2. Cấu hình

Copy `.env.example` → `.env.local`. File `.env.local` đã được gitignore nên an toàn để chứa
key thật.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `ANTHROPIC_API_KEY` | rỗng | Cho Claude |
| `GEMINI_API_KEY` | rỗng | Cho Gemini |
| `OPENAI_API_KEY` / `XAI_API_KEY` / `DEEPSEEK_API_KEY` | rỗng | ChatGPT / Grok / DeepSeek (chưa kiểm chứng) |
| `PIKAFISH_PATH` | `engine/bin/pikafish` | Đường dẫn engine |
| `PIKAFISH_MOVETIME_MS` | `300` | Thời gian engine phân tích mỗi thế cờ |
| `PORT` | `5000` | Cổng máy chủ |
| `HOST` | `127.0.0.1` | Chỉ nghe local |
| `FLASK_DEBUG` | `0` | Debugger Werkzeug |
| `ALLOWED_ORIGINS` | `localhost:5000` | Origin được phép gọi API |

Thiếu key thì kỳ thủ đó tự chuyển về Mock và **ghi rõ lý do** vào nhật ký trọng tài, không
im lặng.

## 3. An toàn vận hành

Hệ thống hiện **chỉ dành cho chạy local**. Ba thiết lập mặc định phục vụ mục đích đó:

| Thiết lập | Giá trị | Vì sao |
|---|---|---|
| `HOST` | `127.0.0.1` | Không lắng nghe ra mạng ngoài |
| `FLASK_DEBUG` | `0` | Debugger Werkzeug cho phép thực thi mã tuỳ ý nếu bị truy cập từ ngoài |
| `ALLOWED_ORIGINS` | chỉ localhost | Chặn trang web khác gọi API và đốt tiền của bạn |

### Trước khi mở ra ngoài (livestream)

Hệ thống **chưa có xác thực**. Bất kỳ ai tới được cổng 5000 đều có thể gọi `/api/step` và
tiêu tiền API của bạn.

Cần làm trước khi đổi `HOST` thành `0.0.0.0`:

1. Thêm lớp xác thực (token hoặc reverse proxy có mật khẩu)
2. Giữ `FLASK_DEBUG=0`
3. Đặt `ALLOWED_ORIGINS` đúng tên miền
4. Cân nhắc giới hạn tần suất cho `/api/step`

### Quản lý key

- Key thật để trong `.env.local` (đã gitignore qua quy tắc `.env.*`)
- `.env.example` chỉ chứa tên biến, không chứa giá trị
- Ô nhập API key trên giao diện chỉ dùng tạm; ưu tiên đặt qua biến môi trường

## 4. Chặn chi phí

Mỗi nước đi là một lần gọi API tốn tiền. Có hai lớp chặn:

**Trên giao diện:** ô "Dừng khi tới $" ở thanh dưới (mặc định `1.00`). Tự động đấu dừng lại
khi chạm ngưỡng và ghi lý do vào banner trọng tài. Bộ đếm chi phí chuyển màu cảnh báo khi
đạt 80% ngân sách.

**Dòng lệnh:** `--max-cost-usd` (bắt buộc có, mặc định `2.00`) và `--max-moves` (mặc định
`140`) để trận không chạy vô hạn.

Ước tính: trận 100 nước với Claude Haiku 4.5 + Gemini 3.6 Flash ≈ **$0.28**.

## 5. Chạy trận và giải đấu

```bash
# Một cặp đấu
scripts/run_matches.py --pairing claude-haiku-4-5:gemini-3.6-flash --max-cost-usd 2.00

# Giải vòng tròn — mọi cặp đánh cả hai màu
scripts/run_matches.py --round-robin claude-haiku-4-5,gemini-3.6-flash,pikafish \
    --max-moves 140 --max-cost-usd 5.00

# Không ghi cơ sở dữ liệu (chỉ xuất JSON)
scripts/run_matches.py --pairing mock:mock --no-db
```

Kết quả ghi vào `data/arena.db` (xem lại được ngay trên giao diện, Elo tự cập nhật) và
`data/matches/*.json`.

Thời gian tham khảo: khoảng 10-15 giây mỗi nước với cặp Haiku + Flash, tức trận 60 nước mất
khoảng 8-10 phút.

## 6. Quay video

### Quay màn hình thường

1. Bấm 🔄 **Trận Mới**, chọn kỳ thủ ở ⚙️ **Cấu Hình**
2. Đặt **Nghỉ giữa nước** = `3s` để có thời gian đọc badge và lời thoại
3. Bật **TTS** nếu muốn máy đọc "Pháo 2 bình 5" kèm câu thoại
4. Bấm ⚡ **Tự Động Đấu**

Toàn bộ studio vừa một màn hình, không cần cuộn. Hết trận hiện banner overlay (không dùng
`alert()` nên không chặn ghi hình).

### Overlay cho OBS

Thêm browser source trỏ tới:

```
http://localhost:5000/?overlay=1&transparent=1
```

Tham số:

| Tham số | Tác dụng |
|---|---|
| `overlay=1` | Ẩn toàn bộ nút bấm, thanh công cụ, hộp thoại |
| `transparent=1` | Nền trong suốt để chồng lớp |
| `refresh=1000` | Chu kỳ làm mới (ms), mặc định 1000 |

Overlay tự bám theo trận đang chạy. Điều khiển trận từ tab khác hoặc gọi API từ máy khác để
tay bấm không lọt vào khung hình.

### Xem lại để quay nhiều lần

Bấm 📼 **Xem Lại** → chọn trận. Đọc từ cơ sở dữ liệu nên **không tốn tiền API** — quay lại
bao nhiêu lần cũng được, kể cả sau khi sửa giao diện.

Có kéo thanh thời gian, phát tự động, và nút 🔴 **Nước tệ nhất** nhảy thẳng tới nước hỏng
nặng nhất.

### Lấy khung script video

```bash
scripts/build_match_report.py --list
scripts/build_match_report.py <match_id> -o plans/reports/tran-abc.md
```

Báo cáo gồm: bảng độ chính xác hai bên, ba nước hỏng nặng nhất kèm lời AI tự giải thích,
điểm xoay chuyển trận (dùng làm hook mở đầu), và gợi ý tiêu đề.

## 7. Sao lưu và bảo trì

- **Dữ liệu trận:** `data/arena.db` (SQLite). Sao lưu bằng cách copy file khi máy chủ đang
  dừng, hoặc `sqlite3 data/arena.db ".backup data/arena-backup.db"` khi đang chạy.
- **`data/` đã gitignore** — không đưa lên kho mã.
- **Đổi lược đồ:** bảng `schema_version` có sẵn cho migration; viết script riêng, không xoá
  cơ sở dữ liệu đang có trận.
- **Nhập lại dữ liệu cũ:** `scripts/import_match_json.py --all` an toàn khi chạy nhiều lần
  (không tạo bản ghi trùng, không cộng Elo hai lần).

## 8. Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| Giao diện báo "Chưa chấm điểm nước đi" | Chưa cài Pikafish — chạy `./scripts/install-pikafish.sh` |
| Kỳ thủ hiện là Mock dù đã chọn model | Thiếu API key; xem nhật ký trọng tài để biết thiếu biến nào |
| Chi phí hiện dấu gạch | Model chưa niêm yết giá trong `model_registry.py` |
| Lỗi SSL khi gọi API | Python thiếu CA bundle; các provider chính đã dùng SDK nên không bị, riêng nhánh OpenAI-compatible cần `certifi` |
| Nhiều máy chủ cùng bind cổng 5000 | `kill $(lsof -ti:5000)` rồi chạy lại |
