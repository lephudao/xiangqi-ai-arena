# Phase 6.1 — Tách phần gọi mạng khỏi trọng tài

**Status:** pending | **Est:** ~0,5 ngày | **Chặn:** 6.2, 6.3

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

- [ ] 151 test cũ xanh, không sửa test nào
- [ ] `step_iter` lái được thủ công, vòng lặp đi lại vẫn trong Python
- [ ] `step()` và `step_iter` cho kết quả giống hệt nhau
- [ ] `referee.py` không còn lời gọi mạng đồng bộ nào ngoài bộ lái của `step()`
