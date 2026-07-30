"""
Kỳ thủ Gemini, gọi qua SDK chính thức `google-genai`.

Dùng response_json_schema để đảm bảo phản hồi parse được, nhưng move_ucci vẫn là string
tự do (xem chú thích ở base_provider) để giữ tín hiệu AI có đọc được bàn cờ hay không.
"""

import json
import time

from engine.model_registry import estimate_cost_usd
from engine.providers.base_provider import MOVE_SCHEMA, MoveDecision, MoveProvider


class GeminiProvider(MoveProvider):
    def __init__(self, model_info, api_key=None):
        super().__init__(model_info, api_key)
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            # api_key=None -> SDK tự đọc GEMINI_API_KEY / GOOGLE_API_KEY
            self._client = genai.Client(api_key=self.api_key or None)
        return self._client

    def decide(self, prompt, legal_moves, board=None, side=None):
        from google.genai import types

        started = time.monotonic()
        try:
            response = self._get_client().models.generate_content(
                model=self.model_info.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=MOVE_SCHEMA,
                ),
            )
        except Exception as exc:
            return MoveDecision(
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}"[:300],
                provider=self.provider_name,
                model_key=self.model_key,
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        usage = response.usage_metadata
        tokens_in = usage.prompt_token_count or 0
        tokens_out = usage.candidates_token_count or 0

        raw_text = response.text
        if not raw_text:
            return self._decision(latency_ms, tokens_in, tokens_out,
                                  error="Gemini trả về phản hồi rỗng")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return self._decision(latency_ms, tokens_in, tokens_out,
                                  error=f"Không parse được JSON: {exc}")

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
