"""
Test danh mục model, prompt builder, và tầng provider.

Không gọi API thật — dùng fixture/monkeypatch để test rẻ và chạy được offline.
"""

import pytest

from engine.model_registry import estimate_cost_usd, get_model, list_models
from engine.prompt_builder import build_move_prompt, render_ascii_board
from engine.providers import MOVE_SCHEMA, create_provider
from engine.xiangqi import XiangqiBoard


# --- Danh mục model ---

def test_registry_has_verified_models_for_available_keys():
    """Chỉ Anthropic/Gemini/mock/pikafish được đánh dấu đã kiểm chứng bằng key thật."""
    verified = {m["key"] for m in list_models() if m["verified"]}
    assert "claude-opus-5" in verified
    assert "gemini-3.1-pro" in verified
    # Chưa có key nên không được hứa suông
    assert "grok-4" not in verified
    assert "gpt-5" not in verified


def test_no_stale_model_ids():
    """gemini-1.5-flash đã bị Google gỡ khỏi API — không được còn trong danh mục."""
    model_ids = {m["model_id"] for m in list_models()}
    assert "gemini-1.5-flash" not in model_ids
    assert "claude-3-5-haiku-20241022" not in model_ids


def test_cost_estimate_uses_price_table():
    # Opus 5: $5 / 1M vào, $25 / 1M ra
    assert estimate_cost_usd("claude-opus-5", 1_000_000, 0) == pytest.approx(5.0)
    assert estimate_cost_usd("claude-opus-5", 0, 1_000_000) == pytest.approx(25.0)


def test_cost_is_none_when_price_unknown():
    """Model chưa có bảng giá phải trả None, không được bịa số."""
    assert get_model("gemini-3.1-pro").input_price is None
    assert estimate_cost_usd("gemini-3.1-pro", 1000, 1000) is None
    assert estimate_cost_usd("khong-ton-tai", 1000, 1000) is None


# --- Prompt builder ---

def test_ascii_board_matches_fen():
    board = XiangqiBoard()
    rendered = render_ascii_board(board.grid)
    lines = rendered.split("\n")
    # Hàng 9 là hậu phương Đen, hàng 0 là hậu phương Đỏ
    assert lines[1].startswith("9") and " r " in lines[1] and " k " in lines[1]
    assert "R" in lines[-3] and "K" in lines[-3]
    assert "楚河" in rendered, "phải có ký hiệu sông giữa bàn"


def test_prompt_requires_analysis_field():
    """Phân tích kỹ thuật phải nằm trong JSON schema, không dựa vào thinking block của API
    (đo thực tế: Claude adaptive thinking bỏ qua suy nghĩ ở task này, Gemini không expose)."""
    board = XiangqiBoard()
    prompt = build_move_prompt(board, 'w', board.generate_legal_moves('w'), "Đỏ")
    assert '"analysis"' in prompt
    assert MOVE_SCHEMA["properties"]["analysis"] == {"type": "string"}
    assert "analysis" in MOVE_SCHEMA["required"]


def test_prompt_contains_all_required_context():
    board = XiangqiBoard()
    legal_moves = board.generate_legal_moves('w')
    prompt = build_move_prompt(board, 'w', legal_moves, "Kỳ thủ Đỏ")

    assert "ĐỎ" in prompt
    assert "楚河" in prompt                      # bàn cờ ASCII
    assert board.to_fen() in prompt              # FEN vẫn có để đối chiếu
    assert "Xe x2" in prompt                     # kiểm kê quân
    assert "Chưa có nước nào" in prompt          # lịch sử
    assert "h2e2" in prompt                      # danh sách nước hợp lệ
    assert "move_ucci" in prompt                 # yêu cầu định dạng output
    assert "CẢNH BÁO" not in prompt              # không bị chiếu thì không cảnh báo


def test_prompt_warns_when_in_check():
    # Xe Đen e4 chiếu Tướng Đỏ e0
    board = XiangqiBoard("3k5/9/9/9/9/4r4/9/9/9/4K4 w - - 0 1")
    prompt = build_move_prompt(board, 'w', board.generate_legal_moves('w'), "Đỏ")
    assert "TƯỚNG CỦA BẠN ĐANG BỊ CHIẾU" in prompt


