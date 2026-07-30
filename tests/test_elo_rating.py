"""Test tính Elo."""

import pytest

from engine.storage.elo_rating import (
    K_FACTOR,
    STARTING_ELO,
    expected_score,
    score_from_result,
    update_ratings,
)


def test_equal_ratings_expect_half():
    assert expected_score(1500, 1500) == pytest.approx(0.5)


def test_higher_rating_expects_more():
    assert expected_score(1700, 1500) > 0.5
    assert expected_score(1300, 1500) < 0.5
    # Tổng kỳ vọng của hai bên luôn bằng 1
    assert expected_score(1700, 1500) + expected_score(1500, 1700) == pytest.approx(1.0)


def test_win_between_equal_players_moves_by_half_k():
    """Hai kỳ thủ 1500 điểm, bên Đỏ thắng: mỗi bên dịch chuyển K/2 = 16 điểm."""
    new_red, new_black = update_ratings(1500, 1500, red_score=1.0)
    assert new_red == pytest.approx(1500 + K_FACTOR / 2)
    assert new_black == pytest.approx(1500 - K_FACTOR / 2)


def test_draw_between_unequal_players_favors_underdog():
    """Hoà với đối thủ mạnh hơn thì bên yếu được cộng điểm."""
    new_strong, new_weak = update_ratings(1700, 1400, red_score=0.5)
    assert new_strong < 1700
    assert new_weak > 1400


def test_total_rating_is_conserved():
    for red_score in (1.0, 0.5, 0.0):
        new_red, new_black = update_ratings(1650, 1420, red_score)
        assert new_red + new_black == pytest.approx(1650 + 1420)


def test_beating_weak_opponent_gains_little():
    strong_win, _ = update_ratings(1900, 1300, red_score=1.0)
    even_win, _ = update_ratings(1500, 1500, red_score=1.0)
    assert (strong_win - 1900) < (even_win - 1500)


def test_score_from_result_maps_both_sides():
    assert score_from_result("red_win", 'w') == 1.0
    assert score_from_result("red_win", 'b') == 0.0
    assert score_from_result("black_win", 'b') == 1.0
    assert score_from_result("black_win", 'w') == 0.0
    assert score_from_result("draw", 'w') == 0.5
    assert score_from_result("draw", 'b') == 0.5


def test_unfinished_match_has_no_score():
    """Trận dở dang (hết giới hạn nước, hết ngân sách) không được tính vào Elo."""
    assert score_from_result("ongoing", 'w') is None
    assert score_from_result("ongoing", 'b') is None


def test_starting_elo_is_standard():
    assert STARTING_ELO == 1500.0
