# Đại Chiến AI Cờ Tướng — Tổng quan & Yêu cầu sản phẩm

**Cập nhật:** 2026-07-30 · **Trạng thái:** Phase 1-4 hoàn tất

## 1. Vấn đề

Cho hai LLM đánh cờ với nhau là ý tưởng content hấp dẫn, nhưng bản thân việc "AI nào thắng
một ván" gần như không nói lên điều gì: một ván cờ có quá nhiều may rủi, và nếu bàn cờ chạy
sai luật thì kết quả hoàn toàn vô nghĩa.

Hệ thống này giải quyết ba câu hỏi:

1. **Trận đấu có đúng luật không?** — nếu engine cho phép nước sai luật thì mọi số liệu phía
   sau đều vô giá trị.
2. **Nước nào hay, nước nào dở?** — "Claude chính xác 91%, mắc 2 blunder" hấp dẫn và có sức
   thuyết phục hơn "Claude thắng" rất nhiều.
3. **Làm sao ra video đều đặn?** — một lần chạy phải dùng được cho nhiều video, không phải
   trả tiền API lại mỗi lần quay.

## 2. Người dùng và mục tiêu

| Đối tượng | Nhu cầu |
|---|---|
| Chủ kênh (người vận hành) | Chạy trận, quay màn hình, lấy số liệu viết script video |
| Người xem YouTube | Hiểu được ai đang thắng và tại sao, không cần biết chơi cờ |

Mục tiêu đo được:

- Không có nước đi sai luật nào lọt qua trọng tài
- Mỗi nước có điểm chất lượng khách quan (centipawn loss) do engine chấm
- Xem lại một trận không tốn thêm tiền API
- Chi phí một trận biết trước và chặn được

## 3. Luật thi đấu

Đây là phần quan trọng nhất về mặt uy tín: nếu luật thi đấu không công bằng thì mọi so sánh
giữa các AI đều vô nghĩa, và người xem có quyền nghi ngờ.

### 3.1. Trọng tài là bên duy nhất xác thực nước đi

Không provider nào được tự sửa nước đi sai của mình thành nước hợp lệ. Bản đầu tiên của hệ
thống có lỗi này: mỗi lời gọi API tự thay nước sai bằng một nước ngẫu nhiên hợp lệ trước khi
trả về, nên trọng tài không bao giờ nhìn thấy lỗi và dữ liệu "AI đi sai luật mấy lần" bị mất
hoàn toàn.

### 3.2. Đi sai luật được đi lại, và bị đếm

AI đi sai được cho chọn lại tối đa **3 lần**, mỗi lần kèm lý do cụ thể bằng tiếng Việt
("Pháo cần ngòi để ăn quân"). Mọi lần sai đều được đếm và hiển thị — đây là một thước đo sức
mạnh, không phải lỗi cần che giấu.

Chỉ khi AI không đưa được nước hợp lệ sau cả 3 lần, trọng tài mới chọn thay và ghi rõ vào
nhật ký.

### 3.3. Nước đi là chuỗi tự do, không phải danh sách chọn

Các API hiện đại cho phép ràng buộc đầu ra theo `enum`, tức là ép AI chỉ chọn được trong
danh sách nước hợp lệ. **Hệ thống cố ý KHÔNG dùng cách đó.** Nếu ép enum thì mọi AI đều đi
hợp lệ 100% và ta mất hoàn toàn tín hiệu "AI có thật sự đọc được bàn cờ không" — vốn là nội
dung hấp dẫn nhất.

JSON schema chỉ dùng để đảm bảo phản hồi parse được; trường `move_ucci` là chuỗi tự do.

### 3.4. Cùng một prompt cho mọi nhà cung cấp

Mọi provider nhận **chung một template prompt** (bàn cờ ASCII, lịch sử 10 nước, kiểm kê quân,
cảnh báo chiếu, danh sách nước hợp lệ). Chỉ khác cách gói request theo từng API. Prompt khác
nhau thì so sánh vô nghĩa.

### 3.5. Engine chấm điểm, không mách nước

Pikafish chỉ đánh giá thế cờ **sau khi AI đã tự quyết định**. Nó không gợi ý gì cho AI trong
lúc AI đang chọn nước.

Ngoại lệ có tuyên bố rõ: chế độ "Pikafish làm kỳ thủ" (đối thủ đối chuẩn) và nút "Gợi ý" ở
chế độ Người vs AI — nước dùng gợi ý bị đánh dấu `used_hint` để không thổi phồng độ chính xác.

### 3.6. Đổi màu khi so sánh

Bên Đỏ đi trước nên có lợi thế. Giải vòng tròn cho **mọi cặp đánh cả hai màu**; nếu mỗi cặp
chỉ đánh một lượt thì bảng xếp hạng phản ánh may mắn bốc màu chứ không phải sức mạnh.

