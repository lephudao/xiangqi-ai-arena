/**
 * Kỳ thủ Claude, gọi thẳng từ trình duyệt.
 *
 * Bản sao của engine/providers/anthropic_provider.py — cùng model ID, cùng schema, cùng
 * max_tokens. Chỉ khác cách gửi request (fetch thay vì SDK). Prompt do Python dựng.
 *
 * Anthropic BẮT BUỘC header `anthropic-dangerous-direct-browser-access` mới cho trình duyệt
 * gọi. Tên header chính là cảnh báo của họ: key nằm ở trình duyệt thì mọi script trên trang
 * đều đọc được. Ở đây chấp nhận được vì là trình duyệt của chính người dùng, key của chính
 * họ, và trang không nạp script bên thứ ba nào.
 */

import { errorMessage, failure, parseMoveJson, success } from "./response-shape.js";

const ENDPOINT = "https://api.anthropic.com/v1/messages";
const API_VERSION = "2023-06-01";

// Để dư chỗ cho phần suy nghĩ; nước đi + câu thoại chỉ chiếm ~100 token
const MAX_TOKENS = 8000;
const DEFAULT_EFFORT = "low";  // cờ tướng cần nhiều lượt gọi, effort thấp giữ chi phí hợp lý

export async function decide({ prompt, apiKey, model, moveSchema, signal }) {
    const outputConfig = { format: { type: "json_schema", schema: moveSchema } };
    if (model.supports_effort) outputConfig.effort = DEFAULT_EFFORT;

    const body = {
        model: model.model_id,
        max_tokens: MAX_TOKENS,
        output_config: outputConfig,
        messages: [{ role: "user", content: prompt }],
    };
    // Adaptive thinking chỉ có từ đời 4.6 trở lên; gửi cho Haiku 4.5 sẽ bị từ chối 400.
    if (model.supports_adaptive_thinking) body.thinking = { type: "adaptive" };

    const started = performance.now();
    let response;
    try {
        response = await fetch(ENDPOINT, {
            method: "POST",
            headers: {
                "content-type": "application/json",
                "x-api-key": apiKey,
                "anthropic-version": API_VERSION,
                "anthropic-dangerous-direct-browser-access": "true",
            },
            body: JSON.stringify(body),
            signal,
        });
    } catch (error) {
        return failure(model, started, `Không gọi được API: ${error.message}`);
    }

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        return failure(model, started, errorMessage(payload, response.status));
    }

    const usage = payload.usage ?? {};
    const tokens = { tokens_in: usage.input_tokens ?? 0, tokens_out: usage.output_tokens ?? 0 };

    // Bộ lọc an toàn có thể từ chối: HTTP 200 nhưng content rỗng. Phải kiểm TRƯỚC khi đọc
    // content, nếu không sẽ vỡ ở content[0].
    if (payload.stop_reason === "refusal") {
        return failure(model, started, "Model từ chối trả lời (stop_reason=refusal)", tokens);
    }

    const textBlock = (payload.content ?? []).find((block) => block.type === "text");
    if (!textBlock) {
        return failure(model, started,
            `Phản hồi không có nội dung text (stop_reason=${payload.stop_reason})`, tokens);
    }

    const parsed = parseMoveJson(textBlock.text);
    return parsed.error
        ? failure(model, started, parsed.error, tokens)
        : success(model, started, parsed, tokens);
}
