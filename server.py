"""
Flask Web Server & API cho Xiangqi AI vs AI Studio.

Mặc định chỉ lắng nghe trên 127.0.0.1 và tắt debug — hệ thống hiện dùng để chạy local
rồi quay màn hình. Khi chuyển sang livestream công khai cần thêm xác thực trước khi
mở HOST ra ngoài (đặt biến môi trường HOST).
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Nạp cấu hình trước khi đọc os.environ. .env.local ghi đè .env để giữ key thật
# ngoài file mẫu được commit.
load_dotenv(".env")
load_dotenv(".env.local", override=True)

from engine.match_manager import MatchManager  # noqa: E402 — phải import sau load_dotenv

app = Flask(__name__, static_folder="web")

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
CORS(app, origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()])

# Nhiều trận cùng lúc, dùng chung một tiến trình engine chấm điểm.
# Các route không có match_id sẽ tác động lên "trận đang xem".
manager = MatchManager()


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("web", path)


def _resolve_match(match_id=None):
    """
    Lấy trận theo id, hoặc trận đang xem nếu không truyền id.
    Trả (referee, phản hồi lỗi) — referee là None khi id không tồn tại.
    """
    if match_id is None:
        return manager.get_current(), None
    referee = manager.get(match_id)
    if referee is None:
        return None, (jsonify({"error": f"Không có trận '{match_id}'"}), 404)
    return referee, None


@app.route("/api/state", methods=["GET"])
@app.route("/api/matches/<match_id>/state", methods=["GET"])
def get_state(match_id=None):
    referee, error = _resolve_match(match_id)
    return error or jsonify(referee.get_state())


@app.route("/api/step", methods=["POST"])
@app.route("/api/matches/<match_id>/step", methods=["POST"])
def step_match(match_id=None):
    referee, error = _resolve_match(match_id)
    return error or jsonify(referee.step())


@app.route("/api/reset", methods=["POST"])
def reset_match():
    """Lập lại trận đang xem, giữ nguyên id trận."""
    data = request.get_json(silent=True) or {}
    referee = manager.get_current()
    referee.reset(data.get("red_config"), data.get("black_config"))
    return jsonify(referee.get_state())


@app.route("/api/matches", methods=["GET"])
def list_matches():
    return jsonify({"matches": manager.list_matches(), "current": manager.current_match_id})


@app.route("/api/matches", methods=["POST"])
def create_match():
    """Mở một trận MỚI song song, không ảnh hưởng trận đang chạy."""
    data = request.get_json(silent=True) or {}
    match_id, referee = manager.create(data.get("red_config"), data.get("black_config"))
    state = referee.get_state()
    state["match_id"] = match_id
    return jsonify(state), 201


@app.route("/api/matches/<match_id>/select", methods=["POST"])
def select_match(match_id):
    """Chuyển trận đang xem — dùng khi quay nhiều trận trong một buổi."""
    if not manager.set_current(match_id):
        return jsonify({"error": f"Không có trận '{match_id}'"}), 404
    return jsonify(manager.get(match_id).get_state())


@app.route("/api/matches/<match_id>", methods=["DELETE"])
def delete_match(match_id):
    if not manager.delete(match_id):
        return jsonify({"error": f"Không có trận '{match_id}'"}), 404
    return "", 204


@app.route("/api/models", methods=["GET"])
def get_models():
    """Danh mục kỳ thủ cho dropdown — UI không hardcode model nữa."""
    from engine.model_registry import DEFAULT_BLACK_MODEL, DEFAULT_RED_MODEL, list_models
    return jsonify({
        "models": list_models(),
        "default_red": DEFAULT_RED_MODEL,
        "default_black": DEFAULT_BLACK_MODEL,
    })


@app.route("/api/history", methods=["GET"])
@app.route("/api/matches/<match_id>/history", methods=["GET"])
def get_history(match_id=None):
    """Toàn bộ nước đi + nhật ký trọng tài (dùng để dựng video)."""
    referee, error = _resolve_match(match_id)
    if error:
        return error
    return jsonify({"moves": referee.move_logs, "referee_log": referee.referee_log})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Starting Xiangqi AI Studio Server on http://{host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug, threaded=True)
