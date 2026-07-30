/**
 * Xiangqi AI vs AI Broadcast Studio Logic
 */

let currentState = null;
let isAutoPlaying = false;
let autoPlayTimer = null;
let synth = window.speechSynthesis;

// Xiangqi Chinese Character Mapping
const PIECE_SYMBOLS_VI = {
    'K': '帥', 'R': '俥', 'N': '傌', 'B': '相', 'A': '仕', 'C': '炮', 'P': '兵',
    'k': '將', 'r': '車', 'n': '馬', 'b': '象', 'a': '士', 'c': '砲', 'p': '卒'
};

document.addEventListener('DOMContentLoaded', () => {
    initBoardSVG();
    fetchState();

    // Event Listeners
    document.getElementById('btn-step').addEventListener('click', handleStep);
    document.getElementById('btn-auto').addEventListener('click', toggleAutoPlay);
    document.getElementById('btn-reset').addEventListener('click', handleReset);
    document.getElementById('btn-toggle-panel').addEventListener('click', openModal);
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-save-config').addEventListener('click', saveConfig);
});

// Render SVG grid lines & river text
function initBoardSVG() {
    const boardEl = document.getElementById('board');
    boardEl.innerHTML = ''; // clear

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("class", "board-grid-svg");
    svg.setAttribute("viewBox", "0 0 480 533");

    // Board parameters: 9 cols, 10 rows
    // Col width = 480 / 8 = 60px
    // Row height = 533 / 9 = 59.2px
    const colW = 480 / 8;
    const rowH = 533 / 9;

    // Draw Grid Lines
    // Ranks (Horizontal)
    for (let r = 0; r < 10; r++) {
        const line = document.createElementNS(svgNS, "line");
        line.setAttribute("x1", 24);
        line.setAttribute("y1", 26 + r * rowH);
        line.setAttribute("x2", 486 - 30);
        line.setAttribute("y2", 26 + r * rowH);
        line.setAttribute("stroke", "#5c3a1e");
        line.setAttribute("stroke-width", "2");
        svg.appendChild(line);
    }

    // Files (Vertical) - split by River between row 4 & 5
    for (let c = 0; c < 9; c++) {
        const x = 24 + c * colW;
        if (c === 0 || c === 8) {
            // Full line
            const line = document.createElementNS(svgNS, "line");
            line.setAttribute("x1", x);
            line.setAttribute("y1", 26);
            line.setAttribute("x2", x);
            line.setAttribute("y2", 26 + 9 * rowH);
            line.setAttribute("stroke", "#5c3a1e");
            line.setAttribute("stroke-width", "2");
            svg.appendChild(line);
        } else {
            // Top half
            const line1 = document.createElementNS(svgNS, "line");
            line1.setAttribute("x1", x);
            line1.setAttribute("y1", 26);
            line1.setAttribute("x2", x);
            line1.setAttribute("y2", 26 + 4 * rowH);
            line1.setAttribute("stroke", "#5c3a1e");
            line1.setAttribute("stroke-width", "2");
            svg.appendChild(line1);

            // Bottom half
            const line2 = document.createElementNS(svgNS, "line");
            line2.setAttribute("x1", x);
            line2.setAttribute("y1", 26 + 5 * rowH);
            line2.setAttribute("x2", x);
            line2.setAttribute("y2", 26 + 9 * rowH);
            line2.setAttribute("stroke", "#5c3a1e");
            line2.setAttribute("stroke-width", "2");
            svg.appendChild(line2);
        }
    }

    // Palaces (X lines)
    // Red Palace (rows 7-9, cols 3-5)
    drawX(svg, svgNS, 3 * colW + 24, 7 * rowH + 26, 5 * colW + 24, 9 * rowH + 26);
    // Black Palace (rows 0-2, cols 3-5)
    drawX(svg, svgNS, 3 * colW + 24, 0 * rowH + 26, 5 * colW + 24, 2 * rowH + 26);

    // River Text
    const textRiver = document.createElementNS(svgNS, "text");
    textRiver.setAttribute("x", "240");
    textRiver.setAttribute("y", 26 + 4.65 * rowH);
    textRiver.setAttribute("font-size", "22");
    textRiver.setAttribute("font-family", "'Noto Serif TC', serif");
    textRiver.setAttribute("font-weight", "900");
    textRiver.setAttribute("fill", "#8b5a2b");
    textRiver.setAttribute("text-anchor", "middle");
    textRiver.textContent = "楚 河           漢 界";
    svg.appendChild(textRiver);

    boardEl.appendChild(svg);
}

