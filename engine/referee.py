"""
Trọng tài & điều khiển trận đấu: quản lý trạng thái ván, phân lượt, và ghi nhận vi phạm.

Trọng tài là bên DUY NHẤT xác thực nước đi. Khi AI đưa nước sai luật, trọng tài cho đi lại
tối đa MAX_MOVE_ATTEMPTS lần kèm lý do cụ thể, đếm số lần sai, và chỉ chọn thay khi AI
hoàn toàn không đưa được nước hợp lệ.
"""

from engine.analysis import PikafishEngine, average_accuracy, score_move
from engine.prompt_builder import build_move_prompt
from engine.providers import MoveDecision, create_provider
from engine.xiangqi import STATUS_DRAW, STATUS_ONGOING, XiangqiBoard

MAX_MOVE_ATTEMPTS = 3
REFEREE_LOG_LIMIT = 200

# Ngưỡng cp_loss để trọng tài bình luận nước dở — dùng làm cao trào cho video
BLUNDER_COMMENT_THRESHOLD = 500

# Phân biệt "không truyền engine -> tự tạo" với "truyền None -> tắt chấm điểm hẳn"
# (tắt chấm điểm cần cho test và cho chế độ chạy giải đấu nhanh).
AUTO_ANALYSIS_ENGINE = object()

DEFAULT_RED_CONFIG = {"name": "Kỳ thủ Đỏ", "model_key": "mock"}
DEFAULT_BLACK_CONFIG = {"name": "Kỳ thủ Đen", "model_key": "mock"}


def normalize_config(config, fallback_name):
    """
    Điền các trường thiếu trong cấu hình kỳ thủ.

    Client chỉ cần gửi model_key; tên hiển thị tự lấy từ nhãn model trong danh mục để
    API không vỡ khi thiếu trường (trước đây thiếu "name" là KeyError làm sập /api/reset).
    """
    from engine.model_registry import get_model

    config = dict(config or {})
    config.setdefault("model_key", "mock")
    if not config.get("name"):
        model = get_model(config["model_key"])
        config["name"] = model.label if model else fallback_name
    return config

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
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "cost_known": True,  # False khi có model chưa có bảng giá
    }


