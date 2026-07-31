"""
Test kho lưu trận SQLite.

Trọng tâm: dữ liệu phải đủ để REPLAY không cần gọi lại API, và crash giữa trận không được
làm mất các nước đã ghi.
"""

import pytest

from engine.referee import MatchReferee
from engine.storage import MatchRepository, STARTING_ELO


@pytest.fixture
def repo(tmp_path):
    repository = MatchRepository(db_path=str(tmp_path / "test-arena.db"))
    yield repository
    repository.close()


def _move(ply, side='w', ucci="h2e2", quality="good", cp_loss=10, cost=0.001):
    return {
        "side": side,
        "ucci": ucci,
        "vi_text": "Pháo 2 bình 5",
        "reasoning": "Pháo về giữa!",
        "thinking": "Khống chế trung lộ",
        "attempts": [ucci],
        "referee_override": None,
        "latency_ms": 5400,
        "error": None,
        "tokens": {"in": 1400, "out": 200},
        "cost_usd": cost,
        "evaluation": {
            "cp_before": 20, "cp_after": 10, "cp_loss": cp_loss,
            "quality": quality, "quality_label": "✅ Tốt", "accuracy": 95.0,
            "engine_bestmove": "h2e2", "engine_pv": ["h2e2", "h9g7"], "depth": 15,
        },
    }


def _state(status="red_win", winner_side='w', plies=2):
    return {
        "result_status": status,
        "result_reason": "checkmate",
        "winner_side": winner_side,
        "history_count": plies,
    }


def _stats(red_cost=0.01, black_cost=0.02, cost_known=True):
    def side(cost):
        return {"accuracy": 91.5, "blunders": 1, "illegal_attempts": 0,
                "cost_usd": cost, "cost_known": cost_known}
    return {"red": side(red_cost), "black": side(black_cost)}


# --- Ghi và đọc ---

def test_match_round_trip_preserves_replay_data(repo):
    """Đọc lại phải đủ dữ liệu dựng thế cờ và hiện điểm chấm — không cần API."""
    match_id = repo.create_match(
        {"model_key": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "provider": "anthropic"},
        {"model_key": "gemini-3.6-flash", "name": "Gemini 3.6 Flash", "provider": "gemini"},
        initial_fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    )
    repo.append_move(match_id, 1, _move(1), fen_after="fen-sau-nuoc-1", in_check_after=False)
    repo.append_move(match_id, 2, _move(2, side='b'), fen_after="fen-sau-nuoc-2",
                     in_check_after=True)

    moves = repo.get_moves(match_id)
    assert [m["ply"] for m in moves] == [1, 2]
    assert moves[0]["fen_after"] == "fen-sau-nuoc-1", "thiếu FEN thì không replay được"
    assert moves[1]["in_check_after"] is True
    assert moves[0]["vi_notation"] == "Pháo 2 bình 5"
    assert moves[0]["cp_loss"] == 10
    assert moves[0]["engine_pv"] == ["h2e2", "h9g7"]
    assert moves[0]["attempts"] == ["h2e2"]
    assert moves[0]["taunt"] == "Pháo về giữa!"
    assert moves[0]["analysis"] == "Khống chế trung lộ"

    match = repo.get_match(match_id)
    assert match["red_name"] == "Claude Haiku 4.5"
    assert match["total_plies"] == 2
    assert match["status"] == "ongoing"


def test_moves_survive_without_finish_call(repo):
    """Mô phỏng crash giữa trận: chưa gọi finish_match nhưng các nước đã ghi vẫn còn."""
    match_id = repo.create_match({"model_key": "mock", "name": "A"},
                                 {"model_key": "mock", "name": "B"}, "fen-dau")
    for ply in range(1, 6):
        repo.append_move(match_id, ply, _move(ply), fen_after=f"fen-{ply}")

    assert len(repo.get_moves(match_id)) == 5
    assert repo.get_match(match_id)["total_plies"] == 5
    assert repo.get_match(match_id)["ended_at"] is None


def test_rewriting_same_ply_does_not_fail(repo):
    """Nhập lại dữ liệu cũ không được vỡ vì khoá trùng."""
    match_id = repo.create_match({"model_key": "mock", "name": "A"},
                                 {"model_key": "mock", "name": "B"}, "fen-dau")
    repo.append_move(match_id, 1, _move(1), fen_after="fen-cu")
    repo.append_move(match_id, 1, _move(1), fen_after="fen-moi")

    moves = repo.get_moves(match_id)
    assert len(moves) == 1
    assert moves[0]["fen_after"] == "fen-moi"


def test_get_unknown_match_returns_none(repo):
    assert repo.get_match("khong-ton-tai") is None
    assert repo.get_moves("khong-ton-tai") == []


def test_delete_match_removes_moves(repo):
    match_id = repo.create_match({"model_key": "mock", "name": "A"},
                                 {"model_key": "mock", "name": "B"}, "fen-dau")
    repo.append_move(match_id, 1, _move(1), fen_after="fen-1")

    assert repo.delete_match(match_id) is True
    assert repo.get_match(match_id) is None
    assert repo.get_moves(match_id) == []
    assert repo.delete_match(match_id) is False


# --- Elo ---

