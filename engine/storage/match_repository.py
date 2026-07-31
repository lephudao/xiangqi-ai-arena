"""
Lưu và đọc trận đấu bằng SQLite (thư viện chuẩn, không thêm phụ thuộc).

Nguyên tắc: GHI NGAY sau mỗi nước đi. Một trận LLM dài có thể chạy 30-60 phút và tốn tiền
API thật; nếu chỉ ghi lúc kết thúc thì mất điện hay lỗi mạng là mất trắng cả trận.

Mỗi nước lưu kèm `fen_after` để replay chỉ cần đọc cơ sở dữ liệu — không gọi lại API,
không chạy lại engine.
"""

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime

from engine.storage.elo_rating import STARTING_ELO, score_from_result, update_ratings

SCHEMA_VERSION = 1
DEFAULT_DB_PATH = "data/arena.db"
_SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


class MatchRepository:
    """
    Kho lưu trận. Dùng được từ nhiều luồng: Flask chạy threaded nên mỗi luồng cần kết nối
    riêng (sqlite3 không cho dùng chung kết nối giữa các luồng).
    """

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    # --- Kết nối ---

    def _connect(self):
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.db_path, timeout=15)
            connection.row_factory = sqlite3.Row
            # WAL cho phép đọc (replay, bảng xếp hạng) trong khi trận khác đang ghi
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection = connection
        return connection

    def _init_schema(self):
        connection = self._connect()
        with open(_SCHEMA_FILE, encoding="utf-8") as handle:
            connection.executescript(handle.read())
        row = connection.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            connection.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        connection.commit()

    def close(self):
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    # --- Kỳ thủ ---

    def ensure_player(self, model_key, label, provider=None):
        """Tạo kỳ thủ nếu chưa có; cập nhật nhãn nếu đã có."""
        connection = self._connect()
        connection.execute(
            """
            INSERT INTO players (model_key, label, provider, elo) VALUES (?, ?, ?, ?)
            ON CONFLICT (model_key) DO UPDATE SET label = excluded.label
            """,
            (model_key, label, provider, STARTING_ELO),
        )
        connection.commit()

    def leaderboard(self):
        """Bảng xếp hạng theo Elo giảm dần."""
        rows = self._connect().execute(
            """
            SELECT model_key, label, provider, elo, matches, wins, losses, draws
            FROM players
            WHERE matches > 0
            ORDER BY elo DESC, matches DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    # --- Vòng đời trận ---

    def create_match(self, red, black, initial_fen, match_id=None):
        """
        Mở bản ghi trận mới. `red`/`black` là dict {model_key, name, provider}.
        Trả match_id.
        """
        match_id = match_id or uuid.uuid4().hex[:12]
        # Nhãn trong bảng xếp hạng là tên MODEL, không phải tên tuỳ chỉnh của một trận.
        # Nếu lấy tên tuỳ chỉnh thì đặt tên "Kỳ thủ B" một lần là nhãn của model đó bị đổi
        # vĩnh viễn, và bảng xếp hạng không còn biết đang xếp hạng model nào.
        self.ensure_player(red["model_key"], red.get("label") or red["model_key"],
                           red.get("provider"))
        self.ensure_player(black["model_key"], black.get("label") or black["model_key"],
                           black.get("provider"))

        connection = self._connect()
        connection.execute(
            """
            INSERT INTO matches (id, red_model_key, black_model_key, red_name, black_name,
                                 started_at, initial_fen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (match_id, red["model_key"], black["model_key"],
             red.get("name", red["model_key"]), black.get("name", black["model_key"]),
             datetime.now().isoformat(timespec="seconds"), initial_fen),
        )
        connection.commit()
        return match_id

    def append_move(self, match_id, ply, move, fen_after, in_check_after=False):
        """
        Ghi một nước đi. `move` là dict last_move của trọng tài.

        Dùng INSERT OR REPLACE để ghi lại cùng ply không làm vỡ (ví dụ khi nhập lại file JSON
        đã có), thay vì báo lỗi khoá trùng.
        """
        evaluation = move.get("evaluation") or {}
        tokens = move.get("tokens") or {}
        connection = self._connect()
        connection.execute(
            """
            INSERT OR REPLACE INTO moves (
                match_id, ply, side, ucci, vi_notation, fen_after, in_check_after,
                cp_before, cp_after, cp_loss, quality, accuracy, engine_bestmove, engine_pv,
                analysis, taunt, attempts, referee_override, error,
                latency_ms, tokens_in, tokens_out, cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id, ply, move["side"], move["ucci"], move["vi_text"],
                fen_after, int(bool(in_check_after)),
                evaluation.get("cp_before"), evaluation.get("cp_after"),
                evaluation.get("cp_loss"), evaluation.get("quality"),
                evaluation.get("accuracy"), evaluation.get("engine_bestmove"),
                " ".join(evaluation.get("engine_pv") or []),
                move.get("thinking"), move.get("reasoning"),
                json.dumps(move.get("attempts") or [], ensure_ascii=False),
                move.get("referee_override"), move.get("error"),
                move.get("latency_ms"), tokens.get("in"), tokens.get("out"),
                move.get("cost_usd"),
            ),
        )
        connection.execute("UPDATE matches SET total_plies = ? WHERE id = ?", (ply, match_id))
        connection.commit()

    def finish_match(self, match_id, state, stats, stopped_reason=None, apply_elo=True):
        """
        Chốt kết quả trận và cập nhật Elo.

        Elo CHỈ tính khi trận kết thúc theo luật cờ. Trận dừng vì hết giới hạn nước hoặc
        hết ngân sách không phản ánh sức mạnh nên không được tính vào xếp hạng.
        """
        connection = self._connect()
        connection.execute(
            """
            UPDATE matches SET
                ended_at = ?, status = ?, winner_side = ?, result_reason = ?,
                stopped_reason = ?, total_plies = ?,
                red_accuracy = ?, black_accuracy = ?,
                red_blunders = ?, black_blunders = ?,
                red_illegal = ?, black_illegal = ?,
                red_cost_usd = ?, black_cost_usd = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                state["result_status"], state.get("winner_side"), state["result_reason"],
                stopped_reason, state["history_count"],
                stats["red"].get("accuracy"), stats["black"].get("accuracy"),
                stats["red"]["blunders"], stats["black"]["blunders"],
                stats["red"]["illegal_attempts"], stats["black"]["illegal_attempts"],
                stats["red"]["cost_usd"] if stats["red"]["cost_known"] else None,
                stats["black"]["cost_usd"] if stats["black"]["cost_known"] else None,
                match_id,
            ),
        )
        connection.commit()

        if apply_elo:
            self._apply_elo(match_id, state["result_status"])

    def _apply_elo(self, match_id, status):
        """Cập nhật Elo và bảng thành tích. Bỏ qua nếu trận dở dang hoặc đã tính rồi."""
        red_score = score_from_result(status, 'w')
        if red_score is None:
            return

        connection = self._connect()
        match = connection.execute(
            "SELECT red_model_key, black_model_key, elo_applied FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()
        if match is None or match["elo_applied"]:
            return  # tránh tính Elo hai lần cho cùng một trận

        red_key, black_key = match["red_model_key"], match["black_model_key"]
        elos = {
            row["model_key"]: row["elo"]
            for row in connection.execute(
                "SELECT model_key, elo FROM players WHERE model_key IN (?, ?)",
                (red_key, black_key),
            )
        }
        new_red, new_black = update_ratings(
            elos.get(red_key, STARTING_ELO), elos.get(black_key, STARTING_ELO), red_score
        )

        for model_key, new_elo, score in (
            (red_key, new_red, red_score),
            (black_key, new_black, 1.0 - red_score),
        ):
            connection.execute(
                """
                UPDATE players SET
                    elo = ?, matches = matches + 1,
                    wins = wins + ?, draws = draws + ?, losses = losses + ?
                WHERE model_key = ?
                """,
                (new_elo, 1 if score == 1.0 else 0, 1 if score == 0.5 else 0,
                 1 if score == 0.0 else 0, model_key),
            )

        connection.execute("UPDATE matches SET elo_applied = 1 WHERE id = ?", (match_id,))
        connection.commit()

    # --- Đọc để replay ---

    def list_matches(self, limit=50):
        rows = self._connect().execute(
            """
            SELECT id, red_name, black_name, red_model_key, black_model_key,
                   started_at, ended_at, status, result_reason, stopped_reason, total_plies,
                   red_accuracy, black_accuracy, red_blunders, black_blunders
            FROM matches
            ORDER BY started_at DESC, rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_match(self, match_id):
        row = self._connect().execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        return dict(row) if row else None

    def get_moves(self, match_id):
        """Toàn bộ nước đi theo thứ tự — đủ để replay không cần API."""
        rows = self._connect().execute(
            "SELECT * FROM moves WHERE match_id = ? ORDER BY ply", (match_id,)
        ).fetchall()
        moves = []
        for row in rows:
            move = dict(row)
            move["attempts"] = json.loads(move["attempts"] or "[]")
            move["engine_pv"] = (move["engine_pv"] or "").split()
            move["in_check_after"] = bool(move["in_check_after"])
            moves.append(move)
        return moves

    def delete_match(self, match_id):
        connection = self._connect()
        cursor = connection.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        connection.execute("DELETE FROM moves WHERE match_id = ?", (match_id,))
        connection.commit()
        return cursor.rowcount > 0