function drawX(svg, svgNS, x1, y1, x2, y2) {
    const l1 = document.createElementNS(svgNS, "line");
    l1.setAttribute("x1", x1); l1.setAttribute("y1", y1);
    l1.setAttribute("x2", x2); l1.setAttribute("y2", y2);
    l1.setAttribute("stroke", "#5c3a1e"); l1.setAttribute("stroke-width", "1.5");
    svg.appendChild(l1);

    const l2 = document.createElementNS(svgNS, "line");
    l2.setAttribute("x1", x2); l2.setAttribute("y1", y1);
    l2.setAttribute("x2", x1); l2.setAttribute("y2", y2);
    l2.setAttribute("stroke", "#5c3a1e"); l2.setAttribute("stroke-width", "1.5");
    svg.appendChild(l2);
}

async function fetchState() {
    try {
        const resp = await fetch('/api/state');
        const data = await resp.json();
        updateUI(data);
    } catch (e) {
        console.error("Failed to fetch state:", e);
    }
}

async function handleStep() {
    try {
        playPieceSound();
        const resp = await fetch('/api/step', { method: 'POST' });
        const data = await resp.json();
        updateUI(data);

        // TTS Speech synthesis if enabled
        if (data.last_move && document.getElementById('chk-tts').checked) {
            speakReasoning(data.last_move.player, data.last_move.reasoning);
        }

        if (data.game_over) {
            stopAutoPlay();
            alert(`KẾT THÚC TRẬN ĐẤU! ${data.winner} thắng!`);
        }
    } catch (e) {
        console.error("Step error:", e);
    }
}

function toggleAutoPlay() {
    if (isAutoPlaying) {
        stopAutoPlay();
    } else {
        isAutoPlaying = true;
        document.getElementById('btn-auto').textContent = "⏸ Tạm Dừng";
        document.getElementById('btn-auto').className = "btn btn-secondary btn-large";
        scheduleNextStep();
    }
}

function stopAutoPlay() {
    isAutoPlaying = false;
    if (autoPlayTimer) clearTimeout(autoPlayTimer);
    document.getElementById('btn-auto').textContent = "⚡ Tự Động Đấu";
    document.getElementById('btn-auto').className = "btn btn-success btn-large";
}

function scheduleNextStep() {
    if (!isAutoPlaying) return;
    const speed = parseInt(document.getElementById('sel-speed').value, 10) || 1200;
    autoPlayTimer = setTimeout(async () => {
        if (!isAutoPlaying) return;
        await handleStep();
        if (currentState && !currentState.game_over && isAutoPlaying) {
            scheduleNextStep();
        }
    }, speed);
}

async function handleReset() {
    stopAutoPlay();
    const resp = await fetch('/api/reset', { method: 'POST' });
    const data = await resp.json();
    updateUI(data);
}

function updateUI(state) {
    currentState = state;

    // Header updates
    const turnBadge = document.getElementById('turn-badge');
    if (state.turn === 'w') {
        turnBadge.textContent = "LƯỢT QUÂN ĐỎ";
        turnBadge.className = "turn-indicator turn-red";
        document.getElementById('card-red').classList.add('active-turn');
        document.getElementById('card-black').classList.remove('active-turn');
    } else {
        turnBadge.textContent = "LƯỢT QUÂN ĐEN";
        turnBadge.className = "turn-indicator turn-black";
        document.getElementById('card-black').classList.add('active-turn');
        document.getElementById('card-red').classList.remove('active-turn');
    }

    document.getElementById('move-counter').textContent = `Lượt: #${state.move_number}`;

    // Player Cards
    document.getElementById('name-red').textContent = state.red_config.name;
    document.getElementById('model-red').textContent = `Provider: ${state.red_config.provider.toUpperCase()}`;

    document.getElementById('name-black').textContent = state.black_config.name;
    document.getElementById('model-black').textContent = `Provider: ${state.black_config.provider.toUpperCase()}`;

    // Referee text
    if (state.referee_log && state.referee_log.length > 0) {
        document.getElementById('referee-text').textContent = state.referee_log[state.referee_log.length - 1];
    }

    // Last move reasoning
    if (state.last_move) {
        if (state.last_move.side === 'w') {
            document.getElementById('reasoning-red').textContent = `"${state.last_move.reasoning}"`;
        } else {
            document.getElementById('reasoning-black').textContent = `"${state.last_move.reasoning}"`;
        }
    }

    // Render Chess Pieces from FEN
    renderPiecesFromFEN(state.fen, state.last_move);
}

