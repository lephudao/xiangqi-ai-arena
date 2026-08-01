"""
Cầu nối cho trình duyệt: bọc MatchReferee thành API phẳng mà JavaScript gọi được.

Vì sao cần lớp này: trọng tài phơi ra `step_iter()` dạng generator, mà lái generator Python
từ JS thì phải bắt `StopIteration` qua ranh giới hai ngôn ngữ — rất dễ sai và khó gỡ. Ở đây
generator được giữ nguyên phía Python, JS chỉ gọi hai hàm phẳng: `begin_turn()` rồi
`submit_decision()`.

Lớp này là GLUE, không chứa luật cờ. Mọi quyết định về luật vẫn nằm trong `referee.py` và
`xiangqi/` — chạy y hệt nhau ở máy chủ lẫn trình duyệt.
"""

from engine.model_registry import ALL_MODELS, estimate_cost_usd
from engine.providers import MoveDecision
from engine.providers.base_provider import MOVE_SCHEMA
from engine.referee import MatchReferee

# Pikafish chạy bằng tiến trình con nên không có trong bản trình duyệt. Để lọt vào danh sách
# kỳ thủ thì người dùng chọn xong sẽ gặp ImportError giữa trận.
BROWSER_UNAVAILABLE_PROVIDERS = {"pikafish"}


class BrowserArena:
    """Một trận đấu chạy hoàn toàn trong trình duyệt."""

    def __init__(self, red_config=None, black_config=None):
        # analysis_engine=None: Pikafish cần subprocess nên không tồn tại trong trình duyệt.
        # Trận vẫn chạy đủ, chỉ không có chấm điểm — đúng thiết kế của bản online.
        #
        # external_providers=True: trình duyệt tự gọi API bằng key của người dùng. Key không
        # bao giờ đi vào Python, và Python không bao giờ mở kết nối mạng.
        self.referee = MatchReferee(red_config, black_config, analysis_engine=None,
                                    external_providers=True)
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


def describe_models():
    """
    Danh mục kỳ thủ cho phía JS: đủ để dựng request API, không phải chép bảng nào sang JS.

    Model ID, base URL và cờ năng lực (`supports_effort`, `supports_adaptive_thinking`) đều
    lấy từ `model_registry`. Chép sang JS thì hai bảng sẽ lệch nhau, và biểu hiện ra ngoài là
    lỗi HTTP 400 khó hiểu — ví dụ gửi `effort` cho Haiku 4.5, model không nhận tham số đó.

    Kèm luôn `MOVE_SCHEMA` để mọi nhà cung cấp bị ràng buộc cùng một định dạng phản hồi.
    """
    return {
        "move_schema": MOVE_SCHEMA,
        "models": [
            {
                "key": model.key,
                "label": model.label,
                "provider": model.provider,
                "model_id": model.model_id,
                "base_url": model.base_url,
                "api_key_env": model.api_key_env,
                "verified": model.verified,
                "has_pricing": model.input_price is not None,
                "note": model.note,
                "supports_effort": model.supports_effort,
                "supports_adaptive_thinking": model.supports_adaptive_thinking,
                "needs_api_key": model.api_key_env is not None,
                "available": (model.provider not in BROWSER_UNAVAILABLE_PROVIDERS
                              and model.browser_cors),
            }
            for model in ALL_MODELS
        ],
    }


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

    decision = MoveDecision(**{k: v for k, v in payload.items() if k in known})

    # Tiền do Python tính, JS chỉ báo số token. Chép bảng giá sang JS là cách chắc chắn để
    # bộ đếm chi phí lệch với hoá đơn thật khi giá thay đổi.
    if decision.cost_usd is None and decision.model_key:
        decision.cost_usd = estimate_cost_usd(
            decision.model_key, decision.tokens_in, decision.tokens_out
        )
    return decision
