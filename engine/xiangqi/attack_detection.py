"""
Phát hiện ô bị tấn công, tướng bị chiếu, và thế lộ mặt tướng.

Kiểm tra trực tiếp theo từng hướng từ ô cần xét (thay vì sinh toàn bộ nước đi của
đối phương) — nhanh hơn và tránh đệ quy vòng tròn với move_generation.
"""

from engine.xiangqi.notation import BOARD_COLS, BOARD_ROWS

ORTHOGONAL_DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAGONAL_DIRECTIONS = ((-1, -1), (-1, 1), (1, -1), (1, 1))

# 8 vị trí mà một con Mã có thể đứng để chiếu tới ô đích.
# Chân mã nằm cạnh CON MÃ, trên trục có độ lệch bằng 2.
KNIGHT_ORIGIN_OFFSETS = (
    (-2, -1), (-2, 1), (2, -1), (2, 1),
    (-1, -2), (-1, 2), (1, -2), (1, 2),
)


def in_bounds(row, col):
    return 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS


def belongs_to(piece, side):
    """side: 'w' (Đỏ, chữ hoa) hoặc 'b' (Đen, chữ thường)."""
    if piece is None:
        return False
    return piece.isupper() if side == 'w' else piece.islower()


def find_king(grid, side):
    target = 'K' if side == 'w' else 'k'
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if grid[row][col] == target:
                return row, col
    return None


def in_palace(row, col, side):
    if not in_bounds(row, col) or not (3 <= col <= 5):
        return False
    return 7 <= row <= 9 if side == 'w' else 0 <= row <= 2


def _attacked_by_rook_or_cannon_or_king(grid, row, col, by_side):
    """Quét 4 tia trực giao: quân chắn thứ nhất -> Xe/Tướng kề; quân thứ hai -> Pháo."""
    rook = 'R' if by_side == 'w' else 'r'
    cannon = 'C' if by_side == 'w' else 'c'
    king = 'K' if by_side == 'w' else 'k'

    for d_row, d_col in ORTHOGONAL_DIRECTIONS:
        r, c = row + d_row, col + d_col
        distance = 1
        first_blocker = None
        while in_bounds(r, c):
            piece = grid[r][c]
            if piece is not None:
                first_blocker = (piece, distance)
                break
            r += d_row
            c += d_col
            distance += 1

        if first_blocker is None:
            continue

        blocker_piece, blocker_distance = first_blocker
        if blocker_piece == rook:
            return True
        if blocker_piece == king and blocker_distance == 1 and in_palace(r, c, by_side):
            return True

        # Vượt qua ngòi để tìm Pháo
        r += d_row
        c += d_col
        while in_bounds(r, c):
            piece = grid[r][c]
            if piece is not None:
                if piece == cannon:
                    return True
                break
            r += d_row
            c += d_col

    return False


def _attacked_by_knight(grid, row, col, by_side):
    knight = 'N' if by_side == 'w' else 'n'
    for d_row, d_col in KNIGHT_ORIGIN_OFFSETS:
        knight_row, knight_col = row + d_row, col + d_col
        if not in_bounds(knight_row, knight_col) or grid[knight_row][knight_col] != knight:
            continue
        # Chân mã: từ vị trí con mã, đi 1 bước về phía ô đích trên trục lệch 2
        if abs(d_row) == 2:
            leg_row, leg_col = knight_row + (1 if d_row < 0 else -1), knight_col
        else:
            leg_row, leg_col = knight_row, knight_col + (1 if d_col < 0 else -1)
        if grid[leg_row][leg_col] is None:
            return True
    return False


def _attacked_by_pawn(grid, row, col, by_side):
    pawn = 'P' if by_side == 'w' else 'p'
    # Binh Đỏ tiến lên (row giảm) nên chiếu từ ô bên dưới; Tốt Đen thì ngược lại
    forward_origin_row = row + 1 if by_side == 'w' else row - 1
    if in_bounds(forward_origin_row, col) and grid[forward_origin_row][col] == pawn:
        return True

    # Ăn ngang chỉ khi quân đó đã qua hà
    for d_col in (-1, 1):
        side_col = col + d_col
        if not in_bounds(row, side_col) or grid[row][side_col] != pawn:
            continue
        crossed_river = row <= 4 if by_side == 'w' else row >= 5
        if crossed_river:
            return True
    return False


def _attacked_by_advisor(grid, row, col, by_side):
    advisor = 'A' if by_side == 'w' else 'a'
    for d_row, d_col in DIAGONAL_DIRECTIONS:
        r, c = row + d_row, col + d_col
        if in_palace(r, c, by_side) and grid[r][c] == advisor:
            return True
    return False


def _attacked_by_elephant(grid, row, col, by_side):
    elephant = 'B' if by_side == 'w' else 'b'
    for d_row, d_col in DIAGONAL_DIRECTIONS:
        r, c = row + 2 * d_row, col + 2 * d_col
        if not in_bounds(r, c) or grid[r][c] != elephant:
            continue
        if grid[row + d_row][col + d_col] is None:  # mắt tượng trống
            return True
    return False


def is_square_attacked(grid, row, col, by_side):
    """
    Ô (row, col) có bị bên `by_side` tấn công không.

    Không tính luật lộ mặt tướng — dùng riêng `kings_facing()` cho luật đó,
    vì đây là hai điều kiện khác nhau về mặt luật.
    """
    return (
        _attacked_by_rook_or_cannon_or_king(grid, row, col, by_side)
        or _attacked_by_knight(grid, row, col, by_side)
        or _attacked_by_pawn(grid, row, col, by_side)
        or _attacked_by_advisor(grid, row, col, by_side)
        or _attacked_by_elephant(grid, row, col, by_side)
    )


def is_in_check(grid, side):
    """Tướng của `side` có đang bị chiếu không. Không có tướng -> False (trận đã kết thúc)."""
    king_pos = find_king(grid, side)
    if king_pos is None:
        return False
    opponent = 'b' if side == 'w' else 'w'
    return is_square_attacked(grid, king_pos[0], king_pos[1], opponent)


def kings_facing(grid):
    """Hai tướng đối mặt trên cùng cột mà không có quân nào chắn giữa (cấm)."""
    red_king = find_king(grid, 'w')
    black_king = find_king(grid, 'b')
    if red_king is None or black_king is None:
        return False
    if red_king[1] != black_king[1]:
        return False
    col = red_king[1]
    for row in range(min(red_king[0], black_king[0]) + 1, max(red_king[0], black_king[0])):
        if grid[row][col] is not None:
            return False
    return True
