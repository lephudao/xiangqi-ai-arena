/**
 * Vẽ bàn cờ tướng: lưới SVG, sông, cung tướng, và các quân cờ.
 *
 * Hình học là MỘT nguồn duy nhất (hằng số BOARD) cho cả lưới và quân. Bản cũ tính
 * khoảng cách ô bằng 480/8 và 533/9 mà không trừ lề, nên cột ngoài cùng nằm ở x=504
 * (vượt ra ngoài bàn rộng 480) và hàng cuối ở y=559 — quân cờ bên phải và hàng dưới
 * rơi ra ngoài mặt bàn.
 */

// viewBox của SVG; mọi toạ độ tính trong hệ này rồi quy ra phần trăm để bàn cờ co giãn
export const BOARD = {
    WIDTH: 480,
    HEIGHT: 533,
    MARGIN_X: 24,
    MARGIN_Y: 26,
    COLS: 9,
    ROWS: 10,
};
BOARD.CELL_W = (BOARD.WIDTH - 2 * BOARD.MARGIN_X) / (BOARD.COLS - 1);   // 54
BOARD.CELL_H = (BOARD.HEIGHT - 2 * BOARD.MARGIN_Y) / (BOARD.ROWS - 1);  // ~53.4

const SVG_NS = 'http://www.w3.org/2000/svg';
const LINE_COLOR = '#5c3a1e';

// Chữ Hán trên mặt quân: chữ hoa = Đỏ, chữ thường = Đen
const PIECE_SYMBOLS = {
    'K': '帥', 'R': '俥', 'N': '傌', 'B': '相', 'A': '仕', 'C': '炮', 'P': '兵',
    'k': '將', 'r': '車', 'n': '馬', 'b': '象', 'a': '士', 'c': '砲', 'p': '卒',
};

function gridX(col) {
    return BOARD.MARGIN_X + col * BOARD.CELL_W;
}

function gridY(row) {
    return BOARD.MARGIN_Y + row * BOARD.CELL_H;
}

/** Vị trí giao điểm theo phần trăm kích thước bàn cờ — dùng cho quân cờ. */
export function gridPointPercent(row, col) {
    return {
        left: (gridX(col) / BOARD.WIDTH) * 100,
        top: (gridY(row) / BOARD.HEIGHT) * 100,
    };
}

function line(svg, x1, y1, x2, y2, width = 2) {
    const element = document.createElementNS(SVG_NS, 'line');
    element.setAttribute('x1', x1);
    element.setAttribute('y1', y1);
    element.setAttribute('x2', x2);
    element.setAttribute('y2', y2);
    element.setAttribute('stroke', LINE_COLOR);
    element.setAttribute('stroke-width', width);
    svg.appendChild(element);
    return element;
}

/** Vẽ dấu X trong cung tướng. */
function palaceCross(svg, colFrom, rowFrom, colTo, rowTo) {
    line(svg, gridX(colFrom), gridY(rowFrom), gridX(colTo), gridY(rowTo), 1.5);
    line(svg, gridX(colTo), gridY(rowFrom), gridX(colFrom), gridY(rowTo), 1.5);
}

/** Vẽ lưới, sông và cung tướng. Gọi một lần khi khởi tạo. */
export function renderBoardGrid(boardElement) {
    boardElement.querySelector('.board-grid-svg')?.remove();

    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'board-grid-svg');
    svg.setAttribute('viewBox', `0 0 ${BOARD.WIDTH} ${BOARD.HEIGHT}`);
    svg.setAttribute('preserveAspectRatio', 'none');

    // Đường ngang: đủ 10 hàng, chạy từ cột 0 tới cột 8
    for (let row = 0; row < BOARD.ROWS; row++) {
        line(svg, gridX(0), gridY(row), gridX(BOARD.COLS - 1), gridY(row));
    }

    // Đường dọc: hai cột biên chạy liền; các cột giữa bị sông cắt (giữa hàng 4 và 5)
    for (let col = 0; col < BOARD.COLS; col++) {
        const x = gridX(col);
        if (col === 0 || col === BOARD.COLS - 1) {
            line(svg, x, gridY(0), x, gridY(BOARD.ROWS - 1));
        } else {
            line(svg, x, gridY(0), x, gridY(4));
            line(svg, x, gridY(5), x, gridY(BOARD.ROWS - 1));
        }
    }

    palaceCross(svg, 3, 0, 5, 2);   // cung Đen (hàng 0-2)
    palaceCross(svg, 3, 7, 5, 9);   // cung Đỏ (hàng 7-9)

    const riverText = document.createElementNS(SVG_NS, 'text');
    riverText.setAttribute('x', BOARD.WIDTH / 2);
    riverText.setAttribute('y', gridY(4) + BOARD.CELL_H * 0.68);
    riverText.setAttribute('font-size', '20');
    riverText.setAttribute('font-family', "'Noto Serif TC', serif");
    riverText.setAttribute('font-weight', '900');
    riverText.setAttribute('fill', '#8b5a2b');
    riverText.setAttribute('text-anchor', 'middle');
    riverText.setAttribute('letter-spacing', '2');
    riverText.textContent = '楚 河          漢 界';
    svg.appendChild(riverText);

    boardElement.appendChild(svg);
}

/** Chuyển 'h2' -> {row, col}. */
export function ucciToPos(square) {
    if (!square || square.length < 2) return null;
    return {
        col: square.charCodeAt(0) - 'a'.charCodeAt(0),
        row: 9 - parseInt(square[1], 10),
    };
}

/**
 * Vẽ lại toàn bộ quân cờ từ FEN, highlight ô đi và ô đến của nước vừa đi.
 */
export function renderPieces(boardElement, fen, lastMove) {
    boardElement.querySelectorAll('.piece, .move-marker').forEach(node => node.remove());

    let from = null;
    let to = null;
    if (lastMove?.ucci?.length === 4) {
        from = ucciToPos(lastMove.ucci.slice(0, 2));
        to = ucciToPos(lastMove.ucci.slice(2, 4));
    }

    // Dấu ô xuất phát: giúp người xem thấy quân vừa đi TỪ đâu, không chỉ tới đâu
    if (from) {
        const marker = document.createElement('div');
        marker.className = 'move-marker';
        const point = gridPointPercent(from.row, from.col);
        marker.style.left = `${point.left}%`;
        marker.style.top = `${point.top}%`;
        boardElement.appendChild(marker);
    }

    const rows = fen.split(' ')[0].split('/');
    rows.forEach((rowString, row) => {
        let col = 0;
        for (const char of rowString) {
            if (/\d/.test(char)) {
                col += parseInt(char, 10);
                continue;
            }
            const piece = document.createElement('div');
            const isRed = char === char.toUpperCase();
            piece.className = `piece ${isRed ? 'red-piece' : 'black-piece'}`;
            piece.textContent = PIECE_SYMBOLS[char] || char;

            const point = gridPointPercent(row, col);
            piece.style.left = `${point.left}%`;
            piece.style.top = `${point.top}%`;
            if (to && to.row === row && to.col === col) {
                piece.classList.add('last-move');
            }
            boardElement.appendChild(piece);
            col++;
        }
    });
}
