"""
Kỳ thủ là người thật.

Khác mọi provider khác ở chỗ nước đi KHÔNG được sinh ra khi trọng tài hỏi: trọng tài phải
dừng lại chờ người bấm chuột. Vì vậy provider này chỉ đóng vai cờ hiệu — trọng tài nhìn
`is_human` để biết cần chờ thay vì gọi `decide()`.
"""

from engine.providers.base_provider import MoveDecision, MoveProvider


class HumanProvider(MoveProvider):
    """Kỳ thủ người: trọng tài chờ nước đi gửi lên qua API thay vì hỏi provider."""

    is_human = True

    def decide(self, prompt, legal_moves, board=None, side=None):
        # Không bao giờ được gọi trong luồng bình thường; trả lỗi rõ ràng thay vì im lặng
        # đi một nước ngẫu nhiên nếu có chỗ nào đó gọi nhầm.
        return MoveDecision(
            error="Kỳ thủ người không tự sinh nước đi — trọng tài phải chờ người gửi nước",
            provider=self.provider_name,
            model_key=self.model_key,
        )
