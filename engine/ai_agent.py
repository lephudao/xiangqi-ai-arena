"""
Tầng tích hợp AI cho trận cờ tướng: Google Gemini, OpenAI GPT, Anthropic Claude, và Mock.

Nguyên tắc quan trọng: agent KHÔNG được tự ý thay nước đi sai bằng nước hợp lệ ngẫu nhiên.
Nước đi nguyên bản của AI luôn được trả về đúng như nó chọn, để trọng tài (referee) đếm
và ghi nhận số lần AI đi sai luật — đây là dữ liệu chính để so sánh sức mạnh các AI.
"""

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

API_TIMEOUT_SECONDS = 30

SYSTEM_PROMPT_TEMPLATE = """Bạn là kỳ thủ Cờ Tướng đại diện cho quân {side_name} ({side_label}).
Phân tích trạng thái bàn cờ và chọn NƯỚC ĐI TỐT NHẤT.

Thông tin bàn cờ:
- Chuỗi FEN: {fen}
- Trạng thái: {check_status}
- Danh sách TẤT CẢ nước đi hợp lệ (UCCI), bạn BẮT BUỘC chọn 1 trong số này:
{legal_moves_str}
{feedback_block}
LƯU Ý:
1. Chỉ được chọn 1 nước đi UCCI nằm trong danh sách trên.
2. Viết 1-2 câu bình luận ngắn bằng tiếng Việt, thể hiện cá tính chiến thuật (hài hước,
   tự tin, hoặc triết lý) để khán giả xem video thấy thú vị.

Chỉ trả về đúng 1 đối tượng JSON nguyên bản (không bọc trong ```):
{{
  "move_ucci": "<nước đi UCCI trong danh sách>",
  "reasoning": "<lời bình luận sắc sảo, ngắn 1-2 câu>"
}}
"""

MOCK_COMMENTARIES_RED = [
    "Khai cuộc bằng nước đi uy lực, làm đối phương phải giật mình!",
    "Quân cờ đã xuất trận, để xem bên Đen đỡ nước này kiểu gì!",
    "Chiến thuật lấy tĩnh chế động, kiểm soát khu vực trung lộ!",
    "Nước đi phế quân để lấy thế công mãnh liệt!",
    "Bẫy giăng sẵn rồi, chỉ chờ đối thủ sa lưới thôi!",
]

MOCK_COMMENTARIES_BLACK = [
    "Đỡ nước đi này quá dễ dàng, chuẩn bị phản công dồn dập!",
    "Cứ thong thả phòng thủ chắc chắn, chờ đối thủ sơ hở!",
    "Nước đi mang tính đột phá cao, không ngờ tới phải không?",
    "Phòng thủ phản công là sở trường của tôi!",
    "Một nước đi khiến đối thủ phải vò đầu bứt tóc!",
]

DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
}


@dataclass
class MoveDecision:
    """Quyết định của AI cho một lượt. `move_ucci` là nguyên văn AI trả về, không bị sửa."""

    move_ucci: str = ""
    reasoning: str = ""
    latency_ms: int = 0
    error: str = None
    provider: str = "mock"
    model: str = ""
    attempts: list = field(default_factory=list)  # trọng tài ghi vào: mọi nước đã thử

    @property
    def failed(self):
        return bool(self.error) or not self.move_ucci


class AIAgent:
    def __init__(self, provider="mock", model_name="", api_key=None):
        self.provider = (provider or "mock").lower()
        self.model_name = model_name or DEFAULT_MODELS.get(self.provider, "")
        self.api_key = api_key or os.environ.get(f"{self._env_prefix()}_API_KEY", "")

    def _env_prefix(self):
        return "GEMINI" if self.provider == "gemini" else self.provider.upper()

    @property
    def is_mock(self):
        return self.provider == "mock" or not self.api_key

    def get_move(self, fen, legal_moves, side_name, side_code, feedback=None, in_check=False):
        """
        Xin một nước đi từ AI. Trả về MoveDecision.

        feedback: lý do nước trước không hợp lệ (nếu đang cho AI đi lại).
        Nước đi trả về KHÔNG được kiểm tra/sửa ở đây — trọng tài chịu trách nhiệm đó.
        """
        if not legal_moves:
            return MoveDecision(
                reasoning="Tôi đã hết nước đi hợp lệ!",
                provider=self.provider,
                model=self.model_name,
            )

        if self.is_mock:
            return self._mock_decision(legal_moves, side_code)

        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            side_name=side_name,
            side_label="Đỏ" if side_code == 'w' else "Đen",
            fen=fen,
            check_status="TƯỚNG CỦA BẠN ĐANG BỊ CHIẾU — bắt buộc phải giải cứu!"
            if in_check else "Bình thường",
            legal_moves_str=", ".join(legal_moves),
            feedback_block=f"\nNƯỚC ĐI TRƯỚC CỦA BẠN BỊ TỪ CHỐI: {feedback}\nHãy chọn lại.\n"
            if feedback else "",
        )

        started = time.monotonic()
        try:
            if self.provider == "gemini":
                move_ucci, reasoning = self._call_gemini(prompt)
            elif self.provider == "openai":
                move_ucci, reasoning = self._call_openai(prompt)
            elif self.provider == "anthropic":
                move_ucci, reasoning = self._call_anthropic(prompt)
            else:
                return self._mock_decision(legal_moves, side_code)

            return MoveDecision(
                move_ucci=(move_ucci or "").strip(),
                reasoning=reasoning,
                latency_ms=int((time.monotonic() - started) * 1000),
                provider=self.provider,
                model=self.model_name,
            )
        except Exception as exc:  # lỗi mạng, lỗi parse, lỗi API — báo thật, không che
            return MoveDecision(
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}"[:200],
                provider=self.provider,
                model=self.model_name,
            )

    def _mock_decision(self, legal_moves, side_code):
        commentaries = MOCK_COMMENTARIES_RED if side_code == 'w' else MOCK_COMMENTARIES_BLACK
        return MoveDecision(
            move_ucci=random.choice(legal_moves),
            reasoning=random.choice(commentaries),
            provider="mock",
            model=self.model_name or "mock-v1",
        )

    # --- Gọi API ---

    def _post_json(self, url, payload, headers):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', **headers},
        )
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode('utf-8'))

    def _parse_move_json(self, raw_text):
        """Trích JSON từ text model trả về; chấp nhận trường hợp bị bọc trong ```json."""
        cleaned = re.sub(r'```(?:json)?\s*', '', raw_text)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        data = json.loads(cleaned)
        return data.get("move_ucci", ""), data.get("reasoning", "")

    def _call_gemini(self, prompt):
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
        }
        data = self._post_json(url, payload, {})
        return self._parse_move_json(data['candidates'][0]['content']['parts'][0]['text'])

    def _call_openai(self, prompt):
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }
        data = self._post_json(
            "https://api.openai.com/v1/chat/completions",
            payload,
            {'Authorization': f'Bearer {self.api_key}'},
        )
        return self._parse_move_json(data['choices'][0]['message']['content'])

    def _call_anthropic(self, prompt):
        payload = {
            "model": self.model_name,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = self._post_json(
            "https://api.anthropic.com/v1/messages",
            payload,
            {'x-api-key': self.api_key, 'anthropic-version': '2023-06-01'},
        )
        return self._parse_move_json(data['content'][0]['text'])
