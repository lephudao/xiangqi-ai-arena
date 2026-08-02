# Kế hoạch kênh YouTube "AI Thực Chiến"

**Ngày:** 2026-08-02 · **Trạng thái:** chưa khởi động · **Chủ kênh:** Lê Phú Đào

| | |
|---|---|
| Tên hiển thị | **AI Thực Chiến** (dùng "AI Thực Chiến Lab" khi cần phân biệt) |
| Handle | `@aithucchienlab` |
| Khán giả | Việt Nam, không làm phụ đề Anh giai đoạn này |
| Định dạng | Voiceover + màn hình, không lộ mặt |
| Ngân sách API | $50/tháng |
| Nhịp đăng | Thứ Ba & thứ Bảy, 19:00–21:00 giờ VN + 4 Shorts/tuần |

---

## 1. Định vị

> **Kênh kiểm chứng AI bằng thực nghiệm, bằng tiếng Việt.**
> Slogan: *"Không nghe quảng cáo. Bắt AI ra trận rồi tính."*

Lý do tồn tại: mảng tin tức AI tiếng Việt bão hoà, rào cản gần bằng 0, video chết sau 3–10 ngày.
Thứ **chỉ kênh này có** là hệ thống đấu trường cờ tướng đã build (trọng tài độc lập + Pikafish
chấm điểm). Nên:

- **Đấu trường = format flagship**, tạo định danh, evergreen, không sao chép được
- **Tin tức + hướng dẫn = nội dung nuôi kênh**, kéo view và tìm kiếm
- **Điểm nối hai thứ:** mọi model mới ra mắt được ném vào đấu trường trong 48h → kênh khác đọc
  thông cáo báo chí, kênh này có accuracy %, số nước sai luật, blunder, Elo

Đấu trường **không** phải toàn bộ kênh. Giao của "người thích cờ tướng" và "người quan tâm AI"
quá nhỏ để nuôi kênh.

---

## 2. Nhận diện

### Mô tả kênh

Dòng đầu (hiện ở kết quả tìm kiếm):
```
Bắt AI ra trận rồi đo bằng số. Không nghe quảng cáo, không đọc thông cáo báo chí.
```

Đầy đủ:
```
AI Thực Chiến — kênh kiểm chứng AI bằng thực nghiệm, bằng tiếng Việt.

Hãng nào cũng nói model của mình thông minh nhất. Kênh này không tin, mà đo.

🏆 ĐẤU TRƯỜNG AI — Claude, Gemini, ChatGPT, Grok, DeepSeek đánh cờ tướng với
   nhau dưới một trọng tài độc lập. Không AI nào được tự sửa nước đi sai của
   mình. Mỗi nước được engine Pikafish chấm điểm: độ chính xác %, số nước đi
   sai luật, số blunder. Không biết chơi cờ vẫn xem được — tất cả hiện thành
   số trên màn hình.

⚡ MODEL MỚI RA — THỬ NGAY trong 48h. Bạn nghe số liệu, không nghe quảng cáo.

🛠️ AI VÀO VIỆC THẬT — quy trình cụ thể để làm việc nhanh hơn. Không phải
   "top 10 công cụ thần thánh".

📰 TIN AI TIẾNG VIỆT — chọn lọc thứ thật sự đáng quan tâm, bỏ qua phần ồn ào.

🔓 Toàn bộ đấu trường là mã nguồn mở, bạn tự chạy được bằng API key của mình.

Video mới thứ Ba & thứ Bảy · Liên hệ: [email]
```

### Từ khoá kênh (Studio → Cài đặt → Kênh → Từ khoá)
```
AI, trí tuệ nhân tạo, AI tiếng Việt, hướng dẫn AI, ứng dụng AI, AI cho công việc, công cụ AI,
tin tức AI, Claude, Gemini, ChatGPT, Grok, DeepSeek, so sánh AI, AI nào tốt nhất, đánh giá AI,
benchmark AI, đấu trường AI, AI đánh cờ tướng, LLM, prompt, tự động hoá công việc, AI miễn phí,
AI 2026
```

Tags không còn ảnh hưởng xếp hạng. **Tiêu đề + thumbnail quyết định 90%.**

