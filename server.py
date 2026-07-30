"""
Flask Web Server & API for Xiangqi AI vs AI Studio
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from engine.referee import MatchReferee

app = Flask(__name__, static_folder="web")
CORS(app)

# Global match referee instance
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
    state = match.step()
    return jsonify(state)

@app.route("/api/reset", methods=["POST"])
def reset_match():
    data = request.get_json(silent=True) or {}
    red_cfg = data.get("red_config")
    black_cfg = data.get("black_config")
    match.reset(red_cfg, black_cfg)
    return jsonify(match.get_state())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Xiangqi AI Studio Server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
