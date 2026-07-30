"""
Test chấm điểm chất lượng nước đi.

Các test công thức không cần engine; các test chấm điểm thật sẽ bỏ qua nếu chưa cài Pikafish.
"""

import pytest

from engine.analysis import PikafishEngine, score_move
from engine.analysis.move_quality_scorer import (
    QUALITY_BEST,
    QUALITY_BLUNDER,
    QUALITY_GOOD,
    QUALITY_INACCURACY,
    QUALITY_MISTAKE,
    average_accuracy,
    classify_move,
    move_accuracy,
    win_percentage,
)

# Thế cờ Xe đối Xe cùng cột e; Tướng Đỏ e0 nằm sau Xe Đỏ e1 nên Xe Đỏ bị "ghim"
PINNED_ROOK_FEN = "3k5/9/9/9/4r4/9/9/9/4R4/4K4 w - - 0 1"


@pytest.fixture(scope="module")
def engine():
    instance = PikafishEngine(movetime_ms=200)
    if not instance.is_available:
        pytest.skip(f"Pikafish chưa cài: {instance.unavailable_reason}")
    yield instance
    instance.close()


# --- Công thức (không cần engine) ---

def test_win_percentage_is_symmetric_around_zero():
    assert win_percentage(0) == pytest.approx(50.0)
    assert win_percentage(300) + win_percentage(-300) == pytest.approx(100.0)
    assert win_percentage(1000) > win_percentage(300) > win_percentage(0)


def test_accuracy_is_full_when_position_does_not_worsen():
    assert move_accuracy(50, 50) == 100.0
    assert move_accuracy(50, 120) == 100.0  # thế tốt lên thì vẫn 100


def test_accuracy_drops_as_position_worsens():
    small_loss = move_accuracy(0, -30)
    big_loss = move_accuracy(0, -600)
    assert 100 > small_loss > big_loss >= 0


def test_classification_thresholds():
    assert classify_move(0) == QUALITY_GOOD
    assert classify_move(150) == QUALITY_INACCURACY
    assert classify_move(300) == QUALITY_MISTAKE
    assert classify_move(900) == QUALITY_BLUNDER


def test_playing_engine_bestmove_is_labelled_best():
    assert classify_move(0, played_move="h2e2", engine_bestmove="h2e2") == QUALITY_BEST
    assert classify_move(0, played_move="h2e2", engine_bestmove="c3c4") == QUALITY_GOOD


def test_average_accuracy_ignores_unscored_moves():
    class FakeEval:
        def __init__(self, accuracy):
            self.accuracy = accuracy

    assert average_accuracy([FakeEval(100), FakeEval(50), None]) == pytest.approx(75.0)
    assert average_accuracy([None, None]) is None
    assert average_accuracy([]) is None


def test_scoring_without_engine_returns_none():
    """Thiếu engine thì bỏ qua chấm điểm, không được raise — trận vẫn phải chạy."""
    assert score_move(None, "fen", "fen", "h2e2") is None
    broken = PikafishEngine(engine_path="/khong/ton/tai")
    assert score_move(broken, "fen", "fen", "h2e2") is None


# --- Chấm điểm thật bằng engine ---

def test_capturing_free_rook_is_the_best_move(engine):
    """Xe Đỏ ăn không Xe Đen: phải được chấm là nước hay nhất, không mất điểm."""
    from engine.xiangqi import XiangqiBoard

    board = XiangqiBoard(PINNED_ROOK_FEN)
    fen_before = board.to_fen()
    success, _ = board.push_ucci("e1e5")
    assert success

    evaluation = score_move(engine, fen_before, board.to_fen(), "e1e5")
    assert evaluation.cp_loss == 0
    assert evaluation.quality == QUALITY_BEST
    assert evaluation.accuracy == pytest.approx(100.0)
    assert evaluation.engine_bestmove == "e1e5"


def test_giving_away_rook_is_a_blunder(engine):
    """Đưa Xe vào tầm Xe đối phương mà không ai đỡ: phải bị chấm blunder."""
    from engine.xiangqi import XiangqiBoard

    board = XiangqiBoard(PINNED_ROOK_FEN)
    fen_before = board.to_fen()
    success, _ = board.push_ucci("e1e2")
    assert success

    evaluation = score_move(engine, fen_before, board.to_fen(), "e1e2")
    assert evaluation.cp_loss > 500
    assert evaluation.quality == QUALITY_BLUNDER
    assert evaluation.accuracy < 20


def test_standard_opening_move_scores_well(engine):
    """Pháo đầu (h2e2) là khai cuộc kinh điển: gần như không mất điểm."""
    from engine.xiangqi import XiangqiBoard

    board = XiangqiBoard()
    fen_before = board.to_fen()
    board.push_ucci("h2e2")

    evaluation = score_move(engine, fen_before, board.to_fen(), "h2e2")
    assert evaluation.cp_loss < 30
    assert evaluation.accuracy > 90


def test_pointless_move_loses_more_than_good_move(engine):
    """Nước vô ích phải mất nhiều điểm hơn nước khai cuộc chuẩn."""
    from engine.xiangqi import XiangqiBoard

    def loss_for(move):
        board = XiangqiBoard()
        fen_before = board.to_fen()
        board.push_ucci(move)
        return score_move(engine, fen_before, board.to_fen(), move).cp_loss

    assert loss_for("a0a1") > loss_for("h2e2")
