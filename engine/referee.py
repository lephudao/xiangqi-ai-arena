"""
Trọng tài & điều khiển trận đấu: quản lý trạng thái ván, phân lượt, và ghi nhận vi phạm.

Trọng tài là bên DUY NHẤT xác thực nước đi. Khi AI đưa nước sai luật, trọng tài cho đi lại
tối đa MAX_MOVE_ATTEMPTS lần kèm lý do cụ thể, đếm số lần sai, và chỉ chọn thay khi AI
hoàn toàn không đưa được nước hợp lệ.
"""

from engine.ai_agent import AIAgent
from engine.analysis import PikafishEngine, average_accuracy, score_move
from engine.xiangqi import STATUS_DRAW, STATUS_ONGOING, XiangqiBoard

MAX_MOVE_ATTEMPTS = 3
REFEREE_LOG_LIMIT = 200

# Ngưỡng cp_loss để trọng tài bình luận nước dở — dùng làm cao trào cho video
BLUNDER_COMMENT_THRESHOLD = 500

# Phân biệt "không truyền engine -> tự tạo" với "truyền None -> tắt chấm điểm hẳn"
# (tắt chấm điểm cần cho test và cho chế độ chạy giải đấu nhanh).
AUTO_ANALYSIS_ENGINE = object()

DEFAULT_RED_CONFIG = {"name": "ChatGPT (Đỏ)", "provider": "mock", "model": "mock-red"}
DEFAULT_BLACK_CONFIG = {"name": "Claude (Đen)", "provider": "mock", "model": "mock-black"}

RESULT_MESSAGES_VI = {
    "checkmate": "CHIẾU BÍ",
    "stalemate": "HẾT NƯỚC ĐI (bị vây chết)",
    "king_captured": "MẤT TƯỚNG",
    "draw_60_moves": "HOÀ — 60 nước không ăn quân",
    "draw_repetition": "HOÀ — lặp lại thế cờ 3 lần",
    "draw_perpetual_check": "HOÀ — nghi vấn chiếu liên tục",
}


def _new_player_stats():
    return {
        "illegal_attempts": 0,
        "api_errors": 0,
        "moves": 0,
        "total_latency_ms": 0,
        "blunders": 0,
        "mistakes": 0,
        "best_moves": 0,
        "accuracy": None,   # None khi chưa chấm được nước nào (thiếu engine)
    }


