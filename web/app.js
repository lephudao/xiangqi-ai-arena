/**
 * Xiangqi AI vs AI Broadcast Studio Logic
 */

let currentState = null;
let isAutoPlaying = false;
let autoPlayTimer = null;
let synth = window.speechSynthesis;
let availableModels = [];

// Xiangqi Chinese Character Mapping
const PIECE_SYMBOLS_VI = {
    'K': '帥', 'R': '俥', 'N': '傌', 'B': '相', 'A': '仕', 'C': '炮', 'P': '兵',
    'k': '將', 'r': '車', 'n': '馬', 'b': '象', 'a': '士', 'c': '砲', 'p': '卒'
};

document.addEventListener('DOMContentLoaded', async () => {
    initBoardSVG();
    await loadModels();
    fetchState();

    // Event Listeners
    document.getElementById('btn-step').addEventListener('click', handleStep);
    document.getElementById('btn-auto').addEventListener('click', toggleAutoPlay);
    document.getElementById('btn-reset').addEventListener('click', handleReset);
    document.getElementById('btn-toggle-panel').addEventListener('click', openModal);
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-save-config').addEventListener('click', saveConfig);
    document.getElementById('btn-close-result').addEventListener('click', hideResultBanner);
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

// Nạp danh mục kỳ thủ và dựng dropdown — tránh hardcode model trong HTML
async function loadModels() {
    try {
        const resp = await fetch('/api/models');
        const data = await resp.json();
        availableModels = data.models;
        fillModelSelect('cfg-red-model', data.default_red);
        fillModelSelect('cfg-black-model', data.default_black);
    } catch (e) {
        console.error('Không nạp được danh mục model:', e);
    }
}

function fillModelSelect(elementId, defaultKey) {
    const select = document.getElementById(elementId);
    select.innerHTML = '';
    availableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.key;
        // Đánh dấu rõ model chưa kiểm chứng để không hứa suông với người dùng
        option.textContent = model.verified ? model.label : `${model.label} (chưa kiểm chứng)`;
        select.appendChild(option);
    });
    select.value = defaultKey;
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
            speakMove(data.last_move);
        }

        if (data.game_over) {
            stopAutoPlay();
            showResultBanner(data);
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
    hideResultBanner();
    const resp = await fetch('/api/reset', { method: 'POST' });
    const data = await resp.json();
    updateUI(data);
}

// Banner kết quả — thay alert() vì hộp thoại browser làm gián đoạn việc ghi hình
function showResultBanner(state) {
    const isDraw = state.result_status === 'draw';
    document.getElementById('result-reason').textContent = state.result_text || 'KẾT THÚC TRẬN ĐẤU';
    document.getElementById('result-winner').textContent = isDraw
        ? 'HOÀ!'
        : `${state.winner} THẮNG!`;
    document.getElementById('result-detail').textContent =
        `Tổng ${state.history_count} nước đi · Nước sai luật: Đỏ ${state.stats.red.illegal_attempts} - Đen ${state.stats.black.illegal_attempts}`;
    document.getElementById('result-overlay').classList.remove('hidden');
}

