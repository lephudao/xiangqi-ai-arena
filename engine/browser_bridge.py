"""
Cầu nối cho trình duyệt: bọc MatchReferee thành API phẳng mà JavaScript gọi được.

Vì sao cần lớp này: trọng tài phơi ra `step_iter()` dạng generator, mà lái generator Python
từ JS thì phải bắt `StopIteration` qua ranh giới hai ngôn ngữ — rất dễ sai và khó gỡ. Ở đây
generator được giữ nguyên phía Python, JS chỉ gọi hai hàm phẳng: `begin_turn()` rồi
`submit_decision()`.

Lớp này là GLUE, không chứa luật cờ. Mọi quyết định về luật vẫn nằm trong `referee.py` và
`xiangqi/` — chạy y hệt nhau ở máy chủ lẫn trình duyệt.
"""

from engine.model_registry import ALL_MODELS, TTS_MODELS, estimate_cost_usd, get_model
from engine.storage.elo_rating import STARTING_ELO, score_from_result, update_ratings
from engine.providers import MoveDecision
from engine.providers.base_provider import MOVE_SCHEMA
from engine.providers.external_provider import ExternalProvider
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
        self._request = None

    def new_match(self, red_config=None, black_config=None):
        self.referee.reset(red_config, black_config)
        self._turn = None
        self._request = None
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

    def submit_local_decision(self):
        """
        Để kỳ thủ chạy ngay trong Python tự quyết (Mock).

        Mock chọn ngẫu nhiên trong danh sách hợp lệ nên không cần gọi mạng. Để JS tự bốc
        nước thay Mock thì bản online và bản local sẽ cho kết quả khác nhau trên cùng thế
        cờ, và Mock thôi không còn là mốc sàn so sánh được nữa.
        """
        if self._turn is None or self._request is None:
            raise RuntimeError("submit_local_decision phải gọi sau begin_turn")
        agent = self.referee._agent(self._request["side"])
        decision = agent.decide(
            self._request["prompt"], self._request["legal_moves"],
            board=self.referee.board, side=self._request["side"],
        )
        return self._resume(decision)

    def _resume(self, decision):
        try:
            self._request = self._turn.send(decision)
        except StopIteration:
            self._turn = None
            self._request = None
            return None

        # `external` cho JS biết phải tự gọi API hay để Python quyết; `model_key` để JS chọn
        # đúng client mà không phải tra lại trạng thái. Tính ở đây chứ không ở trọng tài:
        # trọng tài không cần biết chuyện chạy trong trình duyệt.
        agent = self.referee._agent(self._request["side"])
        return {
            **self._request,
            "external": isinstance(agent, ExternalProvider),
            "model_key": agent.model_key,
        }

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


def apply_elo(board_rows, red_model_key, black_model_key, result_status):
    """
    Cập nhật bảng xếp hạng sau một trận, dùng cho bản online (lưu trong localStorage).

    Dùng CHUNG `engine/storage/elo_rating.py` với bản local — cùng K, cùng điểm khởi đầu.
    Viết lại công thức trong JS thì hai bảng xếp hạng sẽ trôi khỏi nhau và không so được.

    `board_rows`: danh sách dict đã lưu. `result_status`: 'red_win' | 'black_win' | 'draw'.
    Trả về danh sách mới, đã xếp theo Elo giảm dần. Trận chưa kết thúc đúng luật thì trả lại
    bảng cũ nguyên vẹn.
    """
    if hasattr(board_rows, "to_py"):
        board_rows = board_rows.to_py()

    rows = {row["model_key"]: dict(row) for row in (board_rows or [])}
    red_score = score_from_result(result_status, 'w')
    if red_score is None:
        return sorted(rows.values(), key=lambda row: row["elo"], reverse=True)

    # Một model tự đấu với chính nó không nói lên điều gì về sức mạnh tương đối, và cộng vào
    # thì hai bên là CÙNG một dòng trong bảng — thắng và thua đè lên nhau.
    if red_model_key == black_model_key:
        return sorted(rows.values(), key=lambda row: row["elo"], reverse=True)

    def entry(model_key):
        model = get_model(model_key)
        return rows.setdefault(model_key, {
            "model_key": model_key,
            "label": model.label if model else model_key,
            "elo": STARTING_ELO,
            "matches": 0, "wins": 0, "losses": 0, "draws": 0,
        })

    red, black = entry(red_model_key), entry(black_model_key)
    red["elo"], black["elo"] = update_ratings(red["elo"], black["elo"], red_score)

    for row in (red, black):
        row["matches"] += 1
    if result_status == "draw":
        red["draws"] += 1
        black["draws"] += 1
    else:
        winner, loser = (red, black) if result_status == "red_win" else (black, red)
        winner["wins"] += 1
        loser["losses"] += 1

    return sorted(rows.values(), key=lambda row: row["elo"], reverse=True)


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


def describe_tts_models():
    """
    Danh mục giọng đọc cho phía JS.

    Tách khỏi `describe_models()` vì đây không phải kỳ thủ — để lẫn vào thì người dùng sẽ
    thấy "Gemini TTS" trong danh sách chọn đối thủ đánh cờ.
    """
    return [
        {
            "key": model.key,
            "label": model.label,
            "model_id": model.model_id,
            "api_key_env": model.api_key_env,
            "note": model.note,
        }
        for model in TTS_MODELS
    ]


def tts_cost_usd(model_key, tokens_in, tokens_out):
    """Chi phí một lần đọc. Trả None nếu chưa có giá — giao diện hiện '—' thay vì số bịa."""
    return estimate_cost_usd(model_key, tokens_in, tokens_out)


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
