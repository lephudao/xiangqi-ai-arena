"""
Kỳ thủ mà quyết định do BÊN NGOÀI cung cấp — dùng cho bản chạy trong trình duyệt.

Ở bản online, trình duyệt tự gọi API nhà cung cấp bằng key của người dùng, rồi nộp kết quả
vào trọng tài qua `browser_bridge`. Trọng tài vẫn cần một đối tượng kỳ thủ để biết tên, nhà
cung cấp và "có phải người chơi không", nhưng không bao giờ tự gọi mạng.

Lớp này chỉ mang danh tính. Gọi `decide()` là dấu hiệu ai đó đang lái trọng tài bằng
`step()` đồng bộ trong môi trường không có mạng đồng bộ — báo lỗi thẳng thay vì trả về nước
đi rỗng rồi để trọng tài xử thua oan.
"""

from engine.providers.base_provider import MoveProvider


class ExternalProvider(MoveProvider):
    def decide(self, prompt, legal_moves, board=None, side=None):
        raise RuntimeError(
            f"{self.model_key}: quyết định phải do bên ngoài nộp vào qua submit_decision(), "
            "không gọi decide() trực tiếp"
        )
