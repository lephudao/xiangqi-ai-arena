# Bản đồ mã nguồn

**Cập nhật:** 2026-07-30 · **Tổng:** ~4.700 dòng Python + JavaScript · **142 test**

## 1. Tra nhanh: sửa gì thì mở file nào

| Muốn thay đổi | Mở file |
|---|---|
| Luật cờ, sinh nước đi | `engine/xiangqi/move_generation.py` |
| Phát hiện chiếu, lộ mặt tướng | `engine/xiangqi/attack_detection.py` |
| Điều kiện kết thúc trận, luật hoà | `engine/xiangqi/game_rules.py` |
| Ký hiệu tiếng Việt ("Pháo 2 bình 5") | `engine/xiangqi/notation.py` |
| Thêm model mới / sửa giá token | `engine/model_registry.py` |
| Thêm nhà cung cấp AI mới | `engine/providers/` |
| Nội dung prompt gửi cho AI | `engine/prompt_builder.py` |
| Ngưỡng chấm điểm, công thức accuracy | `engine/analysis/move_quality_scorer.py` |
| Quy trình một lượt đi, thống kê | `engine/referee.py` |
| Lược đồ cơ sở dữ liệu | `engine/storage/schema.sql` |
| Nội dung báo cáo trận | `engine/reporting/match_report_builder.py` |
| Vẽ bàn cờ, vị trí quân | `web/js/board-renderer.js` |
| Giao diện chung, gọi API | `web/app.js` |

## 2. Backend

### `engine/xiangqi/` — luật cờ (759 dòng)

| File | Dòng | Vai trò |
|---|---|---|
| `attack_detection.py` | 181 | Ô bị tấn công, chiếu tướng, lộ mặt tướng |
| `board.py` | 176 | Trạng thái bàn, FEN, thực hiện nước đi, bộ đếm luật hoà |
| `move_generation.py` | 173 | Sinh nước đi 7 loại quân, lọc theo an toàn của tướng |
| `notation.py` | 137 | UCCI ↔ toạ độ, ký hiệu cờ tướng tiếng Việt |
| `game_rules.py` | 66 | Chiếu bí / hết nước / mất tướng / các luật hoà |

Mốc kiểm chứng: thế khai cuộc có đúng **44 nước đi hợp lệ**.

### `engine/providers/` — kỳ thủ (548 dòng)

| File | Dòng | Vai trò |
|---|---|---|
| `anthropic_provider.py` | 117 | Claude qua SDK chính thức |
| `openai_compatible_provider.py` | 84 | OpenAI / Grok / DeepSeek (**chưa kiểm chứng**) |
| `gemini_provider.py` | 79 | Gemini qua SDK chính thức |
| `base_provider.py` | 77 | `MoveDecision`, `MoveProvider`, `MOVE_SCHEMA` |
| `__init__.py` | 73 | Nhà máy `create_provider()` |
| `pikafish_provider.py` | 56 | Engine làm kỳ thủ đối chuẩn |
| `mock_provider.py` | 38 | Đi ngẫu nhiên — mốc sàn |
| `human_provider.py` | 24 | Người chơi (cờ hiệu `is_human`) |

Thêm nhà cung cấp mới: viết một lớp kế thừa `MoveProvider`, khai báo trong
`model_registry.py`, nối vào `create_provider()`.

### Các module còn lại

| File | Dòng | Vai trò |
|---|---|---|
| `referee.py` | 463 | Trọng tài: phân lượt, xác thực, đếm vi phạm, chấm điểm, kết luận |
| `storage/match_repository.py` | 274 | SQLite: trận, nước đi, Elo |
| `reporting/match_report_builder.py` | 196 | Báo cáo trận làm khung script video |
| `prompt_builder.py` | 147 | Bàn cờ ASCII, lịch sử, kiểm kê quân, cảnh báo chiếu |
| `model_registry.py` | 130 | Danh mục model, giá token, cờ năng lực API |
| `analysis/pikafish_engine.py` | 249 | Giao tiếp UCI với Pikafish |
| `match_manager.py` | 141 | Nhiều trận song song theo `match_id` |
| `analysis/move_quality_scorer.py` | 135 | cp_loss, nhãn chất lượng, accuracy |
| `storage/elo_rating.py` | 46 | Công thức Elo |

