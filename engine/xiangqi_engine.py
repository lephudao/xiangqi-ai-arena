"""
Xiangqi (Cờ Tướng) Board Engine
Pure Python implementation of Xiangqi rules, FEN handling, and Legal Move generation.
"""

import re

INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

PIECE_NAMES_VI = {
    'R': 'Xe (Đỏ)', 'N': 'Mã (Đỏ)', 'B': 'Tượng (Đỏ)', 'A': 'Sĩ (Đỏ)', 'K': 'Tướng (Đỏ)', 'C': 'Pháo (Đỏ)', 'P': 'Binh (Đỏ)',
    'r': 'Xe (Đen)', 'n': 'Mã (Đen)', 'b': 'Tượng (Đen)', 'a': 'Sĩ (Đen)', 'k': 'Tướng (Đen)', 'c': 'Pháo (Đen)', 'p': 'Tốt (Đen)'
}

def ucci_to_pos(ucci):
    """e.g. 'h2' -> (grid_row, grid_col)"""
    if len(ucci) != 2:
        return None
    col = ord(ucci[0].lower()) - ord('a')
    rank = int(ucci[1])
    if not (0 <= col <= 8 and 0 <= rank <= 9):
        return None
    grid_row = 9 - rank
    grid_col = col
    return grid_row, grid_col

def pos_to_ucci(row, col):
    """(grid_row, grid_col) -> e.g. 'h2'"""
    col_str = chr(ord('a') + col)
    rank_str = str(9 - row)
    return f"{col_str}{rank_str}"

