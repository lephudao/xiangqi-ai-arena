"""
Tính Elo cho các kỳ thủ AI.

Elo cho phép so sánh sức mạnh qua nhiều trận thay vì chỉ một ván, và tạo ra nội dung định
kỳ cho kênh ("Bảng xếp hạng AI cờ tướng tháng 8") mà không cần ý tưởng mới.
"""

STARTING_ELO = 1500.0
K_FACTOR = 32.0

SCORE_WIN = 1.0
SCORE_DRAW = 0.5
SCORE_LOSS = 0.0


def expected_score(rating, opponent_rating):
    """Xác suất thắng kỳ vọng của `rating` khi gặp `opponent_rating`."""
    return 1.0 / (1.0 + 10 ** ((opponent_rating - rating) / 400.0))


def update_ratings(red_elo, black_elo, red_score, k_factor=K_FACTOR):
    """
    Tính Elo mới cho cả hai bên sau một trận.

    `red_score`: 1.0 nếu Đỏ thắng, 0.5 nếu hoà, 0.0 nếu Đỏ thua.
    Trả (elo_đỏ_mới, elo_đen_mới). Tổng Elo được bảo toàn.
    """
    red_expected = expected_score(red_elo, black_elo)
    delta = k_factor * (red_score - red_expected)
    return red_elo + delta, black_elo - delta


def score_from_result(status, side):
    """
    Quy đổi kết quả trận thành điểm Elo cho một bên.

    Trận chưa kết thúc (`ongoing`) trả None — không được tính Elo cho trận dở dang,
    kể cả khi trận bị dừng vì hết ngân sách hoặc hết giới hạn nước.
    """
    if status == "draw":
        return SCORE_DRAW
    if status == "red_win":
        return SCORE_WIN if side == 'w' else SCORE_LOSS
    if status == "black_win":
        return SCORE_WIN if side == 'b' else SCORE_LOSS
    return None