### Cấu trúc series
```
Kênh:  AI Thực Chiến
  ├─ ĐẤU TRƯỜNG AI    cờ tướng, benchmark, bảng xếp hạng Elo
  ├─ AI VÀO VIỆC      hướng dẫn ứng dụng, quy trình
  ├─ TIN AI           tổng hợp, model/tool mới
  └─ HẬU TRƯỜNG       build in public, mã nguồn mở
```
Thumbnail mẫu cố định cho đấu trường: 2 logo model đối đầu + 1 con số lớn (`91% vs 64%`).
Không lộ mặt nên thumbnail gánh toàn bộ CTR — phải nhất quán để nhận ra từ xa.

### Giọng đọc
| Nội dung | Giọng |
|---|---|
| Hướng dẫn, tin tức, hậu trường | **Giọng thật của chủ kênh** |
| Lời bình trong trận, Shorts | TTS Gemini — đóng khung rõ là "bình luận viên AI", giọng thật dẫn vào/ra |

Chốt một giọng TTS duy nhất cho đấu trường và giữ nguyên — giọng là nhận diện thương hiệu.

---

## 3. ⚠️ Vấn đề uy tín phải xử lý TRƯỚC video #1

`engine/prompt_builder.py:128-131` đưa **toàn bộ danh sách nước đi hợp lệ** vào prompt, kèm chú
thích ăn quân. Trong khi README/PDR tuyên bố "cố ý KHÔNG dùng enum để giữ tín hiệu AI có đọc
được bàn cờ không".

Output đúng là string tự do, nhưng hiệu ứng gần như y hệt enum: AI chỉ cần copy một dòng trong
danh sách được đưa sẵn. Chỉ số "số nước đi sai luật" đang đo *"AI có copy đúng danh sách không"*,
**không** đo *"AI có hiểu luật cờ không"*.

Mã nguồn sẽ mở và được dẫn link dưới mô tả → người xem đọc file này sẽ chụp màn hình đăng lên.
Với kênh mà toàn bộ vốn là "đo đạc trung thực", đây là rủi ro lớn nhất.

**Xử lý — biến thành nội dung:** thêm cờ bật/tắt danh sách nước hợp lệ, chạy hai chế độ:

| Chế độ | Prompt | Dùng cho |
|---|---|---|
| Hướng dẫn (hiện tại) | Có danh sách nước hợp lệ | Video giải trí, trận đẹp, chạy ổn định |
| **Thi đấu thật** | Chỉ bàn cờ + FEN + lịch sử | **Bảng Elo chính thức** — số nước sai luật mới có nghĩa |

Mở khoá video #4 và #5 (xem mục 6) — dự kiến tỉ lệ đi sai luật nhảy từ ~0% lên 20–60%.
Số liệu độc quyền, chưa ai ở VN có.

---

## 4. Ngân sách $50/tháng

Giá lấy từ `engine/model_registry.py`. Giả định ~1.8k token input/lượt, ~55 lượt/bên/trận.

| Cặp đấu | Chi phí/trận |
|---|---|
| Haiku 4.5 vs **Pikafish** (miễn phí 1 bên) | **~$0.18** |
| Haiku 4.5 vs Gemini 3.6 Flash | ~$0.66 |
| Gemini 3.1 Pro vs Haiku 4.5 | ~$1.4 |
| Opus 5 vs Gemini 3.1 Pro (siêu cúp) | ~$3.8 |

### Phân bổ
| Khoản | Tiền | Kết quả |
|---|---|---|
| Trận xếp hạng (model rẻ + đối thủ Pikafish) | $28 | **~70 trận/tháng** |
| 3 trận Siêu Cúp (frontier) | $12 | 3 video flagship |
| TTS lời bình | ~$5 | 8 video — **chưa đo thật, cần xác minh** |
| Thử tools cho mảng hướng dẫn/tin tức | $5 | |

70 trận/tháng → 5 model × ~28 ván mỗi model. Đây là điều kiện sống còn để Elo có nghĩa.

### Đòn bẩy chi phí (theo hiệu quả giảm dần)
1. **Pikafish làm đối thủ neo cho Elo** — miễn phí, sức mạnh cố định, chạy local. Vừa giảm nửa
   chi phí mỗi trận vừa làm Elo ổn định hơn hẳn so với chỉ AI đấu AI. Hạ skill level để AI
   thắng được đôi khi.
