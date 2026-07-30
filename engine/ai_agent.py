"""
AI Agent Integration Layer for Xiangqi Match
Supports Google Gemini, OpenAI GPT, Anthropic Claude, and Mock AI for local testing.
"""

import os
import json
import random
import re
import urllib.request
import urllib.error

SYSTEM_PROMPT_TEMPLATE = """Bạn là kỳ thủ Cờ Tướng đại diện cho quân {side_name} ({side_code}).
Nhiệm vụ của bạn là phân tích trạng thái bàn cờ hiện tại và chọn NƯỚC ĐÍ TỐT NHẤT.

Thông tin bàn cờ:
- Chuỗi FEN: {fen}
- Danh sách tất cả NƯỚC ĐỊ HỢP LỆ (UCCI) bạn BẮT BUỘC phải chọn 1 trong số này:
{legal_moves_str}

LƯU Ý QUAN TRỌNG:
1. Bạn BẮT BUỘC chọn 1 nước đi UCCI duy nhất nằm trong danh sách trên!
2. Đưa ra 1-2 câu phát biểu/bình luận ngắn gọn bằng tiếng Việt thể hiện cá tính chiến thuật (hài hước, tự tin, hoặc triết lý) để khán giả xem video cảm thấy thú vị.

Bạn CHỈ trả về đúng 1 đối tượng JSON nguyên bản (không dùng ```json):
{{
  "move_ucci": "<nước đi UCCI trong danh sách>",
  "move_text": "<mô tả nước đi tiếng Việt>",
  "reasoning": "<lời bình luận sắc sảo, hài hước ngắn 1-2 câu>"
}}
"""

MOCK_COMMENTARIES_RED = [
    "Khai cuộc bằng nước đi uy lực, làm đối phương phải giật mình!",
    "Quân cờ đã xuất trận, để xem bên Đen đỡ nước này kiểu gì!",
    "Chiến thuật lấy tĩnh chế động, kiểm soát khu vực trung lộ!",
    "Nước đi phế quân để lấy thế công mãnh liệt!",
    "Bẫy giăng sẵn rồi, chỉ chờ đối thủ sa lưới thôi!"
]

MOCK_COMMENTARIES_BLACK = [
    "Đơ nước đi này quá dễ dàng, chuẩn bị phản công dồn dập!",
    "Cứ thong thả phòng thủ chắc chắn, chờ đối thủ sơ hở!",
    "Nước đi mang tính đột phá cao, không ngờ tới phải không?",
    "Phòng thủ phản công là sở trường của tôi!",
    "Một nước đi khiến đối thủ phải vò đầu bứt tóc!"
]

class AIAgent:
    def __init__(self, provider="mock", model_name="mock-v1", api_key=None):
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key or os.environ.get(f"{self.provider.upper()}_API_KEY", "")

    def get_move(self, fen, legal_moves, side_name, side_code):
        """
        Returns dict: {"move_ucci": str, "move_text": str, "reasoning": str}
        """
        if not legal_moves:
            return {
                "move_ucci": "",
                "move_text": "Hết nước đi",
                "reasoning": "Tôi đã hết nước đi hợp lệ!"
            }

        if self.provider == "mock" or not self.api_key:
            return self._get_mock_move(legal_moves, side_name, side_code)

        legal_moves_str = ", ".join(legal_moves)
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            side_name=side_name,
            side_code=side_code,
            fen=fen,
            legal_moves_str=legal_moves_str
        )

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt, legal_moves)
            elif self.provider == "openai":
                return self._call_openai(prompt, legal_moves)
            elif self.provider == "anthropic":
                return self._call_anthropic(prompt, legal_moves)
            else:
                return self._get_mock_move(legal_moves, side_name, side_code)
        except Exception as e:
            print(f"Error calling {self.provider} API: {e}. Falling back to Mock.")
            mock_res = self._get_mock_move(legal_moves, side_name, side_code)
            mock_res["reasoning"] += f" (Ghi chú: Đã dùng Mock do lỗi API: {str(e)[:50]})"
            return mock_res

    def _get_mock_move(self, legal_moves, side_name, side_code):
        chosen_ucci = random.choice(legal_moves)
        commentaries = MOCK_COMMENTARIES_RED if side_code == 'w' else MOCK_COMMENTARIES_BLACK
        reasoning = random.choice(commentaries)
        return {
            "move_ucci": chosen_ucci,
            "move_text": f"Di chuyển {chosen_ucci}",
            "reasoning": reasoning
        }

    def _clean_json_response(self, raw_text):
        cleaned = re.sub(r'```json\s*', '', raw_text)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)

    def _call_gemini(self, prompt, legal_moves):
        # REST API fallback to avoid strict library requirement
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name or 'gemini-1.5-flash'}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"}
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            text = res_json['candidates'][0]['content']['parts'][0]['text']
            res = self._clean_json_response(text)
            if res.get("move_ucci") not in legal_moves:
                res["move_ucci"] = random.choice(legal_moves)
            return res

    def _call_openai(self, prompt, legal_moves):
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model_name or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            text = res_json['choices'][0]['message']['content']
            res = self._clean_json_response(text)
            if res.get("move_ucci") not in legal_moves:
                res["move_ucci"] = random.choice(legal_moves)
            return res

    def _call_anthropic(self, prompt, legal_moves):
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model_name or "claude-3-5-haiku-20241022",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            text = res_json['content'][0]['text']
            res = self._clean_json_response(text)
            if res.get("move_ucci") not in legal_moves:
                res["move_ucci"] = random.choice(legal_moves)
            return res
