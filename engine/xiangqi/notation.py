"""
Chuyển đổi toạ độ UCCI <-> chỉ số lưới, và sinh ký hiệu cờ tướng tiếng Việt.

Hệ toạ độ lưới nội bộ: grid[row][col], row 0 = hàng trên cùng (hậu phương Đen),
row 9 = hàng dưới cùng (hậu phương Đỏ), col 0 = cột 'a' (bên trái màn hình).

Ký hiệu UCCI: cột 'a'-'i' (trái sang phải), hàng '0'-'9' (dưới lên trên).
"""

BOARD_ROWS = 10
BOARD_COLS = 9

# Tên quân theo tiếng Việt (không kèm màu — màu đã thể hiện qua chữ hoa/thường)
PIECE_NAMES_VI = {
    'K': 'Tướng', 'A': 'Sĩ', 'B': 'Tượng', 'N': 'Mã',
    'R': 'Xe', 'C': 'Pháo', 'P': 'Binh',
}
BLACK_PAWN_NAME = 'Tốt'  # Bên Đen gọi quân 'p' là Tốt, bên Đỏ gọi 'P' là Binh

# Quân đi chéo/vắt: số sau "tấn"/"thoái" là SỐ CỘT ĐÍCH, không phải số ô di chuyển
DIAGONAL_PIECES = {'N', 'B', 'A'}


def ucci_to_pos(square):
    """'h2' -> (row, col). Trả None nếu sai định dạng."""
    if not square or len(square) != 2:
        return None
    col = ord(square[0].lower()) - ord('a')
    if not square[1].isdigit():
        return None
    rank = int(square[1])
    if not (0 <= col < BOARD_COLS and 0 <= rank <= 9):
        return None
    return 9 - rank, col


def pos_to_ucci(row, col):
    """(row, col) -> 'h2'."""
    return f"{chr(ord('a') + col)}{9 - row}"


def parse_ucci_move(ucci):
    """'h2e2' -> (r1, c1, r2, c2). Trả None nếu sai định dạng."""
    if not ucci or len(ucci) != 4:
        return None
    start = ucci_to_pos(ucci[:2])
    end = ucci_to_pos(ucci[2:])
    if start is None or end is None:
        return None
    return start[0], start[1], end[0], end[1]


def move_tuple_to_ucci(r1, c1, r2, c2):
    return f"{pos_to_ucci(r1, c1)}{pos_to_ucci(r2, c2)}"


def is_red_piece(piece):
    return piece is not None and piece.isupper()


def file_number(col, is_red):
    """
    Số cột theo góc nhìn của bên đi: 1-9 tính từ phải sang trái của chính bên đó.
    Đỏ ngồi dưới nên cột 'a' (trái màn hình) là cột 9 của Đỏ.
    Đen ngồi trên, hướng nhìn ngược lại, nên cột 'a' là cột 1 của Đen.
    """
    return (BOARD_COLS - col) if is_red else (col + 1)


def piece_display_name(piece):
    name = PIECE_NAMES_VI.get(piece.upper(), piece)
    if piece == 'p':
        return BLACK_PAWN_NAME
    return name


def _same_file_siblings(grid, piece, col):
    """Các hàng (row) chứa quân cùng loại cùng màu trên cùng cột, sắp xếp từ trên xuống."""
    return [r for r in range(BOARD_ROWS) if grid[r][col] == piece]


def to_vietnamese_notation(grid, ucci):
    """
    Sinh ký hiệu cờ tướng tiếng Việt cho nước đi, dựa trên bàn cờ TRƯỚC khi đi.

    Ví dụ: thế khai cuộc, 'h2e2' -> 'Pháo 2 bình 5'.

    Cấu trúc: [tiền/hậu] <Tên quân> <cột xuất phát> <bình|tấn|thoái> <đích>
      - bình: đi ngang, đích = số cột mới
      - tấn/thoái: quân đi thẳng (Xe/Pháo/Binh/Tướng) -> đích = số ô di chuyển
                   quân đi chéo (Mã/Tượng/Sĩ)         -> đích = số cột đích
    """
    parsed = parse_ucci_move(ucci)
    if parsed is None:
        return ucci
    r1, c1, r2, c2 = parsed

    piece = grid[r1][c1]
    if piece is None:
        return ucci

    is_red = is_red_piece(piece)
    name = piece_display_name(piece)
    from_file = file_number(c1, is_red)

    # Tiền/hậu khi có nhiều quân cùng loại trên cùng cột
    siblings = _same_file_siblings(grid, piece, c1)
    prefix = ""
    if len(siblings) == 2:
        # "tiền" = quân gần phía đối phương hơn
        front_row = min(siblings) if is_red else max(siblings)
        prefix = "Tiền " if r1 == front_row else "Hậu "
        from_file = None  # có tiền/hậu thì lược bỏ số cột theo thông lệ
    elif len(siblings) > 2:
        # 3+ quân cùng cột (thường là Binh/Tốt): đánh số thứ tự từ phía đối phương
        ordered = sorted(siblings) if is_red else sorted(siblings, reverse=True)
        prefix = f"{name} thứ {ordered.index(r1) + 1} "
        name = ""
        from_file = None

    head = f"{prefix}{name}".strip()
    if from_file is not None:
        head = f"{head} {from_file}"

    if r1 == r2:
        return f"{head} bình {file_number(c2, is_red)}"

    # Đỏ tiến = row giảm; Đen tiến = row tăng
    moving_forward = (r2 < r1) if is_red else (r2 > r1)
    verb = "tấn" if moving_forward else "thoái"

    if piece.upper() in DIAGONAL_PIECES:
        target = file_number(c2, is_red)
    else:
        target = abs(r2 - r1)

    return f"{head} {verb} {target}"
