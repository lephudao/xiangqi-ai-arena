"""
Test bản đóng gói cho trình duyệt: cầu nối BrowserArena và nội dung file zip.

Cầu nối là Python thuần nên kiểm được bằng pytest, không cần trình duyệt. Đây là lý do
lớp glue nằm ở Python chứ không nhúng trong file JS.
"""

import subprocess
import zipfile
from pathlib import Path

import pytest

from engine.browser_bridge import BrowserArena, decision_from_payload

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE = REPO_ROOT / "web" / "vendor" / "engine-core.zip"


def _arena():
    return BrowserArena({"model_key": "mock", "name": "Đỏ"},
                        {"model_key": "mock", "name": "Đen"})


# --- Lái một lượt như JS sẽ làm ---

def test_turn_completes_with_one_legal_move():
    arena = _arena()
    request = arena.begin_turn()

    assert request["side"] == 'w'
    assert request["attempt"] == 1
    assert len(request["legal_moves"]) == 44, "thế khai cuộc có 44 nước hợp lệ"
    assert request["prompt"], "phải có prompt để JS gửi đi gọi API"

    assert arena.submit_decision({"move_ucci": request["legal_moves"][0]}) is None
    assert arena.get_state()["last_move"]["ucci"] == request["legal_moves"][0]


def test_illegal_move_triggers_retry_with_reason():
    """Vòng lặp đi lại nằm ở Python — JS chỉ việc gọi API lại với prompt mới."""
    arena = _arena()
    arena.begin_turn()

    retry = arena.submit_decision({"move_ucci": "a0a9"})

    assert retry is not None, "nước sai luật phải được cho đi lại"
    assert retry["attempt"] == 2
    assert "BỊ TRỌNG TÀI TỪ CHỐI" in retry["prompt"]
    assert arena.referee.stats['w']["illegal_attempts"] == 1


def test_begin_turn_returns_none_when_game_is_over():
    """Trận xong rồi mà vẫn hỏi AI là đốt tiền của người dùng."""
    arena = _arena()
    arena.referee.board.load_fen("3k5/9/9/9/9/9/9/9/9/4K4 w - - 120 61")

    assert arena.begin_turn() is None
    assert arena.get_state()["game_over"]


def test_begin_turn_returns_none_on_human_turn():
    arena = BrowserArena({"model_key": "human", "name": "Bạn"},
                         {"model_key": "mock", "name": "Đen"})
    assert arena.begin_turn() is None

    assert arena.submit_human_move("h2e2") == {"ok": True, "message": "Pháo 2 bình 5"}
    rejected = arena.submit_human_move("a0a9")
    assert rejected["ok"] is False and rejected["message"]


def test_legal_moves_from_square_comes_from_referee_rules():
    arena = _arena()
    assert set(arena.legal_moves_from("b2")) == {
        m for m in arena.referee.board.generate_legal_moves('w') if m.startswith("b2")
    }
    assert arena.legal_moves_from("e5") == [], "ô trống thì không có nước nào"


def test_submit_decision_before_begin_turn_is_an_error():
    with pytest.raises(RuntimeError, match="begin_turn"):
        _arena().submit_decision({"move_ucci": "h2e2"})


def test_misspelled_field_is_rejected_loudly():
    """Sai tên trường ở phía JS mà bị bỏ qua thì biểu hiện ra ngoài là 'AI im lặng'."""
    with pytest.raises(TypeError, match="move_ucc"):
        decision_from_payload({"move_ucc": "h2e2"})

    with pytest.raises(TypeError, match="None"):
        decision_from_payload(None)


def test_full_match_runs_through_the_bridge():
    arena = _arena()
    import random
    random.seed(99)
    for _ in range(600):
        request = arena.begin_turn()
        if request is None:
            break
        while request is not None:
            request = arena.submit_decision({"move_ucci": request["legal_moves"][0]})

    state = arena.get_state()
    assert state["game_over"], "trận phải kết thúc đúng luật"
    assert state["analysis_enabled"] is False, "bản online không có Pikafish"


# --- Nội dung bundle ---

@pytest.fixture(scope="module")
def bundle_names():
    subprocess.run([str(REPO_ROOT / "scripts" / "build-web-bundle.sh")],
                   cwd=REPO_ROOT, check=True, capture_output=True)
    with zipfile.ZipFile(BUNDLE) as archive:
        return {n for n in archive.namelist() if n.endswith(".py")}


def test_bundle_has_everything_the_browser_needs(bundle_names):
    for required in (
        "engine/browser_bridge.py",
        "engine/referee.py",
        "engine/prompt_builder.py",
        "engine/model_registry.py",
        "engine/xiangqi/board.py",
        "engine/xiangqi/attack_detection.py",
        "engine/xiangqi/move_generation.py",
        "engine/analysis/move_quality_scorer.py",
        "engine/storage/elo_rating.py",
        "engine/providers/mock_provider.py",
        "engine/providers/human_provider.py",
    ):
        assert required in bundle_names, f"thiếu {required} thì bản online vỡ"


def test_bundle_excludes_modules_that_cannot_run_in_a_browser(bundle_names):
    """
    Module chạy tiến trình con hoặc mở SQLite không bao giờ chạy được trong trình duyệt.

    Gói vào thì vừa tốn băng thông của người dùng, vừa làm người đọc mã tưởng bản online
    có chấm điểm Pikafish và lưu trận.
    """
    for forbidden in (
        "engine/analysis/pikafish_engine.py",
        "engine/storage/match_repository.py",
        "engine/match_manager.py",
        "engine/providers/pikafish_provider.py",
        "engine/providers/anthropic_provider.py",
        "engine/providers/gemini_provider.py",
        "engine/providers/openai_compatible_provider.py",
    ):
        assert forbidden not in bundle_names, f"{forbidden} không được vào bundle"


def test_bundled_modules_import_without_the_excluded_ones(bundle_names):
    """
    Bằng chứng bundle tự đứng được: import mọi module trong bundle bằng một tiến trình
    Python chỉ nhìn thấy đúng các file đã giải nén.

    Nếu một file trong bundle lỡ import Pikafish hay SQLite ở mức module, test này đỏ —
    bắt được lỗi ngay, thay vì để nó nổ trên trình duyệt của người xem.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as workdir:
        with zipfile.ZipFile(BUNDLE) as archive:
            archive.extractall(workdir)

        modules = sorted(
            name[:-3].replace("/", ".") for name in bundle_names
            if not name.endswith("__init__.py")
        )
        script = "import " + "; import ".join(modules)
        result = subprocess.run(["python3", "-c", script], cwd=workdir,
                                capture_output=True, text=True)

    assert result.returncode == 0, f"bundle không tự đứng được:\n{result.stderr}"
