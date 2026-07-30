# Phase 1 — Sửa tính đúng đắn luật cờ + an toàn vận hành

**Status:** ✅ XONG (2026-07-30) | **Est:** ~1 ngày | **Blocks:** Phase 2, Phase 3

## Vì sao bắt buộc làm trước

Engine hiện tại cho phép nước đi **sai luật cờ tướng**. Mọi thứ xây trên đó (chấm điểm, Elo, content) đều vô giá trị: không thể nói "AI này mạnh hơn" khi bàn cờ chạy sai luật.

## Bug đã xác nhận (đọc code)

| # | Vị trí | Vấn đề | Hệ quả |
|---|--------|--------|--------|
| B1 | `engine/xiangqi_engine.py:224` `leaves_kings_facing_or_checked` | Tên hàm nói "checked" nhưng thân hàm CHỈ kiểm tra lộ mặt tướng. Không kiểm tra vua bị quân địch chiếu | AI đi nước để vua mình bị chiếu → sai luật; lượt sau đối phương ăn tướng |
| B2 | `engine/xiangqi_engine.py:96` `generate_legal_moves` | Không kiểm tra tướng còn tồn tại trên bàn | Tướng bị ăn nhưng trận vẫn tiếp tục, không ai phát hiện |
| B3 | `engine/ai_agent.py:124,147,170` | Mỗi `_call_*` tự thay nước sai bằng `random.choice(legal_moves)` trước khi trả về | Referee không bao giờ thấy nước sai → nhánh fallback `referee.py:88-101` là code chết; mất data "AI đi sai luật mấy lần" |
| B4 | `engine/ai_agent.py:120,143,166` | `urllib.request.urlopen` không có `timeout` | 1 API treo → block toàn bộ Flask (single-thread) |
| B5 | `server.py:44` | `debug=True` hardcoded | Werkzeug debugger = RCE nếu expose ra ngoài (livestream sau này) |
| B6 | `server.py:11` | `CORS(app)` mở mọi origin, không auth | Bất kỳ trang web nào cũng POST được `/api/step` → phá trận / đốt tiền API |
| B7 | `engine/xiangqi_engine.py:75` `to_fen` | Halfmove clock hardcode `0` | FEN sai → Pikafish (Phase 2) nhận input sai; không tính được luật 60 nước |
| B8 | `engine/xiangqi_engine.py:299` `move_to_vietnamese_text` | Trả "Xe (Đỏ) (h2 -> e2)" — không phải ký hiệu cờ tướng VN | TTS đọc như robot đọc toạ độ, mất chất "bình luận cờ tướng" |
| B9 | `web/app.js:153` | `alert()` khi hết trận | Hộp thoại modal của browser chặn ghi hình, phải bấm tay |
| B10 | Không có | Zero test | Không cách nào biết engine đúng |

## Files sẽ tạo/sửa

### Tạo mới — tách `xiangqi_engine.py` (312 LOC → 5 module <200 LOC)

```
engine/xiangqi/
  __init__.py              # export XiangqiBoard, GameResult
  board.py                 # state, load_fen, to_fen, push_ucci, pop, find_king
  move_generation.py       # sinh pseudo-legal moves cho 7 loại quân
  attack_detection.py      # is_square_attacked, is_in_check, kings_facing
  game_rules.py            # GameResult: checkmate/stalemate/draw (60 nước, lặp 3 lần)
  notation.py              # ucci<->pos, to_vietnamese_notation (Pháo 2 bình 5)
tests/
  test_move_generation.py  # perft-lite + từng loại quân
  test_check_detection.py  # chiếu, chống chiếu, lộ mặt tướng
  test_game_rules.py       # chiếu bí, hết nước, hòa
```

Giữ `engine/xiangqi_engine.py` làm shim re-export để không phá import cũ, hoặc sửa import ở `referee.py` (chọn sửa import — DRY, không giữ 2 đường).

### Sửa
- `engine/referee.py` — dùng `GameResult`, đếm illegal attempts, log lý do thật
- `engine/ai_agent.py` — bỏ auto-substitute, thêm timeout, trả metadata
- `server.py` — `debug` từ env, CORS localhost-only, threaded=True
- `web/app.js` — bỏ `alert()`, hiện banner kết thúc trận
- `.env.example` — thêm `FLASK_DEBUG`, `ALLOWED_ORIGINS`
- Tạo `README.md` (chưa có; global CLAUDE.md yêu cầu đọc README trước mọi task)

## Implementation steps

### 1. `attack_detection.py` — trái tim của fix B1

