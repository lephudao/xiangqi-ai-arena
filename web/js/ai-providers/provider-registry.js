/**
 * Chọn client theo model và lấy key từ kho.
 *
 * Danh mục model do Python cung cấp (`browser_bridge.describe_models`), không chép sang JS.
 */

import { getKey, providerForEnv } from "../key-vault.js";
import * as anthropic from "./anthropic-client.js";
import * as gemini from "./gemini-client.js";
import * as openaiCompatible from "./openai-compatible-client.js";

const CLIENTS = {
    anthropic,
    gemini,
    openai_compatible: openaiCompatible,
};

let catalog = { models: [], move_schema: null };

/** Nạp danh mục từ Python. Gọi một lần sau khi Pyodide sẵn sàng. */
export function setCatalog(describeModelsResult) {
    catalog = describeModelsResult;
}

export function listModels() {
    return catalog.models;
}

export function getModel(modelKey) {
    return catalog.models.find((model) => model.key === modelKey) ?? null;
}

/** Kỳ thủ này có cần trình duyệt gọi API không? Mock/Người/Pikafish thì không. */
export function needsBrowserCall(modelKey) {
    const model = getModel(modelKey);
    return model !== null && model.provider in CLIENTS;
}

/**
 * Model đã sẵn sàng đấu chưa: có trong danh mục, chạy được ở trình duyệt, và đã có key.
 * Trả { ok, reason } — `reason` hiện thẳng lên giao diện trước khi bắt đầu trận, thay vì
 * để người dùng bấm xong mới thấy trận đứng im.
 */
export function checkReady(modelKey) {
    const model = getModel(modelKey);
    if (!model) return { ok: false, reason: `Không có model '${modelKey}' trong danh mục` };
    if (!model.available) {
        return { ok: false, reason: `${model.label} chỉ chạy được ở bản local` };
    }
    if (!model.needs_api_key) return { ok: true, reason: "" };

    const providerId = providerForEnv(model.api_key_env);
    if (!providerId) return { ok: false, reason: `Chưa hỗ trợ ${model.api_key_env}` };
    if (!getKey(providerId)) {
        return { ok: false, reason: `Chưa có API key cho ${model.label}` };
    }
    return { ok: true, reason: "" };
}

/**
 * Gọi API lấy nước đi. Không bao giờ ném lỗi — mọi trục trặc trả về trong trường `error`
 * để trọng tài đếm vào thống kê lỗi API và ghi vào nhật ký.
 */
export async function decide(modelKey, prompt, { signal } = {}) {
    const model = getModel(modelKey);
    const client = model && CLIENTS[model.provider];
    if (!client) {
        return { error: `Không gọi API được cho model '${modelKey}'`, model_key: modelKey };
    }

    const apiKey = getKey(providerForEnv(model.api_key_env));
    if (!apiKey) {
        return {
            error: `Thiếu API key cho ${model.label}`,
            provider: model.provider,
            model_key: model.key,
        };
    }

    return client.decide({ prompt, apiKey, model, moveSchema: catalog.move_schema, signal });
}
