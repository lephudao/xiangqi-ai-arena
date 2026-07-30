"""
Test trọng tài & vòng đời trận đấu, bao gồm smoke test một trận đầy đủ.
"""

import random

from engine.providers import MoveDecision
from engine.referee import MatchReferee
from engine.xiangqi import STATUS_DRAW, STATUS_ONGOING


def _mock_referee():
    """Trọng tài dùng mock AI và TẮT chấm điểm engine để test chạy nhanh."""
    return MatchReferee(
        {"name": "AI Đỏ", "model_key": "mock"},
        {"name": "AI Đen", "model_key": "mock"},
        analysis_engine=None,
    )


def test_full_mock_match_terminates_legally():
    """
    Smoke test: chạy trận mock tới khi kết thúc. Mọi nước phải hợp lệ và trạng thái
    kết thúc phải là một trong các kết cục đúng luật.
    """
    # Seed cố định để test không phụ thuộc may mắn: mock đi ngẫu nhiên nên độ dài trận
    # dao động lớn (đã quan sát 214-589 nước qua 20 trận).
    random.seed(20260730)
    referee = _mock_referee()
    max_plies = 2000
    for _ in range(max_plies):
        state = referee.step()
        if state["game_over"]:
            break

    assert referee.game_over, "trận mock phải kết thúc trong giới hạn nước đi"
    assert referee.result_reason in (
        "checkmate", "stalemate", "king_captured",
        "draw_60_moves", "draw_repetition", "draw_perpetual_check",
    )
    # Mock luôn chọn từ danh sách hợp lệ nên không được có nước sai luật nào
    assert referee.stats['w']["illegal_attempts"] == 0
    assert referee.stats['b']["illegal_attempts"] == 0
    # Không được có trường hợp trọng tài phải chọn thay
    assert all(move["referee_override"] is None for move in referee.move_logs)


def test_kings_are_never_captured_in_mock_match():
    """Sau khi sửa lọc nước đi, tướng không bao giờ bị ăn (chỉ có thể bị chiếu bí)."""
    random.seed(11)
    referee = _mock_referee()
    for _ in range(2000):
        state = referee.step()
        if state["game_over"]:
            break
    assert referee.result_reason != "king_captured"


def test_illegal_ai_move_is_counted_and_retried(monkeypatch):
    """Nước sai luật phải được ĐẾM và cho đi lại kèm lý do, không bị âm thầm thay thế."""
    referee = _mock_referee()
    call_log = []

    def fake_decide(prompt, legal_moves, board=None, side=None):
        # Prompt lần 2 phải chứa lý do bị từ chối -> kiểm tra qua nội dung prompt
        call_log.append(prompt)
        if len(call_log) == 1:
            return MoveDecision(move_ucci="a0a9", taunt="nước sai luật")  # Xe xuyên quân
        return MoveDecision(move_ucci=legal_moves[0], taunt="đi lại đúng luật")

    monkeypatch.setattr(referee.red_agent, "decide", fake_decide)
    referee.step()

    assert referee.stats['w']["illegal_attempts"] == 1
    assert len(call_log) == 2
    assert "BỊ TRỌNG TÀI TỪ CHỐI" in call_log[1], "prompt lần 2 phải kèm lý do bị từ chối"
    assert referee.last_move["referee_override"] is None
    assert referee.last_move["attempts"] == ["a0a9", referee.last_move["ucci"]]


def test_referee_picks_move_when_ai_keeps_failing(monkeypatch):
    referee = _mock_referee()

    def always_illegal(prompt, legal_moves, board=None, side=None):
        return MoveDecision(move_ucci="zzzz", taunt="cố tình sai")

    monkeypatch.setattr(referee.red_agent, "decide", always_illegal)
    referee.step()

    assert referee.stats['w']["illegal_attempts"] == 3
    assert referee.last_move["referee_override"] is not None
    assert referee.last_move["ucci"] == "a3a4"  # nước hợp lệ đầu tiên trong danh sách


