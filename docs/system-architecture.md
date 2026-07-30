# Kiến trúc hệ thống

**Cập nhật:** 2026-07-30

## 1. Tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│  Trình duyệt (web/)                                                  │
│  app.js ── board-renderer ── replay-controller ── human-input         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP JSON
┌───────────────────────────────▼─────────────────────────────────────┐
│  server.py (Flask)  ── MatchManager: nhiều trận theo match_id         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│  MatchReferee — TRỌNG TÀI, bên duy nhất xác thực nước đi              │
│    ├── engine/xiangqi/     luật cờ, sinh nước, phát hiện chiếu        │
│    ├── engine/providers/   kỳ thủ: Claude, Gemini, Mock, Pikafish,    │
│    │                       OpenAI-compatible, Người                   │
│    ├── engine/prompt_builder.py   dựng prompt dùng chung              │
│    ├── engine/analysis/    Pikafish chấm điểm (tiến trình con, UCI)   │
│    └── engine/storage/     SQLite: trận, nước đi, Elo                 │
└─────────────────────────────────────────────────────────────────────┘
```

Hai tài nguyên nặng được **dùng chung cho mọi trận**: một tiến trình Pikafish (~50MB cho bảng
NNUE) và một kho lưu trữ SQLite.

## 2. Luồng một nước đi

```
step()
  │
  ├─ Kiểm tra kết cục trước khi đi (chiếu bí / hết nước / hoà)
  │
  ├─ Lượt người?  ──yes──► dừng, trả state kèm danh sách nước hợp lệ
  │                        (chờ POST /api/human-move)
  │  no
  ├─ prompt_builder dựng prompt (bàn cờ ASCII + lịch sử + kiểm kê + cảnh báo chiếu)
  ├─ provider.decide() ──► MoveDecision (nước đi NGUYÊN BẢN, không sửa)
  │
  ├─ Nước hợp lệ?  ──no──► đếm vi phạm, dựng lại prompt kèm lý do, thử lại (tối đa 3 lần)
  │  yes
  ├─ board.push_ucci()          thực hiện nước đi
  ├─ score_move()               Pikafish chấm — SAU khi đã đi
  ├─ recorder.append_move()     ghi ngay vào SQLite
  └─ evaluate_result()          kiểm tra kết cục sau nước đi
