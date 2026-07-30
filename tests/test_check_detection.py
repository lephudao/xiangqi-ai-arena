"""
Test phát hiện chiếu tướng — đây là bug nghiêm trọng nhất của bản engine cũ:
bản cũ chỉ kiểm tra lộ mặt tướng nên AI có thể đi nước tự sát.
"""

from engine.xiangqi import XiangqiBoard, is_in_check, is_square_attacked, kings_facing


def test_rook_gives_check():
    # Xe Đen ở e4 (row 5, col 4) chiếu dọc xuống Tướng Đỏ ở e0 (row 9, col 4)
    board = XiangqiBoard("3k5/9/9/9/9/4r4/9/9/9/4K4 w - - 0 1")
    assert is_in_check(board.grid, 'w')
    assert not is_in_check(board.grid, 'b')


def test_cannon_gives_check_only_through_screen():
    # Pháo Đen e5 (row 4), ngòi là Binh Đỏ e2 (row 7), Tướng Đỏ e0 (row 9)
    with_screen = XiangqiBoard("3k5/9/9/9/4c4/9/9/4P4/9/4K4 w - - 0 1")
    assert is_in_check(with_screen.grid, 'w')

    # Không có ngòi -> không chiếu
    without_screen = XiangqiBoard("3k5/9/9/9/4c4/9/9/9/9/4K4 w - - 0 1")
    assert not is_in_check(without_screen.grid, 'w')

    # Hai quân chắn -> pháo không chiếu được (ngòi phải đúng 1 quân)
    two_blockers = XiangqiBoard("3k5/9/9/9/4c4/9/4P4/4P4/9/4K4 w - - 0 1")
    assert not is_in_check(two_blockers.grid, 'w')


def test_knight_gives_check_respecting_leg():
    # Mã Đen ở d2 (row 7, col 3) chiếu Tướng Đỏ e0 (row 9, col 4): lệch (2, 1), chân mã ở d1 (row 8, col 3)
    free_leg = XiangqiBoard("3k5/9/9/9/9/9/9/3n5/9/4K4 w - - 0 1")
    assert is_in_check(free_leg.grid, 'w')

    # Cản chân mã ở d1 -> hết chiếu
    blocked_leg = XiangqiBoard("3k5/9/9/9/9/9/9/3n5/3P5/4K4 w - - 0 1")
    assert not is_in_check(blocked_leg.grid, 'w')


def test_pawn_gives_check():
    # Tốt Đen ở e1 (row 8) tiến xuống, chiếu Tướng Đỏ e0 (row 9)
    board = XiangqiBoard("3k5/9/9/9/9/9/9/9/4p4/4K4 w - - 0 1")
    assert is_in_check(board.grid, 'w')


def test_pawn_sideways_check_requires_crossing_river():
    # Tốt Đen ở d0 (row 9, col 3) — đã qua hà (row >= 5) nên ăn ngang được -> chiếu e0
    crossed = XiangqiBoard("3k5/9/9/9/9/9/9/9/9/3pK4 w - - 0 1")
    assert is_in_check(crossed.grid, 'w')


def test_moving_into_check_is_illegal():
    """
    Test then chốt cho bug cũ: Tướng Đỏ e0, Xe Đen ở d5 (cột d).
    Nước e0d0 đưa Tướng vào cột bị Xe chiếu -> phải bị loại khỏi danh sách hợp lệ.
    """
    board = XiangqiBoard("4k4/9/9/9/9/3r5/9/9/9/4K4 w - - 0 1")
    moves = board.generate_legal_moves('w')
    assert 'e0d0' not in moves
    assert 'e0f0' in moves


def test_must_resolve_existing_check():
    """Đang bị chiếu thì mọi nước hợp lệ phải giải quyết được thế chiếu."""
    # Xe Đen e5 chiếu Tướng Đỏ e0
    board = XiangqiBoard("3k5/9/9/9/9/4r4/9/9/9/4K4 w - - 0 1")
    moves = board.generate_legal_moves('w')
    assert moves, "phải còn nước chạy tướng"
    for move in moves:
        r1, c1 = 9 - int(move[1]), ord(move[0]) - ord('a')
        r2, c2 = 9 - int(move[3]), ord(move[2]) - ord('a')
        board.make_raw_move(r1, c1, r2, c2)
        still_in_check = is_in_check(board.grid, 'w')
        board.unmake_raw_move()
        assert not still_in_check, f"nước {move} không giải được thế chiếu"


def test_kings_facing_is_forbidden():
    board = XiangqiBoard("4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
    assert kings_facing(board.grid)
    # Nước tiến tướng lên e1 vẫn giữ lộ mặt -> bị cấm
    assert 'e0e1' not in board.generate_legal_moves('w')


def test_blocked_kings_are_not_facing():
    board = XiangqiBoard("4k4/9/9/9/4P4/9/9/9/9/4K4 w - - 0 1")
    assert not kings_facing(board.grid)


def test_square_attacked_by_advisor_and_elephant():
    # Sĩ Đen ở d8 (row 1, col 3) kiểm soát e9 (row 0, col 4)
    board = XiangqiBoard("4k4/3a5/9/9/9/9/9/9/9/4K4 w - - 0 1")
    assert is_square_attacked(board.grid, 0, 4, 'b')

    # Tượng Đen c9 (row 0, col 2) kiểm soát e7 (row 2, col 4) khi mắt tượng d8 trống
    board2 = XiangqiBoard("2b1k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
    assert is_square_attacked(board2.grid, 2, 4, 'b')
