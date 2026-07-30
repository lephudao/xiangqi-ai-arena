"""Test sinh nước đi cho từng loại quân."""

from engine.xiangqi import XiangqiBoard, INITIAL_FEN


def test_opening_position_has_44_legal_moves():
    """Thế khai cuộc cờ tướng có đúng 44 nước đi hợp lệ (giá trị chuẩn đã biết)."""
    board = XiangqiBoard()
    assert len(board.generate_legal_moves('w')) == 44
    assert len(board.generate_legal_moves('b')) == 44


def test_make_unmake_restores_position():
    board = XiangqiBoard()
    original_fen = board.to_fen()
    for move in board.generate_legal_moves('w')[:10]:
        r1, c1 = 9 - int(move[1]), ord(move[0]) - ord('a')
        r2, c2 = 9 - int(move[3]), ord(move[2]) - ord('a')
        board.make_raw_move(r1, c1, r2, c2)
        board.unmake_raw_move()
    assert board.to_fen() == original_fen


def test_knight_blocked_leg_cannot_move():
    """Mã bị cản chân (quân ngay cạnh theo trục lệch 2) không sinh được nước đó."""
    # Mã Đỏ ở b0 (row 9, col 1), Binh chắn chân mã ở b1 (row 8, col 1) -> chặn b0c2 và b0a2
    fen = "3k5/9/9/9/9/9/9/9/1P7/1N2K4 w - - 0 1"
    board = XiangqiBoard(fen)
    moves = board.generate_legal_moves('w')
    assert 'b0c2' not in moves
    assert 'b0a2' not in moves
    # Hướng ngang không bị chặn bởi quân trên trục dọc
    assert 'b0d1' in moves


def test_elephant_blocked_eye_cannot_move():
    """Tượng bị cản mắt không đi được."""
    # Tượng Đỏ c0 (row 9, col 2); mắt tượng của nước c0e2 là d1 (row 8, col 3) -> bị Binh cản
    fen = "3k5/9/9/9/9/9/9/9/3P5/2B1K4 w - - 0 1"
    board = XiangqiBoard(fen)
    assert 'c0e2' not in board.generate_legal_moves('w')


def test_elephant_cannot_cross_river():
    fen = "3k5/9/9/9/9/9/9/9/9/2B1K4 w - - 0 1"
    board = XiangqiBoard(fen)
    elephant_moves = [m for m in board.generate_legal_moves('w') if m.startswith('c0')]
    # Tượng chỉ được ở nửa sân mình (rank <= 4 với Đỏ)
    for move in elephant_moves:
        assert int(move[3]) <= 4


def test_cannon_needs_screen_to_capture():
    """Pháo chỉ ăn được khi có đúng 1 quân làm ngòi."""
    # Pháo Đỏ e0 (row 9, col 4), Tốt Đen e5 (row 4, col 4), không có ngòi -> không ăn được
    fen = "4k4/9/9/9/4p4/9/9/9/9/3KC4 w - - 0 1"
    board = XiangqiBoard(fen)
    assert 'e0e5' not in board.generate_legal_moves('w')

    # Thêm ngòi ở e2 (row 7) -> ăn được
    fen_with_screen = "4k4/9/9/9/4p4/9/9/4P4/9/3KC4 w - - 0 1"
    board = XiangqiBoard(fen_with_screen)
    assert 'e0e5' in board.generate_legal_moves('w')


def test_pawn_cannot_move_sideways_before_crossing_river():
    # Binh Đỏ ở e3 (row 6) — chưa qua hà
    fen = "3k5/9/9/9/9/9/4P4/9/9/4K4 w - - 0 1"
    board = XiangqiBoard(fen)
    pawn_moves = [m for m in board.generate_legal_moves('w') if m.startswith('e3')]
    assert pawn_moves == ['e3e4']


def test_pawn_moves_sideways_after_crossing_river():
    # Binh Đỏ ở e6 (row 3) — đã qua hà
    fen = "3k5/9/9/4P4/9/9/9/9/9/4K4 w - - 0 1"
    board = XiangqiBoard(fen)
    pawn_moves = sorted(m for m in board.generate_legal_moves('w') if m.startswith('e6'))
    assert pawn_moves == ['e6d6', 'e6e7', 'e6f6']


def test_king_confined_to_palace():
    fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    board = XiangqiBoard(fen)
    king_moves = sorted(m for m in board.generate_legal_moves('w') if m.startswith('e0'))
    assert king_moves == ['e0d0', 'e0f0']  # e1 bị loại vì lộ mặt tướng với Tướng Đen ở e9
