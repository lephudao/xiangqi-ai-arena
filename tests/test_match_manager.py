"""
Test quản lý nhiều trận cùng lúc.

Trước đây server giữ một đối tượng trọng tài toàn cục nên mọi tab dùng chung một ván và
không thể chạy giải đấu. Các test dưới đây chốt lại hành vi mới.
"""

from engine.match_manager import MAX_ACTIVE_MATCHES, MatchManager


def _manager():
    """Manager tắt chấm điểm engine để test chạy nhanh."""
    return MatchManager(analysis_engine=None)


def test_matches_are_independent():
    """Hai trận song song không được lẫn trạng thái vào nhau."""
    manager = _manager()
    first_id, first = manager.create({"model_key": "mock"}, {"model_key": "mock"})
    second_id, second = manager.create({"model_key": "mock"}, {"model_key": "mock"})

    assert first_id != second_id
    first.step()
    first.step()
    second.step()

    assert len(first.move_logs) == 2
    assert len(second.move_logs) == 1
    assert first.board.to_fen() != second.board.to_fen()


def test_creating_parallel_match_does_not_steal_current_view():
    """Mở trận song song (hoặc chạy giải đấu) không được cướp màn hình đang quay."""
    manager = _manager()
    first_id, _ = manager.create()
    second_id, _ = manager.create()

    # Trận đầu tiên nhận làm hiện tại vì lúc đó chưa có trận nào; trận thứ hai thì không
    assert manager.current_match_id == first_id

    # Muốn chuyển thì phải nói rõ
    third_id, _ = manager.create(make_current=True)
    assert manager.current_match_id == third_id

    assert manager.set_current(first_id) is True
    assert manager.current_match_id == first_id
    assert manager.set_current("khong-ton-tai") is False
    assert manager.current_match_id == first_id


def test_get_current_creates_default_match_when_empty():
    """Route cũ không truyền match_id vẫn phải hoạt động ngay từ lần gọi đầu."""
    manager = _manager()
    assert manager.current_match_id is None

    referee = manager.get_current()
    assert referee is not None
    assert manager.current_match_id is not None
    # Gọi lần nữa phải trả về đúng trận đó, không tạo thêm
    assert manager.get_current() is referee
    assert len(manager.list_matches()) == 1


def test_unknown_match_id_returns_none():
    manager = _manager()
    assert manager.get("khong-ton-tai") is None


def test_list_matches_reports_progress_newest_first():
    manager = _manager()
    manager.create({"name": "Trận cũ", "model_key": "mock"}, {"model_key": "mock"})
    newest_id, newest = manager.create({"name": "Trận mới", "model_key": "mock"},
                                       {"model_key": "mock"})
    newest.step()

    summaries = manager.list_matches()
    assert len(summaries) == 2
    # Sắp xếp theo số thứ tự tạo, không theo dấu thời gian: hai trận này được tạo trong
    # cùng một giây nên dấu thời gian không phân biệt được thứ tự.
    assert summaries[0]["match_id"] == newest_id
    assert summaries[0]["plies"] == 1
    assert summaries[0]["red"] == "Trận mới"
    # Trận đang xem vẫn là trận đầu, vì create() không cướp màn hình
    assert summaries[0]["is_current"] is False
    assert summaries[1]["is_current"] is True


def test_delete_moves_current_to_another_match():
    manager = _manager()
    first_id, _ = manager.create()
    second_id, _ = manager.create()

    assert manager.delete(second_id) is True
    assert manager.current_match_id == first_id
    assert manager.get(second_id) is None
    assert manager.delete(second_id) is False


def test_eviction_keeps_capacity_and_never_drops_current():
    """Vượt ngưỡng thì loại trận cũ nhất, nhưng trận đang xem phải được giữ lại."""
    manager = _manager()
    first_id, _ = manager.create()
    manager.set_current(first_id)

    for _ in range(MAX_ACTIVE_MATCHES + 5):
        manager.create()

    assert len(manager.list_matches()) <= MAX_ACTIVE_MATCHES
    assert manager.get(first_id) is not None, "trận đang xem không được bị loại"


def test_matches_share_one_analysis_engine():
    """Mỗi tiến trình Pikafish tốn ~50MB cho bảng NNUE — không mở một cái cho mỗi trận."""
    sentinel = object()
    manager = MatchManager(analysis_engine=sentinel)
    _, first = manager.create()
    _, second = manager.create()

    assert first.analysis_engine is sentinel
    assert second.analysis_engine is sentinel
