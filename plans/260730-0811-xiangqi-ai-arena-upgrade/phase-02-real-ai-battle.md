# Phase 2 — Đấu trí thật: Pikafish chấm điểm + provider layer + prompt nghiêm túc

**Status:** pending | **Est:** ~2 ngày | **Depends:** Phase 1 | **Blocks:** Phase 3

## Vấn đề đang giải

Hiện tại chỉ biết ai thắng ván, **không biết nước nào hay/dở**. Với content YouTube, câu "Claude chơi chính xác 91%, Grok 68%, GPT mắc 4 nước blunder" hấp dẫn hơn nhiều so với "Claude thắng". Ngoài ra prompt hiện tại quá nghèo (chỉ FEN + list UCCI, không lịch sử, không bàn cờ trực quan) nên đang đo "khả năng đọc FEN" hơn là "khả năng chơi cờ".

## Files sẽ tạo/sửa

```
engine/analysis/
  __init__.py
  pikafish_process.py      # quản lý subprocess UCI, gửi/nhận lệnh
  position_evaluator.py    # eval 1 thế cờ -> centipawn + bestmove + PV
  move_quality_scorer.py   # cp_loss -> nhãn chất lượng + accuracy %
engine/providers/
  __init__.py              # factory: create_provider(config)
  base_provider.py         # LLMProvider ABC + MoveDecision dataclass
  openai_compatible.py     # OpenAI, Grok, DeepSeek, Qwen, Kimi, OpenRouter
  gemini_provider.py
  anthropic_provider.py
  mock_provider.py         # random (baseline sàn)
  engine_provider.py       # Pikafish làm đối thủ (baseline trần)
engine/prompt_builder.py   # dựng prompt: ASCII board + history + material + check
engine/model_registry.py   # danh sách model hiện hành + giá token
engine/match_manager.py    # state theo match_id (bỏ global singleton)
scripts/install-pikafish.sh
engine/bin/                # (gitignore) binary + .nnue
```

Sửa: `engine/referee.py`, `server.py`, `web/app.js`, `web/index.html`, `.env.example`, `requirements.txt`, `.gitignore`

## Step 1 — Cài Pikafish (chi phí 0đ)

`scripts/install-pikafish.sh`:
1. Tải release `Pikafish-2026-01-02` từ GitHub (asset `.7z`, 55MB, đã gồm binaries + NNUE).
2. Giải nén (`brew install p7zip` nếu thiếu `7z`), copy binary macOS arm64 + `pikafish.nnue` → `engine/bin/`.
3. **Fallback nếu archive không có build macOS:** clone repo, `make -j profile-build ARCH=apple-silicon` trong `src/` (Pikafish là fork Stockfish, build ~2 phút trên M-series).
4. Verify: `echo -e "uci\nquit" | engine/bin/pikafish` → phải in `uciok`.
5. Ghi đường dẫn vào `.env`: `PIKAFISH_PATH=engine/bin/pikafish`.

Thêm `engine/bin/` vào `.gitignore` (binary 50MB+, không commit).

## Step 2 — `pikafish_process.py`: giao tiếp UCI

Pikafish nói UCI (không phải UCCI thuần) với FEN cờ tướng — cùng format FEN mà `to_fen()` đang xuất.

```
class PikafishProcess:
    start()                      # subprocess.Popen(stdin/stdout=PIPE, text=True)
                                 # gửi: uci -> chờ uciok -> setoption EvalFile -> isready -> readyok
    analyse(fen, movetime_ms)    # position fen <fen>; go movetime <ms>
                                 # đọc dòng info: score cp X | score mate N; bestmove <mv>
                                 # -> {cp, mate, bestmove, pv, depth}
    stop()                       # quit + terminate
    is_available -> bool
```

Chi tiết cần đúng:
- **Score luôn theo góc nhìn bên tới lượt** (side-to-move). Muốn so sánh 2 thế liên tiếp phải đảo dấu — đây là chỗ dễ sai nhất, phải có test.
- `score mate N` → quy đổi thành ±30000 để tính cp_loss không vỡ.
- Timeout đọc stdout (nếu engine treo → mark unavailable, không block trận).
- **Graceful degradation:** `PIKAFISH_PATH` không tồn tại → `is_available=False`, hệ thống chạy bình thường, chỉ tắt chấm điểm. Không bao giờ để việc thiếu engine làm sập trận.
- Chọn `movetime` thay `depth` để thời gian dự đoán được: mặc định **300ms/nước** (đủ mạnh để chấm LLM vốn chơi yếu hơn engine rất nhiều); config qua `PIKAFISH_MOVETIME_MS`.

## Step 3 — `move_quality_scorer.py`: biến eval thành content

Quy trình mỗi nước (2 lần gọi engine, ~600ms — chạy **sau** khi AI đã đi, không làm chậm quyết định của AI):

