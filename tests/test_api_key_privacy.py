"""
Canh giữ việc API key không bị rò rỉ.

Điều kiện bắt buộc để người dùng dám nhập key của chính họ vào bản chạy công khai: key phải
KHÔNG xuất hiện ở bất kỳ đâu ngoài lời gọi tới nhà cung cấp — không trong phản hồi API,
không trong nhật ký trọng tài, không trong cơ sở dữ liệu.

Lỗi thật đã từng có: `get_state()` trả nguyên `red_config` trong đó có `api_key`, nên bất kỳ
ai đọc được `/api/state` đều lấy được key.
"""

import json

import pytest

from engine.referee import MatchReferee, split_config_and_secret
from engine.storage import MatchRepository

SECRET = "sk-day-la-key-bi-mat-khong-duoc-lo"


def _referee_with_key():
    return MatchReferee(
        {"model_key": "mock", "name": "Đỏ", "api_key": SECRET},
        {"model_key": "mock", "name": "Đen"},
        analysis_engine=None,
    )


def test_split_removes_key_from_public_config():
    public_config, api_key = split_config_and_secret(
        {"model_key": "claude-haiku-4-5", "api_key": SECRET}, "dự phòng"
    )
    assert api_key == SECRET
    assert "api_key" not in public_config
    assert public_config["model_key"] == "claude-haiku-4-5"


def test_key_absent_from_public_config():
    referee = _referee_with_key()
    assert "api_key" not in referee.red_config
    assert "api_key" not in referee.black_config


def test_key_absent_from_entire_state_response():
    """Kiểm tra toàn bộ phản hồi, không chỉ vài trường — key có thể lọt qua đường khác."""
    referee = _referee_with_key()
    referee.step()

    dumped = json.dumps(referee.get_state(), ensure_ascii=False)
    assert SECRET not in dumped


def test_key_absent_from_referee_log():
    referee = _referee_with_key()
    for _ in range(3):
        referee.step()

    assert SECRET not in " ".join(referee.referee_log)


def test_key_absent_from_move_history():
    referee = _referee_with_key()
    referee.step()

    assert SECRET not in json.dumps(referee.move_logs, ensure_ascii=False)


def test_key_survives_reset_without_leaking(tmp_path):
    """Lập lại trận vẫn dùng được key cũ nhưng vẫn không lộ ra ngoài."""
    referee = _referee_with_key()
    referee.reset({"model_key": "mock", "name": "Đỏ mới", "api_key": SECRET},
                  {"model_key": "mock"})

    assert referee._api_keys.get('w') == SECRET, "key phải còn dùng được sau khi lập lại"
    assert SECRET not in json.dumps(referee.get_state(), ensure_ascii=False)


def test_key_absent_from_database(tmp_path):
    """Cơ sở dữ liệu được chia sẻ và sao lưu — tuyệt đối không được chứa key."""
    repository = MatchRepository(db_path=str(tmp_path / "privacy.db"))
    referee = _referee_with_key()
    match_id = referee.attach_recorder(repository)
    referee.step()
    referee.step()

    stored = json.dumps(repository.get_match(match_id), ensure_ascii=False)
    stored += json.dumps(repository.get_moves(match_id), ensure_ascii=False)
    assert SECRET not in stored

    # Quét thẳng file cơ sở dữ liệu để chắc chắn không lọt qua cột nào khác
    repository.close()
    raw = (tmp_path / "privacy.db").read_bytes()
    assert SECRET.encode() not in raw
    repository = MatchRepository(db_path=str(tmp_path / "privacy.db"))
    repository.close()


def test_provider_receives_the_key():
    """Chặn key không được làm hỏng chức năng: provider vẫn phải nhận được key."""
    referee = MatchReferee(
        {"model_key": "claude-haiku-4-5", "api_key": SECRET},
        {"model_key": "mock"},
        analysis_engine=None,
    )
    assert referee.red_agent.api_key == SECRET
