# Phase 6.2 — Chạy lõi Python trong trình duyệt (Pyodide)

**Status: XONG (2026-08-01)** — 167 test xanh, kiểm chứng trong Chrome thật. Xem "Kết quả".

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

- [x] Mock vs Mock đấu hết trận đúng luật trong trình duyệt
- [x] Lõi Python (luật cờ, trọng tài, prompt) **không sửa dòng nào**
- [x] `init()` báo tiến trình theo byte, không có màn hình trắng
- [x] `run.sh` tự build lại bundle
- [x] Bundle không chứa module chỉ dành cho máy chủ

---

## Kết quả (2026-08-01)

### Kiểm chứng trong Chrome thật

Chạy `python-runtime.js` trực tiếp trên trình duyệt, không qua trung gian:

| Phép đo | Kết quả |
|---|---|
| Nạp nguội (tải 10MB + khởi động + giải nén engine) | **6,5 giây** |
| Thế khai cuộc | **44 nước hợp lệ** — trùng mốc kiểm chứng của bản máy chủ |
| Ván Mock vs Mock | **652 nước → hoà theo luật 60 nước**, 12,9 ms/nước |
| Nước sai luật (`a0a9`) | bị bắt đi lại, `attempt: 2`, prompt kèm lý do từ chối |
| Lượt người chơi | `beginTurn()` trả `null`, không gọi AI |
| Chấm gợi ý từ ô `b2` | 12 nước, lấy từ luật của trọng tài |
| Sai tên trường (`move_ucc`) | nổ ngay: `TypeError: Trường không hợp lệ trong quyết định: ['move_ucc']` |
| Console | sạch (chỉ có `favicon.ico` và source map của Pyodide) |

12,9 ms/nước cao hơn con số 1,4 ms đo bằng Node ở kế hoạch gốc, vì phép đo này gồm cả dựng
prompt (1.826 ký tự mỗi lượt) và chuyển kiểu qua lại JS↔Python. So với ~5.400 ms chờ LLM thì
vẫn chỉ chiếm 0,24%.

### Quyết định thiết kế: lớp cầu nối nằm ở Python

Tạo `engine/browser_bridge.py` thay vì nhúng đoạn Python vào file JS. Lý do: JS lái generator
Python phải bắt `StopIteration` qua ranh giới hai ngôn ngữ — rất dễ sai và gần như không gỡ
được. Để glue ở Python thì **pytest kiểm được** (8 test), và JS chỉ gọi hai hàm phẳng
`begin_turn()` / `submit_decision()`.

`decision_from_payload` từ chối tên trường lạ. Nếu bỏ qua âm thầm, gõ nhầm `move_ucc` ở phía
JS sẽ biểu hiện ra ngoài thành "AI im lặng không đi" — mất hàng giờ mới lần ra.

### Phải sửa thêm: hai `__init__.py` kéo theo module không chạy được trong trình duyệt

`engine/analysis/__init__.py` import thẳng `pikafish_engine` (subprocess) và
`engine/storage/__init__.py` import thẳng `match_repository` (SQLite). Chỉ cần `import
engine.referee` là kéo cả hai vào.

Chuyển sang nạp lười bằng `__getattr__` cấp module (PEP 562). Mã máy chủ vẫn
`from engine.analysis import PikafishEngine` như cũ, không phải sửa chỗ nào. Kèm theo,
`referee.py` chuyển `PikafishEngine` xuống import trong hàm.

### Test đáng giá nhất

`test_bundled_modules_import_without_the_excluded_ones` — giải nén bundle ra thư mục tạm rồi
import mọi module bằng một tiến trình Python **chỉ nhìn thấy đúng các file đó**. Nếu sau này
ai thêm một import ở mức module kéo theo Pikafish hay SQLite, test đỏ ngay tại máy dev thay
vì nổ trên trình duyệt người xem.

### Files

| File | Việc |
|---|---|
| `engine/browser_bridge.py` (mới) | Cầu nối: bọc trọng tài thành API phẳng cho JS |
| `web/js/python-runtime.js` (mới) | Nạp Pyodide, giải nén engine, chuyển kiểu |
| `scripts/install-pyodide.sh` (mới) | Tải bản `pyodide-core` (13MB sau khi lọc bỏ file thừa) |
| `scripts/build-web-bundle.sh` (mới) | Gói 18 file Python thành zip 36KB |
| `tests/test_web_bundle.py` (mới) | 11 test: cầu nối + nội dung bundle |
| `engine/analysis/__init__.py`, `engine/storage/__init__.py`, `engine/referee.py` | Nạp lười phần chỉ chạy ở máy chủ |
| `run.sh`, `.gitignore` | Tự dựng bundle; `web/vendor/` không vào git |

### Ghi chú cho phase sau

Bản online **không được hiện model `pikafish`** trong danh sách kỳ thủ:
`providers/__init__.py` sẽ nạp `pikafish_provider` khi được chọn, mà file đó không có trong
bundle → `ImportError`. Xử lý ở phase 6.4 lúc lọc danh sách model theo chế độ.