class MatchReferee:
    def __init__(self, red_config=None, black_config=None, analysis_engine=AUTO_ANALYSIS_ENGINE):
        self.red_config = red_config or dict(DEFAULT_RED_CONFIG)
        self.black_config = black_config or dict(DEFAULT_BLACK_CONFIG)
        # Engine chấm điểm dùng chung cho cả trận. Thiếu engine -> chỉ mất phần chấm điểm,
        # trận vẫn chạy bình thường.
        self.analysis_engine = (
            PikafishEngine() if analysis_engine is AUTO_ANALYSIS_ENGINE else analysis_engine
        )
        self._start_new_game(
            f"Trọng tài: Trận đấu giữa {self.red_config['name']} và "
            f"{self.black_config['name']} chính thức BẮT ĐẦU!"
        )

    def _build_agent(self, config):
        return AIAgent(
            provider=config.get("provider", "mock"),
            model_name=config.get("model", ""),
            api_key=config.get("api_key", ""),
        )

    def _start_new_game(self, opening_message):
        self.board = XiangqiBoard()
        self.red_agent = self._build_agent(self.red_config)
        self.black_agent = self._build_agent(self.black_config)

        self.game_over = False
        self.winner = None            # tên người thắng, None nếu hoà/đang đấu
        self.result_status = STATUS_ONGOING
        self.result_reason = STATUS_ONGOING
        self.last_move = None
        self.move_logs = []
        self.stats = {'w': _new_player_stats(), 'b': _new_player_stats()}
        self.evaluations = {'w': [], 'b': []}   # MoveEvaluation theo từng bên
        self.current_cp = 0                     # điểm thế cờ theo góc nhìn Đỏ, cho eval bar
        self.referee_log = [opening_message]

    def reset(self, red_config=None, black_config=None):
        if red_config:
            self.red_config = red_config
        if black_config:
            self.black_config = black_config
        self._start_new_game("Trọng tài: Trận mới BẮT ĐẦU!")

    # --- Thông tin bên đang đi ---

    def _player_name(self, side):
        return self.red_config["name"] if side == 'w' else self.black_config["name"]

    def _agent(self, side):
        return self.red_agent if side == 'w' else self.black_agent

    def _log(self, message):
        self.referee_log.append(message)
        if len(self.referee_log) > REFEREE_LOG_LIMIT:
            del self.referee_log[:-REFEREE_LOG_LIMIT]

    # --- Vòng đời trận đấu ---

    def step(self):
        """Chạy một lượt của trận đấu. Trả về state dict."""
        if self.game_over:
            return self.get_state()

        # Kiểm tra kết thúc trước khi đi (chiếu bí / hết nước / hoà)
        result = self.board.evaluate_result()
        if result.is_over:
            self._finish(result)
            return self.get_state()

        side = self.board.turn
        legal_moves = self.board.generate_legal_moves(side)
        decision, attempts = self._request_legal_move(side, legal_moves)

        chosen_move = decision.move_ucci
        referee_override = None
        if chosen_move not in legal_moves:
            # AI không đưa được nước hợp lệ sau tất cả các lần thử -> trọng tài chọn thay
            chosen_move = legal_moves[0]
            referee_override = chosen_move
            self._log(
                f"Trọng tài: {self._player_name(side)} không đưa được nước hợp lệ sau "
                f"{len(attempts)} lần thử ({', '.join(attempts) or 'không có phản hồi'}). "
                f"Trọng tài chọn thay: {chosen_move}"
            )

        vi_notation = self.board.to_vietnamese_notation(chosen_move)
        fen_before = self.board.to_fen()
        success, message = self.board.push_ucci(chosen_move)
        if not success:
            # Không nên xảy ra: chosen_move đã nằm trong legal_moves
            self._log(f"Trọng tài: LỖI ENGINE khi thực hiện {chosen_move} — {message}")
            self.game_over = True
            self.result_reason = "engine_error"
            return self.get_state()

        self.stats[side]["moves"] += 1
        self.stats[side]["total_latency_ms"] += decision.latency_ms

        # Chấm điểm SAU khi đi, để engine không ảnh hưởng tới quyết định của AI
        evaluation = score_move(self.analysis_engine, fen_before, self.board.to_fen(), chosen_move)
        self._record_evaluation(side, evaluation)

        self.last_move = {
            "side": side,
            "player": self._player_name(side),
            "ucci": chosen_move,
            "vi_text": vi_notation,
            "reasoning": decision.reasoning,
            "attempts": attempts,
            "referee_override": referee_override,
            "latency_ms": decision.latency_ms,
            "error": decision.error,
            "evaluation": evaluation.to_dict() if evaluation else None,
        }
        self.move_logs.append(self.last_move)

        ply = len(self.move_logs)
        quality_suffix = f" — {evaluation.quality_label_vi}" if evaluation else ""
        self._log(
            f"Nước #{ply}: {self._player_name(side)} đi {vi_notation} "
            f"[{chosen_move}]{quality_suffix}"
        )
        if evaluation and evaluation.cp_loss >= BLUNDER_COMMENT_THRESHOLD:
            self._log(
                f"Trọng tài: Nước đi tai hoạ! {self._player_name(side)} mất "
                f"{evaluation.cp_loss} điểm — engine khuyên {evaluation.engine_bestmove}"
            )

        if self.board.is_in_check():
            self._log(f"Trọng tài: CHIẾU TƯỚNG! {self._player_name(self.board.turn)} bị chiếu!")

        result = self.board.evaluate_result()
        if result.is_over:
            self._finish(result)

        return self.get_state()

    def _request_legal_move(self, side, legal_moves):
        """
        Xin nước đi, cho đi lại kèm lý do khi sai. Trả (decision cuối, danh sách nước đã thử).
        """
        agent = self._agent(side)
        fen = self.board.to_fen()
        in_check = self.board.is_in_check(side)
        attempts = []
        feedback = None
        decision = None

        for attempt_index in range(MAX_MOVE_ATTEMPTS):
            decision = agent.get_move(
                fen, legal_moves, self._player_name(side), side,
                feedback=feedback, in_check=in_check,
            )

            if decision.error:
                self.stats[side]["api_errors"] += 1
                self._log(f"Trọng tài: Lỗi gọi API của {self._player_name(side)} — {decision.error}")
                break

            attempts.append(decision.move_ucci or "(rỗng)")
            if decision.move_ucci in legal_moves:
                if attempt_index > 0:
                    self._log(
                        f"Trọng tài: {self._player_name(side)} đi lại đúng luật ở lần thử "
                        f"thứ {attempt_index + 1}"
                    )
                break

            self.stats[side]["illegal_attempts"] += 1
            feedback = self.board.explain_illegal_move(decision.move_ucci)
            self._log(
                f"Trọng tài: {self._player_name(side)} đi SAI LUẬT "
                f"('{decision.move_ucci}') — {feedback}"
            )

        decision.attempts = attempts
        return decision, attempts

    def _record_evaluation(self, side, evaluation):
        """Cập nhật thống kê chất lượng nước đi và điểm thế cờ cho eval bar."""
        if evaluation is None:
            return

        self.evaluations[side].append(evaluation)
        stats = self.stats[side]
        if evaluation.quality == "blunder":
            stats["blunders"] += 1
        elif evaluation.quality == "mistake":
            stats["mistakes"] += 1
        elif evaluation.quality == "best":
            stats["best_moves"] += 1

        accuracy = average_accuracy(self.evaluations[side])
        stats["accuracy"] = round(accuracy, 1) if accuracy is not None else None

        # Eval bar luôn hiển thị theo góc nhìn Đỏ để người xem không bị lẫn
        self.current_cp = evaluation.cp_after if side == 'w' else -evaluation.cp_after

    def _finish(self, result):
        self.game_over = True
        self.result_status = result.status
        self.result_reason = result.reason
        reason_vi = RESULT_MESSAGES_VI.get(result.reason, result.reason)

        if result.status == STATUS_DRAW:
            self.winner = None
            self._log(f"Trọng tài: TRẬN ĐẤU KẾT THÚC — {reason_vi}")
        else:
            self.winner = self._player_name(result.winner_side)
            loser = self._player_name('b' if result.winner_side == 'w' else 'w')
            self._log(f"Trọng tài: {reason_vi}! {self.winner} THẮNG ({loser} thua)")

    # --- Trạng thái cho API ---

    def get_state(self):
        return {
            "fen": self.board.to_fen(),
            "turn": self.board.turn,
            "turn_player": self._player_name(self.board.turn),
            "move_number": self.board.move_number,
            "halfmove_clock": self.board.halfmove_clock,
            "in_check": self.board.is_in_check(),
            "game_over": self.game_over,
            "winner": self.winner,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "result_text": RESULT_MESSAGES_VI.get(self.result_reason, ""),
            "last_move": self.last_move,
            "red_config": self.red_config,
            "black_config": self.black_config,
            "history_count": len(self.move_logs),
            "material": self.board.material_summary(),
            "stats": {"red": self.stats['w'], "black": self.stats['b']},
            "referee_log": self.referee_log[-5:],
            # Dữ liệu chấm điểm: eval bar + trạng thái engine
            "eval_cp": self.current_cp,
            "analysis_enabled": self.analysis_engine is not None and self.analysis_engine.is_available,
            "analysis_note": getattr(self.analysis_engine, "unavailable_reason", None),
        }
