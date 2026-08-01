"""Tầng lưu trữ: SQLite cho trận đấu, nước đi, và bảng xếp hạng Elo."""

from engine.storage.elo_rating import (
    K_FACTOR,
    STARTING_ELO,
    expected_score,
    score_from_result,
    update_ratings,
)
__all__ = [
    "MatchRepository", "DEFAULT_DB_PATH",
    "STARTING_ELO", "K_FACTOR", "expected_score", "update_ratings", "score_from_result",
]

_SQLITE_NAMES = {"MatchRepository", "DEFAULT_DB_PATH"}


def __getattr__(name):
    """
    Nạp lười phần dùng SQLite.

    Bản online không lưu nước đi (không có chức năng xem lại), chỉ cần công thức Elo để
    giữ bảng xếp hạng trong localStorage. Nạp lười để bundle web khỏi kèm tầng SQLite.
    """
    if name in _SQLITE_NAMES:
        from engine.storage import match_repository
        return getattr(match_repository, name)
    raise AttributeError(f"module {__name__!r} không có thuộc tính {name!r}")
