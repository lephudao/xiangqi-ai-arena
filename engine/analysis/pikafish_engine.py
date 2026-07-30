"""
Giao tiếp với Pikafish (engine cờ tướng mã nguồn mở) qua protocol UCI.

Pikafish đóng vai TRỌNG TÀI CHẤM ĐIỂM: nó đánh giá thế cờ sau khi AI đã tự quyết định
nước đi, chứ không chọn nước hộ AI.

Hai điểm dễ sai khi dùng UCI, đã xử lý ở đây:
1. Điểm `score` luôn tính theo góc nhìn của BÊN TỚI LƯỢT, nên khi so sánh hai thế cờ
   liên tiếp phải đảo dấu (xem move_quality_scorer).
2. Phải đọc hết output tới dòng `bestmove`, không được gửi `quit` sớm — gửi sớm thì engine
   bỏ dở tìm kiếm và trả về nước đi đầu tiên nó thấy.
"""

import os
import queue
import subprocess
import threading
from dataclasses import dataclass, field

# Điểm quy đổi cho thế bị chiếu bí, để phép trừ centipawn không bị vỡ
MATE_SCORE = 30000

DEFAULT_MOVETIME_MS = 300
HANDSHAKE_TIMEOUT_S = 10
READ_TIMEOUT_MARGIN_S = 5


@dataclass
class EngineEval:
    """Kết quả đánh giá một thế cờ, theo góc nhìn của bên tới lượt."""

    cp: int = 0                       # centipawn; thế bị chiếu bí quy về ±MATE_SCORE
    mate_in: int = None               # số nước tới chiếu bí (None nếu không có)
    bestmove: str = ""                # nước đi tốt nhất theo engine
    pv: list = field(default_factory=list)
    depth: int = 0

    @property
    def is_mate(self):
        return self.mate_in is not None


def _mate_to_cp(mate_in):
    """mate n > 0: bên tới lượt sắp thắng. mate 0 hoặc n < 0: bên tới lượt đang bị bí."""
    if mate_in == 0:
        return -MATE_SCORE
    magnitude = MATE_SCORE - abs(mate_in) * 100
    return magnitude if mate_in > 0 else -magnitude


