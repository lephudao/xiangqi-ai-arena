"""
Kỳ thủ giả lập: chọn ngẫu nhiên trong các nước hợp lệ.

Đây là MỐC SÀN của đấu trường — accuracy của mock (~50-60% theo đo thực tế) là mức mà
mọi AI thật phải vượt qua để chứng minh nó thực sự biết chơi cờ.
"""

import random

from engine.providers.base_provider import MoveDecision, MoveProvider

TAUNTS_RED = [
    "Khai cuộc bằng nước đi uy lực, làm đối phương phải giật mình!",
    "Quân cờ đã xuất trận, để xem bên Đen đỡ nước này kiểu gì!",
    "Chiến thuật lấy tĩnh chế động, kiểm soát khu vực trung lộ!",
    "Nước đi phế quân để lấy thế công mãnh liệt!",
    "Bẫy giăng sẵn rồi, chỉ chờ đối thủ sa lưới thôi!",
]

TAUNTS_BLACK = [
    "Đỡ nước đi này quá dễ dàng, chuẩn bị phản công dồn dập!",
    "Cứ thong thả phòng thủ chắc chắn, chờ đối thủ sơ hở!",
    "Nước đi mang tính đột phá cao, không ngờ tới phải không?",
    "Phòng thủ phản công là sở trường của tôi!",
    "Một nước đi khiến đối thủ phải vò đầu bứt tóc!",
]


class MockProvider(MoveProvider):
    def decide(self, prompt, legal_moves, board=None, side=None):
        taunts = TAUNTS_RED if side == 'w' else TAUNTS_BLACK
        return MoveDecision(
            move_ucci=random.choice(legal_moves) if legal_moves else "",
            taunt=random.choice(taunts),
            cost_usd=0.0,
            provider=self.provider_name,
            model_key=self.model_key,
        )
