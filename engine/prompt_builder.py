"""
Dựng prompt cho AI chọn nước đi.

Prompt cũ chỉ có FEN + danh sách UCCI, nên thực chất đang đo "khả năng đọc chuỗi FEN"
hơn là "khả năng chơi cờ". Ở đây bổ sung bàn cờ ASCII, lịch sử nước đi, kiểm kê quân và
cảnh báo chiếu — những thứ một kỳ thủ thật luôn nhìn thấy.

QUAN TRỌNG VỀ TÍNH CÔNG BẰNG: mọi nhà cung cấp dùng CHUNG một template prompt, chỉ khác
cách gói request theo từng API. Nếu prompt khác nhau thì mọi so sánh giữa các AI đều vô nghĩa.
"""

from engine.xiangqi.notation import piece_display_name, to_vietnamese_notation

HISTORY_MOVES_SHOWN = 10

PIECE_LEGEND = (
    "Chữ HOA = quân ĐỎ, chữ thường = quân ĐEN. "
    "K/k=Tướng, A/a=Sĩ, B/b=Tượng, N/n=Mã, R/r=Xe, C/c=Pháo, P/p=Binh(Tốt). "
    "Dấu '.' là ô trống."
)

SYSTEM_ROLE = """Bạn là kỳ thủ Cờ Tướng đang thi đấu giải AI, cầm quân {side_label} ({side_name}).
Mục tiêu: chọn nước đi TỐT NHẤT để giành chiến thắng."""

OUTPUT_INSTRUCTIONS = """Trả về JSON với 3 trường:
- "move_ucci": đúng 1 nước đi trong danh sách nước hợp lệ ở trên (ví dụ "h2e2").
- "analysis": 2-3 câu phân tích kỹ thuật vì sao chọn nước này — ý đồ chiến thuật, nước đi
  bạn dự đoán đối phương sẽ đáp lại, và nguy hiểm bạn đang phòng ngừa.
- "taunt": 1 câu ngắn cho khán giả xem video — thể hiện cá tính (tự tin, hài hước, hoặc
  triết lý). KHÔNG giải thích kỹ thuật ở trường này."""


def render_ascii_board(grid):
    """
    Bàn cờ dạng lưới có toạ độ — LLM đọc dạng này chính xác hơn hẳn so với chuỗi FEN.
    In từ hàng 9 (hậu phương Đen) xuống hàng 0 (hậu phương Đỏ).
    """
    header = "    " + "  ".join("abcdefghi")
    lines = [header]
    for row in range(10):
        rank = 9 - row
        cells = " ".join(f"{grid[row][col] or '.':>2}" for col in range(9))
        lines.append(f"{rank}  {cells}  {rank}")
        if rank == 5:  # sông nằm giữa hàng 5 và hàng 4
            lines.append("   ~~~~~~~~~ 楚河   漢界 ~~~~~~~~~")
    lines.append(header)
    lines.append("   (hàng 0-4 là nửa sân ĐỎ, hàng 5-9 là nửa sân ĐEN)")
    return "\n".join(lines)


def _material_line(material):
    def describe(counts):
        order = ('R', 'C', 'N', 'B', 'A', 'P', 'K')
        parts = [
            f"{piece_display_name(code)} x{counts[code]}"
            for code in order if counts.get(code)
        ]
        return ", ".join(parts) if parts else "không còn quân"

    red = describe(material['red'])
    black = describe(material['black'])
    return f"- Quân Đỏ còn: {red}\n- Quân Đen còn: {black}"


def _history_lines(move_logs):
    if not move_logs:
        return "Chưa có nước nào (đây là nước đầu tiên của trận)."
    recent = move_logs[-HISTORY_MOVES_SHOWN:]
    start_ply = len(move_logs) - len(recent) + 1
    return "\n".join(
        f"{start_ply + index}. {'Đỏ ' if move['side'] == 'w' else 'Đen'}: "
        f"{move['vi_text']} [{move['ucci']}]"
        for index, move in enumerate(recent)
    )


def _annotate_captures(grid, legal_moves):
    """Đánh dấu nước ăn quân để AI thấy ngay cơ hội, thay vì phải tự suy ra từ FEN."""
    from engine.xiangqi.notation import parse_ucci_move

    annotated = []
    for move in legal_moves:
        parsed = parse_ucci_move(move)
        if parsed is None:
            annotated.append(move)
            continue
        target = grid[parsed[2]][parsed[3]]
        if target is not None:
            annotated.append(f"{move}(ăn {piece_display_name(target)})")
        else:
            annotated.append(move)
    return annotated


def build_move_prompt(board, side, legal_moves, side_name, move_logs=None, feedback=None):
    """
    Dựng prompt đầy đủ cho một lượt đi. Dùng chung cho MỌI nhà cung cấp AI.
    """
    move_logs = move_logs or []
    in_check = board.is_in_check(side)
    side_label = "ĐỎ" if side == 'w' else "ĐEN"

    sections = [
        SYSTEM_ROLE.format(side_label=side_label, side_name=side_name),
        "",
        "BÀN CỜ HIỆN TẠI:",
        render_ascii_board(board.grid),
        "",
        f"Ký hiệu: {PIECE_LEGEND}",
        f"Chuỗi FEN: {board.to_fen()}",
        "",
        "TÌNH HÌNH QUÂN:",
        _material_line(board.material_summary()),
        "",
        f"LỊCH SỬ {HISTORY_MOVES_SHOWN} NƯỚC GẦN NHẤT:",
        _history_lines(move_logs),
        "",
    ]

    if in_check:
        sections += [
            "*** CẢNH BÁO: TƯỚNG CỦA BẠN ĐANG BỊ CHIẾU! ***",
            "Nước đi của bạn BẮT BUỘC phải giải quyết được thế chiếu này.",
            "",
        ]

    sections += [
        f"CÁC NƯỚC ĐI HỢP LỆ ({len(legal_moves)} nước) — bạn BẮT BUỘC chọn 1 trong số này:",
        ", ".join(_annotate_captures(board.grid, legal_moves)),
        "",
    ]

    if feedback:
        sections += [
            "*** NƯỚC ĐI TRƯỚC CỦA BẠN BỊ TRỌNG TÀI TỪ CHỐI ***",
            f"Lý do: {feedback}",
            "Hãy chọn lại một nước khác trong danh sách hợp lệ.",
            "",
        ]

    sections.append(OUTPUT_INSTRUCTIONS)
    return "\n".join(sections)


def describe_move_for_speech(board, ucci):
    """Ký hiệu tiếng Việt của nước đi, dùng cho TTS đọc như bình luận viên."""
    return to_vietnamese_notation(board.grid, ucci)
