"""
Kỳ thủ Pikafish: dùng engine cờ tướng chuyên dụng làm đối thủ.

Đây là MỐC TRẦN của đấu trường — câu hỏi "AI nào cầm cự được bao nhiêu nước trước engine?"
là một trong những nội dung hấp dẫn nhất cho video, và hoàn toàn miễn phí vì engine chạy local.
"""

import time

from engine.analysis import PikafishEngine
from engine.providers.base_provider import MoveDecision, MoveProvider

ENGINE_TAUNTS = [
    "Đã tính xong toàn bộ biến. Nước này là tối ưu.",
    "Không cần phán đoán — chỉ cần tính đủ sâu.",
    "Tôi thấy trước 20 nước. Bạn thấy được bao nhiêu?",
    "Đánh giá thế cờ đã xong. Kết quả không thể tránh khỏi.",
]


class PikafishProvider(MoveProvider):
    def __init__(self, model_info, api_key=None, movetime_ms=None, engine=None):
        super().__init__(model_info, api_key)
        # Dùng chung engine với bộ chấm điểm nếu được truyền vào, để không mở 2 tiến trình
        self.engine = engine if engine is not None else PikafishEngine(movetime_ms=movetime_ms)

    def decide(self, prompt, legal_moves, board=None, side=None):
        import random

        started = time.monotonic()
        if board is None:
            return self._error("PikafishProvider cần trạng thái bàn cờ", started)

        result = self.engine.analyse(board.to_fen())
        if result is None:
            reason = getattr(self.engine, "unavailable_reason", "engine không khả dụng")
            return self._error(f"Không lấy được nước đi từ engine: {reason}", started)

        return MoveDecision(
            move_ucci=result.bestmove,
            taunt=random.choice(ENGINE_TAUNTS),
            thinking=f"Đánh giá {result.cp} centipawn ở độ sâu {result.depth}; "
                     f"biến chính: {' '.join(result.pv[:6])}",
            latency_ms=int((time.monotonic() - started) * 1000),
            cost_usd=0.0,
            provider=self.provider_name,
            model_key=self.model_key,
        )

    def _error(self, message, started):
        return MoveDecision(
            latency_ms=int((time.monotonic() - started) * 1000),
            error=message,
            provider=self.provider_name,
            model_key=self.model_key,
        )