2. **Token output là nơi tiền cháy, không phải input.** Trận Opus 5: thinking chiếm ~80% chi phí.
   Giới hạn effort/thinking khi model cho phép → tiết kiệm 3–4 lần.
3. `--max-moves 120` + `--max-cost-usd` cho mọi lần chạy (đã có sẵn trong `run_matches.py`).
4. **Kiểm chứng key DeepSeek** — `verified=False`, chưa có giá trong registry. Nhiều khả năng là
   đối thủ xếp hạng rẻ nhất, có thể tăng gấp đôi số trận/tháng.

### Hai bảng xếp hạng — bắt buộc tách riêng
- **Bảng Elo chính thức** — chỉ model chạy được ≥20 ván/tháng, chạy ở chế độ "thi đấu thật"
- **Trận Siêu Cúp** — Opus 5, Gemini 3.1 Pro, GPT-5… 1–3 ván, ghi rõ trên overlay
  **"biểu diễn, không tính Elo"**

Luôn đóng dấu **số ván + ngày + model ID** trên mọi overlay xếp hạng. Bị bóc "xếp hạng từ 3 ván"
một lần là mất uy tín vĩnh viễn.

---

## 5. Trụ cột nội dung

| Trụ cột | % | Vai trò | Nhịp |
|---|---|---|---|
| 1. Đấu trường cờ tướng | 30% | Định danh kênh, evergreen | 1 video/tuần |
| 2. Model mới vào lò | 15% | Cầu nối tin tức × lợi thế — **giá trị cao nhất** | Theo sự kiện, trong 48h |
| 3. AI vào việc thật | 25% | Traffic tìm kiếm, giữ chân, kiếm tiền | 1 video/tuần |
| 4. Tin tức & tools | 20% | Nuôi thuật toán, kéo sub | Shorts + tổng hợp tháng |
| 5. Hậu trường build | 10% | Uy tín kỹ thuật, kéo dev, GitHub star | 1 video/tháng |

Trụ cột 3 và 4 **không phụ thuộc đấu trường** → kênh không chết khi một tuần các trận đều hoà nhạt.

### Nhịp sản xuất (1 người)
```
Chủ nhật:  chạy batch 15-20 trận qua đêm (--max-cost-usd chặn ngân sách)
Thứ 2:     đọc báo cáo (build_match_report.py), chọn trận, viết script
Thứ 3:     đăng video trụ cột 1 hoặc 2
Thứ 4-5:   quay + dựng video trụ cột 3
Thứ 7:     đăng video trụ cột 3/4
Rải tuần:  4 Shorts cắt từ trận đã lưu trong SQLite — $0 API
```

### Shorts ($0, nguồn dồi dào nhất)
Mỗi trận đã lưu sinh 3–5 Shorts: nước đi sai luật, blunder nặng nhất (đã có nút nhảy tới),
top accuracy tuần, "AI nghĩ 47 giây rồi đi nước mất Xe".

### Khai thác đặc thù VN
`"Dùng AI xịn không cần thẻ quốc tế"`, `"AI viết tiếng Việt: model nào không bị lai văn dịch"` —
kênh nước ngoài không bao giờ làm.

---

## 6. 12 video đầu (6 tuần)