class XiangqiBoard:
    def __init__(self, fen=INITIAL_FEN):
        self.grid = [[None]*9 for _ in range(10)]
        self.turn = 'w'  # 'w' for Red (White in FEN terms), 'b' for Black
        self.move_number = 1
        self.history = []
        self.load_fen(fen)

    def load_fen(self, fen):
        parts = fen.strip().split()
        board_part = parts[0]
        self.turn = parts[1] if len(parts) > 1 else 'w'
        
        self.grid = [[None]*9 for _ in range(10)]
        rows = board_part.split('/')
        for r, row_str in enumerate(rows):
            c = 0
            for char in row_str:
                if char.isdigit():
                    c += int(char)
                else:
                    self.grid[r][c] = char
                    c += 1

    def to_fen(self):
        rows = []
        for r in range(10):
            empty = 0
            row_str = ""
            for c in range(9):
                piece = self.grid[r][c]
                if piece is None:
                    empty += 1
                else:
                    if empty > 0:
                        row_str += str(empty)
                        empty = 0
                    row_str += piece
            if empty > 0:
                row_str += str(empty)
            rows.append(row_str)
        board_fen = "/".join(rows)
        return f"{board_fen} {self.turn} - - 0 {self.move_number}"

    def is_red(self, piece):
        return piece is not None and piece.isupper()

    def is_black(self, piece):
        return piece is not None and piece.islower()

    def is_same_side(self, piece1, piece2):
        if not piece1 or not piece2:
            return False
        return (piece1.isupper() and piece2.isupper()) or (piece1.islower() and piece2.islower())

    def in_palace(self, row, col, is_red):
        if not (3 <= col <= 5):
            return False
        if is_red:
            return 7 <= row <= 9
        else:
            return 0 <= row <= 2

    def generate_legal_moves(self, side=None):
        if side is None:
            side = self.turn
        
        pseudo_moves = []
        is_red_side = (side == 'w')

        for r in range(10):
            for c in range(9):
                piece = self.grid[r][c]
                if not piece:
                    continue
                if is_red_side and not piece.isupper():
                    continue
                if not is_red_side and not piece.islower():
                    continue

                piece_type = piece.upper()

                # --- KING / GENERAL (K) ---
                if piece_type == 'K':
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if self.in_palace(nr, nc, is_red_side):
                            target = self.grid[nr][nc]
                            if not target or not self.is_same_side(piece, target):
                                pseudo_moves.append((r, c, nr, nc))

                # --- ADVISOR / GUARD (A) ---
                elif piece_type == 'A':
                    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        nr, nc = r + dr, c + dc
                        if self.in_palace(nr, nc, is_red_side):
                            target = self.grid[nr][nc]
                            if not target or not self.is_same_side(piece, target):
                                pseudo_moves.append((r, c, nr, nc))

                # --- ELEPHANT / MINISTER (B) ---
                elif piece_type == 'B':
                    for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                        nr, nc = r + dr, c + dc
                        river_ok = (nr >= 5) if is_red_side else (nr <= 4)
                        if 0 <= nr <= 9 and 0 <= nc <= 8 and river_ok:
                            eye_r, eye_c = r + dr // 2, c + dc // 2
                            if self.grid[eye_r][eye_c] is None:
                                target = self.grid[nr][nc]
                                if not target or not self.is_same_side(piece, target):
                                    pseudo_moves.append((r, c, nr, nc))

                # --- KNIGHT / HORSE (N) ---
                elif piece_type == 'N':
                    knight_moves = [
                        (-2, -1, -1, 0), (-2, 1, -1, 0),
                        (2, -1, 1, 0),   (2, 1, 1, 0),
                        (-1, -2, 0, -1), (1, -2, 0, -1),
                        (-1, 2, 0, 1),   (1, 2, 0, 1)
                    ]
                    for dr, dc, br, bc in knight_moves:
                        nr, nc = r + dr, c + dc
                        block_r, block_c = r + br, c + bc
                        if 0 <= nr <= 9 and 0 <= nc <= 8:
                            if self.grid[block_r][block_c] is None:
                                target = self.grid[nr][nc]
                                if not target or not self.is_same_side(piece, target):
                                    pseudo_moves.append((r, c, nr, nc))

                # --- ROOK / CAR (R) ---
                elif piece_type == 'R':
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        while 0 <= nr <= 9 and 0 <= nc <= 8:
                            target = self.grid[nr][nc]
                            if target is None:
                                pseudo_moves.append((r, c, nr, nc))
                            elif self.is_same_side(piece, target):
                                break
                            else:
                                pseudo_moves.append((r, c, nr, nc))
                                break
                            nr += dr
                            nc += dc

                # --- CANNON (C) ---
                elif piece_type == 'C':
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        screen_found = False
                        while 0 <= nr <= 9 and 0 <= nc <= 8:
                            target = self.grid[nr][nc]
                            if not screen_found:
                                if target is None:
                                    pseudo_moves.append((r, c, nr, nc))
                                else:
                                    screen_found = True
                            else:
                                if target is not None:
                                    if not self.is_same_side(piece, target):
                                        pseudo_moves.append((r, c, nr, nc))
                                    break
                            nr += dr
                            nc += dc

                # --- PAWN / SOLDIER (P) ---
                elif piece_type == 'P':
                    forward_dir = -1 if is_red_side else 1
                    nr, nc = r + forward_dir, c
                    if 0 <= nr <= 9 and 0 <= nc <= 8:
                        target = self.grid[nr][nc]
                        if not target or not self.is_same_side(piece, target):
                            pseudo_moves.append((r, c, nr, nc))
                    
                    across_river = (r <= 4) if is_red_side else (r >= 5)
                    if across_river:
                        for dc in [-1, 1]:
                            nr, nc = r, c + dc
                            if 0 <= nc <= 8:
                                target = self.grid[nr][nc]
                                if not target or not self.is_same_side(piece, target):
                                    pseudo_moves.append((r, c, nr, nc))

        legal_moves = []
        for r1, c1, r2, c2 in pseudo_moves:
            if not self.leaves_kings_facing_or_checked(r1, c1, r2, c2, side):
                legal_moves.append((r1, c1, r2, c2))

        legal_ucci = [f"{pos_to_ucci(r1, c1)}{pos_to_ucci(r2, c2)}" for r1, c1, r2, c2 in legal_moves]
        return legal_ucci

    def leaves_kings_facing_or_checked(self, r1, c1, r2, c2, side):
        temp_piece = self.grid[r2][c2]
        moving_piece = self.grid[r1][c1]
        
        self.grid[r2][c2] = moving_piece
        self.grid[r1][c1] = None

        invalid = False

        red_king = None
        black_king = None
        for r in range(10):
            for c in range(9):
                p = self.grid[r][c]
                if p == 'K':
                    red_king = (r, c)
                elif p == 'k':
                    black_king = (r, c)

        if red_king and black_king:
            if red_king[1] == black_king[1]:
                c = red_king[1]
                blocked = False
                for r in range(min(red_king[0], black_king[0]) + 1, max(red_king[0], black_king[0])):
                    if self.grid[r][c] is not None:
                        blocked = True
                        break
                if not blocked:
                    invalid = True

        self.grid[r1][c1] = moving_piece
        self.grid[r2][c2] = temp_piece

        return invalid

    def push_ucci(self, ucci):
        if len(ucci) != 4:
            return False, "Ký hiệu UCCI phải gồm 4 ký tự (vd: h2e2)"
        
        pos1 = ucci_to_pos(ucci[:2])
        pos2 = ucci_to_pos(ucci[2:])

        if not pos1 or not pos2:
            return False, f"Tọa độ UCCI không hợp lệ: {ucci}"

        r1, c1 = pos1
        r2, c2 = pos2

        piece = self.grid[r1][c1]
        if not piece:
            return False, "Không có quân cờ ở ô xuất phát"

        legal_moves = self.generate_legal_moves(self.turn)
        if ucci not in legal_moves:
            return False, f"Nước đi {ucci} không đúng luật cờ tướng!"

        captured = self.grid[r2][c2]

        self.grid[r2][c2] = piece
        self.grid[r1][c1] = None

        self.history.append({
            'ucci': ucci,
            'piece': piece,
            'captured': captured,
            'turn': self.turn,
            'move_number': self.move_number
        })

        if self.turn == 'b':
            self.move_number += 1
        self.turn = 'b' if self.turn == 'w' else 'w'

        return True, "Nước đi hợp lệ"

    def move_to_vietnamese_text(self, ucci, piece=None):
        if len(ucci) != 4:
            return ucci
        pos1 = ucci_to_pos(ucci[:2])
        pos2 = ucci_to_pos(ucci[2:])
        if not pos1 or not pos2:
            return ucci
        r1, c1 = pos1
        r2, c2 = pos2
        if not piece:
            piece = self.grid[r2][c2] or self.grid[r1][c1]
        name = PIECE_NAMES_VI.get(piece, piece)
        return f"{name} ({pos_to_ucci(r1, c1)} -> {pos_to_ucci(r2, c2)})"
