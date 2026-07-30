"""Test sinh báo cáo trận làm khung script video."""

from engine.reporting.match_report_builder import (
    build_report,
    find_top_blunders,
    find_turning_point,
    render_markdown,
    summarize_accuracy,
)


def _move(ply, side, cp_before, cp_after, cp_loss, quality="good", accuracy=90.0, **extra):
    move = {
        "ply": ply, "side": side, "ucci": "h2e2", "vi_notation": f"Nước {ply}",
        "cp_before": cp_before, "cp_after": cp_after, "cp_loss": cp_loss,
        "quality": quality, "accuracy": accuracy, "engine_bestmove": "c3c4",
        "attempts": ["h2e2"], "latency_ms": 5000, "cost_usd": 0.003, "analysis": "",
    }
    move.update(extra)
    return move


MATCH = {
    "red_name": "Claude Haiku 4.5", "black_name": "Gemini 3.6 Flash",
    "status": "red_win", "result_reason": "checkmate", "stopped_reason": None,
}


def test_top_blunders_sorted_by_points_lost():
    moves = [
        _move(1, 'w', 20, 10, 10),
        _move(2, 'b', 10, -600, 610, quality="blunder"),
        _move(3, 'w', 50, -250, 300, quality="mistake"),
        _move(4, 'b', 0, -900, 900, quality="blunder"),
    ]
    worst = find_top_blunders(moves)
    assert [move["ply"] for move in worst] == [4, 2, 3]


def test_top_blunders_ignores_unscored_moves():
    moves = [_move(1, 'w', 0, 0, None, quality=None, accuracy=None), _move(2, 'b', 0, -300, 300)]
    assert [move["ply"] for move in find_top_blunders(moves)] == [2]


def test_turning_point_requires_advantage_to_change_hands():
    """
    Nước dở trong thế đã thua không phải bước ngoặt — chỉ tính khi ưu thế ĐỔI CHỦ.
    """
    moves = [
        # Đang thua nặng rồi đi dở thêm: mất nhiều điểm nhưng không đổi chủ
        _move(1, 'w', -400, -900, 500, quality="blunder"),
        # Đang thắng thì đi hỏng, ưu thế chuyển sang đối phương -> đây mới là bước ngoặt
        _move(2, 'b', 300, -200, 500, quality="blunder"),
    ]
    turning_point = find_turning_point(moves)
    assert turning_point["ply"] == 2


def test_turning_point_picks_largest_swing():
    moves = [
        _move(1, 'w', 100, -50, 150),
        _move(2, 'b', 500, -400, 900),
        _move(3, 'w', 80, -20, 100),
    ]
    assert find_turning_point(moves)["ply"] == 2


def test_turning_point_ignores_mate_scores():
    """Nước dẫn tới chiếu bí luôn có độ lệch lớn nhất, sẽ che mất bước ngoặt thật."""
    moves = [
        _move(1, 'w', 200, -150, 350),
        _move(2, 'b', 100, -29800, 29900, quality="blunder"),
    ]
    assert find_turning_point(moves)["ply"] == 1


def test_no_turning_point_in_one_sided_match():
    moves = [_move(1, 'w', 300, 250, 50), _move(2, 'b', -250, -400, 150)]
    assert find_turning_point(moves) is None


def test_accuracy_summary_counts_per_side():
    moves = [
        _move(1, 'w', 0, 0, 0, quality="best", accuracy=100.0),
        _move(2, 'b', 0, -700, 700, quality="blunder", accuracy=5.0),
        _move(3, 'w', 0, -50, 50, quality="fair", accuracy=80.0),
        _move(4, 'b', 0, -20, 20, quality="good", accuracy=95.0, attempts=["xxxx", "h2e2"]),
    ]
    summary = summarize_accuracy(moves)

    assert summary['w']["moves"] == 2
    assert summary['w']["accuracy"] == 90.0
    assert summary['w']["quality_counts"]["best"] == 1
    assert summary['b']["quality_counts"]["blunder"] == 1
    # attempts có 2 phần tử -> 1 lần đi sai luật
    assert summary['b']["illegal_attempts"] == 1
    assert summary['w']["illegal_attempts"] == 0


def test_report_markdown_contains_key_sections():
    moves = [
        _move(1, 'w', 0, 0, 0, quality="best", accuracy=100.0),
        _move(2, 'b', 400, -300, 700, quality="blunder", accuracy=5.0,
              analysis="Tôi đánh giá sai sức mạnh của Xe đối phương"),
    ]
    markdown = render_markdown(MATCH, moves)

    assert "Claude Haiku 4.5" in markdown
    assert "Điểm xoay chuyển trận" in markdown
    assert "Ba nước hỏng nặng nhất" in markdown
    assert "Gợi ý tiêu đề" in markdown
    assert "700 điểm" in markdown
    assert "Tôi đánh giá sai sức mạnh" in markdown, "phải kèm lời AI tự giải thích"
    assert "thắng — chiếu bí" in markdown


def test_report_handles_match_without_scoring():
    """Trận chạy khi chưa cài engine: không có điểm chấm nhưng vẫn phải ra báo cáo."""
    moves = [
        {"ply": 1, "side": 'w', "ucci": "h2e2", "vi_notation": "Pháo 2 bình 5",
         "cp_before": None, "cp_after": None, "cp_loss": None, "quality": None,
         "accuracy": None, "attempts": [], "latency_ms": 0, "cost_usd": 0},
    ]
    report = build_report(MATCH, moves)
    assert report["top_blunders"] == []
    assert report["turning_point"] is None

    markdown = render_markdown(MATCH, moves)
    assert "chưa được chấm điểm" in markdown


def test_stopped_match_reports_stop_reason():
    match = dict(MATCH, status="ongoing", result_reason="ongoing", stopped_reason="move_limit")
    markdown = render_markdown(match, [_move(1, 'w', 0, 0, 0)])
    assert "giới hạn nước" in markdown


def test_mate_blunder_is_described_not_numbered():
    """cp_loss ~30000 là điểm quy ước cho chiếu bí, in ra con số đó vô nghĩa với người xem."""
    moves = [_move(1, 'w', 100, -29800, 29900, quality="blunder", accuracy=0.0)]
    markdown = render_markdown(MATCH, moves)

    assert "dẫn tới thế chiếu bí" in markdown
    assert "29900 điểm" not in markdown
