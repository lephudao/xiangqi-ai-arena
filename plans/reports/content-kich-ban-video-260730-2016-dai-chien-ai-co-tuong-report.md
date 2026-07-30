# Kịch bản video từ studio Đại Chiến AI Cờ Tướng

**Ngày:** 2026-07-30 · **Cho kênh:** AI và ứng dụng

## Vì sao cờ tướng là đề tài tốt cho kênh AI

Không phải vì cờ tướng, mà vì nó là **bài kiểm tra AI hiếm hoi thoả cả ba điều kiện**:

1. **Có đáp án khách quan** — engine Pikafish chấm từng nước, không phải ý kiến chủ quan
2. **Khán giả Việt hiểu ngay** — ai cũng biết Pháo đầu, Mã đội, chiếu tướng
3. **AI thất bại là thấy được** — đi sai luật, mất quân, chiếu bí; không cần giải thích dài

Đây là điểm khác biệt so với các video "test AI" thông thường (hỏi vài câu rồi tự nhận xét):
**mọi con số trong video đều có nguồn kiểm chứng được.**

---

## Dữ liệu thật đã đo (dùng trực tiếp trong video)

| Kỳ thủ | Độ chính xác | Nước sai luật |
|---|---|---|
| Claude Haiku 4.5 | 80–91% | 0 |
| Gemini 3.6 Flash | 83–89% | 0 |
| Pikafish (engine) | 100% | 0 |
| Mock (đi ngẫu nhiên) | ~50% | 0 |

**Các khoảnh khắc đã ghi lại được:**

- Pikafish **chiếu bí Claude Haiku sau 16 nước**
- Claude Haiku và Gemini 3.1 Pro **độc lập chọn cùng nước Pháo đầu (h2e2)** — đúng khai cuộc kinh điển
- Claude Haiku **gọi sai tên quân của chính mình**: mô tả nước `e0e1` là *"Mã e0-e1 phát triển quân cờ"* trong khi `e0` là **Tướng**
- Gemini Flash mắc blunder mất 817 điểm ở nước 22
- Thời gian nghĩ của Gemini tăng dần 5.9s → 27.8s, Claude ổn định 4–8s
- Trong 240 lượt gọi API của hai LLM: **0 nước sai luật, 0 lỗi API**
- Chi phí toàn bộ đo đạc: **$0.35**

> ⚠️ Đây là số từ các trận thử của tôi. Trước khi lên video, bạn nên tự chạy lại để có trận
> của riêng mình — và vì trận nào cũng lưu vào cơ sở dữ liệu, số liệu sẽ tự có.

---

## Video 1 — Video mở màn (10–12 phút)

**Tiêu đề đề xuất:** *Tôi bắt Claude và Gemini đánh cờ tướng — và chấm điểm từng nước*

Đây nên là video đầu tiên vì nó vừa giới thiệu format, vừa là nội dung độc lập.

### Hook (0:00–0:20)

> "Đây là Claude. Đây là Gemini. Tôi bắt chúng đánh cờ tướng với nhau.
> Nhưng điều thú vị không phải con nào thắng — mà là **tôi chấm được điểm từng nước một
> cách khách quan.** Và con số đầu tiên đã làm tôi bất ngờ."

Cắt ngay sang màn hình eval bar đang đảo chiều + badge 🔴 BLUNDER hiện lên.

### Cấu trúc