def test_prompt_includes_feedback_on_retry():
    board = XiangqiBoard()
    prompt = build_move_prompt(
        board, 'w', board.generate_legal_moves('w'), "Đỏ",
        feedback="Nước a0a9 không hợp lệ vì Xe không thể xuyên qua quân",
    )
    assert "BỊ TRỌNG TÀI TỪ CHỐI" in prompt
    assert "xuyên qua quân" in prompt


def test_prompt_annotates_capture_moves():
    """Nước ăn quân được đánh dấu để AI thấy ngay cơ hội."""
    # Xe Đỏ a0 có thể ăn Xe Đen a1
    board = XiangqiBoard("3k5/9/9/9/9/9/9/9/r8/R3K4 w - - 0 1")
    prompt = build_move_prompt(board, 'w', board.generate_legal_moves('w'), "Đỏ")
    assert "a0a1(ăn Xe)" in prompt


def test_prompt_shows_recent_history():
    board = XiangqiBoard()
    move_logs = [
        {"side": "w", "ucci": "h2e2", "vi_text": "Pháo 2 bình 5"},
        {"side": "b", "ucci": "h7e7", "vi_text": "Pháo 2 bình 5"},
    ]
    prompt = build_move_prompt(board, 'w', board.generate_legal_moves('w'), "Đỏ",
                               move_logs=move_logs)
    assert "1. Đỏ : Pháo 2 bình 5 [h2e2]" in prompt
    assert "2. Đen: Pháo 2 bình 5 [h7e7]" in prompt


# --- Tầng provider ---

def test_move_schema_keeps_move_as_free_string():
    """
    Chủ ý thiết kế: move_ucci KHÔNG dùng enum. Ép enum thì mọi AI đều đi hợp lệ 100%
    và mất tín hiệu 'AI có đọc được bàn cờ không' — vốn là nội dung hấp dẫn nhất.
    """
    assert MOVE_SCHEMA["properties"]["move_ucci"] == {"type": "string"}
    assert "enum" not in MOVE_SCHEMA["properties"]["move_ucci"]


def test_missing_api_key_falls_back_to_mock_with_reason(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    provider, note = create_provider("grok-4")
    assert provider.provider_name == "mock"
    assert "XAI_API_KEY" in note, "phải nói rõ thiếu key nào, không im lặng"


def test_unknown_model_key_falls_back_to_mock():
    provider, note = create_provider("model-khong-ton-tai")
    assert provider.provider_name == "mock"
    assert "không có model" in note.lower()


def test_mock_provider_returns_legal_move():
    provider, _ = create_provider("mock")
    board = XiangqiBoard()
    legal_moves = board.generate_legal_moves('w')
    decision = provider.decide("prompt", legal_moves, board=board, side='w')

    assert decision.move_ucci in legal_moves
    assert decision.taunt
    assert decision.cost_usd == 0.0
    assert decision.error is None


def test_anthropic_provider_reports_refusal_without_crashing():
    """stop_reason=refusal -> content rỗng; provider phải báo lỗi chứ không vỡ."""
    from engine.providers.anthropic_provider import AnthropicProvider

    class FakeUsage:
        input_tokens, output_tokens = 100, 0

    class FakeResponse:
        stop_reason = "refusal"
        content = []
        usage = FakeUsage()

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        messages = FakeMessages()

    provider = AnthropicProvider(get_model("claude-opus-5"), api_key="test")
    provider._client = FakeClient()
    decision = provider.decide("prompt", ["h2e2"])

    assert decision.error and "refusal" in decision.error
    assert decision.move_ucci == ""
    assert decision.cost_usd == pytest.approx(100 * 5.0 / 1_000_000)


def test_anthropic_provider_does_not_send_sampling_params():
    """Opus 5 / Sonnet 5 trả lỗi 400 nếu nhận temperature/top_p/top_k."""
    from engine.providers.anthropic_provider import AnthropicProvider

    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            raise RuntimeError("dừng sau khi bắt được tham số")

    class FakeClient:
        messages = FakeMessages()

    provider = AnthropicProvider(get_model("claude-opus-5"), api_key="test")
    provider._client = FakeClient()
    provider.decide("prompt", ["h2e2"])

    for forbidden in ("temperature", "top_p", "top_k", "budget_tokens"):
        assert forbidden not in captured, f"{forbidden} sẽ làm API trả lỗi 400"
    assert captured["thinking"] == {"type": "adaptive"}
    assert captured["max_tokens"] >= 4000, "max_tokens phải dư chỗ cho phần suy nghĩ"
