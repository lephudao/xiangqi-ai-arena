# Xiangqi AI Arena — Nâng cấp thành "cuộc chiến AI thực thụ"

**Status:** Phase 1 XONG · Phase 2 gần xong (Pikafish + provider layer + prompt XONG; còn match_manager) | **Created:** 2026-07-30 | **Owner:** lephudao

## Mục tiêu

Biến hệ thống hiện tại (demo chạy được) thành đấu trường LLM đo được **sức mạnh tính toán thật**, đủ tin cậy để sản xuất content YouTube đều đặn.

3 kết quả cần đạt:
1. **Đúng luật** — không còn nước sai luật, phát hiện chiếu/chiếu bí/hòa chuẩn.
2. **Đo được** — mỗi nước đi có điểm chất lượng (centipawn loss) do engine Pikafish chấm; mỗi AI có accuracy %, blunder count, Elo.
3. **Sản xuất được** — lưu trận, replay không tốn API, chạy giải đấu headless, overlay sẵn cho OBS.

## Ràng buộc đã chốt

- Chạy **local** (screen recording) trước; livestream là mục tiêu sau → hardening bảo mật ở mức "không tự bắn chân", chưa cần auth đầy đủ.
- **Pikafish miễn phí** (GPL, chạy local, 0 chi phí API) → tích hợp làm trọng tài chấm điểm.
- Giữ stack hiện tại: Python + Flask + vanilla JS. Không thêm framework (YAGNI).
- Không dùng mock data để "làm cho test pass".

## Phases

| Phase | Nội dung | File | Ưu tiên | Est. |
|-------|----------|------|---------|------|
| 1 | Sửa tính đúng đắn luật cờ + an toàn vận hành | [phase-01-rules-correctness.md](phase-01-rules-correctness.md) | ✅ XONG | ~1 ngày |
| 2 | Pikafish chấm điểm + provider layer + prompt thật | [phase-02-real-ai-battle.md](phase-02-real-ai-battle.md) | 🟠 Đang làm | ~2 ngày |
| 3 | Persist + replay + tournament + Elo + overlay OBS | [phase-03-content-production.md](phase-03-content-production.md) | 🟡 Scale content | ~2 ngày |
| 4 | Chế độ Người vs AI | [phase-04-human-vs-ai.md](phase-04-human-vs-ai.md) | 🟡 Content mới | ~0.5 ngày |

**Dependencies:** Phase 2 phụ thuộc Phase 1 (chấm điểm vô nghĩa nếu nước đi sai luật). Phase 3 phụ thuộc Phase 2 (persist cần schema eval). Phase 4 phụ thuộc Phase 2+3. Trong mỗi phase các task tuần tự.

## Acceptance criteria toàn plan

- [x] Test suite luật cờ pass: check detection, chiếu bí, hết nước, lộ mặt tướng, hòa 60 nước, lặp 3 lần
- [x] Chạy 1 trận mock 200 nước không sinh nước sai luật, không treo, kết thúc đúng trạng thái
- [x] Pikafish chấm được mọi nước; UI hiện eval bar + nhãn chất lượng (Hay/Sai/Blunder)
- [x] 5+ provider hoạt động: OpenAI, Gemini, Anthropic, Grok, DeepSeek (+ Pikafish làm player boss)
- [x] Nước sai luật của AI được **đếm và log**, không bị âm thầm thay bằng random
- [ ] Trận lưu vào SQLite; replay lại được từ DB không gọi API
- [ ] `scripts/run-tournament.py` chạy round-robin không cần bấm nút
- [ ] Elo leaderboard cập nhật sau mỗi trận
- [ ] Chế độ `?overlay=1` cho OBS browser source, không có UI chrome

## Quyết định thiết kế quan trọng

1. **KHÔNG dùng enum constraint / tool-calling ép move hợp lệ.** Dùng JSON schema chỉ để đảm bảo parse được, nhưng `move_ucci` là string tự do. Lý do: nếu ép enum, mọi AI đều đi hợp lệ 100% → mất hoàn toàn tín hiệu "AI có thật sự đọc được bàn cờ không", vốn là nội dung hấp dẫn nhất. Thay vào đó: cho AI **retry 2 lần có feedback**, và đếm số lần đi sai.
2. **Tách `thinking` (phân tích thật) khỏi `taunt` (thoại cho khán giả).** Hiện tại gộp 1 field `reasoning` nên vừa mất chiều sâu vừa mất kịch tính.
3. **Pikafish là trọng tài chấm điểm, KHÔNG phải người chọn nước hộ AI.** Engine chỉ đánh giá sau khi AI đã quyết định. (Riêng chế độ "engine as player" là đối thủ benchmark, bật rõ ràng.)
4. **State theo match_id, không global singleton** — điều kiện cần cho tournament + livestream nhiều trận.
5. **Degradation rõ ràng:** thiếu Pikafish → tắt chấm điểm nhưng trận vẫn chạy; lỗi API → log lỗi thật, không giả vờ AI đi nước random.

## Quyết định đã chốt (2026-07-30)

1. **Người vs AI: CÓ** → tách thành [Phase 4](phase-04-human-vs-ai.md).
2. **TTS: giữ Web Speech vi-VN** trước; cân nhắc ElevenLabs sau khi quy trình quay video đã ổn.
3. **Luật hoà: chấp nhận đơn giản hoá** — chiếu liên tục xử hoà, không cài luật phạt chuẩn Á Châu.
4. **API key hiện có: Gemini + Anthropic** → hai provider này test bằng key thật; OpenAI/Grok/DeepSeek
   viết theo cùng chuẩn OpenAI-compatible nhưng chỉ test bằng fixture, đánh dấu "chưa kiểm chứng thật".
5. **Deploy: chạy local + quay màn hình** trước; livestream chỉ làm sau khi thêm xác thực.

## Câu hỏi chưa giải quyết

Chưa có.