def test_api_error_is_recorded_not_hidden(monkeypatch):
    referee = _mock_referee()

    def failing_call(prompt, legal_moves, board=None, side=None):
        return MoveDecision(error="TimeoutError: mạng lỗi")

    monkeypatch.setattr(referee.red_agent, "decide", failing_call)
    referee.step()

    assert referee.stats['w']["api_errors"] == 1
    assert any("Lỗi gọi API" in line for line in referee.referee_log)
    assert referee.last_move["referee_override"] is not None


def test_state_exposes_check_flag_and_material():
    referee = _mock_referee()
    state = referee.get_state()
    assert state["in_check"] is False
    assert state["result_status"] == STATUS_ONGOING
    assert state["material"]["red"]["R"] == 2
    assert state["material"]["black"]["P"] == 5  # 5 Tốt Đen


def test_reset_clears_stats_and_history():
    referee = _mock_referee()
    referee.step()
    referee.step()
    referee.reset()
    assert referee.move_logs == []
    assert referee.stats['w']["moves"] == 0
    assert referee.result_status == STATUS_ONGOING
    assert referee.board.move_number == 1


def test_draw_match_has_no_winner():
    """Trận hoà: winner phải là None, không phải tên người chơi."""
    referee = _mock_referee()
    referee.board.load_fen("3k5/9/9/9/9/9/9/9/9/4K4 w - - 120 61")
    referee.step()
    assert referee.game_over
    assert referee.result_status == STATUS_DRAW
    assert referee.winner is None


def test_match_runs_without_analysis_engine():
    """Thiếu engine chấm điểm: trận vẫn chạy, chỉ không có dữ liệu chất lượng nước đi."""
    referee = _mock_referee()
    state = referee.step()
    assert state["analysis_enabled"] is False
    assert state["last_move"]["evaluation"] is None
    assert state["stats"]["red"]["accuracy"] is None
    assert state["eval_cp"] == 0


def test_evaluation_updates_stats_and_eval_bar():
    """Điểm chấm phải cộng vào thống kê và eval bar (eval bar luôn theo góc nhìn Đỏ)."""
    from engine.analysis import MoveEvaluation

    referee = _mock_referee()
    blunder = MoveEvaluation(cp_before=100, cp_after=-450, cp_loss=550, quality="blunder",
                             accuracy=5.0, engine_bestmove="h2e2")
    referee._record_evaluation('w', blunder)

    assert referee.stats['w']["blunders"] == 1
    assert referee.stats['w']["accuracy"] == 5.0
    assert referee.current_cp == -450, "Đỏ vừa đi nên cp_after đã theo góc nhìn Đỏ"

    # Cùng điểm đó nhưng do Đen đi -> eval bar phải đảo dấu về góc nhìn Đỏ
    referee.current_cp = 0
    referee._record_evaluation('b', blunder)
    assert referee.current_cp == 450
    assert referee.stats['b']["blunders"] == 1


def test_accuracy_is_average_over_scored_moves():
    from engine.analysis import MoveEvaluation

    referee = _mock_referee()
    for accuracy in (100.0, 50.0):
        referee._record_evaluation('w', MoveEvaluation(accuracy=accuracy, quality="good"))
    assert referee.stats['w']["accuracy"] == 75.0


def test_config_without_name_uses_model_label():
    """Client chỉ gửi model_key -> tên hiển thị tự lấy từ danh mục, không được KeyError."""
    from engine.referee import normalize_config

    config = normalize_config({"model_key": "claude-opus-5"}, "dự phòng")
    assert config["name"] == "Claude Opus 5"

    # model không có trong danh mục -> dùng tên dự phòng
    assert normalize_config({"model_key": "la-lung"}, "dự phòng")["name"] == "dự phòng"
    # config rỗng -> mặc định Mock
    assert normalize_config(None, "dự phòng")["model_key"] == "mock"


def test_referee_accepts_config_without_name():
    referee = MatchReferee({"model_key": "mock"}, {"model_key": "mock"}, analysis_engine=None)
    state = referee.step()
    assert state["red_config"]["name"]
    assert state["last_move"]["player"]
