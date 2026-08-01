/**
 * Một giao diện, hai chế độ chạy.
 *
 *   Local   — máy chủ Flask lo trọng tài, Pikafish chấm điểm, SQLite lưu trận.
 *   Online  — Pyodide lo trọng tài trong trình duyệt, không chấm điểm, Elo trong localStorage.
 *
 * Nhận biết bằng `GET /api/capabilities`: có trả lời thì Local, 404 hoặc lỗi mạng thì Online.
 * Không dùng biến build hay hai file HTML — dựng hai bản riêng thì sớm muộn chúng cũng lệch
 * nhau, mà bản local là công cụ sản xuất video nên không được phép hỏng.
 *
 * `app.js` chỉ gọi các phương thức ở đây và không bao giờ cần biết mình đang ở chế độ nào.
 */

import * as runtime from "./python-runtime.js";
import * as registry from "./ai-providers/provider-registry.js";
import { loadBoard, recordResult } from "./browser-elo.js";

/** Chế độ Local: máy chủ Flask làm tất cả. Giữ nguyên hành vi đang chạy tốt. */
class ServerArena {
    constructor(capabilities) {
        this.capabilities = capabilities;
    }

    async getState() {
        return (await fetch("/api/state")).json();
    }

    async step() {
        return (await fetch("/api/step", { method: "POST" })).json();
    }

    async reset(redConfig, blackConfig) {
        const body = redConfig
            ? JSON.stringify({ red_config: redConfig, black_config: blackConfig })
            : null;
        const response = await fetch("/api/reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
        });
        return response.json();
    }

    async submitHumanMove(ucci) {
        const response = await fetch("/api/human-move", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ucci }),
        });
        const data = await response.json();
        return response.ok
            ? { ok: true, state: data }
            : { ok: false, error: data.error, state: data.state };
    }

    async requestHint() {
        const response = await fetch("/api/hint", { method: "POST" });
        const data = await response.json();
        return response.ok ? { ok: true, ...data } : { ok: false, error: data.error };
    }

    async listModels() {
        return (await fetch("/api/models")).json();
    }

    async leaderboard() {
        const { leaderboard } = await (await fetch("/api/leaderboard")).json();
        return leaderboard;
    }

    async listTtsModels() {
        const { tts_models: models } = await (await fetch("/api/models")).json();
        return models ?? [];
    }
}

/** Chế độ Online: Pyodide + trình duyệt tự gọi API AI bằng key người dùng. */
class BrowserArena {
    constructor() {
        this.capabilities = { mode: "online", analysis: false, database: false, replay: false };
        this._recordedMatch = false;
    }

    async getState() {
        return runtime.getState();
    }

    async reset(redConfig, blackConfig) {
        this._recordedMatch = false;
        return runtime.newMatch(redConfig ?? null, blackConfig ?? null);
    }

    /**
     * Một lượt đầy đủ, kể cả các lần đi lại khi AI đi sai luật.
     *
     * Vòng lặp đi lại nằm ở Python; ở đây chỉ đáp ứng yêu cầu mà nó đưa ra. Nhờ vậy số lần
     * đi sai luật đếm được giống hệt bản local.
     */
    async step() {
        let request = runtime.beginTurn();
        while (request) {
            request = request.external
                ? runtime.submitDecision(await registry.decide(request.model_key, request.prompt))
                // Mock chạy ngay trong Python, không tốn lượt gọi mạng nào
                : runtime.submitLocalDecision();
        }
        const state = runtime.getState();
        this._recordIfFinished(state);
        return state;
    }

    /** Elo chỉ tính trận kết thúc đúng luật cờ — trận bấm dừng giữa chừng không phản ánh sức mạnh. */
    _recordIfFinished(state) {
        if (!state.game_over || this._recordedMatch) return;
        if (!["red_win", "black_win", "draw"].includes(state.result_status)) return;
        this._recordedMatch = true;
        recordResult(state);
    }

    async submitHumanMove(ucci) {
        const result = runtime.submitHumanMove(ucci);
        const state = runtime.getState();
        this._recordIfFinished(state);
        return result.ok
            ? { ok: true, state }
            : { ok: false, error: result.message, state };
    }

    async requestHint() {
        // Gợi ý cần Pikafish, mà Pikafish chạy bằng tiến trình con nên không có ở trình duyệt
        return { ok: false, error: "Gợi ý cần Pikafish — chỉ có ở bản chạy trên máy bạn" };
    }

    async listModels() {
        const catalog = runtime.describeModels();
        return {
            // Lọc bỏ model không gọi được từ trình duyệt (Pikafish, ChatGPT) để người dùng
            // không chọn phải thứ chắc chắn hỏng
            models: catalog.models.filter((model) => model.available),
            default_red: "claude-haiku-4-5",
            default_black: "gemini-3.6-flash",
        };
    }

    async leaderboard() {
        return loadBoard();
    }

    async listTtsModels() {
        return runtime.describeTtsModels();
    }
}

/**
 * Dò chế độ rồi dựng client tương ứng.
 *
 * `onProgress` chỉ được gọi ở chế độ Online, lúc nạp Pyodide (~10MB lần đầu).
 */
export async function createArenaClient(onProgress = () => {}) {
    let capabilities = null;
    try {
        const response = await fetch("/api/capabilities");
        if (response.ok) capabilities = await response.json();
    } catch {
        // Không có máy chủ -> bản tĩnh. Đây là đường đi bình thường của bản online.
    }

    if (capabilities) return new ServerArena(capabilities);

    await runtime.init(onProgress);
    registry.setCatalog(runtime.describeModels());
    return new BrowserArena();
}