## 3. Frontend (`web/`, 1.186 dòng)

| File | Dòng | Vai trò |
|---|---|---|
| `app.js` | 715 | Giao diện chung, gọi API, xem lại, chi phí, TTS |
| `js/replay-controller.js` | 177 | Xem lại từ cơ sở dữ liệu |
| `js/board-renderer.js` | 163 | Lưới SVG, vị trí quân (hình học khai báo một lần) |
| `js/human-input.js` | 131 | Chọn quân, chấm gợi ý, gửi nước đi |

## 4. Scripts

| File | Dùng khi |
|---|---|
| `scripts/install-pikafish.sh` | Cài engine chấm điểm (một lần) |
| `scripts/run_matches.py` | Chạy trận / giải vòng tròn không cần giao diện |
| `scripts/import_match_json.py` | Nhập file JSON chạy trước khi có cơ sở dữ liệu |
| `scripts/build_match_report.py` | Xuất báo cáo trận dạng Markdown |

## 5. Test (142 test)

| File | Nội dung canh giữ |
|---|---|
| `test_move_generation.py` | Perft khai cuộc = 44, chân mã, mắt tượng, ngòi pháo, binh qua hà |
| `test_check_detection.py` | Chiếu tướng, cấm tự chiếu, lộ mặt tướng |
| `test_game_rules.py` | Chiếu bí, hết nước (thua), hoà 60 nước, hoà lặp 3 lần |
| `test_notation.py` | Ký hiệu tiếng Việt, tiền/hậu |
| `test_match_referee.py` | Vòng đời trận, đếm nước sai luật, lỗi API không bị che |
| `test_providers_and_prompt.py` | Prompt đủ ngữ cảnh, không gửi tham số model không hỗ trợ |
| `test_pikafish_engine.py` | Handshake UCI, quy đổi điểm chiếu bí, thiếu binary vẫn chạy |
| `test_move_quality_scorer.py` | **Đảo dấu điểm** (lỗi dễ mắc nhất), phân loại chất lượng |
| `test_match_repository.py` | Ghi/đọc trận, crash giữa trận, Elo không tính hai lần |
| `test_elo_rating.py` | Công thức Elo, trận dở dang không tính |
| `test_match_manager.py` | Trận độc lập, không cướp trận đang xem |
| `test_match_report_builder.py` | Top blunder, điểm xoay chuyển |
| `test_human_vs_ai.py` | Trọng tài không đi thay người, cờ `used_hint` |
| `test_tournament_pairings.py` | Mọi cặp đánh cả hai màu |

Chạy: `venv/bin/python3 -m pytest tests/ -q`

Test liên quan Pikafish tự bỏ qua nếu chưa cài engine.

## 6. Nợ kỹ thuật đã biết

### `web/app.js` — 715 dòng, vượt xa ngưỡng 200

File này gộp nhiều trách nhiệm: gọi API, cập nhật giao diện, xem lại, bộ đếm chi phí, TTS,
hộp thoại cấu hình, chế độ overlay.

**Đề xuất tách:**

| Module | Nội dung |
|---|---|
| `js/api-client.js` | Mọi lời gọi `fetch` |
| `js/broadcast-ui.js` | Cập nhật thẻ kỳ thủ, eval bar, badge chất lượng |
| `js/audio-tts.js` | Đọc ký hiệu và lời thoại |
| `js/config-modal.js` | Hộp thoại cấu hình, danh mục model |
| `js/cost-guard.js` | Bộ đếm chi phí và ngân sách tự dừng |

Chưa tách vì đang ưu tiên hoàn thiện tính năng; nên làm trước khi thêm màn hình mới.

### Việc còn treo

- OpenAI / Grok / DeepSeek chưa gọi thử bằng key thật (`verified=False` trong danh mục)
- Bảng xếp hạng Elo mới có 1 trận nên chưa có ý nghĩa thống kê
- Luật phạt chiếu liên tục theo chuẩn Á Châu chưa cài (xử hoà kèm cờ cảnh báo)
- TTS dùng Web Speech vi-VN, giọng máy; nâng ElevenLabs là lựa chọn để ngỏ