```
cp_before, best_move = analyse(fen_trước)        # từ góc nhìn bên đi
cp_after_opp        = analyse(fen_sau)           # từ góc nhìn ĐỐI PHƯƠNG
cp_after            = -cp_after_opp              # đảo về góc nhìn bên đi
cp_loss             = max(0, cp_before - cp_after)
```

Nhãn chất lượng (ngưỡng cp_loss):
| cp_loss | Nhãn | Hiển thị |
|---------|------|----------|
| trùng bestmove | Xuất sắc | ⭐ NƯỚC HAY NHẤT |
| 0–30 | Tốt | ✅ Tốt |
| 30–90 | Khá | 🟢 Khá |
| 90–200 | Không chính xác | 🟡 Thiếu chính xác |
| 200–500 | Sai | 🟠 SAI NƯỚC |
| >500 | Blunder | 🔴 BLUNDER! |

Accuracy % (mô hình win-percentage, chuẩn quen thuộc với người xem):
```
wp(cp)   = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)
acc(mv)  = clamp(0, 100, 103.1668 * exp(-0.04354 * (wp_before - wp_after)) - 3.1669)
player_accuracy = mean(acc của các nước của người đó)
```

Output mỗi nước lưu: `cp_before, cp_after, cp_loss, quality_label, accuracy, engine_bestmove, engine_pv`.
→ Đây là schema Phase 3 sẽ persist, và là nguồn cho "3 nước blunder tệ nhất trận" trong script video.

## Step 4 — `providers/`: mở rộng lên 6+ đối thủ

`base_provider.py`:
```python
@dataclass
class MoveDecision:
    move_ucci: str
    taunt: str            # 1-2 câu cho khán giả
    thinking: str         # phân tích thật (không đọc TTS, hiện ở log/subtitle)
    attempts: list[str]   # mọi nước đã thử kể cả sai
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    error: str | None

class LLMProvider(ABC):
    def decide(self, ctx: MoveContext) -> MoveDecision
```

`openai_compatible.py` phủ 1 lúc nhiều đối thủ (cùng schema `/chat/completions`):
| Player | base_url | env key |
|--------|----------|---------|
| OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| Grok (xAI) | `https://api.x.ai/v1` | `XAI_API_KEY` |
| DeepSeek | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` |
| Qwen | `https://dashscope.../compatible-mode/v1` | `QWEN_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |

`gemini_provider.py`, `anthropic_provider.py` giữ riêng (API format khác).
`engine_provider.py` — Pikafish làm player: đối thủ benchmark tuyệt vời cho content *"AI nào cầm cự được bao nhiêu nước với engine?"*. Có `skill_level` để hạ sức engine cho trận cân bằng hơn.

