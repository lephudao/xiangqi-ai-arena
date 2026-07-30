"""
Kỳ thủ Claude, gọi qua SDK chính thức `anthropic`.

Vài điểm bắt buộc đúng với các model Claude hiện tại:
- Dùng adaptive thinking (`thinking={"type": "adaptive"}`); tham số budget_tokens đã bị bỏ
  và sẽ trả lỗi 400.
- KHÔNG gửi temperature/top_p/top_k — các model Opus 5 / Sonnet 5 từ chối với lỗi 400.
- `max_tokens` bao gồm CẢ phần suy nghĩ, nên phải để dư; đặt sát mức câu trả lời sẽ khiến
  phản hồi bị cắt giữa dòng.
- Phải kiểm tra `stop_reason == "refusal"` TRƯỚC khi đọc `content`, vì khi bị từ chối thì
  content rỗng và code đọc content[0] sẽ vỡ.
"""

import json
import time

from engine.model_registry import estimate_cost_usd
from engine.providers.base_provider import MOVE_SCHEMA, MoveDecision, MoveProvider

# Để dư chỗ cho phần suy nghĩ; nước đi + câu thoại chỉ chiếm ~100 token
MAX_TOKENS = 8000
DEFAULT_EFFORT = "low"  # cờ tướng cần nhiều lượt gọi, effort thấp giữ chi phí hợp lý


class AnthropicProvider(MoveProvider):
    def __init__(self, model_info, api_key=None, effort=DEFAULT_EFFORT):
        super().__init__(model_info, api_key)
        self.effort = effort
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            # api_key=None -> SDK tự đọc ANTHROPIC_API_KEY hoặc profile đã đăng nhập
            self._client = anthropic.Anthropic(api_key=self.api_key or None)
        return self._client

    def decide(self, prompt, legal_moves, board=None, side=None):
        started = time.monotonic()
        try:
            response = self._get_client().messages.create(
                **self._build_request(prompt)
            )
        except Exception as exc:
            return self._failure(exc, started)

        latency_ms = int((time.monotonic() - started) * 1000)
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        # Bộ lọc an toàn có thể từ chối yêu cầu: HTTP 200 nhưng content rỗng
        if response.stop_reason == "refusal":
            return self._decision(
                latency_ms, tokens_in, tokens_out,
                error="Model từ chối trả lời (stop_reason=refusal)",
            )

        text_block = next((b for b in response.content if b.type == "text"), None)
        if text_block is None:
            return self._decision(
                latency_ms, tokens_in, tokens_out,
                error=f"Phản hồi không có nội dung text (stop_reason={response.stop_reason})",
            )

        try:
            data = json.loads(text_block.text)
        except json.JSONDecodeError as exc:
            return self._decision(latency_ms, tokens_in, tokens_out,
                                  error=f"Không parse được JSON: {exc}")

        return self._decision(
            latency_ms, tokens_in, tokens_out,
            move_ucci=str(data.get("move_ucci", "")).strip(),
            taunt=data.get("taunt", ""),
            thinking=data.get("analysis", ""),
        )

    def _build_request(self, prompt):
        """
        Ghép tham số theo đúng năng lực của từng đời model.

        Adaptive thinking và `effort` chỉ có ở các model 4.6 trở lên; gửi cho Haiku 4.5
        sẽ bị API từ chối với lỗi 400. Phần phân tích cho video lấy từ trường "analysis"
        trong JSON nên không phụ thuộc thinking block của API.
        """
        output_config = {"format": {"type": "json_schema", "schema": MOVE_SCHEMA}}
        if self.model_info.supports_effort:
            output_config["effort"] = self.effort

        request = {
            "model": self.model_info.model_id,
            "max_tokens": MAX_TOKENS,
            "output_config": output_config,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.model_info.supports_adaptive_thinking:
            request["thinking"] = {"type": "adaptive"}
        return request

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

    def _failure(self, exc, started):
        return MoveDecision(
            latency_ms=int((time.monotonic() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}"[:300],
            provider=self.provider_name,
            model_key=self.model_key,
        )
