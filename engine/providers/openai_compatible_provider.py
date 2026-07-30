"""
Kỳ thủ dùng chuẩn API OpenAI /chat/completions — phủ một lúc OpenAI, Grok (xAI) và DeepSeek.

CHƯA KIỂM CHỨNG bằng key thật (hiện chỉ có key Gemini và Anthropic). Code viết theo đúng
chuẩn nhưng phải gọi thử ít nhất 1 lần trước khi tin, và model_registry đánh dấu
verified=False cho các model này.

Dùng `requests` (không phải urllib) vì urllib trên bản Python này thiếu CA bundle và
fail SSL với mọi endpoint HTTPS.
"""

import json
import time

from engine.model_registry import estimate_cost_usd
from engine.providers.base_provider import MOVE_SCHEMA, MoveDecision, MoveProvider

REQUEST_TIMEOUT_SECONDS = 60
MAX_TOKENS = 2000


class OpenAICompatibleProvider(MoveProvider):
    def decide(self, prompt, legal_moves, board=None, side=None):
        import requests

        started = time.monotonic()
        payload = {
            "model": self.model_info.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": MAX_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "xiangqi_move", "strict": True, "schema": MOVE_SCHEMA},
            },
        }
        try:
            response = requests.post(
                f"{self.model_info.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            return MoveDecision(
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}"[:300],
                provider=self.provider_name,
                model_key=self.model_key,
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        usage = body.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        try:
            content = body["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return self._decision(latency_ms, tokens_in, tokens_out,
                                  error=f"Phản hồi không đúng định dạng: {exc}")

        return self._decision(
            latency_ms, tokens_in, tokens_out,
            move_ucci=str(data.get("move_ucci", "")).strip(),
            taunt=data.get("taunt", ""),
            thinking=data.get("analysis", ""),
        )

    def _decision(self, latency_ms, tokens_in, tokens_out, **kwargs):
        return MoveDecision(
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=estimate_cost_usd(self.model_key, tokens_in, tokens_out),
            provider=self.provider_name,
            model_key=self.model_key,
            **kwargs,
        )
