"""
Test bản đóng gói cho trình duyệt: cầu nối BrowserArena và nội dung file zip.

Cầu nối là Python thuần nên kiểm được bằng pytest, không cần trình duyệt. Đây là lý do
lớp glue nằm ở Python chứ không nhúng trong file JS.
"""

import subprocess
import zipfile
from pathlib import Path

import pytest

from engine.browser_bridge import (
    BrowserArena,
    apply_elo,
    decision_from_payload,
    describe_models,
    describe_tts_models,
    tts_cost_usd,
)
from engine.providers.external_provider import ExternalProvider
from engine.storage.elo_rating import STARTING_ELO

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


def test_api_players_never_call_the_network_from_python():
    """
    Ở bản trình duyệt, key nằm trong máy người dùng và Python không được mở kết nối nào.

    Kỳ thủ dùng API phải là ExternalProvider — chỉ mang danh tính. Nếu tạo nhầm thành
    provider thật thì Python sẽ đi tìm API key trong biến môi trường, không thấy, rồi âm
    thầm rơi về Mock: người dùng tưởng đang xem Claude đánh cờ mà thật ra là đi ngẫu nhiên.
    """
    arena = BrowserArena({"model_key": "claude-haiku-4-5"}, {"model_key": "gemini-3.6-flash"})

    assert isinstance(arena.referee.red_agent, ExternalProvider)
    assert isinstance(arena.referee.black_agent, ExternalProvider)
    assert arena.referee.red_agent.model_key == "claude-haiku-4-5"

    with pytest.raises(RuntimeError, match="submit_decision"):
        arena.referee.red_agent.decide("prompt", ["h2e2"])


def test_cost_is_computed_by_python_not_javascript():
    """JS chỉ báo số token. Chép bảng giá sang JS thì bộ đếm sẽ lệch hoá đơn thật."""
    decision = decision_from_payload({
        "move_ucci": "h2e2", "model_key": "claude-haiku-4-5",
        "tokens_in": 1_000_000, "tokens_out": 1_000_000,
    })
    assert decision.cost_usd == pytest.approx(6.00)   # Haiku 4.5: $1 vào + $5 ra

    # Model chưa niêm yết giá -> None, để giao diện hiện "—" thay vì con số bịa
    unpriced = decision_from_payload({"move_ucci": "h2e2", "model_key": "gemini-3-pro",
                                      "tokens_in": 1000, "tokens_out": 100})
    assert unpriced.cost_usd is None


def test_model_catalog_marks_pikafish_unavailable_in_browser():
    """
    Pikafish chạy bằng tiến trình con nên không có trong bundle. Để lọt vào danh sách kỳ thủ
    thì người dùng chọn xong sẽ gặp ImportError giữa trận.
    """
    catalog = describe_models()
    by_key = {model["key"]: model for model in catalog["models"]}

    assert by_key["pikafish"]["available"] is False
    assert by_key["mock"]["available"] is True
    assert by_key["human"]["available"] is True
    assert by_key["claude-haiku-4-5"]["available"] is True


def test_openai_is_marked_unavailable_in_browser():
    """
    OpenAI cố ý bỏ header CORS trên phản hồi /chat/completions khi request có Authorization,
    nên trình duyệt không gọi được (đo 2026-08-01, xem chú thích trong model_registry).

    Không đánh dấu thì người dùng chọn ChatGPT xong sẽ thấy "Failed to fetch" — thông báo
    của trình duyệt, không nói được vì sao và không sửa được.
    """
    by_key = {model["key"]: model for model in describe_models()["models"]}

    assert by_key["gpt-5"]["available"] is False
    # Grok và DeepSeek vẫn gọi được từ trình duyệt
    assert by_key["grok-4"]["available"] is True
    assert by_key["deepseek-chat"]["available"] is True


