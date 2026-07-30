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

from engine.referee import MatchReferee  # noqa: E402 — phải import sau load_dotenv

app = Flask(__name__, static_folder="web")

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000")
CORS(app, origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()])

match = MatchReferee()


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("web", path)


@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(match.get_state())


@app.route("/api/step", methods=["POST"])
def step_match():
    return jsonify(match.step())


@app.route("/api/reset", methods=["POST"])
def reset_match():
    data = request.get_json(silent=True) or {}
    match.reset(data.get("red_config"), data.get("black_config"))
    return jsonify(match.get_state())


@app.route("/api/history", methods=["GET"])
def get_history():
    """Toàn bộ nước đi + nhật ký trọng tài của trận hiện tại (dùng để dựng video)."""
    return jsonify({"moves": match.move_logs, "referee_log": match.referee_log})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Starting Xiangqi AI Studio Server on http://{host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug, threaded=True)
