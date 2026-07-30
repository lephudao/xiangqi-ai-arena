"""
Sinh nước đi cho 7 loại quân cờ tướng.

`generate_pseudo_moves` sinh nước đi hợp lệ về hình học (chân mã, mắt tượng, ngòi pháo,
binh qua hà) nhưng CHƯA lọc theo an toàn của tướng.
`generate_legal_moves` lọc thêm: không được để tướng mình bị chiếu, không được lộ mặt tướng.
"""

from engine.xiangqi.attack_detection import (
    DIAGONAL_DIRECTIONS,
    ORTHOGONAL_DIRECTIONS,
    belongs_to,
    in_bounds,
    in_palace,
    is_in_check,
    kings_facing,
)
from engine.xiangqi.notation import move_tuple_to_ucci


def _is_same_side(piece_a, piece_b):
    if piece_a is None or piece_b is None:
        return False
    return piece_a.isupper() == piece_b.isupper()


def _can_land(grid, piece, row, col):
    """Ô đích nằm trong bàn và không có quân cùng màu."""
    if not in_bounds(row, col):
        return False
    return not _is_same_side(piece, grid[row][col])


def _king_moves(grid, piece, row, col, side, moves):
    for d_row, d_col in ORTHOGONAL_DIRECTIONS:
        r, c = row + d_row, col + d_col
        if in_palace(r, c, side) and _can_land(grid, piece, r, c):
            moves.append((row, col, r, c))


def _advisor_moves(grid, piece, row, col, side, moves):
    for d_row, d_col in DIAGONAL_DIRECTIONS:
        r, c = row + d_row, col + d_col
        if in_palace(r, c, side) and _can_land(grid, piece, r, c):
            moves.append((row, col, r, c))


def _elephant_moves(grid, piece, row, col, side, moves):
    for d_row, d_col in DIAGONAL_DIRECTIONS:
        r, c = row + 2 * d_row, col + 2 * d_col
        if not in_bounds(r, c):
            continue
        # Tượng không được qua hà
        own_half = r >= 5 if side == 'w' else r <= 4
        if not own_half:
            continue
        if grid[row + d_row][col + d_col] is not None:  # mắt tượng bị cản
            continue
        if _can_land(grid, piece, r, c):
            moves.append((row, col, r, c))


def _knight_moves(grid, piece, row, col, moves):
    # (d_row, d_col, leg_row_offset, leg_col_offset)
    knight_steps = (
        (-2, -1, -1, 0), (-2, 1, -1, 0), (2, -1, 1, 0), (2, 1, 1, 0),
        (-1, -2, 0, -1), (1, -2, 0, -1), (-1, 2, 0, 1), (1, 2, 0, 1),
    )
    for d_row, d_col, leg_row, leg_col in knight_steps:
        r, c = row + d_row, col + d_col
        if not in_bounds(r, c):
            continue
        if grid[row + leg_row][col + leg_col] is not None:  # chân mã bị cản
            continue
        if _can_land(grid, piece, r, c):
            moves.append((row, col, r, c))


def _rook_moves(grid, piece, row, col, moves):
    for d_row, d_col in ORTHOGONAL_DIRECTIONS:
        r, c = row + d_row, col + d_col
        while in_bounds(r, c):
            target = grid[r][c]
            if target is None:
                moves.append((row, col, r, c))
            else:
                if not _is_same_side(piece, target):
                    moves.append((row, col, r, c))
                break
            r += d_row
            c += d_col


def _cannon_moves(grid, piece, row, col, moves):
    for d_row, d_col in ORTHOGONAL_DIRECTIONS:
        r, c = row + d_row, col + d_col
        screen_found = False
        while in_bounds(r, c):
            target = grid[r][c]
            if not screen_found:
                if target is None:
                    moves.append((row, col, r, c))  # đi (không ăn)
                else:
                    screen_found = True  # tìm được ngòi
            elif target is not None:
                if not _is_same_side(piece, target):
                    moves.append((row, col, r, c))  # ăn quân qua ngòi
                break
            r += d_row
            c += d_col


def _pawn_moves(grid, piece, row, col, side, moves):
    forward = -1 if side == 'w' else 1
    r, c = row + forward, col
    if _can_land(grid, piece, r, c):
        moves.append((row, col, r, c))

    crossed_river = row <= 4 if side == 'w' else row >= 5
    if crossed_river:
        for d_col in (-1, 1):
            r, c = row, col + d_col
            if _can_land(grid, piece, r, c):
                moves.append((row, col, r, c))


def generate_pseudo_moves(grid, side):
    """Nước đi hợp lệ về hình học, chưa xét an toàn của tướng."""
    moves = []
    for row in range(10):
        for col in range(9):
            piece = grid[row][col]
            if not belongs_to(piece, side):
                continue

            piece_type = piece.upper()
            if piece_type == 'K':
                _king_moves(grid, piece, row, col, side, moves)
            elif piece_type == 'A':
                _advisor_moves(grid, piece, row, col, side, moves)
            elif piece_type == 'B':
                _elephant_moves(grid, piece, row, col, side, moves)
            elif piece_type == 'N':
                _knight_moves(grid, piece, row, col, moves)
            elif piece_type == 'R':
                _rook_moves(grid, piece, row, col, moves)
            elif piece_type == 'C':
                _cannon_moves(grid, piece, row, col, moves)
            elif piece_type == 'P':
                _pawn_moves(grid, piece, row, col, side, moves)
    return moves


def generate_legal_move_tuples(board, side):
    """
    Lọc pseudo-moves: loại nước để tướng mình bị chiếu hoặc gây lộ mặt tướng.

    Đây là điểm sửa lỗi cốt lõi so với bản cũ (bản cũ chỉ kiểm tra lộ mặt tướng,
    nên AI có thể đi nước tự sát để tướng bị chiếu).
    """
    legal = []
    for move in generate_pseudo_moves(board.grid, side):
        board.make_raw_move(*move)
        is_safe = not is_in_check(board.grid, side) and not kings_facing(board.grid)
        board.unmake_raw_move()
        if is_safe:
            legal.append(move)
    return legal


def generate_legal_moves(board, side):
    """Danh sách nước đi hợp lệ dạng UCCI, ví dụ ['h2e2', 'b0c2', ...]."""
    return [move_tuple_to_ucci(*move) for move in generate_legal_move_tuples(board, side)]