```

Điểm mấu chốt: **chấm điểm diễn ra sau khi AI đã quyết định**, nên engine không ảnh hưởng tới
lựa chọn của AI.

## 3. Các quyết định thiết kế và lý do

### 3.1. Trọng tài giữ toàn quyền xác thực

Provider trả nước đi nguyên bản, kể cả nước sai. Trọng tài mới là bên kiểm tra, đếm vi phạm
và quyết định cho đi lại.

*Lý do:* bản đầu tiên để mỗi lời gọi API tự thay nước sai bằng nước ngẫu nhiên, làm mất hoàn
toàn dữ liệu về việc AI đi sai luật — đúng thứ cần đo.

### 3.2. Phát hiện chiếu tách khỏi sinh nước đi

`attack_detection.py` kiểm tra trực tiếp theo từng hướng (quét tia cho Xe/Pháo, 8 vị trí cho
Mã, ...) thay vì sinh toàn bộ nước đi của đối phương rồi xem có nước nào ăn tướng.

*Lý do:* nhanh hơn, và tránh đệ quy vòng tròn giữa "sinh nước hợp lệ" và "kiểm tra chiếu".

### 3.3. Hình học bàn cờ khai báo một lần

`board-renderer.js` giữ hằng số `BOARD` dùng cho cả lưới SVG lẫn vị trí quân, tính theo phần
trăm để bàn cờ co giãn.

*Lý do:* bản cũ tính khoảng cách ô bằng `480/8` và `533/9` mà không trừ lề, nên cột ngoài cùng
nằm ở x=504 trên bàn rộng 480 — quân bên phải và hàng dưới rơi ra ngoài mặt bàn.

### 3.4. Danh sách nước hợp lệ do máy chủ cung cấp

Chế độ Người vs AI lấy `legal_moves` từ trạng thái máy chủ để highlight ô đi được, không tự
tính lại bằng JavaScript.

*Lý do:* nhân bản luật cờ sang trình duyệt tạo hai nguồn sự thật, sớm muộn cũng lệch với
trọng tài.

### 3.5. Trạng thái suy ra thay vì lưu song song

`waiting_for_human` được tính từ lượt hiện tại, không giữ thành biến riêng.

*Lý do:* khi còn là biến riêng, nó đã sai ngay sau khi AI đi xong. Hai nguồn sự thật cho cùng
một khái niệm luôn lệch nhau.

### 3.6. Ghi cơ sở dữ liệu sau mỗi nước

Không đợi hết trận mới ghi.

*Lý do:* một trận LLM chạy 30-60 phút và tốn tiền API thật; mất điện hay lỗi mạng giữa chừng
là mất trắng. Có test mô phỏng crash giữa trận.

### 3.7. `fen_after` lưu kèm mỗi nước

*Lý do:* xem lại chỉ cần đọc cơ sở dữ liệu — không gọi API, không chạy lại engine. Đây là thứ
biến "quay lại một trận" từ việc tốn tiền thành miễn phí.

### 3.8. Một tiến trình engine dùng chung

`MatchManager` giữ một `PikafishEngine` và truyền cho mọi trận.

*Lý do:* mỗi tiến trình chiếm ~50MB cho bảng NNUE.

### 3.9. Cache một mục cho kết quả phân tích

`PikafishEngine` nhớ kết quả gần nhất theo (FEN, movetime).

*Lý do:* thế cờ sau nước N chính là thế cờ trước nước N+1, và cùng góc nhìn bên đi. Nhờ đó mỗi
nước chỉ cần một lần phân tích thay vì hai — đo thực tế giảm từ 629ms xuống 352ms mỗi nước.

### 3.10. Năng lực API khác nhau theo đời model

`ModelInfo` có cờ `supports_effort` và `supports_adaptive_thinking`.

*Lý do:* Claude Haiku 4.5 không nhận `effort` và không có adaptive thinking — gửi sẽ bị API
từ chối với lỗi 400. Trong khi Opus 5 thì bắt buộc dùng adaptive và đã bỏ `budget_tokens`.

### 3.11. SDK chính thức thay cho tự gọi HTTP

Dùng `anthropic` và `google-genai` thay vì `urllib` tự viết.

*Lý do:* ngoài việc đúng chuẩn và có sẵn retry/timeout, `urllib` trên bản Python này thiếu CA
bundle nên **fail SSL với mọi nhà cung cấp**; SDK mang theo CA riêng nên khắc phục tận gốc.

## 4. API HTTP

| Nhóm | Endpoint | Ghi chú |
|---|---|---|
| Trận hiện tại | `GET /api/state` · `POST /api/step` · `POST /api/reset` | Không cần match_id |
| Nhiều trận | `GET|POST /api/matches` · `GET /api/matches/<id>/state` · `POST /api/matches/<id>/step` · `POST /api/matches/<id>/select` · `DELETE /api/matches/<id>` | |
| Người chơi | `POST /api/human-move` · `POST /api/hint` | Có bản theo match_id |
| Danh mục | `GET /api/models` | Nguồn cho dropdown |
| Xem lại | `GET /api/replays` · `GET /api/replays/<id>` · `GET /api/replays/<id>/report` | Đọc từ SQLite |
| Xếp hạng | `GET /api/leaderboard` | Elo |
| Lịch sử | `GET /api/history` | Nước đi + nhật ký trọng tài |

Route không có `match_id` tác động lên "trận đang xem". Mở trận mới **không** cướp trận đang
xem — đang quay video một trận thì việc chạy giải đấu không được đổi màn hình.

## 5. Lược đồ cơ sở dữ liệu

```
players (model_key PK, label, provider, elo, matches, wins, losses, draws)
matches (id PK, red_model_key, black_model_key, started_at, ended_at, status,
         winner_side, result_reason, stopped_reason, total_plies, initial_fen,
         red_accuracy, black_accuracy, red_blunders, black_blunders,
         red_illegal, black_illegal, red_cost_usd, black_cost_usd, elo_applied)
moves   (match_id + ply PK, side, ucci, vi_notation, fen_after, in_check_after,
         cp_before, cp_after, cp_loss, quality, accuracy, engine_bestmove, engine_pv,
         analysis, taunt, attempts, referee_override, error,
         latency_ms, tokens_in, tokens_out, cost_usd)
```

- **WAL mode**: đọc bảng xếp hạng và xem lại trong khi trận khác đang ghi
- **Mỗi luồng một kết nối**: Flask chạy threaded, `sqlite3` không cho dùng chung kết nối
- **`elo_applied`**: chặn tính Elo hai lần khi nhập lại dữ liệu
- **`schema_version`**: chuẩn bị cho migration sau này

## 6. Xử lý khi thiếu thành phần

Hệ thống được thiết kế để **không sập** khi thiếu bộ phận phụ trợ:

| Thiếu | Hành vi |
|---|---|
| Pikafish | Trận vẫn chạy, chỉ mất phần chấm điểm; giao diện cảnh báo rõ |
| API key | Chuyển về Mock và ghi lý do vào nhật ký trọng tài |
| Bảng giá model | Hiện dấu gạch thay vì số bịa; ngân sách không áp được |
| Model bị API từ chối | Ghi `stop_reason=refusal` thành lỗi, không đọc nội dung rỗng |
