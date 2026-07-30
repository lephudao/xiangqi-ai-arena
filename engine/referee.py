"""
Xiangqi Referee & Match Controller
Manages game state, turn delegation, referee commentary, and match lifecycle.
"""

from engine.xiangqi_engine import XiangqiBoard
from engine.ai_agent import AIAgent

class MatchReferee:
    def __init__(self, red_config=None, black_config=None):
        self.board = XiangqiBoard()
        self.red_config = red_config or {"name": "ChatGPT (Đỏ)", "provider": "mock", "model": "mock-red"}
        self.black_config = black_config or {"name": "Claude (Đen)", "provider": "mock", "model": "mock-black"}
        
        self.red_agent = AIAgent(
            provider=self.red_config.get("provider", "mock"),
            model_name=self.red_config.get("model", ""),
            api_key=self.red_config.get("api_key", "")
        )
        self.black_agent = AIAgent(
            provider=self.black_config.get("provider", "mock"),
            model_name=self.black_config.get("model", ""),
            api_key=self.black_config.get("api_key", "")
        )

        self.game_over = False
        self.winner = None
        self.last_move = None
        self.move_logs = []
        self.referee_log = ["Trọng tài Python: Trận đấu Cờ Tướng giữa " + self.red_config["name"] + " và " + self.black_config["name"] + " chính thức BẮT ĐẦU!"]

    def reset(self, red_config=None, black_config=None):
        if red_config:
            self.red_config = red_config
        if black_config:
            self.black_config = black_config

        self.board = XiangqiBoard()
        self.red_agent = AIAgent(
            provider=self.red_config.get("provider", "mock"),
            model_name=self.red_config.get("model", ""),
            api_key=self.red_config.get("api_key", "")
        )
        self.black_agent = AIAgent(
            provider=self.black_config.get("provider", "mock"),
            model_name=self.black_config.get("model", ""),
            api_key=self.black_config.get("api_key", "")
        )

        self.game_over = False
        self.winner = None
        self.last_move = None
        self.move_logs = []
        self.referee_log = ["Trọng tài Python: Trận đấu đã được lập lại thành công! Trận mới BẮT ĐẦU!"]

    def step(self):
        """
        Executes one turn of the match.
        Returns match update state dict.
        """
        if self.game_over:
            return self.get_state()

        current_turn = self.board.turn  # 'w' for Red, 'b' for Black
        side_name = self.red_config["name"] if current_turn == 'w' else self.black_config["name"]
        agent = self.red_agent if current_turn == 'w' else self.black_agent

        legal_moves = self.board.generate_legal_moves(current_turn)

        if not legal_moves:
            self.game_over = True
            opponent_name = self.black_config["name"] if current_turn == 'w' else self.red_config["name"]
            self.winner = opponent_name
            ref_msg = f"Trọng tài: {side_name} đã HẾT NƯỚC ĐỊ HỢP LỆ! {opponent_name} GIÀNH CHIẾN THẮNG!"
            self.referee_log.append(ref_msg)
            return self.get_state()

        # Request move from AI
        fen = self.board.to_fen()
        ai_res = agent.get_move(fen, legal_moves, side_name, current_turn)

        ucci_move = ai_res.get("move_ucci", "")
        reasoning = ai_res.get("reasoning", "")

        # Push move into board
        success, msg = self.board.push_ucci(ucci_move)

        if not success:
            # Fallback if invalid
            fallback_move = legal_moves[0]
            self.board.push_ucci(fallback_move)
            ref_msg = f"Trọng tài: {side_name} đưa nước đi lỗi ('{ucci_move}'). Trọng tài bắt buộc chọn lại '{fallback_move}'!"
            self.referee_log.append(ref_msg)
            vi_text = self.board.move_to_vietnamese_text(fallback_move)
            self.last_move = {
                "side": current_turn,
                "player": side_name,
                "ucci": fallback_move,
                "vi_text": vi_text,
                "reasoning": reasoning + " (Trọng tài đã điều chỉnh nước đi)"
            }
        else:
            vi_text = self.board.move_to_vietnamese_text(ucci_move)
            self.last_move = {
                "side": current_turn,
                "player": side_name,
                "ucci": ucci_move,
                "vi_text": vi_text,
                "reasoning": reasoning
            }
            self.referee_log.append(f"Lượt #{len(self.move_logs)+1}: {side_name} đi {vi_text} [{ucci_move}]")

        self.move_logs.append(self.last_move)

        # Check if next turn has legal moves
        next_turn = self.board.turn
        next_legal = self.board.generate_legal_moves(next_turn)
        if not next_legal:
            self.game_over = True
            self.winner = side_name
            self.referee_log.append(f"Trọng tài: CHIẾU BÍ! {side_name} CHIẾN THẮNG TRẬN ĐẤU!")

        return self.get_state()

    def get_state(self):
        return {
            "fen": self.board.to_fen(),
            "turn": self.board.turn,  # 'w' or 'b'
            "turn_player": self.red_config["name"] if self.board.turn == 'w' else self.black_config["name"],
            "move_number": self.board.move_number,
            "game_over": self.game_over,
            "winner": self.winner,
            "last_move": self.last_move,
            "red_config": self.red_config,
            "black_config": self.black_config,
            "history_count": len(self.move_logs),
            "referee_log": self.referee_log[-5:] # last 5 logs
        }