class MatchReferee:
    def attach_recorder(self, repository, match_id=None):
        """
        Gắn kho lưu trữ để ghi lại trận. Ghi ngay sau MỖI nước đi, vì một trận LLM chạy
        30-60 phút và tốn tiền API thật — chỉ ghi lúc kết thúc là mất trắng nếu gặp sự cố.
        """
        from engine.model_registry import get_model

        def side_info(config):
            model = get_model(config.get("model_key", "mock"))
            return {
                "model_key": config.get("model_key", "mock"),
                "name": config["name"],
                "provider": model.provider if model else None,
            }

        self.recorder = repository
        self.record_id = repository.create_match(
            side_info(self.red_config), side_info(self.black_config),
            initial_fen=self.board.to_fen(), match_id=match_id,
        )
        return self.record_id

    def __init__(self, red_config=None, black_config=None, analysis_engine=AUTO_ANALYSIS_ENGINE):
        self.red_config = normalize_config(red_config or DEFAULT_RED_CONFIG, "Kỳ thủ Đỏ")
        self.black_config = normalize_config(black_config or DEFAULT_BLACK_CONFIG, "Kỳ thủ Đen")
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
        """Tạo kỳ thủ từ cấu hình; ghi log nếu phải thay thế (ví dụ thiếu API key)."""
        provider, note = create_provider(
            config.get("model_key", "mock"),
            api_key=config.get("api_key"),
            effort=config.get("effort"),
            analysis_engine=self.analysis_engine,
        )
        if note:
            self._pending_notes.append(f"Trọng tài: {config.get('name', '?')} — {note}")
        return provider

    def _start_new_game(self, opening_message):
        self.board = XiangqiBoard()
        # Ghi chú phát sinh khi tạo kỳ thủ (thiếu API key, model không tồn tại...) —
        # thu ở đây rồi đưa vào log mở đầu để người xem biết ai là AI thật, ai là Mock.
        self._pending_notes = []
        self.red_agent = self._build_agent(self.red_config)
        self.black_agent = self._build_agent(self.black_config)

        self.game_over = False
        self.winner = None            # tên người thắng, None nếu hoà/đang đấu
        self.winner_side = None       # 'w' | 'b' | None — Elo cần bên thắng, không phải tên
        self.result_status = STATUS_ONGOING
        self.result_reason = STATUS_ONGOING
        self.last_move = None
        self.move_logs = []
        self.stats = {'w': _new_player_stats(), 'b': _new_player_stats()}
        self.evaluations = {'w': [], 'b': []}   # MoveEvaluation theo từng bên
        self.current_cp = 0                     # điểm thế cờ theo góc nhìn Đỏ, cho eval bar
        self.recorder = None                    # kho lưu trữ, gắn qua attach_recorder()
        self.record_id = None
        self.hint_used_this_turn = False         # ghi lại để không thổi phồng độ chính xác
        self.referee_log = [opening_message] + self._pending_notes

    def reset(self, red_config=None, black_config=None):
        if red_config:
            self.red_config = normalize_config(red_config, "Kỳ thủ Đỏ")
        if black_config:
            self.black_config = normalize_config(black_config, "Kỳ thủ Đen")

        # Giữ lại kho lưu trữ qua các lần lập lại, nhưng mở BẢN GHI MỚI: đây là một trận
        # khác, không được ghi tiếp vào bản ghi của trận cũ.
        repository = self.recorder
        self._start_new_game("Trọng tài: Trận mới BẮT ĐẦU!")
        if repository is not None:
            self.attach_recorder(repository)

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

        # Kỳ thủ người: dừng lại chờ thao tác chuột, KHÔNG tự đi thay.
        # Đây là lý do tự động đấu phải tạm dừng ở lượt người.
        if self._is_human_turn(side):
            return self.get_state()

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

        return self._apply_move(side, chosen_move, decision, attempts, referee_override)

    def _is_human_turn(self, side=None):
        side = side or self.board.turn
        return getattr(self._agent(side), "is_human", False)

    def submit_human_move(self, ucci):
        """
        Nhận nước đi của người chơi. Trả (thành công, thông báo).

        Xác thực bằng ĐÚNG bộ luật dùng cho AI — người chơi không được ưu ái hơn, và lý do
        từ chối cũng bằng tiếng Việt như khi AI đi sai.
        """
        if self.game_over:
            return False, "Trận đã kết thúc"

        side = self.board.turn
        if not self._is_human_turn(side):
            return False, f"Chưa tới lượt bạn — đang là lượt của {self._player_name(side)}"

        if ucci not in self.board.generate_legal_moves(side):
            return False, self.board.explain_illegal_move(ucci)

        decision = MoveDecision(
            move_ucci=ucci,
            taunt="",
            thinking="",
            latency_ms=0,
            cost_usd=0.0,
            provider="human",
            model_key=self.red_config.get("model_key") if side == 'w'
            else self.black_config.get("model_key"),
        )
        used_hint = self.hint_used_this_turn
        self.hint_used_this_turn = False
        self._apply_move(side, ucci, decision, attempts=[ucci], referee_override=None,
                         used_hint=used_hint)
        return True, self.board.move_history[-1]["vi_notation"]

    def request_hint(self):
        """
        Gợi ý nước đi từ engine cho người chơi.

        Đánh dấu lượt này có dùng gợi ý: nếu không ghi lại thì độ chính xác của người sẽ
        bị thổi phồng và không còn so sánh được với AI.
        """
        if self.analysis_engine is None or not self.analysis_engine.is_available:
            return None, "Chưa cài engine nên không có gợi ý"
        result = self.analysis_engine.analyse(self.board.to_fen())
        if result is None or not result.bestmove:
            return None, "Engine không đưa được gợi ý cho thế cờ này"

        self.hint_used_this_turn = True
        return result.bestmove, self.board.to_vietnamese_notation(result.bestmove)

    def _apply_move(self, side, chosen_move, decision, attempts, referee_override,
                    used_hint=False):
        """Thực hiện nước đi, chấm điểm, ghi nhật ký và lưu trữ. Dùng chung cho AI và người."""
        legal_moves = self.board.generate_legal_moves(side)
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
            "reasoning": decision.taunt,      # câu thoại cho khán giả (TTS đọc câu này)
            "thinking": decision.thinking,    # phân tích thật, hiện ở log chứ không đọc TTS
            "model_key": decision.model_key,
            "tokens": {"in": decision.tokens_in, "out": decision.tokens_out},
            "cost_usd": decision.cost_usd,
            "attempts": attempts,
            "referee_override": referee_override,
            "latency_ms": decision.latency_ms,
            "error": decision.error,
            "used_hint": used_hint,
            "evaluation": evaluation.to_dict() if evaluation else None,
        }
        self.move_logs.append(self.last_move)

        ply = len(self.move_logs)
        if self.recorder is not None:
            self.recorder.append_move(
                self.record_id, ply, self.last_move,
                fen_after=self.board.to_fen(), in_check_after=self.board.is_in_check(),
            )
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
        attempts = []
        feedback = None
        decision = None

        for attempt_index in range(MAX_MOVE_ATTEMPTS):
            # Prompt dựng lại mỗi lần thử để kèm được lý do nước trước bị từ chối.
            # Cùng một template cho mọi provider — điều kiện cần để so sánh công bằng.
            prompt = build_move_prompt(
                self.board, side, legal_moves, self._player_name(side),
                move_logs=self.move_logs, feedback=feedback,
            )
            decision = agent.decide(prompt, legal_moves, board=self.board, side=side)
            self._record_usage(side, decision)

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

    def _record_usage(self, side, decision):
        """
        Cộng token và chi phí. Mỗi LẦN THỬ đều tính tiền, kể cả lần đi sai luật — nếu chỉ
        tính lần thành công thì chi phí báo ra sẽ thấp hơn hoá đơn thật.
        """
        stats = self.stats[side]
        stats["tokens_in"] += decision.tokens_in
        stats["tokens_out"] += decision.tokens_out
        if decision.cost_usd is None:
            stats["cost_known"] = False   # model chưa có bảng giá -> không báo số sai
        else:
            stats["cost_usd"] = round(stats["cost_usd"] + decision.cost_usd, 6)

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

    def _total_cost(self):
        """Chi phí cả trận. None nếu có kỳ thủ dùng model chưa có bảng giá."""
        if not all(self.stats[side]["cost_known"] for side in ('w', 'b')):
            return None
        return round(self.stats['w']["cost_usd"] + self.stats['b']["cost_usd"], 4)

    def _finish(self, result):
        self.game_over = True
        self.result_status = result.status
        self.result_reason = result.reason
        reason_vi = RESULT_MESSAGES_VI.get(result.reason, result.reason)

        self.winner_side = result.winner_side
        if result.status == STATUS_DRAW:
            self.winner = None
            self._log(f"Trọng tài: TRẬN ĐẤU KẾT THÚC — {reason_vi}")
        else:
            self.winner = self._player_name(result.winner_side)
            loser = self._player_name('b' if result.winner_side == 'w' else 'w')
            self._log(f"Trọng tài: {reason_vi}! {self.winner} THẮNG ({loser} thua)")

        if self.recorder is not None:
            self.recorder.finish_match(
                self.record_id, self.get_state(),
                {"red": self.stats['w'], "black": self.stats['b']},
            )

    # --- Trạng thái cho API ---

    def get_state(self):
        return {
            "fen": self.board.to_fen(),
            "turn": self.board.turn,
            "turn_player": self._player_name(self.board.turn),
            "move_number": self.board.move_number,
            "halfmove_clock": self.board.halfmove_clock,
            "in_check": self.board.is_in_check(),
            # Chờ người chơi = tới lượt người và trận chưa xong. Suy ra trực tiếp thay vì
            # giữ một biến trạng thái riêng, vì hai nguồn sự thật sẽ lệch nhau.
            "waiting_for_human": self._is_human_turn() and not self.game_over,
            "is_human_turn": self._is_human_turn() and not self.game_over,
            # Chỉ gửi danh sách nước hợp lệ khi tới lượt người, để giao diện highlight ô đi
            # được mà không phải nhân bản luật cờ sang JavaScript (hai nguồn sự thật dễ lệch)
            "legal_moves": (self.board.generate_legal_moves()
                            if self._is_human_turn() and not self.game_over else []),
            "game_over": self.game_over,
            "winner": self.winner,
            "winner_side": self.winner_side,
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
            "cost_total_usd": self._total_cost(),
            "analysis_enabled": self.analysis_engine is not None and self.analysis_engine.is_available,
            "analysis_note": getattr(self.analysis_engine, "unavailable_reason", None),
        }
