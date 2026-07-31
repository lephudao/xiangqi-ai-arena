# Phase 6.2 — Chạy lõi Python trong trình duyệt (Pyodide)

**Status:** pending | **Est:** ~0,75 ngày | **Phụ thuộc:** 6.1

## Mục tiêu

Nạp Pyodide, đưa `engine/` vào, chạy được luật cờ và trọng tài **trong trình duyệt** —
không sửa một dòng nào của lõi Python.

Cuối phase này: mở trang tĩnh, bấm "Trận Mới", hai bên Mock đấu tới hết trận, bàn cờ chạy
đúng. Chưa gọi API AI thật (đó là 6.3).

## Đóng gói engine

Pyodide không đọc được thư mục trên máy chủ. Phải gói `engine/` thành zip rồi nạp vào hệ
thống file ảo:

```
scripts/build-web-bundle.sh   # gói engine/ -> web/vendor/engine-core.zip
```

Chỉ gói phần chạy được trong trình duyệt. **Loại trừ** `analysis/pikafish_engine.py`
(subprocess), `storage/match_repository.py` (SQLite), `providers/*_provider.py` bản SDK —
gói vào cũng chỉ để vỡ lúc import.

Script này phải chạy lại mỗi khi sửa lõi Python. Thêm vào `run.sh` để bản local luôn có bundle
mới, tránh cảnh sửa Python xong bản online vẫn chạy code cũ.

## Files tạo

```
web/js/python-runtime.js     # nạp Pyodide, giải nén engine, khởi tạo trọng tài
web/vendor/                  # pyodide + engine-core.zip (gitignore file sinh ra)
scripts/build-web-bundle.sh
```

## Giao diện `python-runtime.js`

```
init(onProgress)             # nạp Pyodide + engine, báo tiến trình
newMatch(redConfig, blackConfig)
beginTurn()                  # -> {prompt, legalMoves, side} | null
submitDecision(decision)     # -> {done, retryPrompt} — lái generator của 6.1
getState()                   # -> state dict y hệt /api/state
submitHumanMove(ucci)
```

Chữ ký trả về **giống hệt** `/api/state` hiện tại. Đó là điều kiện để `web/app.js` không phải
biết mình đang chạy chế độ nào.

## Việc phải làm

1. **Nạp Pyodide** — tải từ CDN jsDelivr, hoặc tự host trong `web/vendor/` nếu muốn bản
   online không phụ thuộc CDN. Tự host an toàn hơn nhưng repo nặng thêm ~10MB.
2. **Giải nén engine** vào hệ thống file ảo bằng `pyodide.unpackArchive`.
3. **Màn hình nạp** — Pyodide mất vài giây lần đầu. Vẽ bàn cờ trước, hiện thanh tiến trình,
   **không** để trang trắng.
4. **Bọc generator** — `step_iter` của 6.1 giữ trong biến JS, `.send()` mỗi khi có quyết định.
5. **Chuyển đổi kiểu** — dict Python ↔ object JS. Dùng `.toJs({dict_converter: Object.fromEntries})`,
   đừng để lọt `Map` ra ngoài rồi `app.js` đọc `undefined`.

## Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Tải 10MB lần đầu, người dùng tưởng treo | Thanh tiến trình + bàn cờ vẽ sẵn + câu "lần đầu tải ~10MB, sau đó chạy ngay" |
| Bundle engine cũ so với code Python | `run.sh` build lại mỗi lần chạy; ghi số hiệu build vào console |
| `Map` lọt ra JS gây lỗi âm thầm | `dict_converter` ở mọi ranh giới; test một vòng chuyển đổi |
| CDN Pyodide chết | Tự host trong `web/vendor/` — quyết ở mục "Việc phải làm" #1 |

## Tests

| Test | Nội dung |
|---|---|
| Thủ công | Mở trang tĩnh (không chạy Flask), Mock vs Mock đấu tới hết trận |
| Thủ công | So thế cờ cuối của cùng một hạt giống giữa bản Pyodide và bản Flask — phải trùng |
| `tests/test_web_bundle.py` | Bundle chứa đủ module cần, **không** chứa `pikafish_engine.py` hay `match_repository.py` |

Không test tự động phần trình duyệt (cần Playwright, ngoài phạm vi). Kiểm thủ công rồi ghi
kết quả vào báo cáo.

## Acceptance criteria

- [ ] Mở file tĩnh, không có máy chủ nào, Mock vs Mock đấu hết trận đúng luật
- [ ] Lõi Python **không sửa dòng nào** để chạy được trong trình duyệt
- [ ] Có thanh tiến trình khi nạp, không có màn hình trắng
- [ ] `run.sh` tự build lại bundle
- [ ] Bundle không chứa module chỉ dành cho máy chủ
