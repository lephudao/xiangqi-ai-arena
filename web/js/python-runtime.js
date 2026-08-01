/**
 * Chạy lõi Python của trọng tài ngay trong trình duyệt bằng Pyodide.
 *
 * Đây là lý do bản online và bản local không bao giờ lệch luật cờ: cả hai chạy CÙNG các
 * file .py, không có bản dịch sang JS. Module này chỉ làm ba việc — nạp Pyodide, giải nén
 * engine, và chuyển kiểu dữ liệu qua lại. Mọi quyết định về luật nằm ở phía Python.
 *
 * Pyodide được tự host trong web/vendor/ (cài bằng scripts/install-pyodide.sh) nên trang
 * không phụ thuộc CDN nào.
 */

const PYODIDE_DIR = "/vendor/pyodide/";
const ENGINE_BUNDLE = "/vendor/engine-core.zip";

// File .wasm gần 10MB. Tải trước để đo được tiến trình thật theo byte, rồi loadPyodide gọi
// lại URL đó sẽ trúng cache của trình duyệt. Không làm vậy thì người dùng nhìn màn hình
// đứng im vài chục giây mà không biết còn bao lâu.
const WASM_URL = PYODIDE_DIR + "pyodide.asm.wasm";

let pyodide = null;
let arena = null;

/** Chuyển dict Python sang object JS thường. Không có dòng này thì JS nhận Map và đọc ra undefined. */
function toJs(value) {
    if (value === null || value === undefined) return null;
    return typeof value.toJs === "function"
        ? value.toJs({ dict_converter: Object.fromEntries })
        : value;
}

async function prefetchWithProgress(url, onProgress) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Không tải được ${url} (HTTP ${response.status})`);

    const total = Number(response.headers.get("content-length")) || 0;
    if (!total || !response.body) {
        await response.arrayBuffer();
        return;
    }

    const reader = response.body.getReader();
    let loaded = 0;
    for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        loaded += value.length;
        onProgress(loaded / total);
    }
}

/**
 * Nạp Pyodide và lõi Python. Gọi được nhiều lần, chỉ nạp thật một lần.
 *
 * onProgress({ phase, ratio }) — `ratio` chỉ có nghĩa ở phase "download".
 */
export async function init(onProgress = () => {}) {
    if (pyodide) return;

    onProgress({ phase: "download", ratio: 0 });
    await prefetchWithProgress(WASM_URL, (ratio) => onProgress({ phase: "download", ratio }));

    onProgress({ phase: "boot" });
    const { loadPyodide } = await import(PYODIDE_DIR + "pyodide.mjs");
    pyodide = await loadPyodide({ indexURL: PYODIDE_DIR });

    onProgress({ phase: "engine" });
    const bundle = await fetch(ENGINE_BUNDLE);
    if (!bundle.ok) {
        throw new Error(
            `Thiếu ${ENGINE_BUNDLE}. Chạy ./scripts/build-web-bundle.sh để dựng lại.`
        );
    }
    pyodide.unpackArchive(await bundle.arrayBuffer(), "zip");

    pyodide.runPython(`
import os, sys
_bundle_dir = os.getcwd()
if _bundle_dir not in sys.path:
    sys.path.insert(0, _bundle_dir)
from engine.browser_bridge import BrowserArena, apply_elo, describe_models
`);

    onProgress({ phase: "ready" });
}

/**
 * Danh mục kỳ thủ và schema phản hồi, lấy từ model_registry của Python.
 *
 * JS không giữ bản sao nào của bảng model: model ID, base URL, cờ năng lực và giá đều chỉ
 * tồn tại ở một chỗ.
 */
export function describeModels() {
    if (!pyodide) throw new Error("Chưa nạp xong Pyodide — gọi init() trước");
    return toJs(pyodide.globals.get("describe_models")());
}

/**
 * Cập nhật bảng xếp hạng sau một trận, bằng công thức Elo dùng chung với bản local.
 * `resultStatus`: 'red_win' | 'black_win' | 'draw'.
 */
export function applyElo(rows, redModelKey, blackModelKey, resultStatus) {
    if (!pyodide) throw new Error("Chưa nạp xong Pyodide — gọi init() trước");
    return toJs(pyodide.globals.get("apply_elo")(
        pyodide.toPy(rows), redModelKey, blackModelKey, resultStatus,
    ));
}

export function isReady() {
    return pyodide !== null;
}

function requireArena() {
    if (!arena) throw new Error("Chưa có trận nào — gọi newMatch() trước");
    return arena;
}

/** Tạo trận mới. Cấu hình là object thường, ví dụ { model_key, name }. */
export function newMatch(redConfig, blackConfig) {
    if (!pyodide) throw new Error("Chưa nạp xong Pyodide — gọi init() trước");
    const BrowserArena = pyodide.globals.get("BrowserArena");
    arena = BrowserArena(
        pyodide.toPy(redConfig ?? null),
        pyodide.toPy(blackConfig ?? null),
    );
    return getState();
}

export function getState() {
    return toJs(requireArena().get_state());
}

/**
 * Bắt đầu lượt AI. Trả { prompt, legal_moves, side, attempt } để gọi API, hoặc null khi
 * không cần hỏi AI (trận đã xong, hoặc tới lượt người chơi).
 */
export function beginTurn() {
    return toJs(requireArena().begin_turn());
}

/**
 * Nộp kết quả gọi API. Trả yêu cầu tiếp theo khi trọng tài bắt đi lại vì nước sai luật,
 * hoặc null khi lượt đã xong.
 *
 * `decision` là object phẳng: { move_ucci, taunt, thinking, latency_ms, tokens_in,
 * tokens_out, cost_usd, error, provider, model_key }. Sai tên trường sẽ bị Python báo lỗi
 * ngay chứ không âm thầm bỏ qua.
 */
export function submitDecision(decision) {
    return toJs(requireArena().submit_decision(pyodide.toPy(decision)));
}

/**
 * Để kỳ thủ chạy ngay trong Python tự quyết (Mock). Dùng khi `beginTurn()` trả về yêu cầu
 * có `external: false` — không tốn lượt gọi mạng nào.
 */
export function submitLocalDecision() {
    return toJs(requireArena().submit_local_decision());
}

export function submitHumanMove(ucci) {
    return toJs(requireArena().submit_human_move(ucci));
}

/** Các nước hợp lệ xuất phát từ một ô, để hiện chấm gợi ý khi người chơi bấm quân. */
export function legalMovesFrom(square) {
    return toJs(requireArena().legal_moves_from(square));
}
