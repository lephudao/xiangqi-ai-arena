"""
Nhà máy tạo kỳ thủ: từ cấu hình (model key + api key) ra đúng provider tương ứng.

Thiếu API key -> tự chuyển về Mock và ghi rõ lý do, để trận vẫn chạy được nhưng người xem
biết đó không phải AI thật.
"""

import os

from engine.model_registry import get_model
from engine.providers.base_provider import MOVE_SCHEMA, MoveDecision, MoveProvider

__all__ = ["MoveDecision", "MoveProvider", "MOVE_SCHEMA", "create_provider", "describe_player"]


def _resolve_api_key(model_info, explicit_key=None):
    if explicit_key:
        return explicit_key
    if model_info.api_key_env:
        return os.environ.get(model_info.api_key_env, "")
    return ""


def create_provider(model_key, api_key=None, effort=None, analysis_engine=None):
    """
    Tạo provider cho một kỳ thủ. Trả (provider, note) — note khác None khi phải thay thế
    provider được yêu cầu (ví dụ thiếu key).
    """
    from engine.providers.mock_provider import MockProvider

    model_info = get_model(model_key)
    if model_info is None:
        fallback = get_model("mock")
        return MockProvider(fallback), f"Không có model '{model_key}' trong danh mục — dùng Mock"

    if model_info.provider == "mock":
        return MockProvider(model_info), None

    if model_info.provider == "human":
        from engine.providers.human_provider import HumanProvider
        return HumanProvider(model_info), None

    if model_info.provider == "pikafish":
        from engine.providers.pikafish_provider import PikafishProvider
        return PikafishProvider(model_info, engine=analysis_engine), None

    resolved_key = _resolve_api_key(model_info, api_key)
    if not resolved_key:
        return (
            MockProvider(get_model("mock")),
            f"Thiếu {model_info.api_key_env} cho {model_info.label} — dùng Mock thay thế",
        )

    if model_info.provider == "anthropic":
        from engine.providers.anthropic_provider import AnthropicProvider
        kwargs = {"effort": effort} if effort else {}
        return AnthropicProvider(model_info, resolved_key, **kwargs), None

    if model_info.provider == "gemini":
        from engine.providers.gemini_provider import GeminiProvider
        return GeminiProvider(model_info, resolved_key), None

    if model_info.provider == "openai_compatible":
        from engine.providers.openai_compatible_provider import OpenAICompatibleProvider
        return OpenAICompatibleProvider(model_info, resolved_key), None

    return MockProvider(get_model("mock")), f"Provider '{model_info.provider}' chưa hỗ trợ"


def describe_player(model_key):
    """Nhãn hiển thị cho kỳ thủ, dùng trên overlay và trong log."""
    model_info = get_model(model_key)
    return model_info.label if model_info else model_key
