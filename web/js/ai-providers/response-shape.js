/**
 * Hình dạng quyết định trả về, dùng chung cho mọi client.
 *
 * Phải khớp đúng tên trường của MoveDecision phía Python. Sai một chữ sẽ bị
 * `decision_from_payload` từ chối thẳng — chủ ý như vậy, vì bỏ qua âm thầm thì biểu hiện ra
 * ngoài chỉ là "AI im lặng không đi", rất tốn công lần ra.
 *
 * KHÔNG tính cost_usd ở đây. JS chỉ báo số token, Python tra bảng giá và tính tiền — hai
 * bảng giá song song là cách chắc chắn để bộ đếm chi phí lệch với hoá đơn thật.
 */

const NO_TOKENS = { tokens_in: 0, tokens_out: 0 };

function elapsedMs(started) {
    return Math.round(performance.now() - started);
}

export function success(model, started, { moveUcci, taunt, thinking }, tokens = NO_TOKENS) {
    return {
        move_ucci: moveUcci,
        taunt,
        thinking,
        latency_ms: elapsedMs(started),
        provider: model.provider,
        model_key: model.key,
        ...tokens,
    };
}

export function failure(model, started, error, tokens = NO_TOKENS) {
    return {
        error: String(error).slice(0, 300),
        latency_ms: elapsedMs(started),
        provider: model.provider,
        model_key: model.key,
        ...tokens,
    };
}

/**
 * Rút thông điệp lỗi từ thân phản hồi.
 *
 * Các nhà cung cấp trả về hình dạng khác nhau: OpenAI/Anthropic/Gemini dùng
 * `{error: {message}}`, còn xAI dùng `{error: "chuỗi"}`. Chỉ đọc `error.message` thì lỗi
 * của xAI biến thành "HTTP 400" trống rỗng, không đủ để người dùng biết phải sửa gì.
 */
export function errorMessage(payload, status) {
    const error = payload?.error;
    if (typeof error === "string" && error) return error;
    if (error?.message) return error.message;
    if (typeof payload?.message === "string" && payload.message) return payload.message;
    return `HTTP ${status}`;
}

/**
 * Đọc JSON nước đi từ phản hồi.
 *
 * `move_ucci` giữ NGUYÊN VĂN model trả về, chỉ cắt khoảng trắng. Không sửa nước sai thành
 * nước hợp lệ — số lần đi sai luật là một thước đo sức mạnh, và là nội dung hấp dẫn nhất
 * cho video.
 */
export function parseMoveJson(rawText) {
    if (!rawText) return { error: "Phản hồi rỗng" };
    let data;
    try {
        data = JSON.parse(rawText);
    } catch (error) {
        return { error: `Không parse được JSON: ${error.message}` };
    }
    return {
        moveUcci: String(data.move_ucci ?? "").trim(),
        taunt: data.taunt ?? "",
        thinking: data.analysis ?? "",
    };
}
