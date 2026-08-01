/**
 * Kho API key phía trình duyệt.
 *
 * Key nằm trong localStorage của chính máy người dùng và đi THẲNG tới nhà cung cấp AI.
 * Không có máy chủ nào của dự án này nhìn thấy key — kể cả khi chạy bản local.
 *
 * Lưu theo NHÀ CUNG CẤP chứ không theo model: một key Anthropic dùng được cho mọi model
 * Claude, bắt nhập lại cho từng model là hành hạ người dùng vô ích.
 */

const STORAGE_PREFIX = "xiangqi-arena.key.";

// Nhãn hiển thị + nơi lấy key miễn phí, để người dùng không phải đi tìm
export const PROVIDERS = [
    { id: "gemini", label: "Google Gemini", signup: "https://aistudio.google.com/apikey" },
    { id: "anthropic", label: "Anthropic (Claude)", signup: "https://console.anthropic.com/settings/keys" },
    { id: "openai", label: "OpenAI (ChatGPT)", signup: "https://platform.openai.com/api-keys" },
    { id: "xai", label: "xAI (Grok)", signup: "https://console.x.ai" },
    { id: "deepseek", label: "DeepSeek", signup: "https://platform.deepseek.com/api_keys" },
];

// Danh mục model dùng tên biến môi trường; quy về id nhà cung cấp để tra key.
const ENV_TO_PROVIDER = {
    GEMINI_API_KEY: "gemini",
    ANTHROPIC_API_KEY: "anthropic",
    OPENAI_API_KEY: "openai",
    XAI_API_KEY: "xai",
    DEEPSEEK_API_KEY: "deepseek",
};

export function providerForEnv(apiKeyEnv) {
    return ENV_TO_PROVIDER[apiKeyEnv] ?? null;
}

export function saveKey(providerId, value) {
    const trimmed = (value ?? "").trim();
    if (!trimmed) {
        clearKey(providerId);
        return;
    }
    localStorage.setItem(STORAGE_PREFIX + providerId, trimmed);
}

export function getKey(providerId) {
    return localStorage.getItem(STORAGE_PREFIX + providerId) ?? "";
}

export function clearKey(providerId) {
    localStorage.removeItem(STORAGE_PREFIX + providerId);
}

export function clearAll() {
    for (const { id } of PROVIDERS) clearKey(id);
}

export function listStoredProviders() {
    return PROVIDERS.filter(({ id }) => getKey(id)).map(({ id }) => id);
}

/**
 * Dạng che để hiện lại trên giao diện: `sk-ant-…4f2a`.
 *
 * Quay màn hình là hoạt động chính của dự án này, nên key không bao giờ được hiện nguyên
 * văn sau khi đã lưu.
 */
export function maskKey(value) {
    if (!value) return "";
    if (value.length <= 10) return "•".repeat(value.length);
    return `${value.slice(0, 6)}…${value.slice(-4)}`;
}

/**
 * Chuỗi này trông giống API key không? Dùng để cảnh báo khi người dùng dán nhầm key vào ô
 * tên kỳ thủ — chỗ đó hiển thị công khai trên overlay và sẽ lộ ngay trong video.
 */
export function looksLikeApiKey(value) {
    const text = (value ?? "").trim();
    return /^(sk-|AIza|xai-|gsk_)/.test(text) && text.length > 16;
}
