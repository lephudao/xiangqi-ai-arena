"""Test luật kết thúc trận: chiếu bí, hết nước, mất tướng, hoà."""

from engine.xiangqi import XiangqiBoard
from engine.xiangqi.game_rules import (
    HALFMOVE_DRAW_LIMIT,
    STATUS_BLACK_WIN,
    STATUS_DRAW,
    STATUS_ONGOING,
    STATUS_RED_WIN,
    evaluate_position,
)


def test_ongoing_at_opening():
    result = evaluate_position(XiangqiBoard())
    assert result.status == STATUS_ONGOING
    assert not result.is_over


def test_checkmate_detected():
    """
    Tướng Đỏ e0 bị hai Xe Đen khoá: Xe e5 chiếu dọc cột e, Xe d5 khống chế cột d,
    Xe f-file khống chế cột f -> Tướng không có ô nào chạy.
    """
    board = XiangqiBoard("3k5/9/9/9/9/3rrr3/9/9/9/4K4 w - - 0 1")
    result = evaluate_position(board)
    assert result.status == STATUS_BLACK_WIN
    assert result.reason == "checkmate"
    assert result.winner_side == 'b'


def test_stalemate_is_a_loss_in_xiangqi():
    """
    Cờ tướng: hết nước đi mà KHÔNG bị chiếu thì bên tới lượt THUA (khác cờ vua).
    Tướng Đỏ e0 không bị chiếu, nhưng d0/f0 bị Xe khống chế và e1 bị lộ mặt tướng.
    """
    board = XiangqiBoard("4k4/9/9/9/9/3r1r3/9/9/9/4K4 w - - 0 1")
    result = evaluate_position(board)
    assert result.status == STATUS_BLACK_WIN
    assert result.reason == "stalemate"


def test_missing_king_ends_match():
    board = XiangqiBoard("9/9/9/9/9/9/9/9/9/4K4 b - - 0 1")
    result = evaluate_position(board)
    assert result.status == STATUS_RED_WIN
    assert result.reason == "king_captured"


def test_halfmove_limit_is_a_draw():
    fen = f"3k5/9/9/9/9/9/9/9/9/4K4 w - - {HALFMOVE_DRAW_LIMIT} 61"
    result = evaluate_position(XiangqiBoard(fen))
    assert result.status == STATUS_DRAW
    assert result.reason == "draw_60_moves"


def test_threefold_repetition_is_a_draw():
    """Hai Xe đi qua lại tạo lặp thế cờ 3 lần -> hoà."""
    board = XiangqiBoard("3k5/9/9/r8/9/9/9/9/R8/4K4 w - - 0 1")
    # Xe Đỏ và Xe Đen đi qua lại giữa 2 ô, trở về đúng thế ban đầu sau mỗi 4 nước
    cycle = ['a1b1', 'a6b6', 'b1a1', 'b6a6']
    for _ in range(2):
        for move in cycle:
            success, message = board.push_ucci(move)
            assert success, message

    result = evaluate_position(board)
    assert result.status == STATUS_DRAW
    assert result.reason in ("draw_repetition", "draw_perpetual_check")


def test_halfmove_clock_resets_on_capture():
    board = XiangqiBoard("3k5/9/9/9/9/9/9/9/r8/R3K4 w - - 5 3")
    success, _ = board.push_ucci('a0a1')  # Xe Đỏ ăn Xe Đen
    assert success
    assert board.halfmove_clock == 0
    assert '0' == board.to_fen().split()[4]


def test_halfmove_clock_increments_without_capture():
    board = XiangqiBoard()
    board.push_ucci('h2e2')
    assert board.halfmove_clock == 1
    assert board.to_fen().split()[4] == '1'


def test_move_number_increments_after_black_move():
    board = XiangqiBoard()
    board.push_ucci('h2e2')
    assert board.move_number == 1
    board.push_ucci('h7e7')
    assert board.move_number == 2


def test_illegal_move_is_rejected_with_reason():
    board = XiangqiBoard()
    success, message = board.push_ucci('a0a9')  # Xe không thể xuyên qua quân
    assert not success
    assert 'không thể đi' in message

    success, message = board.push_ucci('zz99')
    assert not success
    assert 'UCCI' in message
