"""
Sinh báo cáo trận đấu làm khung script video.

Xem lại cả trận 100 nước để tìm chỗ đáng nói mất rất nhiều thời gian. Module này rút sẵn
những thứ dựng video cần: ai thắng thế nào, ai chính xác hơn, ba nước hỏng nặng nhất, và
điểm xoay chuyển trận (nơi thế cờ đảo chiều mạnh nhất) để làm hook mở đầu.
"""

from engine.analysis.move_quality_scorer import QUALITY_LABELS_VI

TOP_BLUNDER_COUNT = 3
# Engine quy thế chiếu bí về khoảng ±30000; loại các giá trị này khi tìm điểm xoay chuyển
# vì nước dẫn tới chiếu bí luôn có độ lệch lớn nhất và sẽ che mất các bước ngoặt thật sự
MATE_SCORE_THRESHOLD = 20000

RESULT_TEXT_VI = {
    "checkmate": "chiếu bí",
    "stalemate": "hết nước đi",
    "king_captured": "mất tướng",
    "draw_60_moves": "hoà do 60 nước không ăn quân",
    "draw_repetition": "hoà do lặp thế cờ 3 lần",
    "draw_perpetual_check": "hoà do nghi vấn chiếu liên tục",
}

STOPPED_TEXT_VI = {
    "move_limit": "dừng vì đạt giới hạn nước",
    "cost_budget": "dừng vì hết ngân sách chi phí",
}


def _side_name(match, side):
    return match["red_name"] if side == 'w' else match["black_name"]


def find_top_blunders(moves, limit=TOP_BLUNDER_COUNT):
    """Các nước mất nhiều điểm nhất — phần 'phân tích sai lầm' của video."""
    scored = [move for move in moves if move.get("cp_loss") is not None]
    return sorted(scored, key=lambda move: move["cp_loss"], reverse=True)[:limit]


def find_turning_point(moves):
    """
    Nước làm thế cờ đảo chiều mạnh nhất — dùng làm hook mở đầu và ảnh thumbnail.

    Khác với 'nước mất nhiều điểm nhất': ở đây tìm chỗ ƯU THẾ ĐỔI CHỦ (từ bên này sang bên
    kia), vì một nước dở trong thế đã thua không phải bước ngoặt.
    """
    best_move = None
    best_swing = 0

    for move in moves:
        cp_before, cp_after = move.get("cp_before"), move.get("cp_after")
        if cp_before is None or cp_after is None:
            continue
        if abs(cp_before) > MATE_SCORE_THRESHOLD or abs(cp_after) > MATE_SCORE_THRESHOLD:
            continue
        # Đảo dấu: cả hai đều theo góc nhìn người đi, nên đổi chủ nghĩa là đổi dấu
        if cp_before <= 0 or cp_after >= 0:
            continue
        swing = cp_before - cp_after
        if swing > best_swing:
            best_swing, best_move = swing, move

    return best_move


def summarize_accuracy(moves):
    """Độ chính xác trung bình và số nước theo từng nhãn chất lượng, cho mỗi bên."""
    summary = {}
    for side in ('w', 'b'):
        side_moves = [move for move in moves if move["side"] == side]
        scored = [move for move in side_moves if move.get("accuracy") is not None]
        counts = {}
        for move in side_moves:
            if move.get("quality"):
                counts[move["quality"]] = counts.get(move["quality"], 0) + 1
        summary[side] = {
            "moves": len(side_moves),
            "accuracy": round(sum(m["accuracy"] for m in scored) / len(scored), 1) if scored else None,
            "quality_counts": counts,
            "illegal_attempts": sum(max(0, len(m.get("attempts") or []) - 1) for m in side_moves),
            "avg_latency_s": round(
                sum(m.get("latency_ms") or 0 for m in side_moves) / len(side_moves) / 1000, 1
            ) if side_moves else 0,
            "cost_usd": round(sum(m.get("cost_usd") or 0 for m in side_moves), 4),
        }
    return summary


def build_report(match, moves):
    """Trả về dict dữ liệu báo cáo (dùng cho Markdown hoặc API)."""
    accuracy = summarize_accuracy(moves)
    return {
        "match": match,
        "accuracy": accuracy,
        "top_blunders": find_top_blunders(moves),
        "turning_point": find_turning_point(moves),
        "total_plies": len(moves),
    }