```
is_square_attacked(grid, row, col, by_side) -> bool
```
Kiểm tra trực tiếp theo từng hướng thay vì sinh toàn bộ nước đi đối phương (nhanh hơn, không đệ quy vô hạn):
- **Xe/Tướng-lộ-mặt:** quét 4 tia; quân đầu tiên chặn đường là `R`/`r` → bị chiếu. Nếu là `K`/`k` và cùng cột → lộ mặt tướng.
- **Pháo:** quét 4 tia; tìm quân chắn đầu tiên (ngòi), tiếp tục quét, quân thứ 2 là `C`/`c` → bị chiếu.
- **Mã:** 8 vị trí mã có thể chiếu tới ô này; với mỗi vị trí kiểm tra chân mã (ô cản giữa mã và đích) có trống không. **Lưu ý:** chân mã tính từ phía con mã, không phải phía ô bị chiếu.
- **Binh/Tốt:** binh Đỏ chiếu lên (từ ô dưới), thêm 2 ô ngang nếu binh đã qua hà.
- **Tướng:** 4 ô kề trong cung.
- **Sĩ/Tượng:** về lý thuyết không chiếu được tướng đối phương nhưng vẫn implement cho đủ (dùng chung cho eval sau này).

```
is_in_check(grid, side) -> bool   # tìm tướng của side, hỏi is_square_attacked
kings_facing(grid) -> bool        # giữ logic cũ, đã đúng
```

### 2. `board.py` — make/unmake move

Thay pattern "sửa grid rồi trả lại" hiện tại (dễ lỗi, `leaves_kings_facing_or_checked` đang làm thủ công) bằng:
```
make_move(r1,c1,r2,c2) -> captured   # đẩy vào undo stack
unmake_move()                        # phục hồi từ stack
```
Có `unmake` đúng là điều kiện cần cho Phase 2 (thử nước để chấm điểm).

Thêm:
- `find_king(side) -> (r,c) | None`
- `halfmove_clock` — reset khi ăn quân, +1 khi không ăn → `to_fen()` xuất đúng (fix B7)
- `position_key()` — chuỗi board+turn, dùng cho phát hiện lặp 3 lần
- `repetition_counts: dict[str,int]`

### 3. `move_generation.py` — filter đúng

```
generate_legal_moves(board, side):
    for mv in generate_pseudo_moves(board, side):
        board.make_move(mv)
        ok = not is_in_check(board.grid, side) and not kings_facing(board.grid)
        board.unmake_move()
        if ok: yield mv
```
Sinh pseudo-moves giữ nguyên logic quân hiện tại (đã đúng: chân mã, mắt tượng, ngòi pháo, binh qua hà đều OK).

### 4. `game_rules.py` — fix B2 + kết thúc trận đúng luật

```
GameResult = {status, winner, reason}   # status: ongoing|red_win|black_win|draw
evaluate_position(board) -> GameResult
```
Thứ tự kiểm tra:
1. Tướng của 1 bên **không tồn tại** → bên còn lại thắng, `reason="king_captured"` (fix B2 — bug này lẽ ra không xảy ra sau khi fix B1, nhưng giữ làm safety net).
2. Bên tới lượt **không còn nước hợp lệ**:
   - đang bị chiếu → `checkmate` (chiếu bí) → bên kia thắng
   - không bị chiếu → `stalemate` (hết nước / 困斃) → bên kia thắng **(cờ tướng: hết nước là THUA, không phải hòa như cờ vua)**