| Thời lượng | Nội dung | Quay gì |
|---|---|---|
| 0:20–1:30 | **Vấn đề:** làm sao biết AI nào thông minh hơn? Các bài test thường mang tính chủ quan | Nói trước camera / màn hình |
| 1:30–3:00 | **Giải pháp:** cờ tướng có đáp án khách quan. Giới thiệu engine Pikafish chấm điểm | Giao diện studio, giải thích eval bar |
| 3:00–4:00 | **Mốc so sánh:** cho AI đấu với bot đi ngẫu nhiên trước | Trận mock, accuracy ~50% |
| 4:00–8:00 | **Trận chính:** Claude vs Gemini, tua nhanh, dừng ở 3 khoảnh khắc | Xem lại + nút "Nước tệ nhất" |
| 8:00–10:00 | **Kết quả:** bảng độ chính xác, số blunder, chi phí | Bảng tổng kết |
| 10:00–11:30 | **Điều bất ngờ nhất:** cả hai chọn cùng nước khai cuộc | Cận cảnh 2 màn hình |
| 11:30–12:00 | Chốt + teaser video sau (đấu engine) | |

### Điểm nhấn bắt buộc có

**Mốc 50% là chìa khoá của cả video.** Bot đi ngẫu nhiên đạt ~50% độ chính xác. LLM đạt
80–91%. Câu chốt:

> "Nếu AI chỉ đoán bừa, nó sẽ được khoảng 50 điểm. Claude được 91. Nghĩa là nó **thật sự
> đang chơi cờ**, không phải đoán."

Đây là bằng chứng mạnh nhất và không video "test AI" nào khác có.

---

## Video 2 — Trận đấu boss (8–10 phút)

**Tiêu đề đề xuất:** *AI mạnh nhất cầm cự được bao nhiêu nước trước engine cờ tướng?*

Format rẻ nhất và kịch tính nhất: engine miễn phí, trận kết thúc nhanh và dứt khoát.

### Hook (0:00–0:15)

> "Claude Haiku vừa đánh ngang ngửa với Gemini. Bây giờ tôi cho nó gặp Pikafish —
> engine cờ tướng chuyên dụng. **Nó trụ được 16 nước.**"

Cắt sang màn hình chiếu bí + "ĐEN BÍ" trên eval bar.

### Cấu trúc

| Thời lượng | Nội dung |
|---|---|
| 0:15–1:30 | Engine chuyên dụng khác LLM thế nào: một bên tính toán, một bên "hiểu" |
| 1:30–5:00 | Xem lại 16 nước, dừng ở nước 9 — nước Tướng 5 tấn 1 dẫn tới thua |
| 5:00–7:00 | **Đọc lời AI tự giải thích** cho nước sai đó — và chỉ ra nó gọi sai tên quân |
| 7:00–8:30 | Ý nghĩa: LLM giỏi ngôn ngữ về cờ, không giỏi tính toán cờ |
| 8:30–9:30 | Thử lại với model đắt hơn (Opus 5) — có khá hơn không? |

### Khoảnh khắc vàng

Nước #9, Claude mô tả nước đi của mình:

> *"Nước **Mã** e0-e1 phát triển quân cờ một cách hiệu quả..."*

Nhưng `e0` là **Tướng**, không phải Mã. Toạ độ đúng, tên quân sai.

Đây là chất liệu tuyệt vời để nói về bản chất LLM: nó thao tác ký hiệu đúng nhưng **mô hình
thế giới bên trong không khớp** — một chủ đề AI thật sự, không phải trò vui.

---

## Video 3 — Tôi thách đấu AI (10–12 phút)

**Tiêu đề đề xuất:** *Tôi đấu cờ tướng với AI — và để nó chấm điểm tôi*

Format có sức đồng cảm cao nhất: khán giả thấy người thật, không phải hai bot.

### Hook (0:00–0:20)

> "Tôi biết đánh cờ tướng ở mức trung bình. Hôm nay tôi đấu với AI —
> và **cùng một engine sẽ chấm điểm cả tôi lẫn nó**, cùng một thước đo."

### Cấu trúc

| Thời lượng | Nội dung |
|---|---|
| 0:20–1:00 | Luật chơi: cùng thước đo, tôi không dùng gợi ý (hoặc dùng thì có đánh dấu) |
| 1:00–8:00 | Ván đấu, bình luận trực tiếp cảm giác của mình khi AI đi lạ |
| 8:00–10:00 | Kết quả: độ chính xác của tôi vs của AI |
| 10:00–11:30 | Cảm nhận: AI mạnh/yếu ở đâu — thứ mà con số không nói được |

