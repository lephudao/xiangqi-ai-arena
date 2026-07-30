"""Test ký hiệu cờ tướng tiếng Việt."""

from engine.xiangqi import XiangqiBoard
from engine.xiangqi.notation import file_number, to_vietnamese_notation


def test_file_numbering_is_per_side_perspective():
    # Đỏ đếm cột 1-9 từ phải sang trái: cột 'a' (index 0) là cột 9
    assert file_number(0, is_red=True) == 9
    assert file_number(8, is_red=True) == 1
    # Đen đếm ngược lại
    assert file_number(0, is_red=False) == 1
    assert file_number(8, is_red=False) == 9


def test_classic_cannon_to_center():
    """Nước khai cuộc phổ biến nhất: Pháo đầu."""
    board = XiangqiBoard()
    assert to_vietnamese_notation(board.grid, 'h2e2') == "Pháo 2 bình 5"
    assert to_vietnamese_notation(board.grid, 'b2e2') == "Pháo 8 bình 5"


def test_knight_uses_destination_file():
    board = XiangqiBoard()
    # Mã Đỏ b0 (cột 8 của Đỏ) tiến tới c2 (cột 7 của Đỏ)
    assert to_vietnamese_notation(board.grid, 'b0c2') == "Mã 8 tấn 7"


def test_rook_forward_uses_step_count():
    # Xe Đỏ a0 (cột 9) tiến 4 ô lên a4
    board = XiangqiBoard("3k5/9/9/9/9/9/9/9/9/R3K4 w - - 0 1")
    assert to_vietnamese_notation(board.grid, 'a0a4') == "Xe 9 tấn 4"


def test_rook_retreat():
    board = XiangqiBoard("3k5/9/9/9/9/R8/9/9/9/4K4 w - - 0 1")
    assert to_vietnamese_notation(board.grid, 'a4a1') == "Xe 9 thoái 3"


def test_black_pawn_is_called_tot():
    board = XiangqiBoard()
    text = to_vietnamese_notation(board.grid, 'a6a5')
    assert text.startswith("Tốt")


def test_black_side_uses_own_file_numbering():
    board = XiangqiBoard()
    # Pháo Đen b7 -> cột 'b' là cột 2 của Đen; bình về e7 là cột 5
    assert to_vietnamese_notation(board.grid, 'b7e7') == "Pháo 2 bình 5"


def test_tandem_pieces_use_front_rear_prefix():
    # Hai Xe Đỏ cùng cột a: a0 (row 9) và a3 (row 6). Xe gần Đen hơn là "Tiền"
    board = XiangqiBoard("3k5/9/9/9/9/9/R8/9/9/R3K4 w - - 0 1")
    assert to_vietnamese_notation(board.grid, 'a3a4') == "Tiền Xe tấn 1"
    assert to_vietnamese_notation(board.grid, 'a0a1') == "Hậu Xe tấn 1"


def test_invalid_input_falls_back_to_raw_string():
    board = XiangqiBoard()
    assert to_vietnamese_notation(board.grid, 'zzz') == 'zzz'
    # Ô trống -> trả nguyên văn
    assert to_vietnamese_notation(board.grid, 'e4e5') == 'e4e5'
