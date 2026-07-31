# Phase 6.4 — Hai chế độ, lưu trữ, triển khai

**Status:** pending | **Est:** ~0,5–1 ngày | **Phụ thuộc:** 6.3

## Mục tiêu

Cùng một trang web tự nhận biết đang chạy ở đâu, và **bản local lấy lại được Pikafish thật**.

## Nhận biết chế độ

Khi nạp xong, trình duyệt thử gọi `GET /api/capabilities`:

- **Có trả lời** → chế độ **Local**: bật chấm điểm Pikafish, lưu SQLite, xem lại, Elo, overlay OBS
- **404 / lỗi mạng** → chế độ **Online**: Pyodide lo tất cả, lưu IndexedDB, không chấm điểm

Không dùng biến build hay hai file HTML. Một bản mã, tự dò — sửa một chỗ là cả hai chế độ
cùng được sửa.

Hiện huy hiệu rõ ràng trên giao diện (`🔬 Local — có Pikafish` / `🌐 Online — không chấm điểm`)
để lúc quay video không nhầm mình đang ở chế độ nào.

## Máy chủ local co lại thành dịch vụ phụ trợ

Trình duyệt giờ tự lo trọng tài và gọi AI. Máy chủ local chỉ còn phục vụ những thứ **không thể**
chạy trong trình duyệt:

| Route | Việc |
|---|---|
| `GET /api/capabilities` | báo có Pikafish không, có cơ sở dữ liệu không |
| `POST /api/analysis` | chấm một thế cờ bằng Pikafish → `{cp, bestmove, pv, depth}` |
| `POST /api/matches/{id}/moves` | ghi nước đi vào SQLite |
| `POST /api/matches/{id}/finish` | chốt kết quả, cập nhật Elo |
| `GET /api/replays`, `/api/leaderboard` | đọc lại |

**Các route cũ giữ nguyên, không xoá.** `scripts/run_matches.py` và luồng CLI vẫn dùng chúng,
và 151 test đang phủ chúng. Đây là bổ sung, không phải thay thế.

**Máy chủ không bao giờ nhận API key nữa** — kể cả ở chế độ local. Bỏ hẳn đường nhận key
trong `/api/reset`.

## Lưu trữ bản online: IndexedDB

Cùng hình dạng dữ liệu với SQLite (`fen_after` mỗi nước để xem lại không tốn tiền API).
Elo tính bằng `engine/storage/elo_rating.py` chạy trong Pyodide — **cùng công thức, cùng K=32**.

Elo bản online nằm trong máy người dùng, **không trộn** vào bảng xếp hạng của bạn. Đây chính
là điều lo trong phase 5.2 cũ, giờ tự khắc hết vì không có cơ sở dữ liệu chung.

## Triển khai

```
.github/workflows/deploy-pages.yml   # build bundle -> đẩy web/ lên GitHub Pages
```

Chạy `scripts/build-web-bundle.sh` rồi publish `web/`. Không Docker, không máy chủ, không tốn
tiền. Cần HTTPS để gọi API — GitHub Pages có sẵn.

## Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Bản local đang chạy tốt bị hỏng | Route cũ giữ nguyên; 151 test là lưới an toàn; chuyển giao diện sang đường mới **sau khi** đường mới chạy được |
| Người dùng tưởng bản online có chấm điểm | Huy hiệu chế độ rõ ràng + ẩn hẳn thanh eval khi online |
| IndexedDB đầy | Giới hạn số trận lưu, xoá trận cũ nhất |
| Elo online vô nghĩa vì mỗi người một bảng | Nói rõ trong giao diện: "bảng xếp hạng này chỉ tính các trận trên máy bạn" |
| Bundle cũ lên Pages | Workflow luôn build lại từ nguồn, không commit bundle |

## Tests

| Test | Nội dung |
|---|---|
| có sẵn | 151 test phải xanh |
| `tests/test_capabilities_endpoint.py` | Báo đúng có/không Pikafish; **không lộ key nào** |
| Thủ công | Chạy `./run.sh` → huy hiệu Local, có chấm điểm, Elo vào SQLite |
| Thủ công | Mở bản Pages → huy hiệu Online, không có thanh eval, Elo vào IndexedDB |
| Thủ công | Cùng một trận Mock, thế cờ cuối trùng nhau giữa hai chế độ |

## Acceptance criteria

- [ ] Một bản mã, tự nhận biết chế độ, không có hai file HTML
- [ ] Chế độ local: Pikafish chấm điểm thật, SQLite, Elo, overlay OBS — **đủ như hiện nay**
- [ ] Chế độ online: chạy trên GitHub Pages, không máy chủ, không tốn tiền
- [ ] Máy chủ không nhận API key ở bất kỳ chế độ nào
- [ ] Huy hiệu chế độ hiện rõ trên giao diện
- [ ] 151 test cũ vẫn xanh
