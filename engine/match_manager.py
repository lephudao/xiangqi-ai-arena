"""
Quản lý nhiều trận đấu cùng lúc, thay cho một biến toàn cục duy nhất.

Trước đây server giữ đúng MỘT đối tượng trọng tài toàn cục, nên không thể chạy giải đấu
nhiều trận, không thể mở hai trận song song để so sánh, và mọi tab trình duyệt đều dùng
chung một ván. Đây là điều kiện cần cho giải đấu (Phase 3) và chế độ Người vs AI (Phase 4).

Engine chấm điểm được dùng CHUNG cho mọi trận: mỗi tiến trình Pikafish chiếm ~50MB bộ nhớ
cho bảng NNUE, mở một tiến trình cho mỗi trận là lãng phí.
"""

import threading
import uuid
from datetime import datetime

from engine.analysis import PikafishEngine
from engine.referee import MatchReferee
from engine.storage import MatchRepository

# Giới hạn số trận giữ trong bộ nhớ; trận cũ nhất bị loại khi vượt ngưỡng
MAX_ACTIVE_MATCHES = 20


class MatchManager:
    def __init__(self, analysis_engine=None, repository=None):
        # Một engine dùng chung cho tất cả các trận
        self.analysis_engine = analysis_engine if analysis_engine is not None else PikafishEngine()
        # Kho lưu trận dùng chung; truyền repository=False để tắt hẳn việc ghi (dùng trong test)
        self.repository = MatchRepository() if repository is None else (repository or None)
        self._matches = {}          # match_id -> MatchReferee
        self._created_at = {}       # match_id -> thời điểm tạo (để hiển thị)
        self._sequence = {}         # match_id -> số thứ tự tạo (để sắp xếp)
        self._next_sequence = 0
        self._lock = threading.Lock()
        self.current_match_id = None

    def create(self, red_config=None, black_config=None, make_current=False):
        """
        Tạo trận mới. Trả (match_id, referee).

        Mặc định KHÔNG chuyển trận đang xem: mở thêm trận song song (hoặc chạy giải đấu)
        không được cướp màn hình của trận đang quay. Chỉ tự nhận làm trận đang xem khi
        chưa có trận nào.
        """
        match_id = uuid.uuid4().hex[:12]
        referee = MatchReferee(red_config, black_config, analysis_engine=self.analysis_engine)
        if self.repository is not None:
            # Dùng chung một id giữa bộ nhớ và cơ sở dữ liệu để replay tra được đúng trận
            referee.attach_recorder(self.repository, match_id=match_id)

        with self._lock:
            self._matches[match_id] = referee
            self._created_at[match_id] = datetime.now()
            # Dùng số thứ tự tăng dần để sắp xếp: dấu thời gian làm tròn tới giây sẽ cho
            # thứ tự sai khi nhiều trận được tạo trong cùng một giây.
            self._sequence[match_id] = self._next_sequence
            self._next_sequence += 1
            if make_current or self.current_match_id is None:
                self.current_match_id = match_id
            self._evict_oldest_if_needed()

        return match_id, referee

    def _evict_oldest_if_needed(self):
        """Loại trận cũ nhất khi quá ngưỡng, nhưng không bao giờ loại trận đang xem."""
        while len(self._matches) > MAX_ACTIVE_MATCHES:
            removable = [mid for mid in self._matches if mid != self.current_match_id]
            if not removable:
                return
            oldest = min(removable, key=lambda mid: self._sequence[mid])
            self._forget(oldest)

    def _forget(self, match_id):
        """Xoá mọi dấu vết của một trận khỏi bộ nhớ."""
        del self._matches[match_id]
        del self._created_at[match_id]
        del self._sequence[match_id]

    def get(self, match_id):
        """Trả referee theo id, hoặc None nếu không có."""
        return self._matches.get(match_id)

    def get_current(self):
        """
        Trận đang xem. Tự tạo một trận mặc định nếu chưa có trận nào — nhờ đó các route cũ
        (/api/state, /api/step) vẫn hoạt động mà không cần client truyền match_id.
        """
        with self._lock:
            referee = self._matches.get(self.current_match_id)
        if referee is None:
            _, referee = self.create()
        return referee

    def set_current(self, match_id):
        """Chuyển trận đang xem. Trả False nếu id không tồn tại."""
        with self._lock:
            if match_id not in self._matches:
                return False
            self.current_match_id = match_id
            return True

    def list_matches(self):
        """Tóm tắt các trận, mới nhất trước — dùng cho bảng chọn trận và replay."""
        with self._lock:
            items = list(self._matches.items())
            created = dict(self._created_at)
            sequence = dict(self._sequence)
            current = self.current_match_id

        summaries = []
        for match_id, referee in items:
            state = referee.get_state()
            summaries.append({
                "match_id": match_id,
                "is_current": match_id == current,
                "created_at": created[match_id].isoformat(timespec="seconds"),
                "red": referee.red_config["name"],
                "black": referee.black_config["name"],
                "plies": len(referee.move_logs),
                "game_over": state["game_over"],
                "result_reason": state["result_reason"],
                "winner": state["winner"],
            })
        summaries.sort(key=lambda item: sequence[item["match_id"]], reverse=True)
        return summaries

    def delete(self, match_id):
        with self._lock:
            if match_id not in self._matches:
                return False
            self._forget(match_id)
            if self.current_match_id == match_id:
                self.current_match_id = next(iter(self._matches), None)
            return True

    def close(self):
        """Đóng tiến trình engine và kết nối cơ sở dữ liệu. Gọi khi tắt server."""
        if self.analysis_engine is not None:
            self.analysis_engine.close()
        if self.repository is not None:
            self.repository.close()