class PikafishEngine:
    """
    Bọc một tiến trình Pikafish dùng lâu dài.

    Thiếu binary thì `is_available` trả False và `analyse()` trả None — hệ thống vẫn chạy
    trận bình thường, chỉ mất phần chấm điểm. Không bao giờ để việc thiếu engine làm sập trận.
    """

    def __init__(self, engine_path=None, nnue_path=None, movetime_ms=None, threads=1, hash_mb=64):
        self.engine_path = engine_path or os.environ.get("PIKAFISH_PATH", "engine/bin/pikafish")
        self.nnue_path = nnue_path or os.environ.get("PIKAFISH_NNUE_PATH") or self._default_nnue()
        self.movetime_ms = int(movetime_ms or os.environ.get("PIKAFISH_MOVETIME_MS", DEFAULT_MOVETIME_MS))
        self.threads = threads
        self.hash_mb = hash_mb

        self._process = None
        self._output_queue = queue.Queue()
        self._reader_thread = None
        self._lock = threading.Lock()
        self.unavailable_reason = None

        # Cache kết quả gần nhất: thế cờ SAU nước đi N chính là thế cờ TRƯỚC nước đi N+1,
        # và cùng góc nhìn bên đi, nên mỗi nước chỉ cần 1 lần phân tích thay vì 2.
        self._cached_key = None
        self._cached_result = None

    def _default_nnue(self):
        candidate = os.path.join(os.path.dirname(self.engine_path or ""), "pikafish.nnue")
        return candidate if os.path.exists(candidate) else None

    # --- Vòng đời tiến trình ---

    @property
    def is_available(self):
        if self._process is not None and self._process.poll() is None:
            return True
        if self.unavailable_reason:
            return False
        return self._start()

    def _start(self):
        if not os.path.exists(self.engine_path):
            self.unavailable_reason = (
                f"Không tìm thấy engine tại '{self.engine_path}'. "
                f"Chạy ./scripts/install-pikafish.sh để cài."
            )
            return False

        try:
            self._process = subprocess.Popen(
                [os.path.abspath(self.engine_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(self.engine_path)),
            )
        except OSError as exc:
            self.unavailable_reason = f"Không khởi động được engine: {exc}"
            return False

        # Đọc stdout bằng thread riêng để mọi lần chờ đều có timeout,
        # tránh treo cứng cả trận nếu engine không phản hồi.
        self._reader_thread = threading.Thread(target=self._pump_output, daemon=True)
        self._reader_thread.start()

        try:
            self._handshake()
        except (TimeoutError, BrokenPipeError, OSError) as exc:
            self.unavailable_reason = f"Engine không hoàn tất handshake UCI: {exc}"
            self.close()
            return False
        return True

    def _pump_output(self):
        for line in self._process.stdout:
            self._output_queue.put(line.strip())
        self._output_queue.put(None)  # dấu hiệu tiến trình đã đóng stdout

    def _send(self, command):
        self._process.stdin.write(f"{command}\n")
        self._process.stdin.flush()

    def _read_until(self, prefix, timeout_s):
        """Đọc tới dòng bắt đầu bằng `prefix`. Trả về toàn bộ các dòng đã đọc."""
        lines = []
        while True:
            try:
                line = self._output_queue.get(timeout=timeout_s)
            except queue.Empty:
                raise TimeoutError(f"engine không trả về '{prefix}' trong {timeout_s}s")
            if line is None:
                raise BrokenPipeError("engine đã đóng kết nối")
            lines.append(line)
            if line.startswith(prefix):
                return lines

    def _handshake(self):
        self._send("uci")
        self._read_until("uciok", HANDSHAKE_TIMEOUT_S)

        if self.nnue_path and os.path.exists(self.nnue_path):
            self._send(f"setoption name EvalFile value {os.path.abspath(self.nnue_path)}")
        self._send(f"setoption name Threads value {self.threads}")
        self._send(f"setoption name Hash value {self.hash_mb}")
        self._send("isready")
        self._read_until("readyok", HANDSHAKE_TIMEOUT_S)

    def close(self):
        if self._process is None:
            return
        try:
            self._send("quit")
            self._process.wait(timeout=3)
        except Exception:
            self._process.kill()
        finally:
            self._process = None

    # --- Phân tích ---

    def analyse(self, fen, movetime_ms=None):
        """
        Đánh giá thế cờ. Trả EngineEval (điểm theo góc nhìn bên tới lượt), hoặc None
        nếu engine không dùng được.
        """
        if not self.is_available:
            return None

        movetime = int(movetime_ms or self.movetime_ms)
        cache_key = (fen, movetime)
        if cache_key == self._cached_key:
            return self._cached_result

        with self._lock:  # một tiến trình engine chỉ xử lý được một tìm kiếm tại một thời điểm
            try:
                self._send(f"position fen {fen}")
                self._send(f"go movetime {movetime}")
                lines = self._read_until("bestmove", movetime / 1000 + READ_TIMEOUT_MARGIN_S)
            except (TimeoutError, BrokenPipeError, OSError) as exc:
                self.unavailable_reason = f"Lỗi khi phân tích: {exc}"
                self.close()
                return None

        result = self._parse_analysis(lines)
        self._cached_key, self._cached_result = cache_key, result
        return result

    def _parse_analysis(self, lines):
        """
        Chọn dòng `info` để lấy điểm và biến chính.

        Ưu tiên dòng có điểm đã chốt VÀ biến chính bắt đầu bằng đúng nước `bestmove`, để
        điểm/pv/bestmove nhất quán với nhau. Dòng upperbound/lowerbound chỉ là điểm tạm
        giữa lúc tìm kiếm nên chỉ dùng khi không còn lựa chọn nào khác.
        """
        evaluation = EngineEval()
        info_lines = []

        for line in lines:
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) > 1 and parts[1] != "(none)":
                    evaluation.bestmove = parts[1]
            elif line.startswith("info ") and " score " in line:
                info_lines.append(line)

        settled = [line for line in info_lines if "upperbound" not in line and "lowerbound" not in line]
        matching_bestmove = [
            line for line in settled
            if evaluation.bestmove and f" pv {evaluation.bestmove}" in line
        ]

        chosen_info = None
        for candidates in (matching_bestmove, settled, info_lines):
            if candidates:
                chosen_info = candidates[-1]
                break

        if chosen_info:
            self._apply_info_line(evaluation, chosen_info)
        return evaluation

    def _apply_info_line(self, evaluation, line):
        tokens = line.split()
        for index, token in enumerate(tokens):
            if token == "depth" and index + 1 < len(tokens):
                evaluation.depth = int(tokens[index + 1])
            elif token == "score" and index + 2 < len(tokens):
                score_type, score_value = tokens[index + 1], int(tokens[index + 2])
                if score_type == "cp":
                    evaluation.cp = score_value
                elif score_type == "mate":
                    evaluation.mate_in = score_value
                    evaluation.cp = _mate_to_cp(score_value)
            elif token == "pv":
                evaluation.pv = tokens[index + 1:]
                break