3. `halfmove_clock >= 120` (60 nước đôi không ăn quân) → hòa
4. `repetition_counts[key] >= 3` → hòa
   - Ghi chú: luật Á Châu đầy đủ xử phạt chiếu liên tục / vây bắt liên tục là bên chiếu THUA. Phase 1 đơn giản hoá thành hòa + log cảnh báo `perpetual_check_suspected` (xem câu hỏi #3 trong plan.md).

### 5. `notation.py` — fix B8, ký hiệu cờ tướng Việt Nam

Format chuẩn: `<Quân> <cột xuất phát> <động từ> <đích>`
- Cột đánh số 1-9 **từ phải sang trái theo góc nhìn của bên đi** (Đỏ: cột a=9…i=1; Đen: a=1…i=9)
- Động từ: `bình` (ngang), `tấn`/`tiến` (lên), `thoái`/`lùi` (xuống)
- Đi ngang → đích là số cột mới; đi dọc → đích là **số ô di chuyển** (với Xe/Pháo/Binh/Tướng) hoặc **số cột đích** (với Mã/Tượng/Sĩ, vì chúng đi chéo)
- 2 quân cùng loại cùng cột → thêm `tiền`/`hậu` (trước/sau)

Ví dụ đúng: `Pháo 2 bình 5`, `Mã 8 tấn 7`, `Xe 1 tiến 4`, `Tiền Binh 3 tấn 1`.
Đây là nâng cấp content lớn: TTS đọc "Pháo hai bình năm" nghe như bình luận viên thật, thay vì "Xe Đỏ h2 mũi tên e2".

### 6. `ai_agent.py` — fix B3, B4

Đổi return type thành dataclass:
```python
@dataclass
class MoveDecision:
    move_ucci: str          # nguyên văn AI trả về, KHÔNG sửa
    is_legal: bool          # do referee gán sau khi validate
    taunt: str              # thoại cho khán giả
    thinking: str           # phân tích (nếu model trả)
    latency_ms: int
    error: str | None       # lỗi API thật, không che
    attempts: list[str]     # các nước AI đã thử (kể cả sai)
```
- **Xoá** `if res.get("move_ucci") not in legal_moves: res["move_ucci"] = random.choice(...)` ở cả 3 provider.
- Thêm `timeout=30` cho mọi `urlopen`.
- Retry nước sai: nếu nước AI trả về không hợp lệ → gọi lại tối đa 2 lần kèm feedback `"Nước {x} không hợp lệ vì {lý do}. Chọn lại từ danh sách."`; ghi mọi lần thử vào `attempts`.
- Chỉ khi hết retry mới fallback engine-pick, và referee log rõ: `"AI X không đưa được nước hợp lệ sau 3 lần thử — trọng tài chọn thay"`.

### 7. `referee.py` — dùng GameResult

- Sau mỗi nước: `result = evaluate_position(board)`; nếu `!= ongoing` → set game_over + winner + reason.
- Log riêng: `illegal_attempts` per player (đếm vào stats).
- Thêm vào state: `in_check: bool` (để UI cảnh báo "CHIẾU TƯỚNG!"), `result_reason`.

### 8. `server.py` — fix B5, B6

```python
debug = os.environ.get("FLASK_DEBUG", "0") == "1"
origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000").split(",")
CORS(app, origins=origins)
app.run(host="127.0.0.1", port=port, debug=debug, threaded=True)
```
`host` đổi `0.0.0.0` → `127.0.0.1` (local-only, đúng use case hiện tại; đổi lại khi làm livestream có auth).

### 9. `web/app.js` — fix B9
Thay `alert()` bằng overlay banner `#match-result-banner` (fade in, tự động ở lại) — không chặn ghi hình.

## Tests (pytest, thêm vào requirements.txt)

Chạy: `venv/bin/python3 -m pytest tests/ -q`

| Test | Nội dung |
|------|----------|
| `test_move_generation.py` | Số nước hợp lệ ở thế khai cuộc = **44** (giá trị chuẩn cờ tướng). Mã bị cản chân không sinh nước. Tượng bị cản mắt. Pháo cần ngòi mới ăn được. Binh chưa qua hà không đi ngang. |
| `test_check_detection.py` | Pháo chiếu qua ngòi. Mã chiếu (đúng chân mã). Xe chiếu. Lộ mặt tướng bị cấm. Nước đi để vua bị chiếu bị loại khỏi legal moves (**test chính cho B1**). |
| `test_game_rules.py` | Thế chiếu bí → `checkmate`. Thế hết nước không bị chiếu → `stalemate` (bên đó thua). 120 halfmove không ăn → hòa. Lặp 3 lần → hòa. Bàn thiếu tướng → thắng ngay. |
| `test_notation.py` | `h2e2` (thế khai cuộc) → `"Pháo 2 bình 5"`. Vài case tiền/hậu. |

Smoke test end-to-end: chạy 1 trận mock 200 nước, assert không có illegal move nào từ engine, kết thúc với status hợp lệ.

## Risks & rollback

| Risk | Xử lý |
|------|-------|
| Refactor 5 module làm hỏng import hiện có | Sửa import trong `referee.py` cùng lúc; test suite bắt lỗi ngay |
| Perft 44 sai vì mình hiểu luật lệch | Nếu con số khác 44, dừng lại kiểm tra từng loại quân bằng test riêng trước khi đi tiếp |
| `unmake_move` sai → grid rác âm thầm | Test: sau khi make+unmake N lần, `to_fen()` phải khớp FEN gốc |
| Notation VN phức tạp (tiền/hậu, 3 binh cùng cột) | Nếu quá phức tạp, v1 chỉ xử lý 2 quân cùng cột; case 3+ binh log fallback UCCI |

Rollback: chưa có git repo (`Is a git repository: false`) → **việc đầu tiên: `git init` + commit baseline** trước khi sửa gì.

## Acceptance criteria

- [x] `git init` + commit baseline trước khi refactor
- [x] Toàn bộ test pass; perft khai cuộc = 44
- [x] Không nước nào để vua mình bị chiếu được sinh ra
- [x] Trận kết thúc đúng: chiếu bí / hết nước / hòa 60 nước / lặp 3 lần
- [x] `to_fen()` xuất halfmove clock đúng
- [x] Nước sai của AI được đếm + log, không âm thầm thay bằng random
- [x] API call có timeout 30s; API treo không làm chết server
- [x] `debug=False` mặc định; server bind 127.0.0.1
- [x] TTS đọc được "Pháo 2 bình 5"
- [x] Hết trận hiện banner, không có `alert()`
- [x] README.md tồn tại, mô tả cách chạy