def test_finished_match_updates_elo_and_record(repo):
    match_id = repo.create_match(
        {"model_key": "winner-model", "name": "Winner"},
        {"model_key": "loser-model", "name": "Loser"}, "fen-dau")
    repo.finish_match(match_id, _state("red_win", 'w'), _stats())

    board = {row["model_key"]: row for row in repo.leaderboard()}
    assert board["winner-model"]["elo"] > STARTING_ELO
    assert board["loser-model"]["elo"] < STARTING_ELO
    assert board["winner-model"]["wins"] == 1
    assert board["loser-model"]["losses"] == 1
    assert board["winner-model"]["matches"] == 1


def test_unfinished_match_does_not_touch_elo(repo):
    """Trận dừng vì hết giới hạn nước không phản ánh sức mạnh -> không tính Elo."""
    match_id = repo.create_match({"model_key": "a-model", "name": "A"},
                                 {"model_key": "b-model", "name": "B"}, "fen-dau")
    repo.finish_match(match_id, _state("ongoing", None), _stats(), stopped_reason="move_limit")

    assert repo.leaderboard() == [], "trận dở dang không được vào bảng xếp hạng"
    assert repo.get_match(match_id)["stopped_reason"] == "move_limit"


def test_elo_is_not_applied_twice(repo):
    """Gọi finish_match hai lần (ví dụ nhập lại dữ liệu) không được cộng Elo hai lần."""
    match_id = repo.create_match({"model_key": "a-model", "name": "A"},
                                 {"model_key": "b-model", "name": "B"}, "fen-dau")
    repo.finish_match(match_id, _state("red_win", 'w'), _stats())
    elo_after_first = {r["model_key"]: r["elo"] for r in repo.leaderboard()}

    repo.finish_match(match_id, _state("red_win", 'w'), _stats())
    elo_after_second = {r["model_key"]: r["elo"] for r in repo.leaderboard()}

    assert elo_after_first == elo_after_second
    assert repo.leaderboard()[0]["matches"] == 1


def test_draw_gives_both_players_a_draw(repo):
    match_id = repo.create_match({"model_key": "a-model", "name": "A"},
                                 {"model_key": "b-model", "name": "B"}, "fen-dau")
    repo.finish_match(match_id, _state("draw", None), _stats())

    for row in repo.leaderboard():
        assert row["draws"] == 1
        assert row["elo"] == pytest.approx(STARTING_ELO)


def test_cost_is_null_when_price_unknown(repo):
    """Model chưa niêm yết giá -> lưu NULL, không lưu số sai."""
    match_id = repo.create_match({"model_key": "a-model", "name": "A"},
                                 {"model_key": "b-model", "name": "B"}, "fen-dau")
    repo.finish_match(match_id, _state("draw", None), _stats(cost_known=False))

    match = repo.get_match(match_id)
    assert match["red_cost_usd"] is None
    assert match["black_cost_usd"] is None


# --- Tích hợp với trọng tài ---

def test_referee_records_match_automatically(repo):
    """Gắn recorder rồi đi vài nước: dữ liệu phải tự vào cơ sở dữ liệu."""
    referee = MatchReferee({"model_key": "mock", "name": "Đỏ"},
                           {"model_key": "mock", "name": "Đen"}, analysis_engine=None)
    match_id = referee.attach_recorder(repo)

    referee.step()
    referee.step()

    moves = repo.get_moves(match_id)
    assert len(moves) == 2
    assert moves[0]["side"] == 'w'
    assert moves[1]["side"] == 'b'
    # FEN lưu lại phải khớp thế cờ thật để replay đúng
    assert moves[1]["fen_after"] == referee.board.to_fen()


def test_referee_records_result_and_elo_on_finish(repo):
    """Trận kết thúc đúng luật -> ghi kết quả và cập nhật Elo."""
    referee = MatchReferee({"model_key": "mock", "name": "Đỏ"},
                           {"model_key": "mock", "name": "Đen"}, analysis_engine=None)
    match_id = referee.attach_recorder(repo)
    # Thế Đen sắp bị chiếu bí: Đỏ đi là kết thúc luôn
    referee.board.load_fen("3k5/9/9/9/9/3RR4/9/9/9/4K4 w - - 0 1")
    for _ in range(6):
        if referee.step()["game_over"]:
            break

    match = repo.get_match(match_id)
    assert match["status"] in ("red_win", "black_win", "draw")
    assert match["ended_at"] is not None
    if match["status"] != "draw":
        assert repo.leaderboard(), "trận kết thúc đúng luật phải vào bảng xếp hạng"


def test_leaderboard_label_comes_from_model_not_custom_name(repo):
    """
    Nhãn bảng xếp hạng phải là tên model, không phải tên tuỳ chỉnh của một trận.

    Nếu lấy tên tuỳ chỉnh thì đặt tên "Kỳ thủ B" một lần là nhãn của model đó bị đổi vĩnh
    viễn, và bảng xếp hạng không còn biết đang xếp hạng model nào.
    """
    match_id = repo.create_match(
        {"model_key": "mock", "name": "Kỳ thủ B", "label": "Mock (đi ngẫu nhiên)"},
        {"model_key": "claude-haiku-4-5", "name": "Đối thủ", "label": "Claude Haiku 4.5"},
        "fen-dau")
    repo.finish_match(match_id, _state("red_win", 'w'), _stats())

    labels = {row["model_key"]: row["label"] for row in repo.leaderboard()}
    assert labels["mock"] == "Mock (đi ngẫu nhiên)"
    assert labels["claude-haiku-4-5"] == "Claude Haiku 4.5"
    # Tên tuỳ chỉnh vẫn được giữ trong bản ghi trận
    assert repo.get_match(match_id)["red_name"] == "Kỳ thủ B"