function hideResultBanner() {
    document.getElementById('result-overlay').classList.add('hidden');
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

    // Cảnh báo chiếu tướng — kịch tính nhất trong cờ tướng, cần nổi bật khi quay video
    document.getElementById('check-alert').classList.toggle('visible', !!state.in_check);

    // Player Cards
    document.getElementById('name-red').textContent = state.red_config.name;
    document.getElementById('model-red').textContent = describeConfig(state.red_config);

    document.getElementById('name-black').textContent = state.black_config.name;
    document.getElementById('model-black').textContent = describeConfig(state.black_config);

    updatePlayerStats('red', state.stats.red);
    updatePlayerStats('black', state.stats.black);
    updateEvalBar(state.eval_cp);
    updateQualityBadge(state.last_move);
    updateAnalysisWarning(state);

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

// Nhãn model dưới tên kỳ thủ; lấy từ danh mục nạp qua /api/models
function describeConfig(config) {
    const model = availableModels.find(m => m.key === config.model_key);
    if (!model) return config.model_key || 'Mock';
    const effort = config.effort ? ` · effort ${config.effort}` : '';
    return `${model.label}${effort}`;
}

function updatePlayerStats(sideKey, stats) {
    const illegalEl = document.getElementById(`illegal-${sideKey}`);
    illegalEl.textContent = `Sai luật: ${stats.illegal_attempts}`;
    illegalEl.classList.toggle('has-violation', stats.illegal_attempts > 0);

    const avgSeconds = stats.moves > 0 ? (stats.total_latency_ms / stats.moves / 1000) : 0;
    document.getElementById(`latency-${sideKey}`).textContent = `Nghĩ: ${avgSeconds.toFixed(1)}s`;

    const accuracyEl = document.getElementById(`accuracy-${sideKey}`);
    if (stats.accuracy === null) {
        accuracyEl.textContent = 'Độ chính xác: —';
    } else {
        accuracyEl.textContent = `Độ chính xác: ${stats.accuracy}% · Blunder: ${stats.blunders}`;
    }
}

// Eval bar: cp dương = Đỏ ưu thế. Nén bằng hàm phi tuyến để lợi thế nhỏ vẫn thấy được
// và lợi thế lớn không làm cột chạm đáy ngay.
function updateEvalBar(evalCp) {
    const cp = evalCp || 0;
    const clamped = Math.max(-1000, Math.min(1000, cp));
    const redShare = 50 + 50 * (2 / (1 + Math.exp(-0.004 * clamped)) - 1);
    document.getElementById('eval-bar-fill').style.height = `${redShare.toFixed(1)}%`;

    const pawnUnits = (cp / 100).toFixed(1);
    document.getElementById('eval-value-red').textContent = cp >= 0 ? `+${pawnUnits}` : pawnUnits;
    document.getElementById('eval-value-black').textContent = cp <= 0 ? `+${(-cp / 100).toFixed(1)}` : `${(-cp / 100).toFixed(1)}`;
}

// Badge chất lượng hiện trên thẻ của người vừa đi; xoá badge của bên còn lại
function updateQualityBadge(lastMove) {
    const badges = { red: document.getElementById('quality-red'), black: document.getElementById('quality-black') };
    if (!lastMove || !lastMove.evaluation) {
        Object.values(badges).forEach(el => el.classList.remove('visible'));
        return;
    }

    const moverKey = lastMove.side === 'w' ? 'red' : 'black';
    const otherKey = moverKey === 'red' ? 'black' : 'red';
    const evaluation = lastMove.evaluation;

    const badge = badges[moverKey];
    badge.className = `quality-badge visible q-${evaluation.quality}`;
    badge.textContent = evaluation.cp_loss > 0
        ? `${evaluation.quality_label} (−${evaluation.cp_loss})`
        : evaluation.quality_label;

    badges[otherKey].classList.remove('visible');
}

function updateAnalysisWarning(state) {
    const warningEl = document.getElementById('analysis-warning');
    if (state.analysis_enabled) {
        warningEl.hidden = true;
        return;
    }
    warningEl.hidden = false;
    warningEl.textContent = `⚠️ Chưa chấm điểm nước đi: ${state.analysis_note || 'chạy ./scripts/install-pikafish.sh để bật'}`;
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

// Web Speech Synthesis (TTS) — đọc ký hiệu cờ tướng ("Pháo 2 bình 5") rồi tới lời bình
function speakMove(lastMove) {
    if (!synth) return;
    const parts = [];
    if (lastMove.vi_text) parts.push(lastMove.vi_text);
    if (lastMove.reasoning) parts.push(lastMove.reasoning);
    if (parts.length === 0) return;

    synth.cancel(); // dừng câu trước để không đọc dồn khi chạy tốc độ nhanh
    const utterance = new SpeechSynthesisUtterance(parts.join('. '));
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
    const buildConfig = (sideKey, fallbackName) => {
        const modelKey = document.getElementById(`cfg-${sideKey}-model`).value;
        const model = availableModels.find(m => m.key === modelKey);
        return {
            // Bỏ trống tên -> lấy tên model để overlay luôn hiển thị đúng kỳ thủ
            name: document.getElementById(`cfg-${sideKey}-name`).value || (model ? model.label : fallbackName),
            model_key: modelKey,
            effort: document.getElementById(`cfg-${sideKey}-effort`).value || undefined,
            api_key: document.getElementById(`cfg-${sideKey}-key`).value || undefined
        };
    };
    const redConfig = buildConfig('red', 'Kỳ thủ Đỏ');
    const blackConfig = buildConfig('black', 'Kỳ thủ Đen');

    closeModal();

    const resp = await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ red_config: redConfig, black_config: blackConfig })
    });
    const data = await resp.json();
    updateUI(data);
}
