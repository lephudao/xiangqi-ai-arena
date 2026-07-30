"""
Giao diện chung cho mọi kỳ thủ AI, và kiểu dữ liệu quyết định nước đi.

Nguyên tắc bất di bất dịch: provider KHÔNG được tự sửa nước đi sai thành nước hợp lệ.
Nước AI chọn luôn được trả về nguyên bản để trọng tài đếm số lần đi sai luật — đó là một
thước đo sức mạnh, và là nội dung hấp dẫn nhất cho video.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Schema JSON dùng chung cho mọi provider hỗ trợ structured output.
# CHỦ Ý: move_ucci là string tự do, KHÔNG dùng enum giới hạn danh sách nước hợp lệ.
# Nếu ép enum thì mọi AI đều đi hợp lệ 100% và ta mất hoàn toàn tín hiệu
# "AI có thật sự đọc được bàn cờ không".
# `analysis` nằm trong schema thay vì dựa vào thinking block của API: Claude với adaptive
# thinking thường bỏ qua suy nghĩ ở task này (đo được: chỉ ~60 output token), và Gemini
# không expose thinking. Đưa vào schema thì mọi provider đều trả phân tích như nhau —
# vừa đảm bảo có nội dung cho video, vừa công bằng khi so sánh.
MOVE_SCHEMA = {
    "type": "object",
    "properties": {
        "move_ucci": {"type": "string"},
        "analysis": {"type": "string"},
        "taunt": {"type": "string"},
    },
    "required": ["move_ucci", "analysis", "taunt"],
    "additionalProperties": False,
}


@dataclass
class MoveDecision:
    """Quyết định của một kỳ thủ cho một lượt."""

    move_ucci: str = ""          # nguyên văn AI trả về, không bị sửa
    taunt: str = ""              # câu thoại cho khán giả (TTS đọc câu này)
    thinking: str = ""           # phân tích/suy luận nếu provider trả về
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = None       # None = chưa có bảng giá cho model đó
    error: str = None            # lỗi thật, không che
    provider: str = ""
    model_key: str = ""
    attempts: list = field(default_factory=list)  # trọng tài ghi vào

    # Giữ tên cũ để giao diện hiện tại không phải sửa cùng lúc
    @property
    def reasoning(self):
        return self.taunt


class MoveProvider(ABC):
    """Một kỳ thủ: nhận prompt + danh sách nước hợp lệ, trả về quyết định."""

    def __init__(self, model_info, api_key=None):
        self.model_info = model_info
        self.api_key = api_key

    @property
    def provider_name(self):
        return self.model_info.provider

    @property
    def model_key(self):
        return self.model_info.key

    @abstractmethod
    def decide(self, prompt, legal_moves, board=None, side=None):
        """Trả về MoveDecision. Không được raise — lỗi phải nằm trong `error`."""

    def close(self):
        """Giải phóng tài nguyên (chỉ provider chạy tiến trình con mới cần)."""
