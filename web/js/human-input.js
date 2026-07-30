/**
 * Cho người chơi đi cờ bằng chuột.
 *
 * Danh sách nước hợp lệ LẤY TỪ MÁY CHỦ (trường legal_moves trong state), không tự tính lại
 * bằng JavaScript. Nhân bản luật cờ sang trình duyệt sẽ tạo hai nguồn sự thật và sớm muộn
 * cũng lệch với trọng tài.
 */

import { gridPointPercent, ucciToPos } from './board-renderer.js';

export class HumanInput {
    /**
     * @param {HTMLElement} boardElement
     * @param {function} onMove - gọi khi người chơi chọn xong nước đi, nhận chuỗi UCCI
     */
    constructor(boardElement, onMove) {
        this.boardElement = boardElement;
        this.onMove = onMove;
        this.legalMoves = [];
        this.enabled = false;
        this.selectedSquare = null;

        this.boardElement.addEventListener('click', (event) => this.handleClick(event));
    }

    /**
     * Bật/tắt theo lượt: chỉ nhận thao tác khi tới lượt người chơi.
     *
     * Luôn xoá lựa chọn cũ: hàm này được gọi mỗi khi trạng thái bàn cờ thay đổi, nên quân
     * đang chọn và các chấm gợi ý của lượt trước đã không còn đúng nữa.
     */
    setState(enabled, legalMoves) {
        this.enabled = enabled;
        this.legalMoves = legalMoves || [];
        this.clearSelection();
    }

    /** Các ô đích hợp lệ khi đã chọn quân ở `fromSquare`. */
    destinationsFrom(fromSquare) {
        return this.legalMoves
            .filter(move => move.startsWith(fromSquare))
            .map(move => move.slice(2, 4));
    }

    handleClick(event) {
        if (!this.enabled) return;

        const square = this.squareFromPoint(event.clientX, event.clientY);
        if (!square) return;

        // Đã chọn quân: click ô đích hợp lệ thì đi, click chỗ khác thì chọn lại
        if (this.selectedSquare) {
            if (this.destinationsFrom(this.selectedSquare).includes(square)) {
                const ucci = this.selectedSquare + square;
                this.clearSelection();
                this.onMove(ucci);
                return;
            }
            if (square === this.selectedSquare) {
                this.clearSelection();   // click lại chính quân đó để bỏ chọn
                return;
            }
        }

        if (this.destinationsFrom(square).length > 0) {
            this.select(square);
        } else {
            this.clearSelection();
        }
    }

    /** Toạ độ chuột -> ô cờ gần nhất; trả null nếu bấm quá xa mọi giao điểm. */
    squareFromPoint(clientX, clientY) {
        const rect = this.boardElement.getBoundingClientRect();
        const xPercent = ((clientX - rect.left) / rect.width) * 100;
        const yPercent = ((clientY - rect.top) / rect.height) * 100;

        let closest = null;
        let closestDistance = Infinity;
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 9; col++) {
                const point = gridPointPercent(row, col);
                const distance = Math.hypot(point.left - xPercent, point.top - yPercent);
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closest = { row, col };
                }
            }
        }
        // Ngưỡng ~nửa ô: bấm ra ngoài bàn thì không chọn nhầm ô rìa
        if (closestDistance > 6) return null;
        return `${String.fromCharCode(97 + closest.col)}${9 - closest.row}`;
    }

    select(square) {
        this.selectedSquare = square;
        this.renderHints();
    }

    clearSelection() {
        this.selectedSquare = null;
        this.renderHints();
    }

    /** Vẽ chấm gợi ý ở các ô đi được và viền quân đang chọn. */
    renderHints() {
        this.boardElement.querySelectorAll('.move-hint').forEach(node => node.remove());
        this.boardElement.querySelectorAll('.piece.selected')
            .forEach(node => node.classList.remove('selected'));
        if (!this.selectedSquare) return;

        const from = ucciToPos(this.selectedSquare);
        const fromPoint = gridPointPercent(from.row, from.col);
        this.boardElement.querySelectorAll('.piece').forEach(piece => {
            if (Math.abs(parseFloat(piece.style.left) - fromPoint.left) < 0.1
                && Math.abs(parseFloat(piece.style.top) - fromPoint.top) < 0.1) {
                piece.classList.add('selected');
            }
        });

        this.destinationsFrom(this.selectedSquare).forEach(square => {
            const position = ucciToPos(square);
            const point = gridPointPercent(position.row, position.col);
            const hint = document.createElement('div');
            hint.className = 'move-hint';
            hint.style.left = `${point.left}%`;
            hint.style.top = `${point.top}%`;
            this.boardElement.appendChild(hint);
        });
    }
}
