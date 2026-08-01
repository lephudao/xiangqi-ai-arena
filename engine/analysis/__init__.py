"""Tầng phân tích: dùng Pikafish chấm điểm chất lượng nước đi của các AI."""

from engine.analysis.move_quality_scorer import (
    MoveEvaluation,
    QUALITY_LABELS_VI,
    average_accuracy,
    classify_move,
    move_accuracy,
    score_move,
    win_percentage,
)
__all__ = [
    "PikafishEngine", "EngineEval", "MATE_SCORE",
    "MoveEvaluation", "score_move", "classify_move", "move_accuracy",
    "win_percentage", "average_accuracy", "QUALITY_LABELS_VI",
]

_PIKAFISH_NAMES = {"PikafishEngine", "EngineEval", "MATE_SCORE"}


def __getattr__(name):
    """
    Nạp lười phần cần Pikafish.

    Pikafish chạy bằng subprocess nên không tồn tại trong trình duyệt. Nạp lười để bản
    đóng gói cho web khỏi phải kèm theo module không bao giờ chạy được, trong khi mã máy
    chủ vẫn `from engine.analysis import PikafishEngine` như cũ.

    Phần chấm điểm thuần toán (move_quality_scorer) vẫn nạp thẳng vì chạy được cả hai nơi.
    """
    if name in _PIKAFISH_NAMES:
        from engine.analysis import pikafish_engine
        return getattr(pikafish_engine, name)
    raise AttributeError(f"module {__name__!r} không có thuộc tính {name!r}")