def render_markdown(match, moves):
    """Báo cáo dạng Markdown — dán thẳng vào script video."""
    report = build_report(match, moves)
    accuracy = report["accuracy"]
    red, black = match["red_name"], match["black_name"]

    lines = [
        f"# {red} (Đỏ) vs {black} (Đen)",
        "",
        f"- **Kết quả:** {_describe_result(match)}",
        f"- **Số nước:** {report['total_plies']}",
        "",
        "## Độ chính xác",
        "",
        "| Kỳ thủ | Độ chính xác | Nước hay nhất | Sai | Blunder | Sai luật | Nghĩ TB | Chi phí |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for side, name in (('w', red), ('b', black)):
        side_stats = accuracy[side]
        counts = side_stats["quality_counts"]
        lines.append(
            f"| {name} | {side_stats['accuracy'] or '—'}% | {counts.get('best', 0)} | "
            f"{counts.get('mistake', 0)} | {counts.get('blunder', 0)} | "
            f"{side_stats['illegal_attempts']} | {side_stats['avg_latency_s']}s | "
            f"${side_stats['cost_usd']:.4f} |"
        )

    turning_point = report["turning_point"]
    lines += ["", "## Điểm xoay chuyển trận (dùng làm hook mở đầu)", ""]
    if turning_point:
        lines.append(
            f"Nước #{turning_point['ply']} — **{_side_name(match, turning_point['side'])}** đi "
            f"`{turning_point['vi_notation']}` ({turning_point['ucci']}): thế cờ từ "
            f"{turning_point['cp_before'] / 100:+.1f} đảo thành "
            f"{turning_point['cp_after'] / 100:+.1f} quân."
        )
        if turning_point.get("engine_bestmove"):
            lines.append(f"Engine khuyên đi `{turning_point['engine_bestmove']}`.")
    else:
        lines.append("Không có nước nào làm ưu thế đổi chủ — trận diễn ra một chiều.")

    lines += ["", "## Ba nước hỏng nặng nhất", ""]
    if report["top_blunders"]:
        for rank, move in enumerate(report["top_blunders"], start=1):
            label = QUALITY_LABELS_VI.get(move.get("quality"), move.get("quality") or "")
            # Nước để đối phương chiếu bí có cp_loss ~30000 — con số đó vô nghĩa với người
            # xem, nói thẳng "dẫn tới thế chiếu bí" thì rõ hơn
            cost_text = ("**dẫn tới thế chiếu bí**" if move["cp_loss"] > MATE_SCORE_THRESHOLD
                         else f"mất **{move['cp_loss']} điểm**")
            lines.append(
                f"{rank}. Nước #{move['ply']} — {_side_name(match, move['side'])} đi "
                f"`{move['vi_notation']}` {cost_text} {label}"
                + (f", engine khuyên `{move['engine_bestmove']}`" if move.get("engine_bestmove") else "")
            )
            if move.get("analysis"):
                lines.append(f"   > AI giải thích: {move['analysis']}")
    else:
        lines.append("Trận này chưa được chấm điểm (chạy khi chưa cài engine).")

    lines += ["", "## Gợi ý tiêu đề", ""]
    lines += [f"- {title}" for title in _suggest_titles(match, report)]
    return "\n".join(lines)


def _describe_result(match):
    reason = RESULT_TEXT_VI.get(match.get("result_reason"), match.get("result_reason") or "chưa xong")
    if match.get("stopped_reason"):
        return f"{STOPPED_TEXT_VI.get(match['stopped_reason'], match['stopped_reason'])}"
    if match.get("status") == "draw":
        return f"Hoà — {reason}"
    if match.get("status") == "red_win":
        return f"{match['red_name']} thắng — {reason}"
    if match.get("status") == "black_win":
        return f"{match['black_name']} thắng — {reason}"
    return reason


def _suggest_titles(match, report):
    red, black = match["red_name"], match["black_name"]
    accuracy = report["accuracy"]
    titles = [f"{red} vs {black} — ai chơi cờ tướng giỏi hơn?"]

    red_accuracy, black_accuracy = accuracy['w']["accuracy"], accuracy['b']["accuracy"]
    if red_accuracy is not None and black_accuracy is not None:
        winner, loser = ((red, black) if red_accuracy >= black_accuracy else (black, red))
        high, low = max(red_accuracy, black_accuracy), min(red_accuracy, black_accuracy)
        titles.append(f"{winner} chính xác {high}%, {loser} chỉ {low}% — chênh lệch rõ rệt")

    blunders = (accuracy['w']["quality_counts"].get("blunder", 0)
                + accuracy['b']["quality_counts"].get("blunder", 0))
    if blunders:
        titles.append(f"{blunders} nước blunder trong một ván AI đấu AI")
    if match.get("result_reason") == "checkmate":
        titles.append(f"Chiếu bí sau {report['total_plies']} nước!")
    return titles
