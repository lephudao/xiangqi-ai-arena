"""
Cầu nối cho trình duyệt: bọc MatchReferee thành API phẳng mà JavaScript gọi được.

Vì sao cần lớp này: trọng tài phơi ra `step_iter()` dạng generator, mà lái generator Python
từ JS thì phải bắt `StopIteration` qua ranh giới hai ngôn ngữ — rất dễ sai và khó gỡ. Ở đây
generator được giữ nguyên phía Python, JS chỉ gọi hai hàm phẳng: `begin_turn()` rồi
`submit_decision()`.

Lớp này là GLUE, không chứa luật cờ. Mọi quyết định về luật vẫn nằm trong `referee.py` và
`xiangqi/` — chạy y hệt nhau ở máy chủ lẫn trình duyệt.
"""

from engine.providers import MoveDecision
from engine.referee import MatchReferee


class BrowserArena:
    """Một trận đấu chạy hoàn toàn trong trình duyệt."""

    def __init__(self, red_config=None, black_config=None):
        # analysis_engine=None: Pikafish cần subprocess nên không tồn tại trong trình duyệt.
        # Trận vẫn chạy đủ, chỉ không có chấm điểm — đúng thiết kế của bản online.
        self.referee = MatchReferee(red_config, black_config, analysis_engine=None)
        self._turn = None

    def new_match(self, red_config=None, black_config=None):
        self.referee.reset(red_config, black_config)
        self._turn = None
        return self.get_state()

    def get_state(self):
        return self.referee.get_state()

    # --- Một lượt của AI, chia làm hai lời gọi ---

    def begin_turn(self):
        """
        Bắt đầu một lượt. Trả về yêu cầu nước đi để JS đi gọi API, hoặc None khi không cần
        hỏi AI (trận đã kết thúc, hoặc đang tới lượt người chơi).

        Trả None thì JS phải đọc lại `get_state()` — trạng thái có thể đã đổi vì trọng tài
        vừa kết luận trận.
        """
        self._turn = self.referee.step_iter()
        return self._resume(None)

    def submit_decision(self, payload):
        """
        Nộp kết quả gọi API. Trả về yêu cầu tiếp theo nếu trọng tài bắt đi lại (nước sai
        luật), hoặc None khi lượt đã xong.
        """
        if self._turn is None:
            raise RuntimeError("submit_decision phải gọi sau begin_turn")
        return self._resume(decision_from_payload(payload))

    def _resume(self, decision):
        try:
            return self._turn.send(decision)
        except StopIteration:
            self._turn = None
            return None

    # --- Kỳ thủ người ---

    def submit_human_move(self, ucci):
        """Trả (thành công, thông báo) — thông báo là lý do từ chối khi đi sai luật."""
        ok, message = self.referee.submit_human_move(ucci)
        return {"ok": ok, "message": message}

    def legal_moves_from(self, square):
        """
        Các nước hợp lệ xuất phát từ một ô, để giao diện chấm gợi ý khi người chơi bấm quân.

        Danh sách lấy từ chính bộ luật của trọng tài, không nhân bản sang JS.
        """
        side = self.referee.board.turn
        return [m for m in self.referee.board.generate_legal_moves(side) if m.startswith(square)]


def decision_from_payload(payload):
    """
    Dựng MoveDecision từ object JS.

    Nhận cả dict Python lẫn JsProxy: JS gửi object thường, Pyodide chuyển thành JsProxy có
    `.to_py()`. Không ép JS phải tự chuyển đổi vì đó là chỗ rất dễ quên.
    """
    if payload is None:
        raise TypeError("submit_decision cần một object quyết định, nhận được None")
    if hasattr(payload, "to_py"):
        payload = payload.to_py()

    known = {f for f in MoveDecision.__dataclass_fields__ if f != "attempts"}
    unknown = set(payload) - known
    if unknown:
        # Sai chính tả tên trường ở phía JS sẽ âm thầm bị bỏ qua và biến thành "AI im lặng".
        raise TypeError(f"Trường không hợp lệ trong quyết định: {sorted(unknown)}")

    return MoveDecision(**{k: v for k, v in payload.items() if k in known})
