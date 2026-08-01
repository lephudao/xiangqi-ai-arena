/**
 * Bảng xếp hạng Elo của bản online, lưu trong localStorage.
 *
 * Bản online không lưu nước đi (không có chức năng xem lại), chỉ lưu KẾT QUẢ trận — rẻ mà
 * vẫn trả lời được câu hỏi người xem quan tâm nhất: AI nào mạnh hơn.
 *
 * Bảng này nằm trong máy của từng người và KHÔNG trộn với bảng xếp hạng trong SQLite của
 * bản local. Đó là điều mong muốn: số liệu dùng cho video phải chỉ đến từ các trận bạn tự
 * chạy, không lẫn trận của người lạ.
 *
 * Công thức Elo lấy từ Python (`engine/storage/elo_rating.py`) — cùng K, cùng điểm khởi đầu
 * với bản local. Viết lại trong JS thì hai bảng sẽ trôi khỏi nhau và không so được.
 */

import { applyElo } from "./python-runtime.js";

const STORAGE_KEY = "xiangqi-arena.leaderboard";

export function loadBoard() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const rows = raw ? JSON.parse(raw) : [];
        return Array.isArray(rows) ? rows : [];
    } catch {
        // Dữ liệu hỏng thì bắt đầu lại từ bảng rỗng, không để vỡ cả giao diện
        return [];
    }
}

export function clearBoard() {
    localStorage.removeItem(STORAGE_KEY);
}

/**
 * Ghi nhận một trận đã kết thúc đúng luật cờ.
 *
 * Bỏ qua trận có kỳ thủ là người: Elo dùng để so sánh các AI với nhau, trộn người vào thì
 * không còn ý nghĩa.
 */
export function recordResult(state) {
    const redKey = state.red_config?.model_key;
    const blackKey = state.black_config?.model_key;
    if (!redKey || !blackKey) return loadBoard();
    if (redKey === "human" || blackKey === "human") return loadBoard();

    const rows = applyElo(loadBoard(), redKey, blackKey, state.result_status);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
    return rows;
}
