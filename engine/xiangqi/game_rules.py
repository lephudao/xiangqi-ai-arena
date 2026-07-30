"""
Xác định trạng thái kết thúc trận: chiếu bí, hết nước, mất tướng, và các luật hoà.

Lưu ý luật cờ tướng khác cờ vua: bên tới lượt mà KHÔNG còn nước đi hợp lệ thì THUA
(gọi là "hết nước" / 困斃), không phải hoà như stalemate trong cờ vua.
"""

from dataclasses import dataclass

from engine.xiangqi.attack_detection import find_king, is_in_check
from engine.xiangqi.move_generation import generate_legal_move_tuples

# Số nước đơn (half-move) không ăn quân thì xử hoà: 60 nước đôi = 120 nước đơn
HALFMOVE_DRAW_LIMIT = 120
REPETITION_DRAW_LIMIT = 3

STATUS_ONGOING = "ongoing"
STATUS_RED_WIN = "red_win"
STATUS_BLACK_WIN = "black_win"
STATUS_DRAW = "draw"


@dataclass
class GameResult:
    status: str            # ongoing | red_win | black_win | draw
    winner_side: str = None  # 'w' | 'b' | None
    reason: str = STATUS_ONGOING

    @property
    def is_over(self):
        return self.status != STATUS_ONGOING


def _win_for(side, reason):
    status = STATUS_RED_WIN if side == 'w' else STATUS_BLACK_WIN
    return GameResult(status=status, winner_side=side, reason=reason)


def evaluate_position(board):
    """
    Đánh giá trạng thái bàn cờ ở lượt hiện tại (board.turn là bên sắp đi).
    """
    side = board.turn
    opponent = 'b' if side == 'w' else 'w'

    # Mất tướng — lưới an toàn: sau khi sửa lọc nước đi thì tình huống này không nên xảy ra
    if find_king(board.grid, side) is None:
        return _win_for(opponent, "king_captured")
    if find_king(board.grid, opponent) is None:
        return _win_for(side, "king_captured")

    if not generate_legal_move_tuples(board, side):
        if is_in_check(board.grid, side):
            return _win_for(opponent, "checkmate")     # chiếu bí
        return _win_for(opponent, "stalemate")          # hết nước — bên tới lượt THUA

    if board.halfmove_clock >= HALFMOVE_DRAW_LIMIT:
        return GameResult(status=STATUS_DRAW, reason="draw_60_moves")

    if board.repetition_counts.get(board.position_key(), 0) >= REPETITION_DRAW_LIMIT:
        # Luật Á Châu đầy đủ xử bên chiếu/vây bắt liên tục là THUA. Bản này đơn giản hoá
        # thành hoà; cờ cảnh báo dưới đây để log lại trường hợp nghi vấn.
        reason = "draw_perpetual_check" if is_in_check(board.grid, side) else "draw_repetition"
        return GameResult(status=STATUS_DRAW, reason=reason)

    return GameResult(status=STATUS_ONGOING)
