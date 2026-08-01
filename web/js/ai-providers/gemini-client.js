/**
 * Kỳ thủ Gemini, gọi thẳng từ trình duyệt.
 *
 * Bản sao của engine/providers/gemini_provider.py — cùng model ID, cùng response_json_schema.
 * Gemini cho trình duyệt gọi thẳng, không cần header đặc biệt nào.
 */

import { errorMessage, failure, parseMoveJson, success } from "./response-shape.js";

const BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models";

export async function decide({ prompt, apiKey, model, moveSchema, signal }) {
    const body = {
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
            responseMimeType: "application/json",
            responseJsonSchema: moveSchema,
        },
    };

    const started = performance.now();
    let response;
    try {
        response = await fetch(`${BASE_URL}/${model.model_id}:generateContent`, {
            method: "POST",
            headers: { "content-type": "application/json", "x-goog-api-key": apiKey },
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

    const usage = payload.usageMetadata ?? {};
    const tokens = {
        tokens_in: usage.promptTokenCount ?? 0,
        // Token suy nghĩ tính vào phần output và có giá — bỏ qua sẽ báo thiếu chi phí
        tokens_out: (usage.candidatesTokenCount ?? 0) + (usage.thoughtsTokenCount ?? 0),
    };

    const parts = payload.candidates?.[0]?.content?.parts ?? [];
    const text = parts.map((part) => part.text ?? "").join("");
    if (!text) {
        const reason = payload.candidates?.[0]?.finishReason ?? "không rõ";
        return failure(model, started, `Gemini trả về phản hồi rỗng (${reason})`, tokens);
    }

    const parsed = parseMoveJson(text);
    return parsed.error
        ? failure(model, started, parsed.error, tokens)
        : success(model, started, parsed, tokens);
}