### Lưu ý sản xuất

Nút 💡 Gợi Ý có đánh dấu `used_hint`. **Nói rõ trong video** nếu bạn có dùng — đây là điểm
tạo uy tín, và cũng là chi tiết thú vị ("tôi có gian lận 2 nước, hệ thống ghi lại hết").

---

## Video 4 — Bảng xếp hạng định kỳ (6–8 phút, hàng tháng)

**Tiêu đề đề xuất:** *Bảng xếp hạng AI cờ tướng tháng [X] — con nào đang dẫn đầu?*

Đây là **format tự sinh nội dung**: chạy giải vòng tròn qua đêm, sáng có số liệu, không cần
nghĩ ý tưởng mới mỗi tháng.

### Cấu trúc

| Thời lượng | Nội dung |
|---|---|
| 0:00–0:20 | Hook: thứ hạng thay đổi thế nào so với tháng trước |
| 0:20–2:00 | Cách chấm: Elo, đổi màu, chỉ tính trận kết thúc đúng luật |
| 2:00–5:00 | Đi qua từng kỳ thủ: Elo, độ chính xác, số blunder, chi phí mỗi trận |
| 5:00–7:00 | Trận hay nhất tháng — tua nhanh |
| 7:00–8:00 | Model mới sắp thêm vào tháng sau |

### Cần làm trước

Chạy giải vòng tròn để bảng Elo có ý nghĩa:

```bash
scripts/run_matches.py --round-robin claude-haiku-4-5,gemini-3.6-flash,pikafish \
    --max-moves 140 --max-cost-usd 5.00
```

Hiện mới có 1 trận trong bảng nên chưa dùng làm video được.

---

## Video 5 — Meta: dùng AI để xây đấu trường cho AI (12–15 phút)

**Tiêu đề đề xuất:** *Tôi dùng AI viết code để xây hệ thống chấm điểm AI — và nó tìm ra lỗi của chính nó*

Video này hợp nhất với định vị kênh "AI và ứng dụng", vì nói về **quy trình làm việc với AI**
chứ không chỉ kết quả.

### Nội dung

Câu chuyện có thật trong quá trình xây:

1. **Engine cờ ban đầu cho phép đi nước sai luật** — hàm tên là "kiểm tra chiếu tướng" nhưng
   thân hàm chỉ kiểm tra lộ mặt tướng. AI có thể đi nước tự sát mà không ai biết.
2. **Model ID hardcode đã chết** — `gemini-1.5-flash` không còn tồn tại trên API.
3. **Bàn cờ vẽ sai hình học từ đầu** — quân bên phải nằm ngoài mặt bàn, không ai để ý cho tới
   khi chụp màn hình.
4. **Bài học:** AI viết code rất nhanh, nhưng **thứ giữ cho nó đúng là bài test và việc kiểm
   chứng bằng dữ liệu thật**, không phải tin lời nó.

### Vì sao video này đáng làm

Đa số video "AI viết code hộ tôi" chỉ khoe kết quả. Video này cho thấy **quy trình kiểm
chứng** — đúng thứ khán giả làm nghề cần. Và bạn có bằng chứng: 142 test, mỗi lỗi đều có
test canh giữ.

---

## Shorts (30–60 giây)

Nguyên liệu có sẵn, cắt từ trận đã lưu:

| Chủ đề | Nội dung |
|---|---|
| **AI gọi sai tên quân của mình** | Cận cảnh dòng "Mã e0-e1" trong khi đó là Tướng |
| **Khoảnh khắc blunder** | Eval bar đảo chiều + badge 🔴 BLUNDER + số điểm mất |
| **Hai AI cùng nghĩ một nước** | Chia đôi màn hình, cả hai chọn Pháo đầu |
| **AI trash-talk** | Ghép các câu thoại hay nhất, có TTS đọc |
| **Engine hạ AI trong 16 nước** | Tua siêu nhanh cả ván, kết ở chiếu bí |
| **Giá của một ván cờ AI** | Bộ đếm chi phí chạy từ $0 tới $0.28 |

