"""
Danh mục model dùng cho đấu trường, kèm giá token để tính chi phí mỗi trận.

Một chỗ duy nhất để cập nhật model — trước đây model ID bị hardcode rải rác trong
ai_agent.py và đã lỗi thời (gemini-1.5-flash nay không còn tồn tại trên API).

Giá tính theo USD cho 1 triệu token. `None` nghĩa là CHƯA có số liệu xác thực —
hệ thống sẽ hiện "—" thay vì bịa ra con số.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    key: str              # định danh dùng trong cấu hình/UI
    label: str            # tên hiển thị cho khán giả
    provider: str         # anthropic | gemini | openai_compatible | mock | pikafish
    model_id: str         # ID gửi lên API
    input_price: float = None   # USD / 1M token vào
    output_price: float = None  # USD / 1M token ra
    base_url: str = None        # chỉ dùng cho provider openai_compatible
    api_key_env: str = None
    verified: bool = False      # đã gọi thử bằng key thật chưa
    note: str = ""
    # Năng lực API khác nhau theo đời model: Haiku 4.5 không nhận `effort` và không có
    # adaptive thinking (gửi sẽ bị từ chối 400), trong khi Opus 5 / Sonnet 5 thì bắt buộc
    # dùng adaptive và đã bỏ budget_tokens.
    supports_effort: bool = True
    supports_adaptive_thinking: bool = True
    # Trình duyệt gọi thẳng được không? OpenAI CỐ Ý bỏ header CORS trên phản hồi
    # /chat/completions khi request có Authorization — xem chú thích ở _OPENAI_COMPATIBLE.
    browser_cors: bool = True


# Giá Anthropic theo bảng giá chính thức. Sonnet 5 đang có giá giới thiệu
# $2/$10 tới 2026-08-31; ở đây dùng giá niêm yết để không tính thiếu chi phí.
_ANTHROPIC = [
    ModelInfo("claude-opus-5", "Claude Opus 5", "anthropic", "claude-opus-5",
              5.00, 25.00, api_key_env="ANTHROPIC_API_KEY", verified=True,
              note="Mạnh nhất cho suy luận dài; đắt nhất trong nhóm Opus/Sonnet"),
    ModelInfo("claude-sonnet-5", "Claude Sonnet 5", "anthropic", "claude-sonnet-5",
              3.00, 15.00, api_key_env="ANTHROPIC_API_KEY",
              note="Cân bằng tốc độ/chi phí; đang có giá giới thiệu $2/$10"),
    ModelInfo("claude-haiku-4-5", "Claude Haiku 4.5", "anthropic", "claude-haiku-4-5",
              1.00, 5.00, api_key_env="ANTHROPIC_API_KEY",
              note="Rẻ và nhanh nhất; dùng cho trận dài nhiều nước",
              supports_effort=False, supports_adaptive_thinking=False),
    ModelInfo("claude-opus-4-8", "Claude Opus 4.8", "anthropic", "claude-opus-4-8",
              5.00, 25.00, api_key_env="ANTHROPIC_API_KEY",
              note="Thế hệ Opus trước, để so sánh tiến bộ giữa các đời model"),
]

# Model ID lấy trực tiếp từ API Gemini (models.list) ngày 2026-07-30.
# Giá lấy từ ai.google.dev/gemini-api/docs/pricing, bậc "prompt <= 200k token" — prompt của
# hệ thống chỉ khoảng 1-2k token nên luôn nằm ở bậc này. Giá output đã bao gồm thinking token.
_GEMINI = [
    ModelInfo("gemini-3.1-pro", "Gemini 3.1 Pro", "gemini", "gemini-3.1-pro-preview",
              2.00, 12.00, api_key_env="GEMINI_API_KEY", verified=True,
              note="Bản Pro mới nhất; đã gọi thử thành công"),
    ModelInfo("gemini-3.6-flash", "Gemini 3.6 Flash", "gemini", "gemini-3.6-flash",
              1.50, 7.50, api_key_env="GEMINI_API_KEY",
              note="Flash mới nhất, nhanh và rẻ hơn Pro"),
    # Trang giá của Google không niêm yết Gemini 3 Pro -> để None thay vì đoán
    ModelInfo("gemini-3-pro", "Gemini 3 Pro", "gemini", "gemini-3-pro-preview",
              api_key_env="GEMINI_API_KEY", note="Trang giá Google chưa niêm yết model này"),
    ModelInfo("gemini-2.5-pro", "Gemini 2.5 Pro", "gemini", "gemini-2.5-pro",
              1.25, 10.00, api_key_env="GEMINI_API_KEY",
              note="Thế hệ trước, để so sánh tiến bộ giữa các đời model"),
]

# Các nhà cung cấp dùng chung chuẩn OpenAI /chat/completions.
# CHƯA kiểm chứng bằng key thật — đánh dấu verified=False để không hứa suông.
#
# OpenAI KHÔNG gọi được từ trình duyệt (đo ngày 2026-08-01): preflight OPTIONS trả 200 và
# cho phép cả header `authorization`, nhưng phản hồi THẬT của POST /chat/completions lại bỏ
# `access-control-allow-origin` khi request có Authorization. Cùng request đó mà bỏ
# Authorization thì phản hồi có đủ header CORS. Đây là chủ ý của OpenAI nhằm chặn dùng API
# key ở trình duyệt — và là lý do không được kết luận chỉ từ preflight.
_OPENAI_COMPATIBLE = [
    ModelInfo("gpt-5", "ChatGPT (GPT-5)", "openai_compatible", "gpt-5",
              base_url="https://api.openai.com/v1", api_key_env="OPENAI_API_KEY",
              browser_cors=False,
              note="Chỉ đấu được ở bản local — OpenAI chặn gọi API từ trình duyệt"),
    ModelInfo("grok-4", "Grok 4", "openai_compatible", "grok-4",
              base_url="https://api.x.ai/v1", api_key_env="XAI_API_KEY",
              note="Chưa kiểm chứng: cần XAI_API_KEY"),
    ModelInfo("deepseek-chat", "DeepSeek", "openai_compatible", "deepseek-chat",
              base_url="https://api.deepseek.com/v1", api_key_env="DEEPSEEK_API_KEY",
              note="Chưa kiểm chứng: cần DEEPSEEK_API_KEY"),
]

# Đối thủ không phải LLM: người thật, mốc sàn (đi ngẫu nhiên) và mốc trần (engine cờ tướng)
_BASELINES = [
    ModelInfo("human", "Người chơi (bạn)", "human", "human", 0.0, 0.0, verified=True,
              note="Bạn tự đánh; nước đi được chấm điểm y như AI"),
    ModelInfo("mock", "Mock (đi ngẫu nhiên)", "mock", "mock-v1", 0.0, 0.0, verified=True,
              note="Mốc sàn: chọn ngẫu nhiên trong các nước hợp lệ"),
    ModelInfo("pikafish", "Pikafish (engine)", "pikafish", "pikafish", 0.0, 0.0, verified=True,
              note="Mốc trần: engine cờ tướng chuyên dụng, chạy local miễn phí"),
]

# Model đọc tiếng (TTS). KHÔNG nằm trong ALL_MODELS: chúng không đánh cờ nên không được
# xuất hiện trong danh sách chọn kỳ thủ. Nhưng vẫn vào _BY_KEY để estimate_cost_usd tra được
# giá — tiếng đọc cũng tốn tiền và phải hiện trong bộ đếm chi phí.
#
# Giá lấy từ ai.google.dev/gemini-api/docs/pricing ngày 2026-08-01, bậc trả phí tiêu chuẩn.
# Bậc miễn phí của Google cho TTS là $0, nhưng bộ đếm dùng giá trả phí để không báo thiếu.
TTS_MODELS = [
    ModelInfo("gemini-2.5-flash-tts", "Gemini 2.5 Flash TTS", "gemini_tts",
              "gemini-2.5-flash-preview-tts", 0.50, 10.00, api_key_env="GEMINI_API_KEY",
              note="Rẻ nhất; đủ tốt cho lời bình trận đấu"),
    ModelInfo("gemini-3.1-flash-tts", "Gemini 3.1 Flash TTS", "gemini_tts",
              "gemini-3.1-flash-tts-preview", 1.00, 20.00, api_key_env="GEMINI_API_KEY",
              note="Mới nhất; đắt gấp đôi bản 2.5 Flash"),
    ModelInfo("gemini-2.5-pro-tts", "Gemini 2.5 Pro TTS", "gemini_tts",
              "gemini-2.5-pro-preview-tts", 1.00, 20.00, api_key_env="GEMINI_API_KEY",
              note="Không có bậc miễn phí"),
]

ALL_MODELS = _ANTHROPIC + _GEMINI + _OPENAI_COMPATIBLE + _BASELINES
_BY_KEY = {model.key: model for model in ALL_MODELS + TTS_MODELS}

DEFAULT_RED_MODEL = "claude-haiku-4-5"
# Flash cùng phân khúc giá/tốc độ với Haiku 4.5 -> cặp đấu công bằng
DEFAULT_BLACK_MODEL = "gemini-3.6-flash"


def get_model(key):
    """Tra model theo key. Trả None nếu không có."""
    return _BY_KEY.get(key)


def list_models():
    """Danh sách model cho dropdown UI."""
    return [
        {
            "key": model.key,
            "label": model.label,
            "provider": model.provider,
            "model_id": model.model_id,
            "verified": model.verified,
            "has_pricing": model.input_price is not None,
            "note": model.note,
        }
        for model in ALL_MODELS
    ]


def estimate_cost_usd(model_key, tokens_in, tokens_out):
    """
    Chi phí một lượt gọi API. Trả None nếu chưa có giá cho model đó — để hệ thống
    hiển thị "—" thay vì con số bịa.
    """
    model = get_model(model_key)
    if model is None or model.input_price is None or model.output_price is None:
        return None
    return (tokens_in * model.input_price + tokens_out * model.output_price) / 1_000_000