### 3.7. Elo chỉ tính trận kết thúc đúng luật cờ

Trận dừng vì hết giới hạn nước hoặc hết ngân sách chi phí **không được tính vào Elo**, vì
không phản ánh sức mạnh.

## 4. Cách đo chất lượng nước đi

Dùng Pikafish (engine cờ tướng mã nguồn mở, GPL, chạy local, chi phí 0đ).

Mỗi nước được phân tích hai lần — thế trước và thế sau khi đi:

```
cp_loss = điểm_trước_khi_đi − điểm_sau_khi_đi   (cùng quy về góc nhìn người vừa đi)
```

| cp_loss | Nhãn |
|---|---|
| trùng nước engine khuyên | ⭐ NƯỚC HAY NHẤT |
| 0–30 | ✅ Tốt |
| 30–90 | 🟢 Khá |
| 90–200 | 🟡 Thiếu chính xác |
| 200–500 | 🟠 SAI NƯỚC |
| > 500 | 🔴 BLUNDER |

Độ chính xác quy đổi qua mô hình xác suất thắng, thang 0-100% quen thuộc với người xem.

**Điểm cần biết khi đọc số:** engine trả điểm theo góc nhìn *bên tới lượt*, nên so sánh hai
thế cờ liên tiếp bắt buộc phải đảo dấu. Đây là lỗi dễ mắc nhất và có test riêng canh giữ.

## 5. Số liệu thực đo (2026-07-30)

| Kỳ thủ | Độ chính xác | Nước sai luật |
|---|---|---|
| Claude Haiku 4.5 | 80–91% | 0 |
| Gemini 3.6 Flash | 83–89% | 0 |
| Pikafish (engine) | 100% | 0 |
| Mock (đi ngẫu nhiên) | ~50% | 0 |

Trong 240 lượt gọi API của hai LLM: **0 nước sai luật, 0 lỗi API**. Pikafish chiếu bí Claude
Haiku 4.5 sau 16 nước. Tổng chi phí đo đạc: $0.35.

Mốc so sánh quan trọng: mock đi ngẫu nhiên đạt ~50%, nên khoảng 80-91% của LLM là bằng chứng
chúng thực sự chơi cờ chứ không đoán bừa.

## 6. Chi phí

| Model | Giá vào /1M | Giá ra /1M | Chi phí mỗi nước (đo thật) |
|---|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 | ~$0.0027 |
| Claude Opus 5 | $5.00 | $25.00 | ~$0.019 |
| Gemini 3.6 Flash | $1.50 | $7.50 | ~$0.0026 |
| Gemini 3.1 Pro | $2.00 | $12.00 | ~$0.0039 |
| Pikafish, Mock, Người | — | — | $0 |

Trận 100 nước với cặp Haiku + Flash ≈ **$0.28**.

Hai lớp chặn chi phí: ô "Dừng khi tới $" trên giao diện, và `--max-cost-usd` cho chạy dòng lệnh.

Model chưa niêm yết giá chính thức để trống, hệ thống hiện dấu gạch thay vì bịa số.

## 7. Phạm vi hiện tại và giới hạn

**Có:**
- Luật cờ tướng đầy đủ (chân mã, mắt tượng, ngòi pháo, lộ mặt tướng, cấm tự chiếu)
- Kết cục: chiếu bí, hết nước (thua), hoà 60 nước, hoà lặp 3 lần
- Chấm điểm, xem lại, Elo, giải vòng tròn, overlay OBS, báo cáo trận, Người vs AI

**Chưa có / đơn giản hoá:**
- Luật phạt chiếu liên tục và vây bắt liên tục theo chuẩn Á Châu — hiện xử **hoà** kèm cờ
  cảnh báo `draw_perpetual_check`
- OpenAI, Grok, DeepSeek: code đã viết theo chuẩn nhưng **chưa kiểm chứng bằng key thật**;
  giao diện ghi rõ "(chưa kiểm chứng)"
- Chưa có xác thực người dùng — hệ thống chỉ chạy local, xem [deployment-guide.md](deployment-guide.md)

## 8. Tài liệu liên quan

- [system-architecture.md](system-architecture.md) — kiến trúc và các quyết định thiết kế
- [codebase-summary.md](codebase-summary.md) — bản đồ mã nguồn
- [deployment-guide.md](deployment-guide.md) — cài đặt, cấu hình, an toàn vận hành
- [../plans/260730-0811-xiangqi-ai-arena-upgrade/plan.md](../plans/260730-0811-xiangqi-ai-arena-upgrade/plan.md) — kế hoạch nâng cấp theo phase
