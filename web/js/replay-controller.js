/**
 * Xem lại trận đã lưu.
 *
 * Toàn bộ dữ liệu lấy từ cơ sở dữ liệu (mỗi nước có sẵn fen_after) nên KHÔNG gọi API AI:
 * xem lại bao nhiêu lần cũng miễn phí và không có độ trễ. Đây là công cụ chính để dựng
 * video — quay lại một trận nhiều lần, nhiều góc, mà không tốn thêm tiền.
 */

import { renderPieces } from './board-renderer.js';

const INITIAL_FEN = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1';

export class ReplayController {
    /**
     * @param {object} options
     * @param {HTMLElement} options.boardElement
     * @param {function} options.onFrame - gọi mỗi khi đổi nước, nhận (frame) để cập nhật giao diện
     */
    constructor({ boardElement, onFrame }) {
        this.boardElement = boardElement;
        this.onFrame = onFrame;
        this.match = null;
        this.moves = [];
        this.index = -1;          // -1 = thế cờ ban đầu, chưa đi nước nào
        this.playTimer = null;
        this.playIntervalMs = 1200;
    }

    get isActive() {
        return this.match !== null;
    }

    get isPlaying() {
        return this.playTimer !== null;
    }

    get totalPlies() {
        return this.moves.length;
    }

    async load(matchId) {
        const response = await fetch(`/api/replays/${matchId}`);
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(body.error || `Không tải được trận ${matchId}`);
        }
        const data = await response.json();
        this.match = data.match;
        this.moves = data.moves;
        this.index = -1;
        this.render();
        return this.match;
    }

    close() {
        this.pause();
        this.match = null;
        this.moves = [];
        this.index = -1;
    }

    /** Nhảy tới một nước cụ thể; -1 là thế cờ ban đầu. */
    seek(index) {
        const clamped = Math.max(-1, Math.min(this.totalPlies - 1, index));
        this.index = clamped;
        this.render();
    }

    next() {
        if (this.index >= this.totalPlies - 1) {
            this.pause();
            return false;
        }
        this.seek(this.index + 1);
        return true;
    }

    previous() {
        this.seek(this.index - 1);
    }

    play(intervalMs) {
        if (intervalMs) this.playIntervalMs = intervalMs;
        this.pause();
        // Đang ở nước cuối thì phát lại từ đầu, thay vì không làm gì
        if (this.index >= this.totalPlies - 1) this.seek(-1);
        this.playTimer = setInterval(() => this.next(), this.playIntervalMs);
    }

    pause() {
        if (this.playTimer !== null) {
            clearInterval(this.playTimer);
            this.playTimer = null;
        }
    }

    togglePlay(intervalMs) {
        if (this.isPlaying) this.pause();
        else this.play(intervalMs);
    }

    /** Nhảy tới nước có cp_loss lớn nhất — thường là điểm xoay chuyển trận. */
    seekWorstMove() {
        let worstIndex = -1;
        let worstLoss = -1;
        this.moves.forEach((move, index) => {
            if ((move.cp_loss ?? -1) > worstLoss) {
                worstLoss = move.cp_loss ?? -1;
                worstIndex = index;
            }
        });
        if (worstIndex >= 0) this.seek(worstIndex);
        return worstIndex >= 0 ? this.moves[worstIndex] : null;
    }

    /** Dữ liệu của khung hình hiện tại, để giao diện hiển thị. */
    currentFrame() {
        const atStart = this.index < 0;
        const move = atStart ? null : this.moves[this.index];
        return {
            match: this.match,
            move,
            index: this.index,
            total: this.totalPlies,
            fen: atStart ? (this.match?.initial_fen || INITIAL_FEN) : move.fen_after,
            // Điểm cộng dồn tới nước hiện tại, dùng cho eval bar và độ chính xác
            stats: this.statsUpTo(this.index),
            isPlaying: this.isPlaying,
        };
    }

    /**
     * Thống kê tính tới nước `upToIndex`.
     *
     * Tính dồn theo từng nước thay vì lấy số tổng của trận: khi kéo thanh thời gian tới
     * giữa trận, độ chính xác phải là con số TẠI thời điểm đó, không phải kết quả cuối.
     */
    statsUpTo(upToIndex) {
        const blank = () => ({ accuracySum: 0, scored: 0, blunders: 0, illegal: 0, cost: 0 });
        const totals = { w: blank(), b: blank() };

        for (let i = 0; i <= upToIndex && i < this.moves.length; i++) {
            const move = this.moves[i];
            const side = totals[move.side];
            if (!side) continue;
            if (move.accuracy !== null && move.accuracy !== undefined) {
                side.accuracySum += move.accuracy;
                side.scored += 1;
            }
            if (move.quality === 'blunder') side.blunders += 1;
            side.illegal += Math.max(0, (move.attempts?.length || 1) - 1);
            side.cost += move.cost_usd || 0;
        }

        const shape = (side) => ({
            accuracy: side.scored ? Math.round((side.accuracySum / side.scored) * 10) / 10 : null,
            blunders: side.blunders,
            illegal_attempts: side.illegal,
            cost_usd: side.cost,
        });
        const lastMove = upToIndex >= 0 ? this.moves[upToIndex] : null;
        // Eval bar luôn theo góc nhìn Đỏ
        const evalCp = lastMove?.cp_after == null
            ? 0
            : (lastMove.side === 'w' ? lastMove.cp_after : -lastMove.cp_after);

        return { red: shape(totals.w), black: shape(totals.b), eval_cp: evalCp };
    }

    render() {
        const frame = this.currentFrame();
        renderPieces(this.boardElement, frame.fen, frame.move
            ? { ucci: frame.move.ucci, side: frame.move.side }
            : null);
        this.onFrame(frame);
    }
}
