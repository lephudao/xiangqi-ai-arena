"""
Test tích hợp Pikafish. Bỏ qua nếu chưa cài engine (./scripts/install-pikafish.sh).
"""

import pytest

from engine.analysis import MATE_SCORE, PikafishEngine
from engine.analysis.pikafish_engine import _mate_to_cp

OPENING_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
# Đỏ có 2 Xe, Đen chỉ còn Tướng trơ trọi -> Đỏ thắng chắc
RED_CRUSHING_FEN = "3k5/9/9/9/9/9/9/9/R8/R3K4"


@pytest.fixture(scope="module")
def engine():
    instance = PikafishEngine(movetime_ms=200)
    if not instance.is_available:
        pytest.skip(f"Pikafish chưa cài: {instance.unavailable_reason}")
    yield instance
    instance.close()


def test_missing_binary_degrades_gracefully():
    """Thiếu engine phải trả về không khả dụng, không được raise — trận vẫn phải chạy được."""
    broken = PikafishEngine(engine_path="/duong/dan/khong/ton/tai/pikafish")
    assert broken.is_available is False
    assert "Không tìm thấy engine" in broken.unavailable_reason
    assert broken.analyse(OPENING_FEN) is None


def test_mate_score_conversion():
    assert _mate_to_cp(0) == -MATE_SCORE           # đang bị bí
    assert _mate_to_cp(3) == MATE_SCORE - 300      # sắp thắng
    assert _mate_to_cp(-3) == -(MATE_SCORE - 300)  # sắp bị bí
    assert _mate_to_cp(1) > _mate_to_cp(5)         # bí nhanh hơn thì tốt hơn


def test_analyse_opening_position(engine):
    result = engine.analyse(OPENING_FEN)
    assert result is not None
    assert result.depth >= 8, "200ms phải đạt độ sâu hợp lý"
    assert result.bestmove, "phải trả về nước đi tốt nhất"
    assert abs(result.cp) < 150, f"khai cuộc phải gần cân bằng, nhận cp={result.cp}"
    assert result.pv, "phải có biến chính (principal variation)"


def test_score_sign_follows_side_to_move(engine):
    """
    Test then chốt: điểm engine tính theo góc nhìn BÊN TỚI LƯỢT.
    Cùng một thế Đỏ áp đảo, Đỏ đi thì điểm dương, Đen đi thì điểm âm.
    """
    red_to_move = engine.analyse(f"{RED_CRUSHING_FEN} w - - 0 1")
    black_to_move = engine.analyse(f"{RED_CRUSHING_FEN} b - - 0 1")

    assert red_to_move.cp > 300, f"Đỏ áp đảo và tới lượt Đỏ -> điểm dương lớn, nhận {red_to_move.cp}"
    assert black_to_move.cp < -300, f"Đen tới lượt trong thế thua -> điểm âm lớn, nhận {black_to_move.cp}"


def test_detects_checkmate(engine):
    """Tướng Đen d9 bị Xe d0 chiếu, không có ô thoát (e9 lộ mặt tướng, c9 ngoài cung)."""
    result = engine.analyse("3k5/9/9/9/9/9/9/9/9/R2RK4 b - - 0 1")
    assert result.is_mate
    assert result.cp <= -MATE_SCORE + 1000, "bên bị bí phải có điểm rất âm"
