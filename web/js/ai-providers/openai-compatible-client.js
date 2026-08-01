/**
 * Kỳ thủ dùng chuẩn API OpenAI /chat/completions — phủ một lúc OpenAI, Grok (xAI), DeepSeek.
 *
 * Bản sao của engine/providers/openai_compatible_provider.py. `base_url` lấy từ danh mục
 * model phía Python, không hardcode ở đây.
 *
 * CHƯA KIỂM CHỨNG bằng key thật — cả ba nhà cung cấp này đều đánh dấu verified=false trong
 * danh mục. Preflight CORS đã thông, nhưng thông CORS không có nghĩa là request đúng.
 */

import { errorMessage, failure, parseMoveJson, success } from "./response-shape.js";

const MAX_TOKENS = 2000;

export async function decide({ prompt, apiKey, model, moveSchema, signal }) {
    const body = {
        model: model.model_id,
        messages: [{ role: "user", content: prompt }],
        max_completion_tokens: MAX_TOKENS,
        response_format: {
            type: "json_schema",
            json_schema: { name: "xiangqi_move", strict: true, schema: moveSchema },
        },
    };

    const started = performance.now();
    let response;
    try {
        response = await fetch(`${model.base_url}/chat/completions`, {
            method: "POST",
            headers: {
                "content-type": "application/json",
                authorization: `Bearer ${apiKey}`,
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
    const tokens = {
        tokens_in: usage.prompt_tokens ?? 0,
        tokens_out: usage.completion_tokens ?? 0,
    };

    const content = payload.choices?.[0]?.message?.content;
    if (!content) {
        const reason = payload.choices?.[0]?.finish_reason ?? "không rõ";
        return failure(model, started, `Phản hồi không có nội dung (${reason})`, tokens);
    }

    const parsed = parseMoveJson(content);
    return parsed.error
        ? failure(model, started, parsed.error, tokens)
        : success(model, started, parsed, tokens);
}
