# Phase 6.4 — Hai chế độ, lưu trữ, triển khai

**Status: XONG (2026-08-01)** — 176 test xanh, kiểm chứng cả hai chế độ trong Chrome.
Xem "Kết quả".

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

- [x] Một bản mã, tự nhận biết chế độ, không có hai file HTML
- [x] Chế độ local: Pikafish chấm điểm thật, SQLite, Elo, gợi ý — **đủ như hiện nay**
- [x] Chế độ online: chạy hoàn toàn từ file tĩnh, không máy chủ
- [x] Huy hiệu chế độ hiện rõ trên giao diện
- [x] Test cũ vẫn xanh (176 test)
- [ ] Đã deploy lên GitHub Pages — **chưa**, repo còn riêng tư theo quyết định của bạn

---

## Kết quả (2026-08-01)

### Nhận biết chế độ

`GET /api/capabilities` → có trả lời thì Local, 404 thì Online. Không dùng biến build, không
có hai file HTML.

Kiểm chứng bằng cách chạy song song hai máy chủ trên cùng thư mục `web/`:

| | `:5000` (Flask) | `:5173` (`http.server`, chỉ file tĩnh) |
|---|---|---|
| Huy hiệu | `🔬 Local — có Pikafish` | `🌐 Online — không chấm điểm` |
| Danh sách trận đã lưu | hiện | ẩn |
| Nút 💡 Gợi Ý | hiện ở lượt người, trả `Pháo 2 bình 5` từ Pikafish | ẩn |
| Model chào mời | đủ 14 | 12 — bỏ Pikafish và ChatGPT |
| Console | sạch | sạch |

### `arena-client.js` — chỗ khiến app.js không cần biết mình ở đâu

Một giao diện, hai lớp cài đặt (`ServerArena` / `BrowserArena`). Thay 8 lời gọi `fetch('/api/…')`
trong `app.js` bằng `arena.xxx()`. Bản local giữ nguyên hành vi cũ từng dòng.

### Ba lỗi chỉ lộ ra khi chạy thật

**1. `score_from_result` nhận trạng thái kết quả, không phải bên thắng.** Truyền
`winner_side` ('w') thay vì `result_status` ('red_win') → hàm trả `None` → phép trừ trong
`update_ratings` vỡ **đúng lúc người dùng vừa đánh xong ván**. Không có test nào bắt được vì
đây là mã mới; giờ đã có.

**2. Mock vs Mock là cùng một dòng trong bảng xếp hạng.** Cùng `model_key` nên `red` và
`black` trỏ vào một dict — thắng và thua đè lên nhau, `matches` cộng hai lần. Và tự đấu với
chính mình vốn không nói lên điều gì về sức mạnh tương đối. Nay bỏ qua hẳn.

**3. Nút Gợi Ý bị điều khiển từ hai nơi.** `updateUI` đã ẩn/hiện nó theo lượt người chơi;
tôi thêm một dòng nữa trong `applyCapabilities` và hai dòng đánh nhau — kết quả là nút biến
mất cả ở bản local. Gộp lại một điều kiện duy nhất: `lượt người && có engine`.

### Bản online: ván Mock vs Mock qua đúng đường giao diện

82 nước → chiếu bí, **399 ms**. Elo ghi vào `localStorage`: Claude Haiku 4.5 lên 1516,
Gemini 3.6 Flash xuống 1484 (±16, đúng K=32). Tự đấu bị bỏ qua.

Bảng xếp hạng online **không trộn** với SQLite của bản local — số liệu dùng cho video chỉ đến
từ các trận bạn tự chạy.

### Files

| File | Việc |
|---|---|
| `web/js/arena-client.js` (mới) | Lớp trung gian, dò chế độ, hai lớp cài đặt |
| `web/js/browser-elo.js` (mới) | Bảng xếp hạng trong localStorage |
| `.github/workflows/deploy-pages.yml` (mới) | Build + test + đẩy lên Pages, **chạy tay** |
| `server.py` | `GET /api/capabilities` |
| `engine/browser_bridge.py` | `apply_elo`, `submit_local_decision`, cờ `external` trong yêu cầu |
| `web/app.js` | 8 lời gọi API → `arena.*`; huy hiệu chế độ; màn hình nạp |
| `web/index.html`, `web/style.css` | Huy hiệu chế độ, màn hình nạp có thanh tiến trình |

### Chưa làm

- **Chưa deploy** — repo còn riêng tư. Workflow để `workflow_dispatch` (chạy tay) chứ không
  tự chạy theo push: deploy là hành động công khai, phải do người quyết định.
- **Hộp thoại nhập key** vẫn là ô `api_key` cũ trong hộp Cấu Hình, chưa nối vào `key-vault`.
  Bản online hiện phải nhập key bằng console. Đây là việc còn lại lớn nhất.