| # | Trụ cột | Tiêu đề | API |
|---|---|---|---|
| 1 | Đấu trường | **Tôi bắt 5 AI mạnh nhất thế giới đánh cờ tướng** (video giới thiệu kênh) | ~$4 |
| 2 | Việc thật | Tôi làm 8 tiếng công việc trong 90 phút bằng AI — quy trình đầy đủ | ~$1 |
| 3 | Đấu trường | **Claude vs Gemini — trận đầy đủ, chấm điểm từng nước** | ~$1.4 |
| 4 | Hậu trường | ⭐ **"Tôi phát hiện mình đang chấm điểm sai" — vì sao tôi bỏ danh sách gợi ý** | $0 |
| 5 | Đấu trường | ⭐ **Bỏ gợi ý đi — AI nào còn biết đi đúng luật?** *(số liệu độc quyền)* | ~$3 |
| 6 | Việc thật | 5 prompt tôi dùng mỗi ngày — kèm file copy được | ~$1 |
| 7 | Model mới | *(theo sự kiện)* **[Model vừa ra] — ném thẳng vào đấu trường trong 48h** | ~$4 |
| 8 | Tin tức | Tin AI đáng chú ý tháng này trong 12 phút | $0 |
| 9 | Đấu trường | **AI vs Pikafish — engine cờ tướng thật. Trụ được bao lâu?** | ~$0.2 |
| 10 | Việc thật | Dùng AI xịn ở Việt Nam không cần thẻ quốc tế | ~$1 |
| 11 | Đấu trường | 🏆 **BẢNG XẾP HẠNG ELO THÁNG ĐẦU — AI nào thật sự thông minh nhất?** | $0 |
| 12 | Hậu trường | Tự chạy đấu trường bằng key của bạn *(demo bản web)* | $0 |

Tổng API 6 tuần **~$16** — còn dư để chạy 70 trận nền cho video #11.

**Video #4 + #5 là cặp quan trọng nhất.** Tự công khai lỗi của mình rồi sửa là cách xây uy tín
nhanh nhất, và biến rủi ro ở mục 3 thành tài sản.

**Video #11 là video có sức lan xa nhất** — nếu đủ trận, đây là thứ báo chí công nghệ VN trích
dẫn được, biến kênh thành "cơ quan xếp hạng".

---

## 7. Việc cần làm trước video #1

- [ ] Đăng ký handle `@aithucchienlab`, dựng banner + avatar, dán mô tả & từ khoá ở mục 2
- [ ] **Thêm cờ tắt danh sách nước hợp lệ trong `prompt_builder`** → mở khoá video #4, #5, bảng Elo
- [ ] Deploy bản BYOK lên GitHub Pages / Cloudflare Pages (web tĩnh, $0/tháng)
  - Cảnh báo rõ trong UI: key gửi thẳng tới nhà cung cấp AI, không qua server
  - Ẩn/vô hiệu hoá GPT-5 ở bản web (`browser_cors=False`) kèm giải thích, tránh lỗi CORS khó hiểu
- [ ] Kiểm chứng key DeepSeek + Grok, điền giá vào `model_registry.py`
- [ ] Chạy batch ~70 trận tháng 1 để có dữ liệu cho video #11
- [ ] **Đo chi phí TTS thật cho 1 video 12 phút** — con số duy nhất chưa xác minh được
- [ ] Chốt giọng TTS cho series đấu trường, thu thử giọng thật cho trụ cột 3

---

## 8. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Danh sách nước hợp lệ trong prompt làm hỏng chỉ số | Mục 3 — bắt buộc, trước video #1 |
| Elo từ ít trận là số vô nghĩa | Tách 2 bảng, ≥20 ván/model, đóng dấu số ván + ngày trên overlay |
| Model đổi phiên bản liên tục | Ghi model ID + ngày; biến thành nội dung định kỳ hàng tháng |
| Người xem không biết cờ tướng | Overlay accuracy %/blunder/nước sai luật luôn hiện, to |
| Chi phí API vượt $50 | `--max-cost-usd`, `--max-moves 120`, ưu tiên đối thủ Pikafish |
| Nội dung tin tức có deadline nghiệt | Không để trễ tin làm hỏng nhịp đăng trụ cột 1 |
| Kênh trùng tên "AI Thực Chiến" | Dùng "AI Thực Chiến Lab" ở nơi cần phân biệt; hậu tố lab hợp DNA đo đạc |
| Stream 24/7 | **Chưa làm** — đốt API liên tục, view giờ đầu thấp. Cân nhắc lại sau ~5k sub |

---

## Câu hỏi chưa có lời giải

1. $50 là ngân sách API thuần hay gồm cả thuê bao ChatGPT Plus / Claude Pro?
2. Đã có tài khoản DeepSeek/xAI để kiểm chứng key chưa?
3. Kênh `@aithucchien` trùng tên đang hoạt động hay bỏ hoang, cùng mảng AI hay khác? Ảnh hưởng
   mức độ cần dùng hậu tố "Lab".
4. Chi phí TTS thật/video — chưa đo, đang ước tính $0.3–0.6.
