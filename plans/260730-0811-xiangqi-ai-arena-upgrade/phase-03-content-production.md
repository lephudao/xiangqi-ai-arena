# Phase 3 — Sản xuất content ở quy mô: persist, replay, tournament, Elo, overlay OBS

**Status:** ✅ XONG (2026-07-30) | **Est:** ~2 ngày | **Depends:** Phase 2

## Vấn đề đang giải

Sau Phase 2, mỗi trận là "đấu trí thật" nhưng vẫn **tan biến khi refresh**: không lưu, không replay, phải ngồi bấm nút từng nước, mỗi lần quay lại là tốn tiền API. Không scale nổi cho kênh YouTube ra video đều.

Mục tiêu Phase 3: **1 lần chạy → nhiều video**. Chạy giải đấu qua đêm, sáng ra có 10 trận trong DB, replay miễn phí để quay, có sẵn số liệu cho script.

## Files sẽ tạo/sửa

```
engine/storage/
  __init__.py
  match_repository.py       # SQLite CRUD: matches, moves, players
  schema.sql               # DDL
  elo_rating.py            # tính Elo sau mỗi trận
engine/reporting/
  match_report_builder.py  # trận -> số liệu + script video (JSON/Markdown)
scripts/
  run-tournament.py        # headless round-robin, không cần UI
web/
  overlay.html             # chế độ OBS: chrome-free, transparent bg
  js/replay-controller.js  # scrub timeline từ DB, 0 API cost
  js/leaderboard.js
data/                      # (gitignore) arena.db
```

## Step 1 — Persist bằng SQLite (`sqlite3` stdlib, không thêm dep)

`schema.sql`:
```sql
CREATE TABLE players (          -- 1 dòng / cấu hình AI
  id INTEGER PRIMARY KEY, name TEXT UNIQUE, provider TEXT, model TEXT,
  elo REAL DEFAULT 1500, matches INTEGER DEFAULT 0,
  wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0
);
CREATE TABLE matches (
  id TEXT PRIMARY KEY, red_player_id INT, black_player_id INT,
  started_at TEXT, ended_at TEXT,
  status TEXT, winner_side TEXT, result_reason TEXT, total_moves INT,
  red_accuracy REAL, black_accuracy REAL,
  red_illegal_attempts INT, black_illegal_attempts INT,
  red_cost_usd REAL, black_cost_usd REAL,
  initial_fen TEXT
);
CREATE TABLE moves (
  id INTEGER PRIMARY KEY, match_id TEXT, ply INT, side TEXT,
  ucci TEXT, vi_notation TEXT, fen_after TEXT,
  cp_before INT, cp_after INT, cp_loss INT, quality_label TEXT, accuracy REAL,
  engine_bestmove TEXT, engine_pv TEXT,
  thinking TEXT, taunt TEXT, attempts TEXT,   -- attempts: JSON array
  latency_ms INT, tokens_in INT, tokens_out INT, cost_usd REAL,
  UNIQUE(match_id, ply)
);
```
Lưu `fen_after` mỗi ply → replay chỉ cần đọc DB, **không cần chạy lại engine hay gọi API**.

`match_repository.py`: `create_match`, `append_move`, `finish_match`, `get_match`, `get_moves`, `list_matches`, `upsert_player`. Ghi ngay sau mỗi nước (crash giữa trận vẫn giữ được dữ liệu).

## Step 2 — Replay (giá trị cao nhất cho việc dựng video)

API: `GET /api/matches/<id>/replay` → `{match, moves[]}`.

`web/js/replay-controller.js`:
- Timeline scrub bar, ◀ ▶ từng nước, phát tự động theo tốc độ chọn được.
- Render từ `fen_after` — **0 API cost, 0 độ trễ**, quay lại bao nhiêu lần cũng được.
- Nhảy tới các mốc: nước blunder, nước có eval swing lớn nhất (điểm xoay chuyển trận).
- Ích lợi thực tế: quay 1 trận hay nhiều góc/nhiều lần, hoặc quay lại sau khi sửa UI mà không mất tiền.

## Step 3 — `run-tournament.py`: chạy không cần người

```bash
venv/bin/python3 scripts/run-tournament.py \
  --players gpt5,claude5,gemini3,grok4,deepseek \
  --rounds 2 --swap-colors --max-moves 300 \
  --max-cost-usd 5 --db data/arena.db
```
- Round-robin, `--swap-colors` để mỗi cặp đánh cả 2 màu (Đỏ đi trước có lợi → phải đổi màu mới công bằng).
- Chạy headless (không cần Flask/browser), dùng trực tiếp `MatchReferee`.
- Giới hạn chi phí: chạm `--max-cost-usd` → dừng sạch, ghi lại tiến độ.
- Resume được: bỏ qua cặp đã có trong DB.
- Log tiến độ ra stdout + ghi `plans/reports/tournament-<date>-summary.md`.

→ Đây là thứ biến hệ thống từ "demo bấm tay" thành "dây chuyền sản xuất content". Chạy qua đêm, sáng có sẵn 10-20 trận để chọn trận hay nhất mà quay.

## Step 4 — Elo leaderboard

`elo_rating.py`: Elo chuẩn, K=32, start 1500.
```
expected = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
new_elo  = elo + K * (score - expected)      # score: 1 / 0.5 / 0
```
- Cập nhật sau mỗi trận trong `finish_match`.
- `GET /api/leaderboard` → bảng: Elo, số trận, W/D/L, accuracy trung bình, blunder/trận, nước sai luật, chi phí/trận.
- UI trang leaderboard riêng → **content định kỳ cho kênh**: "Bảng xếp hạng AI cờ tướng tháng 8" là video tự sinh ra mỗi tháng mà không cần ý tưởng mới.