function renderPiecesFromFEN(fen, lastMove) {
    const boardEl = document.getElementById('board');
    // Remove existing piece elements
    const oldPieces = boardEl.querySelectorAll('.piece');
    oldPieces.forEach(p => p.remove());

    const fenBoard = fen.split(' ')[0];
    const rows = fenBoard.split('/');

    const colW = 480 / 8;
    const rowH = 533 / 9;

    let lastMoveFrom = null;
    let lastMoveTo = null;
    if (lastMove && lastMove.ucci && lastMove.ucci.length === 4) {
        lastMoveFrom = ucciToPos(lastMove.ucci.substring(0, 2));
        lastMoveTo = ucciToPos(lastMove.ucci.substring(2, 4));
    }

    for (let r = 0; r < 10; r++) {
        let c = 0;
        const rowStr = rows[r];
        for (let i = 0; i < rowStr.length; i++) {
            const char = rowStr[i];
            if (!isNaN(char)) {
                c += parseInt(char, 10);
            } else {
                const pieceDiv = document.createElement('div');
                const isRed = (char === char.toUpperCase());
                pieceDiv.className = `piece ${isRed ? 'red-piece' : 'black-piece'}`;
                pieceDiv.textContent = PIECE_SYMBOLS_VI[char] || char;

                const leftPx = 24 + c * colW - 24; // center piece
                const topPx = 26 + r * rowH - 24;

                pieceDiv.style.left = `${leftPx}px`;
                pieceDiv.style.top = `${topPx}px`;

                // Highlight last move target
                if (lastMoveTo && lastMoveTo.r === r && lastMoveTo.c === c) {
                    pieceDiv.classList.add('last-move');
                }

                boardEl.appendChild(pieceDiv);
                c++;
            }
        }
    }
}

function ucciToPos(ucci) {
    if (!ucci || ucci.length < 2) return null;
    const col = ucci.charCodeAt(0) - 'a'.charCodeAt(0);
    const rank = parseInt(ucci[1], 10);
    return { r: 9 - rank, c: col };
}

// Web Speech Synthesis (TTS)
function speakReasoning(playerName, text) {
    if (!synth || !text) return;
    synth.cancel(); // stop previous speech
    const utterance = new SpeechSynthesisUtterance(`${playerName} phát biểu: ${text}`);
    utterance.lang = 'vi-VN';
    utterance.rate = 1.0;
    synth.speak(utterance);
}

// Web Audio API Synthetic Piece Sound
function playPieceSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(150, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.5, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.1);
    } catch (e) {}
}

// Modal Handlers
function openModal() {
    document.getElementById('modal-config').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-config').classList.add('hidden');
}

async function saveConfig() {
    const redConfig = {
        name: document.getElementById('cfg-red-name').value || "ChatGPT",
        provider: document.getElementById('cfg-red-provider').value,
        api_key: document.getElementById('cfg-red-key').value
    };
    const blackConfig = {
        name: document.getElementById('cfg-black-name').value || "Claude 3.5",
        provider: document.getElementById('cfg-black-provider').value,
        api_key: document.getElementById('cfg-black-key').value
    };

    closeModal();

    const resp = await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ red_config: redConfig, black_config: blackConfig })
    });
    const data = await resp.json();
    updateUI(data);
}
