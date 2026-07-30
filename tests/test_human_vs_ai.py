"""
Test chế độ Người vs AI.

Trọng tâm: trọng tài phải DỪNG chờ người, không được tự đi thay; và nước của người được
xác thực bằng đúng bộ luật dùng cho AI.
"""

from engine.providers import create_provider
from engine.referee import MatchReferee


def _human_vs_mock():
    return MatchReferee(
        {"model_key": "human", "name": "Tôi"},
        {"model_key": "mock", "name": "AI Đen"},
        analysis_engine=None,
    )


def test_human_provider_is_flagged():
    provider, note = create_provider("human")
    assert provider.is_human is True
    assert note is None

    ai_provider, _ = create_provider("mock")
    assert ai_provider.is_human is False


def test_human_provider_never_invents_a_move():
    """Nếu có chỗ nào gọi nhầm decide() thì phải báo lỗi rõ, không đi bừa một nước."""
    provider, _ = create_provider("human")
    decision = provider.decide("prompt", ["h2e2", "b2e2"])

    assert decision.move_ucci == ""
    assert "không tự sinh nước đi" in decision.error


def test_step_waits_instead_of_moving_for_human():
    referee = _human_vs_mock()
    state = referee.step()

    assert state["waiting_for_human"] is True
    assert state["is_human_turn"] is True
    assert state["history_count"] == 0, "trọng tài không được đi thay người chơi"
    # Gọi thêm lần nữa vẫn không đi
    assert referee.step()["history_count"] == 0


def test_state_exposes_legal_moves_only_on_human_turn():
    """
    Giao diện highlight ô đi được bằng danh sách này. Chỉ gửi khi tới lượt người để không
    phải nhân bản luật cờ sang JavaScript (hai nguồn sự thật sẽ lệch nhau).
    """
    referee = _human_vs_mock()
    state = referee.step()
    assert len(state["legal_moves"]) == 44   # thế khai cuộc
    assert "h2e2" in state["legal_moves"]

    referee.submit_human_move("h2e2")
    assert referee.get_state()["legal_moves"] == [], "lượt AI thì không gửi danh sách"


def test_human_move_is_applied_and_scored_like_ai():
    referee = _human_vs_mock()
    referee.step()
    success, message = referee.submit_human_move("h2e2")

    assert success is True
    assert message == "Pháo 2 bình 5"
    assert referee.stats['w']["moves"] == 1
    assert referee.last_move["ucci"] == "h2e2"
    assert referee.last_move["used_hint"] is False
    assert referee.get_state()["waiting_for_human"] is False


def test_illegal_human_move_is_rejected_with_vietnamese_reason():
    referee = _human_vs_mock()
    referee.step()
    success, message = referee.submit_human_move("a0a9")

    assert success is False
    assert "không thể đi" in message
    assert referee.stats['w']["moves"] == 0, "nước sai không được ghi vào lịch sử"


def test_move_out_of_turn_is_rejected():
    referee = _human_vs_mock()
    referee.step()
    referee.submit_human_move("h2e2")   # xong lượt người, giờ tới AI

    success, message = referee.submit_human_move("b2e2")
    assert success is False
    assert "Chưa tới lượt bạn" in message


def test_move_after_game_over_is_rejected():
    referee = _human_vs_mock()
    referee.game_over = True
    success, message = referee.submit_human_move("h2e2")

    assert success is False
    assert "kết thúc" in message


def test_ai_side_still_moves_automatically():
    """Chỉ bên người mới dừng; bên AI vẫn tự đi khi gọi step()."""
    referee = _human_vs_mock()
    referee.step()
    referee.submit_human_move("h2e2")

    state = referee.step()
    assert state["history_count"] == 2
    assert state["is_human_turn"] is True, "tới lượt người thì lại chờ"
    assert state["waiting_for_human"] is True


def test_hint_marks_the_turn_and_clears_after_move():
    """
    Nước dùng gợi ý phải được đánh dấu, nếu không độ chính xác của người sẽ bị thổi phồng
    và mất ý nghĩa khi so với AI.
    """
    referee = _human_vs_mock()
    referee.step()
    referee.hint_used_this_turn = True      # mô phỏng đã bấm gợi ý

    referee.submit_human_move("h2e2")
    assert referee.last_move["used_hint"] is True
    assert referee.hint_used_this_turn is False, "cờ phải được xoá cho lượt sau"

    referee.step()
    referee.submit_human_move("b2e2")
    assert referee.last_move["used_hint"] is False


def test_hint_without_engine_returns_reason():
    referee = _human_vs_mock()   # analysis_engine=None
    referee.step()
    bestmove, note = referee.request_hint()

    assert bestmove is None
    assert "engine" in note.lower()
    assert referee.hint_used_this_turn is False, "không có gợi ý thì không được đánh dấu"


def test_ai_vs_ai_match_is_unaffected():
    """Chế độ AI vs AI phải giữ nguyên hành vi cũ."""
    referee = MatchReferee({"model_key": "mock"}, {"model_key": "mock"}, analysis_engine=None)
    state = referee.step()

    assert state["is_human_turn"] is False
    assert state["waiting_for_human"] is False
    assert state["legal_moves"] == []
    assert state["history_count"] == 1
