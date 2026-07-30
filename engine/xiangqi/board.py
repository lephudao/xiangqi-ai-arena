"""
Trạng thái bàn cờ tướng: nạp/xuất FEN, thực hiện nước đi, và các chỉ số phục vụ luật hoà.

`make_raw_move` / `unmake_raw_move` là cặp thao tác nhẹ dùng để THỬ nước đi khi lọc
nước hợp lệ và khi chấm điểm bằng engine (Phase 2) — không đổi lượt, không đổi bộ đếm.
`push_ucci` là nước đi thật: có kiểm tra hợp lệ, đổi lượt, cập nhật bộ đếm.
"""

from engine.xiangqi.attack_detection import is_in_check
from engine.xiangqi.game_rules import evaluate_position
from engine.xiangqi.move_generation import generate_legal_moves
from engine.xiangqi.notation import (
    BOARD_COLS,
    BOARD_ROWS,
    parse_ucci_move,
    to_vietnamese_notation,
)

INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


class XiangqiBoard:
    def __init__(self, fen=INITIAL_FEN):
        self.grid = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.turn = 'w'
        self.move_number = 1
        self.halfmove_clock = 0
        self.move_history = []        # nhật ký nước đi thật
        self.repetition_counts = {}
        self._raw_undo_stack = []     # ngăn xếp phục hồi cho make_raw_move
        self.load_fen(fen)

    # --- FEN ---

    def load_fen(self, fen):
        parts = fen.strip().split()
        self.grid = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
        for row, row_str in enumerate(parts[0].split('/')):
            col = 0
            for char in row_str:
                if char.isdigit():
                    col += int(char)
                else:
                    self.grid[row][col] = char
                    col += 1

        self.turn = parts[1] if len(parts) > 1 else 'w'
        self.halfmove_clock = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
        self.move_number = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 1
        self.repetition_counts = {self.position_key(): 1}

    def board_fen(self):
        rows = []
        for row in range(BOARD_ROWS):
            row_str = ""
            empty = 0
            for col in range(BOARD_COLS):
                piece = self.grid[row][col]
                if piece is None:
                    empty += 1
                    continue
                if empty:
                    row_str += str(empty)
                    empty = 0
                row_str += piece
            if empty:
                row_str += str(empty)
            rows.append(row_str)
        return "/".join(rows)

    def to_fen(self):
        return f"{self.board_fen()} {self.turn} - - {self.halfmove_clock} {self.move_number}"

    def position_key(self):
        """Khoá nhận dạng thế cờ (bàn + bên đi) dùng để phát hiện lặp nước."""
        return f"{self.board_fen()} {self.turn}"

    # --- Thử nước đi (không đổi lượt) ---

    def make_raw_move(self, r1, c1, r2, c2):
        captured = self.grid[r2][c2]
        self._raw_undo_stack.append((r1, c1, r2, c2, self.grid[r1][c1], captured))
        self.grid[r2][c2] = self.grid[r1][c1]
        self.grid[r1][c1] = None
        return captured

    def unmake_raw_move(self):
        r1, c1, r2, c2, moving_piece, captured = self._raw_undo_stack.pop()
        self.grid[r1][c1] = moving_piece
        self.grid[r2][c2] = captured

    # --- Nước đi thật ---

    def push_ucci(self, ucci):
        """Thực hiện nước đi. Trả (success, message)."""
        parsed = parse_ucci_move(ucci)
        if parsed is None:
            return False, f"Ký hiệu UCCI không hợp lệ: '{ucci}' (cần 4 ký tự, ví dụ h2e2)"

        r1, c1, r2, c2 = parsed
        if self.grid[r1][c1] is None:
            return False, f"Không có quân nào ở ô {ucci[:2]}"

        if ucci not in self.generate_legal_moves(self.turn):
            return False, self.explain_illegal_move(ucci)

        vi_notation = to_vietnamese_notation(self.grid, ucci)
        captured = self.make_raw_move(r1, c1, r2, c2)
        self._raw_undo_stack.pop()  # nước đi thật: không cần phục hồi

        self.halfmove_clock = 0 if captured else self.halfmove_clock + 1
        if self.turn == 'b':
            self.move_number += 1
        self.turn = 'b' if self.turn == 'w' else 'w'

        key = self.position_key()
        self.repetition_counts[key] = self.repetition_counts.get(key, 0) + 1

        self.move_history.append({
            'ucci': ucci,
            'vi_notation': vi_notation,
            'captured': captured,
            'halfmove_clock': self.halfmove_clock,
        })
        return True, vi_notation

    def explain_illegal_move(self, ucci):
        """Lý do cụ thể một nước không hợp lệ — dùng làm feedback khi cho AI đi lại."""
        parsed = parse_ucci_move(ucci)
        if parsed is None:
            return f"'{ucci}' không đúng định dạng UCCI 4 ký tự"

        r1, c1, r2, c2 = parsed
        piece = self.grid[r1][c1]
        if piece is None:
            return f"Ô {ucci[:2]} không có quân nào"
        if (piece.isupper() and self.turn == 'b') or (piece.islower() and self.turn == 'w'):
            return f"Quân ở {ucci[:2]} không thuộc bên đang đi"

        from engine.xiangqi.move_generation import generate_pseudo_moves
        if (r1, c1, r2, c2) not in generate_pseudo_moves(self.grid, self.turn):
            return f"Quân {piece} không thể đi từ {ucci[:2]} tới {ucci[2:]} theo luật di chuyển"

        # Hợp lệ về hình học nhưng để tướng mình bị nguy
        self.make_raw_move(r1, c1, r2, c2)
        exposes_check = is_in_check(self.grid, self.turn)
        self.unmake_raw_move()
        if exposes_check:
            return f"Nước {ucci} để Tướng bên bạn bị chiếu"
        return f"Nước {ucci} làm hai Tướng lộ mặt nhau (bị cấm)"

    # --- Truy vấn ---

    def generate_legal_moves(self, side=None):
        return generate_legal_moves(self, side or self.turn)

    def is_in_check(self, side=None):
        return is_in_check(self.grid, side or self.turn)

    def evaluate_result(self):
        return evaluate_position(self)

    def to_vietnamese_notation(self, ucci):
        return to_vietnamese_notation(self.grid, ucci)

    def material_summary(self):
        """Kiểm kê quân còn lại 2 bên — dùng cho prompt và overlay."""
        red, black = {}, {}
        for row in self.grid:
            for piece in row:
                if piece is None:
                    continue
                bucket = red if piece.isupper() else black
                key = piece.upper()
                bucket[key] = bucket.get(key, 0) + 1
        return {'red': red, 'black': black}