Shorts nên đăng **giữa các video dài**, cắt từ chính trận đã dùng — không tốn thêm chi phí
vì xem lại đọc từ cơ sở dữ liệu.

---

## Quy trình sản xuất

### Trước khi quay

```bash
# 1. Chạy trận (qua đêm nếu muốn nhiều trận)
scripts/run_matches.py --round-robin claude-haiku-4-5,gemini-3.6-flash \
    --max-moves 140 --max-cost-usd 3.00

# 2. Xem trận nào đáng làm video
scripts/build_match_report.py --list

# 3. Lấy khung script: top blunder, điểm xoay chuyển, gợi ý tiêu đề
scripts/build_match_report.py <match_id> -o plans/reports/tran-abc.md
```

### Khi quay

- **Quay trực tiếp:** đặt Nghỉ giữa nước = `3s` để kịp đọc badge và lời thoại
- **Quay lại từ trận cũ:** bấm 📼 Xem Lại — **không tốn tiền API**, quay bao nhiêu lần cũng được
- **Overlay OBS:** `http://localhost:5000/?overlay=1&transparent=1`, điều khiển từ tab khác
  để tay không lọt khung hình
- **Nút 🔴 Nước tệ nhất** nhảy thẳng tới khoảnh khắc kịch tính nhất

### Thứ tự đăng đề xuất

1. Video 1 (mở màn) → định hình format
2. Shorts từ chính trận đó
3. Video 2 (đấu engine) → kịch tính, rẻ
4. Video 5 (meta) → chiều sâu, hợp định vị kênh
5. Video 3 (thách đấu) → cá nhân hoá
6. Video 4 (bảng xếp hạng) → định kỳ hàng tháng

---

## Nguyên tắc giữ uy tín

Điểm mạnh lớn nhất của kênh sẽ là **mọi con số đều kiểm chứng được**. Cần giữ:

- **Công bố luật thi đấu** trong video đầu và mô tả — xem
  [docs/project-overview-pdr.md](../../docs/project-overview-pdr.md) mục 3
- **Nói rõ đổi màu** khi so sánh hai AI (Đỏ đi trước có lợi)
- **Nói rõ phân khúc giá** — Haiku $1/$5 vs Opus $5/$25 là hai hạng khác nhau, so sánh
  chúng với nhau là không công bằng
- **Không giấu khi AI làm tốt** — nếu AI đi 0 nước sai luật thì nói thẳng, đừng chỉ khai
  thác lỗi
- **Nói rõ nếu dùng gợi ý** ở chế độ Người vs AI

---

## Việc cần làm trước khi sản xuất

1. **Chạy giải vòng tròn** để có bảng Elo dùng được cho Video 4
2. **Thêm key OpenAI / Grok / DeepSeek** — có 5 kỳ thủ thì nội dung phong phú hơn hẳn
   (hiện code đã sẵn nhưng chưa kiểm chứng)
3. **Cân nhắc nâng TTS** — giọng Web Speech vi-VN hiện tại nghe máy móc, ảnh hưởng chất
   lượng video

## Câu hỏi chưa rõ

1. Kênh nhắm khán giả phổ thông hay dân kỹ thuật? Video 5 (meta) hợp dân kỹ thuật, Video 3
   (thách đấu) hợp phổ thông — thứ tự đăng nên đổi theo.
2. Độ dài video mục tiêu là bao nhiêu? Các kịch bản trên đang giả định 8–15 phút.
3. Có định làm bản tiếng Anh không? Ký hiệu cờ tướng và lời thoại AI hiện đều tiếng Việt;
   nếu cần thì phải chỉnh prompt.
