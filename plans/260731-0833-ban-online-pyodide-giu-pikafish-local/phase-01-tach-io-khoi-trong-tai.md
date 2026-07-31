# Phase 6.1 — Tách phần gọi mạng khỏi trọng tài

**Status: XONG (2026-07-31)** — 156 test xanh (151 cũ + 5 mới). Xem "Kết quả" cuối file.

## Vấn đề

`MatchReferee` chạy được trong Pyodide **trừ một chỗ**: [referee.py:367](../../engine/referee.py#L367)

```python
decision = agent.decide(prompt, legal_moves, board=self.board, side=side)
```

Lời gọi này đồng bộ và đi ra mạng. Trong trình duyệt, mạng là **bất đồng bộ** — không thể gọi
kiểu này từ Python đồng bộ.

## Cách sai và vì sao

Cách hiển nhiên là tách thành hai lời gọi (`begin_turn()` → JS gọi AI → `submit_decision()`),
để JS lo vòng lặp đi lại. **Không làm thế.** Vòng lặp đi lại chứa: đếm số lần sai luật, dựng
lý do từ chối bằng tiếng Việt, ghi nhật ký trọng tài, đếm lỗi API. Viết lại đống đó trong JS
là nhân đôi đúng phần dễ lệch nhất, và số liệu "AI đi sai bao nhiêu lần" sẽ khác nhau giữa
hai chế độ — mà đó chính là thước đo cốt lõi của kênh.

## Cách làm: generator

Vòng lặp **ở nguyên trong Python**, chỉ nhả prompt ra ngoài rồi nhận quyết định vào:

```python
def step_iter(self):
    """
    Chạy một lượt dưới dạng generator: yield ra prompt, nhận vào MoveDecision.

    Cho phép bên gọi tự quyết cách lấy nước đi — đồng bộ (máy chủ) hay bất đồng bộ
    (trình duyệt) — mà toàn bộ luật đi lại, đếm vi phạm và ghi nhật ký vẫn nằm một chỗ.
    """
    for attempt_index in range(MAX_MOVE_ATTEMPTS):
        prompt = build_move_prompt(...)
        decision = yield prompt
        ...   # nguyên logic hiện có
```

`step()` giữ nguyên chữ ký cũ, chỉ đổi ruột thành "lái" generator bằng `agent.decide`:

```python
def step(self):
    gen = self.step_iter()
    prompt = next(gen)
    while True:
        decision = agent.decide(prompt, ...)
        prompt = gen.send(decision)   # StopIteration -> xong lượt
```

JS lái cùng generator đó qua Pyodide, chỉ khác là `await` lời gọi `fetch` giữa hai bước.

## Files sửa

- `engine/referee.py` — tách `_request_legal_move` thành `step_iter`; `step()` thành bộ lái
- `tests/test_referee.py` — bổ sung test lái generator thủ công

**Không sửa:** `server.py`, `web/`, provider — chữ ký `step()` không đổi.

## Ràng buộc

**151 test hiện có phải xanh nguyên.** Bản local là công cụ sản xuất video của người dùng;
phase này không được đổi hành vi của nó một ly. Nếu có test đỏ, dừng và sửa, không nới test.

## Tests

| Test | Nội dung |
|---|---|
| có sẵn | Toàn bộ 151 test phải xanh, không sửa test nào để cho qua |
| mới | Lái `step_iter` thủ công, nhét nước sai luật 2 lần rồi nước đúng → `illegal_attempts == 2`, nhật ký có đủ 2 dòng lý do |
| mới | Nhét nước sai cả 3 lần → trọng tài chọn thay, `referee_override` được ghi |
| mới | `step()` và lái `step_iter` thủ công cho **cùng kết quả** trên cùng hạt giống ngẫu nhiên |

Test cuối là quan trọng nhất: nó chính là bằng chứng hai chế độ không lệch nhau.

## Acceptance criteria

- [x] 151 test cũ xanh
- [x] `step_iter` lái được thủ công, vòng lặp đi lại vẫn trong Python
- [x] `step()` và `step_iter` cho kết quả giống hệt nhau
- [x] `referee.py` không còn lời gọi mạng đồng bộ nào ngoài bộ lái của `step()`

---

## Kết quả (2026-07-31)

### Đã làm

`engine/referee.py`:

- `_request_legal_move` → `_request_legal_move_iter`, generator yield ra
  `{"prompt", "legal_moves", "side", "attempt"}` và nhận `MoveDecision` qua `send()`.
  Yield dict thay vì chỉ prompt vì bên lái (JS ở phase 6.3) cần cả `legal_moves` và `side`.
- `step()` → `step_iter()` generator, cộng thêm `step()` mới làm bộ lái đồng bộ dùng
  `agent.decide`. Chữ ký `step()` không đổi, `server.py` và `web/` không phải sửa gì.
- Chặn `send(None)` bằng `TypeError` có thông điệp rõ. Bên lái sẽ là JS, để nó vỡ bằng
  `AttributeError` ở dòng sau thì rất khó lần ngược.

`tests/test_match_referee.py`: thêm 5 test, quan trọng nhất là
`test_step_iter_and_step_reach_identical_state` — cùng hạt giống ngẫu nhiên, lái tay và
`step()` phải cho **cùng thế cờ, cùng nhật ký trọng tài, cùng thống kê**. Đây là bằng chứng
hai chế độ không lệch nhau, và nó sẽ bắt được hồi quy ở các phase sau.

### Sửa thêm: một test vốn đã hỏng 10% số lần

`test_referee_records_result_and_elo_on_finish` đỏ khi chạy cả bộ. Không phải do refactor:
test này **không seed RNG** nên phụ thuộc trạng thái ngẫu nhiên các test trước để lại, rồi
trông chờ Mock đi ngẫu nhiên tự tìm ra chiếu bí trong 6 nước. Đo thật: **chỉ kết thúc 180/200
lần (90%)**. `random.seed(4242)` của test mới vô tình rơi vào 10% còn lại.

Sửa bằng cách bỏ hẳn yếu tố ngẫu nhiên: dựng thế chiếu bí cưỡng bức
(`4k4/8R/9/9/9/9/9/9/R8/3K5 w`) và ép Đỏ đi `a1a9`. Không đổi seed để né — đổi seed chỉ giấu
lỗi đi chờ ngày nó quay lại.

Lưu ý khi dựng thế test: hai xe cùng cột thì chặn nhau. Thế đầu tiên tôi thử
(`4k4/R8/…/R8/…`) làm `a1a9` thành nước không hợp lệ.

### Kiểm chứng

156 test xanh, chạy lại 3 lần đều ổn định.