## Step 5 — Overlay cho OBS

`web/overlay.html` + `?overlay=1`:
- Không header/footer/button — chỉ bàn cờ, 2 card AI, eval bar, banner.
- Nền transparent (`background: transparent`) để chồng lớp trong OBS.
- Khoá tỉ lệ 1920×1080 (16:9), font scale theo viewport.
- Điều khiển qua hotkey hoặc `/api/matches/<id>/step` từ máy khác → tay bạn không lộ trong hình.

Overlay thành phần cần thêm:
| Thành phần | Vì sao cần cho video |
|-----------|---------------------|
| Eval bar động | Người xem hiểu ai đang thắng mà không cần biết cờ |
| Badge chất lượng nước (⭐/🔴 BLUNDER) | Tạo cao trào tức thì |
| Cảnh báo **CHIẾU TƯỚNG!** (flash đỏ + tiếng) | Kịch tính nhất trong cờ tướng, hiện chưa có |
| Khay quân bị ăn (2 bên) | Nhìn ra thế mạnh yếu nhanh |
| Đồng hồ nghĩ + accuracy live | "AI này nghĩ 8 giây mà vẫn đi sai" |
| Vệt highlight nước đi (from→to) | Hiện chỉ highlight ô đích |
| Ticker chi phí API | Chi tiết thú vị: "trận này tốn $0.42" |

## Step 6 — Auto-gen script video

`match_report_builder.py` → từ 1 match_id sinh Markdown:
- Kết quả + lý do (chiếu bí / hết nước / hòa 60 nước)
- Bảng accuracy 2 bên, số blunder, số nước sai luật, thời gian nghĩ TB, chi phí
- **Top 3 blunder** kèm FEN + nước engine khuyên (dùng làm phần "phân tích" trong video)
- **Điểm xoay chuyển trận**: ply có eval swing lớn nhất (dùng làm hook mở đầu / thumbnail)
- Gợi ý tiêu đề + timestamps chương

→ Xong 1 trận là có sẵn khung script, không phải ngồi xem lại từ đầu để tìm nội dung.

## Step 7 — Dọn UX ghi hình + docs

- TTS queue: hiện `synth.cancel()` cắt câu trước giữa chừng ([app.js:301](../../web/app.js#L301)) → xếp hàng, hoặc bỏ qua nếu câu trước chưa xong (xem câu hỏi #2 plan.md về ElevenLabs).
- Tuỳ chọn tự dừng khi hết trận + chờ N giây trước khi hiện banner (đủ thời gian cắt cảnh).
- `docs/`: `project-overview-pdr.md`, `system-architecture.md`, `codebase-summary.md` — mô tả "luật thi đấu" (prompt giống nhau, cùng movetime engine, đổi màu) để công khai tính công bằng. Đây cũng là nội dung tin cậy để trả lời comment "video này thiên vị".

## Tests

| Test | Nội dung |
|------|----------|
`tests/test_match_repository.py` | Ghi/đọc trận + nước; UNIQUE(match_id, ply) chặn ghi trùng; crash giữa trận vẫn đọc lại được các nước đã ghi |
`tests/test_elo_rating.py` | Case chuẩn: 2 người 1500, người A thắng → 1516/1484. Hoà giữa lệch Elo. Đối xứng (tổng Elo không đổi) |
`tests/test_match_report_builder.py` | Từ match giả lập: chọn đúng top-3 blunder, đúng ply eval swing lớn nhất |
Smoke | `run-tournament.py` với 3 player mock, 1 round → DB có đúng số trận, Elo đã cập nhật |

## Risks

| Risk | Xử lý |
|------|-------|
| SQLite ghi đồng thời khi tournament song song | Chạy tournament **tuần tự** (YAGNI — không cần song song); bật WAL mode |
| Tournament chạy qua đêm đốt tiền API ngoài dự kiến | `--max-cost-usd` bắt buộc; mặc định $5; log cost sau mỗi trận |
| Trận không bao giờ kết thúc (2 AI lặp vô hạn) | `--max-moves 300` → xử hòa `move_limit`; Phase 1 đã có luật 60 nước và lặp 3 lần |
| Overlay transparent không hoạt động đúng trong OBS | Test bằng OBS browser source thật trước khi build nhiều tính năng trên đó |
| DB schema đổi sau này làm mất trận cũ | Thêm `schema_version`; migration bằng script riêng, không xoá DB |

## Acceptance criteria

- [x] Trận lưu đầy đủ vào `data/arena.db` ngay sau từng nước
- [x] Replay chạy được từ DB, không gọi API, scrub được từng nước
- [x] `run-tournament.py` chạy round-robin headless, resume được, tôn trọng `--max-cost-usd`
- [x] Elo cập nhật đúng, có `/api/leaderboard` + UI
- [x] `?overlay=1` sạch chrome, 1920×1080, chạy được trong OBS browser source
- [x] Cảnh báo CHIẾU TƯỚNG + badge blunder + eval bar hiện đúng lúc
- [x] `match_report_builder` sinh được script video có top-3 blunder + điểm xoay chuyển
- [x] `docs/` có PDR + architecture + "luật thi đấu" công khai