def test_model_catalog_carries_what_javascript_needs_to_build_requests():
    """JS không được chép bảng model — mọi thứ dựng request phải đến từ đây."""
    by_key = {model["key"]: model for model in describe_models()["models"]}

    haiku = by_key["claude-haiku-4-5"]
    assert haiku["model_id"] == "claude-haiku-4-5"
    assert haiku["api_key_env"] == "ANTHROPIC_API_KEY"
    # Haiku 4.5 từ chối effort và adaptive thinking với lỗi 400 — JS phải biết mà không gửi
    assert haiku["supports_effort"] is False
    assert haiku["supports_adaptive_thinking"] is False

    assert by_key["grok-4"]["base_url"] == "https://api.x.ai/v1"
    assert by_key["mock"]["needs_api_key"] is False

    schema = describe_models()["move_schema"]
    assert schema["properties"]["move_ucci"]["type"] == "string", \
        "move_ucci phải là string tự do, ép enum sẽ mất tín hiệu AI đọc được bàn cờ hay không"


# --- Giọng đọc (TTS) ---

def test_tts_models_are_not_offered_as_chess_players():
    """Model TTS không đánh cờ. Lọt vào danh sách kỳ thủ là người dùng chọn được nó làm đối thủ."""
    player_keys = {model["key"] for model in describe_models()["models"]}
    tts_keys = {model["key"] for model in describe_tts_models()}

    assert tts_keys, "phải có ít nhất một giọng đọc"
    assert not (player_keys & tts_keys)


def test_tts_cost_comes_from_the_price_table():
    """
    Tiếng đọc tốn tiền theo token âm thanh, và giá chênh nhau 2 lần giữa các model.
    Bỏ qua thì bộ đếm báo thiếu so với hoá đơn thật.
    """
    # Gemini 2.5 Flash TTS: $0.50 vào + $10.00 ra cho 1 triệu token
    assert tts_cost_usd("gemini-2.5-flash-tts", 1_000_000, 1_000_000) == pytest.approx(10.50)
    # Bản 3.1 đắt gấp đôi
    assert tts_cost_usd("gemini-3.1-flash-tts", 1_000_000, 1_000_000) == pytest.approx(21.00)
    assert tts_cost_usd("khong-ton-tai", 1000, 1000) is None


def test_tts_catalog_gives_javascript_what_it_needs():
    by_key = {model["key"]: model for model in describe_tts_models()}
    assert by_key["gemini-2.5-flash-tts"]["model_id"] == "gemini-2.5-flash-preview-tts"
    assert by_key["gemini-2.5-flash-tts"]["api_key_env"] == "GEMINI_API_KEY"


# --- Bảng xếp hạng Elo của bản online ---

def test_elo_uses_result_status_not_winner_side():
    """
    `score_from_result` nhận TRẠNG THÁI KẾT QUẢ ('red_win'), không phải bên thắng ('w').

    Truyền nhầm thì nó trả None và phép trừ trong update_ratings vỡ giữa trận — đúng lúc
    người dùng vừa đánh xong.
    """
    rows = apply_elo([], "claude-haiku-4-5", "gemini-3.6-flash", "red_win")
    by_key = {row["model_key"]: row for row in rows}

    assert by_key["claude-haiku-4-5"]["elo"] > STARTING_ELO
    assert by_key["gemini-3.6-flash"]["elo"] < STARTING_ELO
    assert by_key["claude-haiku-4-5"]["wins"] == 1
    assert by_key["gemini-3.6-flash"]["losses"] == 1
    assert rows[0]["model_key"] == "claude-haiku-4-5", "phải xếp theo Elo giảm dần"


def test_elo_ignores_a_model_playing_itself():
    """
    Mock vs Mock là cùng một dòng trong bảng: thắng và thua đè lên nhau, và tự đấu với chính
    mình cũng không nói lên điều gì về sức mạnh tương đối.
    """
    assert apply_elo([], "mock", "mock", "red_win") == []


def test_elo_ignores_unfinished_match():
    assert apply_elo([], "claude-haiku-4-5", "gemini-3.6-flash", "ongoing") == []


def test_elo_accumulates_across_matches():
    rows = apply_elo([], "claude-haiku-4-5", "gemini-3.6-flash", "red_win")
    rows = apply_elo(rows, "claude-haiku-4-5", "gemini-3.6-flash", "draw")
    by_key = {row["model_key"]: row for row in rows}

    assert by_key["claude-haiku-4-5"]["matches"] == 2
    assert by_key["claude-haiku-4-5"]["draws"] == 1
    # Tổng Elo được bảo toàn qua mọi trận
    assert sum(row["elo"] for row in rows) == pytest.approx(2 * STARTING_ELO)


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
