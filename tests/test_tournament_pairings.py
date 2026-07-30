"""Test sinh cặp đấu cho giải vòng tròn."""

import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "run_matches", pathlib.Path(__file__).parent.parent / "scripts" / "run_matches.py"
)
run_matches = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_matches)


def test_every_pair_plays_both_colours():
    """Đỏ đi trước có lợi nên mỗi cặp bắt buộc đánh cả hai màu."""
    pairings = run_matches.round_robin_pairings(["a", "b", "c"])

    assert len(pairings) == 6          # 3 cặp x 2 lượt
    assert ("a", "b") in pairings and ("b", "a") in pairings
    assert ("a", "c") in pairings and ("c", "a") in pairings
    assert ("b", "c") in pairings and ("c", "b") in pairings


def test_no_self_pairing():
    for red, black in run_matches.round_robin_pairings(["a", "b", "c", "d"]):
        assert red != black


def test_pair_count_is_n_times_n_minus_one():
    for count in (2, 3, 4, 5):
        models = [f"m{index}" for index in range(count)]
        assert len(run_matches.round_robin_pairings(models)) == count * (count - 1)


def test_single_model_has_no_match():
    assert run_matches.round_robin_pairings(["a"]) == []
