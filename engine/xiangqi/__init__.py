"""Engine cờ tướng: bàn cờ, sinh nước đi, phát hiện chiếu, luật kết thúc trận."""

from engine.xiangqi.attack_detection import find_king, is_in_check, is_square_attacked, kings_facing
from engine.xiangqi.board import INITIAL_FEN, XiangqiBoard
from engine.xiangqi.game_rules import (
    GameResult,
    STATUS_BLACK_WIN,
    STATUS_DRAW,
    STATUS_ONGOING,
    STATUS_RED_WIN,
    evaluate_position,
)
from engine.xiangqi.notation import (
    parse_ucci_move,
    pos_to_ucci,
    to_vietnamese_notation,
    ucci_to_pos,
)

__all__ = [
    "XiangqiBoard", "INITIAL_FEN",
    "GameResult", "evaluate_position",
    "STATUS_ONGOING", "STATUS_RED_WIN", "STATUS_BLACK_WIN", "STATUS_DRAW",
    "is_in_check", "is_square_attacked", "kings_facing", "find_king",
    "ucci_to_pos", "pos_to_ucci", "parse_ucci_move", "to_vietnamese_notation",
]
