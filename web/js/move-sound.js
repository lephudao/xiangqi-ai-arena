/**
 * Tiếng động bàn cờ, tổng hợp bằng Web Audio — không tải file âm thanh nào.
 *
 * Mỗi loại sự kiện một tiếng khác nhau để người xem video NGHE ra chuyện gì vừa xảy ra mà
 * không cần đọc chữ: đi thường, ăn quân, chiếu tướng, kết thúc trận.
 *
 * Dùng CHUNG một AudioContext. Bản cũ tạo context mới mỗi nước đi — trình duyệt chỉ cho
 * khoảng 6 context đồng thời, nên trận dài sẽ mất tiếng hẳn giữa chừng.
 */

let context = null;

function audio() {
    if (!context) {
        const Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) return null;
        context = new Ctor();
    }
    // Trình duyệt treo context khi trang chưa được tương tác; đánh thức lại khi có thể
    if (context.state === "suspended") context.resume().catch(() => {});
    return context;
}

/**
 * Một tiếng gõ: dao động tần số giảm dần + đường bao âm lượng tắt nhanh.
 * Đây là cách dựng tiếng "cạch" của quân cờ chạm mặt bàn mà không cần file mẫu.
 */
function knock(ctx, { startHz, endHz, durationSec, volume, type = "triangle", delaySec = 0 }) {
    const start = ctx.currentTime + delaySec;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(startHz, start);
    osc.frequency.exponentialRampToValueAtTime(endHz, start + durationSec);
    gain.gain.setValueAtTime(volume, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + durationSec);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(start);
    osc.stop(start + durationSec);
}

/**
 * Phát tiếng cho một nước đi.
 *
 * `event`: "move" | "capture" | "check" | "checkmate" | "draw"
 * Không bao giờ ném lỗi — mất tiếng không được phép làm hỏng trận đang chạy.
 */
export function playMoveSound(event = "move") {
    try {
        const ctx = audio();
        if (!ctx) return;

        switch (event) {
            case "capture":
                // Ăn quân: gõ mạnh hơn, kèm tiếng gỗ va chạm ngay sau
                knock(ctx, { startHz: 220, endHz: 40, durationSec: 0.13, volume: 0.55 });
                knock(ctx, { startHz: 90, endHz: 30, durationSec: 0.16, volume: 0.35,
                             type: "sawtooth", delaySec: 0.035 });
                break;

            case "check":
                // Chiếu tướng: hai nốt cao đi lên — nghe là biết có chuyện, không cần nhìn
                knock(ctx, { startHz: 160, endHz: 40, durationSec: 0.1, volume: 0.4 });
                knock(ctx, { startHz: 880, endHz: 830, durationSec: 0.12, volume: 0.22,
                             type: "sine", delaySec: 0.1 });
                knock(ctx, { startHz: 1180, endHz: 1120, durationSec: 0.16, volume: 0.22,
                             type: "sine", delaySec: 0.22 });
                break;

            case "checkmate":
                // Kết thúc: ba nốt đi xuống, dứt khoát
                [660, 520, 380].forEach((hz, index) => {
                    knock(ctx, { startHz: hz, endHz: hz * 0.94, durationSec: 0.3,
                                 volume: 0.26, type: "sine", delaySec: index * 0.17 });
                });
                break;

            case "draw":
                knock(ctx, { startHz: 440, endHz: 430, durationSec: 0.4, volume: 0.2,
                             type: "sine" });
                break;

            default:
                // Đi thường: tiếng gõ gọn, nhẹ hơn ăn quân để phân biệt được
                knock(ctx, { startHz: 170, endHz: 45, durationSec: 0.09, volume: 0.34 });
        }
    } catch {
        // Không có Web Audio hoặc trình duyệt chặn — trận vẫn chạy bình thường
    }
}

/**
 * Loại sự kiện âm thanh cho một nước, suy ra từ trạng thái trận.
 *
 * Ăn quân nhận biết bằng SỐ QUÂN trên bàn giảm đi. Trạng thái trả về không có cờ "vừa ăn
 * quân", mà so số quân thì đúng trong mọi trường hợp và không phải sửa hợp đồng dữ liệu
 * giữa Python và JS.
 */
export function classifyMove(previousFen, state) {
    if (state.game_over) {
        return state.result_status === "draw" ? "draw" : "checkmate";
    }
    if (state.in_check) return "check";
    if (previousFen && countPieces(previousFen) > countPieces(state.fen)) return "capture";
    return "move";
}

function countPieces(fen) {
    return (fen.split(" ")[0].match(/[a-zA-Z]/g) || []).length;
}
