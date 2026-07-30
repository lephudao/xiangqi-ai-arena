"""
Chấm điểm chất lượng nước đi bằng centipawn loss, và tính accuracy % cho từng kỳ thủ.

Đây là phần biến trận đấu thành nội dung đo được: "Claude chơi chính xác 91%, mắc 2 nước
blunder" hấp dẫn hơn nhiều so với "Claude thắng".

CẢNH BÁO VỀ DẤU: engine trả điểm theo góc nhìn BÊN TỚI LƯỢT. Sau khi một bên đi xong thì
lượt thuộc về đối phương, nên điểm của thế cờ mới phải ĐẢO DẤU trước khi so sánh.
"""

import math
from dataclasses import dataclass

# Ngưỡng centipawn loss -> nhãn chất lượng (đơn vị: centipawn)
QUALITY_BEST = "best"
QUALITY_GOOD = "good"
QUALITY_FAIR = "fair"
QUALITY_INACCURACY = "inaccuracy"
QUALITY_MISTAKE = "mistake"
QUALITY_BLUNDER = "blunder"

QUALITY_LABELS_VI = {
    QUALITY_BEST: "⭐ NƯỚC HAY NHẤT",
    QUALITY_GOOD: "✅ Tốt",
    QUALITY_FAIR: "🟢 Khá",
    QUALITY_INACCURACY: "🟡 Thiếu chính xác",
    QUALITY_MISTAKE: "🟠 SAI NƯỚC",
    QUALITY_BLUNDER: "🔴 BLUNDER!",
}

# (ngưỡng cp_loss tối đa, nhãn) — xét theo thứ tự
QUALITY_THRESHOLDS = (
    (30, QUALITY_GOOD),
    (90, QUALITY_FAIR),
    (200, QUALITY_INACCURACY),
    (500, QUALITY_MISTAKE),
)


@dataclass
class MoveEvaluation:
    """Điểm chấm cho một nước đi, tất cả theo góc nhìn của người vừa đi."""

    cp_before: int = 0
    cp_after: int = 0
    cp_loss: int = 0
    quality: str = QUALITY_GOOD
    accuracy: float = 100.0
    engine_bestmove: str = ""
    engine_pv: list = None
    depth: int = 0

    @property
    def quality_label_vi(self):
        return QUALITY_LABELS_VI.get(self.quality, self.quality)

    def to_dict(self):
        return {
            "cp_before": self.cp_before,
            "cp_after": self.cp_after,
            "cp_loss": self.cp_loss,
            "quality": self.quality,
            "quality_label": self.quality_label_vi,
            "accuracy": round(self.accuracy, 1),
            "engine_bestmove": self.engine_bestmove,
            "engine_pv": self.engine_pv or [],
            "depth": self.depth,
        }


def win_percentage(centipawns):
    """
    Quy đổi centipawn thành xác suất thắng (0-100) — thang đo dễ hiểu với người xem hơn cp.
    Dùng mô hình logistic quen thuộc trong giới cờ.
    """
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * centipawns)) - 1)


def move_accuracy(cp_before, cp_after):
    """Độ chính xác của một nước (0-100), suy từ mức sụt xác suất thắng."""
    win_drop = win_percentage(cp_before) - win_percentage(cp_after)
    if win_drop <= 0:
        return 100.0
    raw = 103.1668 * math.exp(-0.04354 * win_drop) - 3.1669
    return max(0.0, min(100.0, raw))


def classify_move(cp_loss, played_move=None, engine_bestmove=None):
    """Gán nhãn chất lượng. Trùng nước engine khuyên -> nhãn cao nhất."""
    if played_move and engine_bestmove and played_move == engine_bestmove:
        return QUALITY_BEST
    for threshold, label in QUALITY_THRESHOLDS:
        if cp_loss < threshold:
            return label
    return QUALITY_BLUNDER


def score_move(engine, fen_before, fen_after, played_move, movetime_ms=None):
    """
    Chấm một nước đi bằng 2 lần phân tích: thế trước khi đi và thế sau khi đi.

    Gọi SAU khi nước đi đã thực hiện, để không làm chậm quyết định của AI.
    Trả None nếu engine không dùng được (hệ thống vẫn chạy trận bình thường).
    """
    if engine is None or not engine.is_available:
        return None

    eval_before = engine.analyse(fen_before, movetime_ms)
    eval_after = engine.analyse(fen_after, movetime_ms)
    if eval_before is None or eval_after is None:
        return None

    # eval_after tính theo góc nhìn đối phương (họ vừa được trao lượt) -> đảo dấu
    cp_before = eval_before.cp
    cp_after = -eval_after.cp
    cp_loss = max(0, cp_before - cp_after)

    return MoveEvaluation(
        cp_before=cp_before,
        cp_after=cp_after,
        cp_loss=cp_loss,
        quality=classify_move(cp_loss, played_move, eval_before.bestmove),
        accuracy=move_accuracy(cp_before, cp_after),
        engine_bestmove=eval_before.bestmove,
        engine_pv=eval_before.pv[:6],
        depth=eval_before.depth,
    )


def average_accuracy(evaluations):
    """Accuracy trung bình của một kỳ thủ qua các nước đã chấm được."""
    scored = [item for item in evaluations if item is not None]
    if not scored:
        return None
    return sum(item.accuracy for item in scored) / len(scored)