Yêu cầu chung mọi provider:
- Đổi `urllib` → `requests` (timeout, retry, error message rõ). Thêm `requests>=2.32` vào requirements.
- Retry mạng: 2 lần, backoff 1s/3s, chỉ retry lỗi 429/5xx/timeout.
- **Structured output chỉ để đảm bảo parse được, KHÔNG ép enum move** (xem quyết định #1 trong plan.md): OpenAI/Grok dùng `response_format: json_schema`; Gemini dùng `responseSchema`; Anthropic dùng tool `submit_move`. Field `move_ucci` là **string tự do** → giữ được tín hiệu "AI có đọc nổi bàn cờ không".
- Retry nước sai: tối đa 2 lần, kèm feedback cụ thể (`"e3e5 không hợp lệ: Pháo cần ngòi để ăn quân"`). Ghi vào `attempts`.
- Đếm token → `cost_usd` từ `model_registry`.

## Step 5 — `prompt_builder.py`: nâng chất lượng đầu vào

Prompt hiện tại chỉ có FEN + list UCCI. Bổ sung:

1. **Bàn cờ ASCII** (LLM đọc dạng grid tốt hơn FEN rất nhiều):
```
    a  b  c  d  e  f  g  h  i
9   xe ma tg si TG si tg ma xe
8   .  .  .  .  .  .  .  .  .
7   .  ph .  .  .  .  .  ph .
...     ── 楚河 漢界 ──
```
2. **Lịch sử 10 nước gần nhất** (UCCI + ký hiệu VN) → cho AI có tính liên tục kế hoạch, thay vì mỗi nước là quyết định cô lập.
3. **Kiểm kê quân còn lại 2 bên + chênh lệch chất** ("Đỏ hơn 1 Pháo").
4. **Cảnh báo `ĐANG BỊ CHIẾU`** khi `in_check=True` (có được từ Phase 1).
5. Danh sách nước hợp lệ (giữ), kèm ký hiệu VN cho các nước ăn quân.
6. Yêu cầu output 2 field tách biệt: `thinking` (phân tích thật, tối đa 3 câu) + `taunt` (1 câu trash-talk cho khán giả).
7. Optional: bật reasoning/thinking mode nếu provider hỗ trợ (`reasoning_effort` / `thinking.budget_tokens`) — cấu hình per-player để so sánh "có suy nghĩ sâu vs không".

**Quan trọng cho fairness:** cùng 1 template prompt cho MỌI provider, chỉ khác cách gói API. Nếu prompt khác nhau thì kết quả so sánh vô nghĩa → ghi rõ trong README như "luật thi đấu".

## Step 6 — `match_manager.py`: bỏ global singleton

`server.py:14` hiện là `match = MatchReferee()` global → không chạy được nhiều trận, không dùng được cho tournament.

```
class MatchManager:
    create(red_cfg, black_cfg) -> match_id
    get(match_id) -> MatchReferee
    list() -> [summary]
    delete(match_id)
```
API mới: `POST /api/matches`, `GET /api/matches/<id>/state`, `POST /api/matches/<id>/step`.
Giữ route cũ (`/api/state`, `/api/step`, `/api/reset`) trỏ vào "current match" để không phá frontend giữa lúc refactor.

Thêm `GET /api/models` → frontend render dropdown từ `model_registry` thay vì hardcode 4 option trong HTML.

## Step 7 — UI hiển thị dữ liệu mới

- **Eval bar** dọc cạnh bàn cờ (đỏ/đen theo cp, giống chess.com) — cực kỳ dễ hiểu với người xem.
- **Badge chất lượng nước đi** hiện lên khi đi (⭐/🟡/🔴 + cp_loss).
- **Accuracy % live** trên card mỗi player.
- **Counter**: số nước sai luật, thời gian nghĩ trung bình, chi phí API.
- Hiện `thinking` ở log dưới, `taunt` ở speech bubble (chỉ `taunt` được TTS đọc).
- Modularize `web/app.js` (357 LOC) → `web/js/api-client.js`, `board-renderer.js`, `broadcast-ui.js`, `audio-tts.js`, `config-modal.js`, `eval-bar.js`.

## Tests

| Test | Nội dung |
|------|----------|
`tests/test_pikafish_process.py` | Handshake `uciok`; analyse thế khai cuộc trả cp gần 0; thiếu binary → `is_available=False` không raise |
`tests/test_move_quality_scorer.py` | **Đảo dấu đúng** (test then chốt): thế thắng rõ cho Đỏ phải ra cp>0 khi Đỏ đi và cp<0 khi Đen đi. Nước bỏ Xe không lý do → cp_loss > 500 → nhãn Blunder. Nước = bestmove → cp_loss = 0 |
`tests/test_prompt_builder.py` | ASCII board khớp FEN; history đúng thứ tự; cảnh báo chiếu xuất hiện khi in_check |
`tests/test_providers.py` | Parse response từng provider (fixture JSON, **không gọi API thật**); nước sai → ghi vào `attempts` chứ không bị thay âm thầm; lỗi mạng → `error` có nội dung |

Tests provider dùng fixture, không tốn tiền API. Smoke test có API thật chạy tay 1 lần, ghi kết quả vào `plans/reports/`.

## Risks

| Risk | Xử lý |
|------|-------|
| **Sai dấu eval** (lỗi kinh điển) → toàn bộ điểm chấm ngược | Test bắt buộc như trên; kiểm tra tay 1 thế "Đỏ sắp thắng" |
| Pikafish không có build macOS trong archive | Fallback build source (`ARCH=apple-silicon`), đã ghi trong Step 1 |
| Analyse 300ms × 2 làm trận chậm | Chấm điểm **sau** khi đi, có thể chạy async/nền; nếu vẫn chậm → giảm còn 1 lần analyse (chỉ cp_after, suy ra cp_loss từ nước trước) |
| Chi phí API tăng vì prompt dài hơn (ASCII board + history) | `model_registry` đếm cost realtime; đặt cảnh báo ngưỡng `MAX_COST_PER_MATCH_USD` → hết thì dừng trận |
| Model ID lỗi thời (hiện hardcode `gemini-1.5-flash`, `gpt-4o-mini`, `claude-3-5-haiku`) | `model_registry.py` là 1 chỗ duy nhất để cập nhật; verify từng model ID bằng 1 call thật trước khi ghi vào registry |

## Acceptance criteria

- [ ] `scripts/install-pikafish.sh` chạy xong → `uciok`; thiếu binary vẫn chạy được trận (degradation)
- [ ] Mọi nước có `cp_loss` + nhãn chất lượng; test đảo dấu pass
- [ ] Accuracy % mỗi player hiện trên UI, khớp công thức
- [ ] 6 loại player hoạt động: OpenAI, Gemini, Anthropic, Grok, DeepSeek, Pikafish(+mock)
- [ ] Prompt giống nhau cho mọi provider (fairness), có ASCII board + history + cảnh báo chiếu
- [ ] Nước sai luật được đếm hiển thị, có retry-with-feedback 2 lần
- [ ] `thinking` và `taunt` tách biệt; TTS chỉ đọc `taunt`
- [ ] Chạy song song 2 trận qua `/api/matches` không lẫn state
- [ ] Cost tracker hiện chi phí trận realtime
