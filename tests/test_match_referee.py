"""
Test trọng tài & vòng đời trận đấu, bao gồm smoke test một trận đầy đủ.
"""

from engine.ai_agent import MoveDecision
from engine.referee import MatchReferee
from engine.xiangqi import STATUS_DRAW, STATUS_ONGOING


def _mock_referee():
    return MatchReferee(
        {"name": "AI Đỏ", "provider": "mock", "model": "mock"},
        {"name": "AI Đen", "provider": "mock", "model": "mock"},
    )


def test_full_mock_match_terminates_legally():
    """
    Smoke test: chạy trận mock tới khi kết thúc. Mọi nước phải hợp lệ và trạng thái
    kết thúc phải là một trong các kết cục đúng luật.
    """
    referee = _mock_referee()
    max_plies = 600
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
    referee = _mock_referee()
    for _ in range(600):
        state = referee.step()
        if state["game_over"]:
            break
    assert referee.result_reason != "king_captured"


def test_illegal_ai_move_is_counted_and_retried(monkeypatch):
    """Nước sai luật phải được ĐẾM và cho đi lại kèm lý do, không bị âm thầm thay thế."""
    referee = _mock_referee()
    call_log = []

    def fake_get_move(fen, legal_moves, side_name, side_code, feedback=None, in_check=False):
        call_log.append(feedback)
        if len(call_log) == 1:
            return MoveDecision(move_ucci="a0a9", reasoning="nước sai luật")  # Xe xuyên quân
        return MoveDecision(move_ucci=legal_moves[0], reasoning="đi lại đúng luật")

    monkeypatch.setattr(referee.red_agent, "get_move", fake_get_move)
    referee.step()

    assert referee.stats['w']["illegal_attempts"] == 1
    assert len(call_log) == 2
    assert call_log[1] is not None, "lần thử thứ 2 phải nhận được lý do bị từ chối"
    assert referee.last_move["referee_override"] is None
    assert referee.last_move["attempts"] == ["a0a9", referee.last_move["ucci"]]


def test_referee_picks_move_when_ai_keeps_failing(monkeypatch):
    referee = _mock_referee()

    def always_illegal(fen, legal_moves, side_name, side_code, feedback=None, in_check=False):
        return MoveDecision(move_ucci="zzzz", reasoning="cố tình sai")

    monkeypatch.setattr(referee.red_agent, "get_move", always_illegal)
    referee.step()

    assert referee.stats['w']["illegal_attempts"] == 3
    assert referee.last_move["referee_override"] is not None
    assert referee.last_move["ucci"] == "a3a4"  # nước hợp lệ đầu tiên trong danh sách


def test_api_error_is_recorded_not_hidden(monkeypatch):
    referee = _mock_referee()

    def failing_call(fen, legal_moves, side_name, side_code, feedback=None, in_check=False):
        return MoveDecision(error="TimeoutError: mạng lỗi")

    monkeypatch.setattr(referee.red_agent, "get_move", failing_call)
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
