/**
 * Điều khiển studio phát sóng AI vs AI: gọi API, cập nhật giao diện, TTS.
 * Phần vẽ bàn cờ nằm ở js/board-renderer.js.
 */

import { renderBoardGrid, renderPieces } from './js/board-renderer.js';
import { ReplayController } from './js/replay-controller.js';
import { HumanInput } from './js/human-input.js';
import { createArenaClient } from './js/arena-client.js';
import * as geminiTts from './js/gemini-tts.js';
import { renderKeyVault } from './js/key-vault-ui.js';
import { classifyMove, playMoveSound } from './js/move-sound.js';
import { getKey, looksLikeApiKey, providerForEnv } from './js/key-vault.js';
import { VOICES as TTS_VOICES } from './js/gemini-tts.js';

let currentState = null;
let isAutoPlaying = false;
let autoPlayTimer = null;
let synth = window.speechSynthesis;
let availableModels = [];
let replay = null;
let humanInput = null;
// Lớp trung gian: chế độ Local gọi máy chủ Flask, chế độ Online chạy Pyodide trong trình
// duyệt. Phần còn lại của file này không cần biết đang ở chế độ nào.
let arena = null;
// Thế cờ TRƯỚC nước vừa rồi — so số quân để biết nước đó có ăn quân không, từ đó chọn
// đúng tiếng động. Trạng thái trả về không có cờ "vừa ăn quân".
let previousFen = null;

document.addEventListener('DOMContentLoaded', async () => {
    applyOverlayMode();
    renderBoardGrid(document.getElementById('board'));

    arena = await createArenaClient(showLoadingProgress);
    hideLoadingProgress();
    applyCapabilities(arena.capabilities);

    await loadModels();
    ttsModels = await arena.listTtsModels();
    setupTts();
    setupKeyVault();
    fetchState();

    // Event Listeners
    document.getElementById('btn-step').addEventListener('click', handleStep);
    document.getElementById('btn-auto').addEventListener('click', toggleAutoPlay);
    document.getElementById('btn-reset').addEventListener('click', handleReset);
    document.getElementById('btn-toggle-panel').addEventListener('click', openModal);
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-save-config').addEventListener('click', saveConfig);
    document.getElementById('btn-close-result').addEventListener('click', hideResultBanner);

    setupReplay();
    setupHumanPlay();
});

// ===== Chế độ Người vs AI =====

function setupHumanPlay() {
    humanInput = new HumanInput(document.getElementById('board'), submitHumanMove);
    document.getElementById('btn-hint').addEventListener('click', requestHint);
}

async function submitHumanMove(ucci) {
    try {
        const result = await arena.submitHumanMove(ucci);
        const data = result.state;
        if (!result.ok) {
            // Nước sai luật: hiện đúng lý do trọng tài đưa ra, không im lặng bỏ qua
            document.getElementById('referee-text').textContent = `Nước không hợp lệ: ${result.error}`;
            updateUI(data);
            return;
        }
        playMoveSound(classifyMove(previousFen, data));
        previousFen = data.fen;
        updateUI(data);
        if (data.last_move) speakMove(data.last_move);
        if (data.game_over) return showResultBanner(data);

        // Đi xong thì để AI đáp lại ngay, người chơi không phải bấm thêm nút
        if (!data.is_human_turn) await handleStep();
    } catch (e) {
        document.getElementById('referee-text').textContent = `Lỗi gửi nước đi: ${e.message}`;
    }
}

async function requestHint() {
    try {
        const data = await arena.requestHint();
        if (!data.ok) {
            document.getElementById('referee-text').textContent = data.error;
            return;
        }
        document.getElementById('referee-text').textContent =
            `Engine gợi ý: ${data.vi_text} [${data.ucci}] — nước này sẽ bị đánh dấu là có dùng gợi ý`;
    } catch (e) {
        document.getElementById('referee-text').textContent = `Không lấy được gợi ý: ${e.message}`;
    }
}

/**
 * Chế độ overlay cho OBS: ?overlay=1
 *
 * Ẩn toàn bộ nút bấm và thanh công cụ, nền trong suốt để chồng lớp trong OBS. Điều khiển
 * trận bằng tab khác hoặc gọi API từ máy khác — nhờ đó tay bấm không lọt vào khung hình.
 * Dùng lại chính trang này thay vì nhân bản mã, để hai chế độ không bị lệch nhau.
 */
function applyOverlayMode() {
    const params = new URLSearchParams(location.search);
    if (params.get('overlay') !== '1') return;

    document.body.classList.add('overlay-mode');
    // Nền trong suốt chỉ khi được yêu cầu; mặc định giữ nền tối để xem trên trình duyệt
    if (params.get('transparent') === '1') {
        document.body.classList.add('overlay-transparent');
    }
    // Tự làm mới để overlay bám theo trận đang chạy ở tab điều khiển
    const refreshMs = parseInt(params.get('refresh'), 10) || 1000;
    setInterval(() => { if (!replay || !replay.isActive) fetchState(); }, refreshMs);
}

// ===== Xem lại trận đã lưu (đọc từ cơ sở dữ liệu, không gọi API AI) =====

function setupReplay() {
    replay = new ReplayController({
        boardElement: document.getElementById('board'),
        onFrame: renderReplayFrame,
    });

    document.getElementById('btn-open-replays').addEventListener('click', openReplayList);
    document.getElementById('btn-close-replays').addEventListener('click',
        () => document.getElementById('modal-replays').classList.add('hidden'));
    document.getElementById('btn-replay-exit').addEventListener('click', exitReplay);
    document.getElementById('btn-replay-start').addEventListener('click', () => replay.seek(-1));
    document.getElementById('btn-replay-prev').addEventListener('click', () => replay.previous());
    document.getElementById('btn-replay-next').addEventListener('click', () => replay.next());
    document.getElementById('btn-replay-play').addEventListener('click', () => {
        const interval = parseInt(document.getElementById('sel-speed').value, 10) || 1200;
        replay.togglePlay(interval);
        updateReplayPlayButton();
    });
    document.getElementById('btn-replay-worst').addEventListener('click', () => {
        replay.pause();
        updateReplayPlayButton();
        if (!replay.seekWorstMove()) {
            document.getElementById('referee-text').textContent =
                'Trận này không có nước nào được chấm điểm (thiếu engine khi chạy).';
        }
    });
    document.getElementById('replay-slider').addEventListener('input', (event) => {
        replay.pause();
        updateReplayPlayButton();
        replay.seek(parseInt(event.target.value, 10));
    });
}

async function openReplayList() {
    const modal = document.getElementById('modal-replays');
    modal.classList.remove('hidden');
    await Promise.all([loadLeaderboard(), loadReplayList()]);
}

async function loadLeaderboard() {
    const container = document.getElementById('leaderboard-list');
    container.innerHTML = '<div class="data-empty">Đang tải…</div>';
    try {
        const leaderboard = await arena.leaderboard();
        if (!leaderboard.length) {
            container.innerHTML = '<div class="data-empty">Chưa có trận nào kết thúc đúng luật cờ.</div>';
            return;
        }
        container.innerHTML = leaderboard.map((row, index) => `
            <div class="data-row">
                <span class="rank">${index + 1}</span>
                <span class="grow">${escapeHtml(row.label)}</span>
                <span class="elo">Elo ${row.elo.toFixed(0)}</span>
                <span class="muted">${row.matches} trận · ${row.wins}W-${row.draws}D-${row.losses}L</span>
            </div>`).join('');
    } catch (e) {
        container.innerHTML = '<div class="data-empty">Không tải được bảng xếp hạng.</div>';
    }
}

async function loadReplayList() {
    if (!arena.capabilities.replay) return;   // bản online không lưu nước đi
    const container = document.getElementById('replay-list');
    container.innerHTML = '<div class="data-empty">Đang tải…</div>';
    try {
        const { replays } = await (await fetch('/api/replays')).json();
        if (!replays.length) {
            container.innerHTML = '<div class="data-empty">Chưa có trận nào được lưu.</div>';
            return;
        }
        container.innerHTML = replays.map(match => {
            const accuracy = (match.red_accuracy !== null && match.black_accuracy !== null)
                ? `${match.red_accuracy}% vs ${match.black_accuracy}%` : 'chưa chấm điểm';
            return `
            <div class="data-row replay-row" data-match-id="${match.id}">
                <span class="grow">
                    <strong>${escapeHtml(match.red_name)}</strong> vs
                    <strong>${escapeHtml(match.black_name)}</strong>
                    <span class="muted"> · ${match.total_plies} nước · ${accuracy}</span>
                </span>
                <span class="muted">${describeResult(match)}</span>
                <button class="btn btn-primary btn-small">Xem lại</button>
            </div>`;
        }).join('');
        container.querySelectorAll('.replay-row').forEach(row => {
            row.querySelector('button').addEventListener('click',
                () => startReplay(row.dataset.matchId));
        });
    } catch (e) {
        container.innerHTML = '<div class="data-empty">Không tải được danh sách trận.</div>';
    }
}

function describeResult(match) {
    if (match.status === 'ongoing') {
        return match.stopped_reason === 'move_limit' ? 'dừng do giới hạn nước'
            : match.stopped_reason === 'cost_budget' ? 'dừng do hết ngân sách' : 'chưa xong';
    }
    if (match.status === 'draw') return 'hoà';
    return match.status === 'red_win' ? 'Đỏ thắng' : 'Đen thắng';
}

async function startReplay(matchId) {
    stopAutoPlay();
    try {
        const match = await replay.load(matchId);
        document.getElementById('modal-replays').classList.add('hidden');
        document.getElementById('replay-bar').hidden = false;
        document.body.classList.add('replay-mode');
        document.getElementById('replay-title').textContent =
            `${match.red_name} (Đỏ) vs ${match.black_name} (Đen)`;
        const slider = document.getElementById('replay-slider');
        slider.min = -1;
        slider.max = Math.max(0, replay.totalPlies - 1);
        slider.value = -1;
    } catch (e) {
        document.getElementById('referee-text').textContent = `Không xem lại được: ${e.message}`;
    }
}

function exitReplay() {
    replay.close();
    document.getElementById('replay-bar').hidden = true;
    document.body.classList.remove('replay-mode');
    updateReplayPlayButton();
    fetchState();   // trở về trận đang đấu trực tiếp
}

function updateReplayPlayButton() {
    document.getElementById('btn-replay-play').textContent =
        replay && replay.isPlaying ? '⏸ Dừng' : '▶ Phát';
}

/** Cập nhật toàn bộ giao diện theo khung hình xem lại (dùng lại các hàm của chế độ live). */
function renderReplayFrame(frame) {
    const { match, move, index, total, stats } = frame;

    document.getElementById('replay-counter').textContent = `${index + 1} / ${total}`;
    document.getElementById('replay-slider').value = index;
    updateReplayPlayButton();

    document.getElementById('name-red').textContent = match.red_name;
    document.getElementById('name-black').textContent = match.black_name;
    document.getElementById('model-red').textContent = match.red_model_key;
    document.getElementById('model-black').textContent = match.black_model_key;

    const turnBadge = document.getElementById('turn-badge');
    const nextSide = move ? (move.side === 'w' ? 'b' : 'w') : 'w';
    turnBadge.textContent = nextSide === 'w' ? 'LƯỢT QUÂN ĐỎ' : 'LƯỢT QUÂN ĐEN';
    turnBadge.className = `turn-indicator ${nextSide === 'w' ? 'turn-red' : 'turn-black'}`;
    document.getElementById('move-counter').textContent = `Nước: #${index + 1}`;
    document.getElementById('check-alert').classList.toggle('visible', !!move?.in_check_after);

    updateEvalBar(stats.eval_cp);
    ['red', 'black'].forEach(sideKey => {
        const side = stats[sideKey];
        const accuracyEl = document.getElementById(`accuracy-${sideKey}`);
        accuracyEl.textContent = side.accuracy == null
            ? 'Độ chính xác: —'
            : `Độ chính xác: ${side.accuracy}% · Blunder: ${side.blunders}`;
        const illegalEl = document.getElementById(`illegal-${sideKey}`);
        illegalEl.textContent = `Sai luật: ${side.illegal_attempts}`;
        illegalEl.classList.toggle('has-violation', side.illegal_attempts > 0);
        document.getElementById(`latency-${sideKey}`).textContent = '';
    });
    document.getElementById('cost-value').textContent =
        `$${(stats.red.cost_usd + stats.black.cost_usd).toFixed(4)}`;

    // Badge chất lượng + lời thoại của nước đang xem
    updateQualityBadge(move ? {
        side: move.side,
        evaluation: move.quality ? {
            quality: move.quality,
            quality_label: qualityLabel(move.quality),
            cp_loss: move.cp_loss,
        } : null,
    } : null);

    if (move) {
        const sideKey = move.side === 'w' ? 'red' : 'black';
        document.getElementById(`reasoning-${sideKey}`).textContent = `"${move.taunt || ''}"`;
        const engineNote = move.engine_bestmove && move.cp_loss >= 200
            ? ` — engine khuyên ${move.engine_bestmove}` : '';
        document.getElementById('referee-text').textContent =
            `Nước #${index + 1}: ${move.vi_notation} [${move.ucci}]`
            + `${move.quality ? ' — ' + qualityLabel(move.quality) : ''}${engineNote}`;
    } else {
        document.getElementById('referee-text').textContent = 'Thế cờ ban đầu — bấm ▶ để xem lại.';
    }
}

const QUALITY_LABELS = {
    best: '⭐ NƯỚC HAY NHẤT', good: '✅ Tốt', fair: '🟢 Khá',
    inaccuracy: '🟡 Thiếu chính xác', mistake: '🟠 SAI NƯỚC', blunder: '🔴 BLUNDER!',
};

function qualityLabel(quality) {
    return QUALITY_LABELS[quality] || quality;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

// Nạp danh mục kỳ thủ và dựng dropdown — tránh hardcode model trong HTML
async function loadModels() {
    try {
        const data = await arena.listModels();
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
        const state = await arena.getState();
        previousFen = state.fen;
        updateUI(state);
    } catch (e) {
        console.error("Failed to fetch state:", e);
    }
}

async function handleStep() {
    if (replay && replay.isActive) return;   // đang xem lại thì không gọi API
    if (currentState && currentState.is_human_turn) {
        document.getElementById('referee-text').textContent =
            'Tới lượt bạn — bấm vào quân cờ để đi.';
        return;
    }
    // Tên bên sắp đi, lấy TRƯỚC khi gọi API để lớp phủ nói đúng ai đang nghĩ
    const thinkingPlayer = currentState
        ? (currentState.turn === 'w' ? currentState.red_config.name : currentState.black_config.name)
        : null;
    showThinking(thinkingPlayer);
    try {
        const data = await arena.step();
        playMoveSound(classifyMove(previousFen, data));
        previousFen = data.fen;
        updateUI(data);

        // TTS Speech synthesis if enabled
        if (data.last_move) speakMove(data.last_move);

        if (data.game_over) {
            stopAutoPlay();
            showResultBanner(data);
        } else if (isAutoPlaying && data.is_human_turn) {
            // Không được tự đi thay người chơi
            stopAutoPlay();
            document.getElementById('referee-text').textContent =
                'Đã dừng tự động: tới lượt bạn đi.';
        } else if (isAutoPlaying && exceedsBudget(data)) {
            stopAutoPlay();
            document.getElementById('referee-text').textContent =
                `Đã tự dừng: chi phí trận đạt ${formatUsd(data.cost_total_usd)}, `
                + `chạm ngân sách ${formatUsd(budgetLimit())}. `
                + `Nâng ngân sách rồi bấm Tự Động Đấu để tiếp.`;
        }
    } catch (e) {
        console.error("Step error:", e);
        document.getElementById('referee-text').textContent =
            'Lỗi gọi máy chủ — kiểm tra terminal đang chạy server.';
    } finally {
        hideThinking();
    }
}

// ===== Chế độ chạy: Local (có máy chủ) hay Online (Pyodide trong trình duyệt) =====

const LOADING_PHASES = {
    download: 'Đang tải bộ máy Python…',
    boot: 'Đang khởi động Python…',
    engine: 'Đang nạp luật cờ…',
    ready: 'Xong!',
};

function showLoadingProgress({ phase, ratio }) {
    const overlay = document.getElementById('loading-overlay');
    overlay.hidden = false;
    document.getElementById('loading-phase').textContent = LOADING_PHASES[phase] ?? phase;
    // Chỉ phase tải mới đo được theo byte; các phase sau chạy nhanh nên lấp đầy thanh luôn
    const percent = phase === 'download' ? Math.round((ratio ?? 0) * 100) : 100;
    document.getElementById('loading-bar').style.width = `${percent}%`;
}

function hideLoadingProgress() {
    document.getElementById('loading-overlay').hidden = true;
}

/**
 * Bật/tắt tính năng theo năng lực thật của chế độ đang chạy.
 *
 * Ẩn nút thay vì để người dùng bấm rồi nhận lỗi: bản online không có Pikafish nên không có
 * chấm điểm, không có gợi ý, và không lưu trận để xem lại.
 */
function applyCapabilities(capabilities) {
    const isLocal = capabilities.mode === 'local';

    const badge = document.getElementById('mode-badge');
    badge.hidden = false;
    badge.textContent = isLocal ? '🔬 Local — có Pikafish' : '🌐 Online — không chấm điểm';
    badge.classList.toggle('mode-online', !isLocal);

    // Nút vẫn giữ vì hộp thoại đó cũng chứa bảng xếp hạng — bản online có Elo riêng trong
    // trình duyệt. Chỉ ẩn phần danh sách trận, vì bản online không lưu nước đi.
    document.getElementById('replay-section').hidden = !capabilities.replay;
    // Nút Gợi Ý do updateUI điều khiển theo lượt; nó cũng đọc capabilities.analysis.
}

// Lớp phủ trong lúc chờ AI trả lời, kèm đồng hồ đếm để biết đã chờ bao lâu
let thinkingTimer = null;

function showThinking(playerName) {
    const overlay = document.getElementById('thinking-overlay');
    const label = document.getElementById('thinking-text');
    const startedAt = Date.now();
    const who = playerName ? `${playerName} đang suy nghĩ` : 'Đang suy nghĩ';

    label.textContent = `${who}…`;
    overlay.classList.add('visible');
    clearInterval(thinkingTimer);
    thinkingTimer = setInterval(() => {
        label.textContent = `${who}… ${((Date.now() - startedAt) / 1000).toFixed(0)}s`;
    }, 500);
}

function hideThinking() {
    clearInterval(thinkingTimer);
    document.getElementById('thinking-overlay').classList.remove('visible');
}

// Chỉ chặn được khi biết chi phí; model chưa niêm yết giá thì cost_total_usd là null
function exceedsBudget(state) {
    return typeof state.cost_total_usd === 'number' && state.cost_total_usd >= budgetLimit();
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
    previousFen = null;   // trận mới: chưa có thế cờ trước để so số quân
    updateUI(await arena.reset());
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
    updateCostMeter(state);
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

    renderPieces(document.getElementById('board'), state.fen, state.last_move);

    // Bật thao tác chuột và nút gợi ý đúng lượt người chơi
    const humanTurn = !!state.is_human_turn && !state.game_over;
    if (humanInput) humanInput.setState(humanTurn, state.legal_moves);
    document.body.classList.toggle('human-turn', humanTurn);
    // Gợi ý cần Pikafish, mà bản online không có -> ẩn hẳn thay vì để bấm rồi báo lỗi
    document.getElementById('btn-hint').hidden = !humanTurn || !arena?.capabilities.analysis;
    if (humanTurn) {
        document.getElementById('referee-text').textContent =
            'Tới lượt bạn — bấm vào quân cờ để xem các nước đi được.';
    }
}

// Dòng phụ dưới tên kỳ thủ: nêu nhà cung cấp và ID model chính xác, không lặp lại tên
// (tên kỳ thủ mặc định đã là nhãn model nên lặp lại là dư thừa)
function describeConfig(config) {
    const model = availableModels.find(m => m.key === config.model_key);
    if (!model) return config.model_key || 'mock';
    const effort = config.effort && model.provider === 'anthropic' ? ` · effort ${config.effort}` : '';
    return `${model.provider} · ${model.model_id}${effort}`;
}

// Bộ đếm chi phí. cost_total_usd = null khi có kỳ thủ dùng model chưa niêm yết giá —
// khi đó hiện "—" thay vì con số sai, và ngân sách tự dừng không thể áp dụng.
function updateCostMeter(state) {
    const element = document.getElementById('cost-value');
    const cost = state.cost_total_usd;
    if (cost == null) {
        element.textContent = '—';
        element.classList.remove('over-budget');
        return;
    }
    element.textContent = `$${cost.toFixed(4)}`;
    element.classList.toggle('over-budget', cost >= budgetLimit() * 0.8);
}

// Số tiền nhỏ hơn 1 xu vẫn phải đọc được: toFixed(2) sẽ biến $0.003 thành "$0.00"
function formatUsd(value) {
    if (!Number.isFinite(value)) return '∞';
    return value < 0.01 ? `$${value.toFixed(4)}` : `$${value.toFixed(2)}`;
}

function budgetLimit() {
    const value = parseFloat(document.getElementById('inp-budget').value);
    return Number.isFinite(value) && value > 0 ? value : Infinity;
}

function updatePlayerStats(sideKey, stats) {
    const illegalEl = document.getElementById(`illegal-${sideKey}`);
    illegalEl.textContent = `Sai luật: ${stats.illegal_attempts}`;
    illegalEl.classList.toggle('has-violation', stats.illegal_attempts > 0);

    const avgSeconds = stats.moves > 0 ? (stats.total_latency_ms / stats.moves / 1000) : 0;
    document.getElementById(`latency-${sideKey}`).textContent = `Nghĩ: ${avgSeconds.toFixed(1)}s`;

    const accuracyEl = document.getElementById(`accuracy-${sideKey}`);
    // == null bắt CẢ null lẫn undefined: Pyodide chuyển None của Python thành undefined,
    // nên so sánh === null sẽ trượt và giao diện hiện "undefined%" ở bản online.
    if (stats.accuracy == null) {
        accuracyEl.textContent = 'Độ chính xác: —';
    } else {
        accuracyEl.textContent = `Độ chính xác: ${stats.accuracy}% · Blunder: ${stats.blunders}`;
    }
}

// Eval bar: cp dương = Đỏ ưu thế. Nén bằng hàm phi tuyến để lợi thế nhỏ vẫn thấy được
// và lợi thế lớn không làm cột chạm đáy ngay.
// Engine quy thế chiếu bí về khoảng ±30000 centipawn
const MATE_SCORE_THRESHOLD = 20000;

function updateEvalBar(evalCp) {
    const cp = evalCp || 0;
    const clamped = Math.max(-1000, Math.min(1000, cp));
    const redShare = 50 + 50 * (2 / (1 + Math.exp(-0.004 * clamped)) - 1);
    document.getElementById('eval-bar-fill').style.height = `${redShare.toFixed(1)}%`;

    // Chỉ bên đang có ưu thế mới hiện con số — hai đầu cùng hiện "+0.0" gây rối cho
    // người xem. Đơn vị quy về "quân" (100 centipawn = 1 quân) cho dễ hiểu.
    // Thế chiếu bí được engine quy về ±30000 centipawn; chia 100 sẽ ra "+293.0" vô nghĩa,
    // nên hiển thị chữ "BÍ" thay vì con số.
    const isMate = Math.abs(cp) > MATE_SCORE_THRESHOLD;
    const advantage = isMate ? 'BÍ' : `+${Math.abs(cp / 100).toFixed(1)}`;
    const redLabel = document.getElementById('eval-value-red');
    const blackLabel = document.getElementById('eval-value-black');
    const redAhead = cp > 20;
    const blackAhead = cp < -20;

    redLabel.textContent = redAhead ? `ĐỎ ${advantage}` : 'ĐỎ';
    blackLabel.textContent = blackAhead ? `ĐEN ${advantage}` : 'ĐEN';
    redLabel.classList.toggle('leading', redAhead);
    blackLabel.classList.toggle('leading', blackAhead);
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

// Web Speech Synthesis (TTS) — đọc ký hiệu cờ tướng ("Pháo 2 bình 5") rồi tới lời bình
// ===== Kho API key =====

function setupKeyVault() {
    renderKeyVault({ mode: arena.capabilities.mode, onChange: refreshKeyWarnings });
    ['red', 'black'].forEach(side => {
        document.getElementById(`cfg-${side}-model`)
            .addEventListener('change', refreshKeyWarnings);
        // Dán nhầm key vào ô tên là lộ nó lên overlay, tức là lộ luôn trong video
        document.getElementById(`cfg-${side}-name`).addEventListener('input', refreshKeyWarnings);
    });
    refreshKeyWarnings();
}

/** Key của nhà cung cấp tương ứng với model. Trả undefined nếu model không cần key. */
function keyForModel(model) {
    if (!model || !model.api_key_env) return undefined;
    return getKey(providerForEnv(model.api_key_env)) || undefined;
}

/**
 * Cảnh báo ngay trong hộp thoại, TRƯỚC khi bắt đầu trận.
 *
 * Không có cảnh báo thì người dùng bấm Bắt Đầu rồi mới phát hiện kỳ thủ của mình âm thầm rơi
 * về Mock — tưởng đang xem Claude đánh cờ mà thật ra là đi ngẫu nhiên.
 */
function refreshKeyWarnings() {
    ['red', 'black'].forEach(side => {
        const warning = document.getElementById(`cfg-${side}-keywarn`);
        const model = availableModels.find(
            m => m.key === document.getElementById(`cfg-${side}-model`).value);
        const messages = [];

        if (model && model.api_key_env && !keyForModel(model)) {
            messages.push(`⚠️ Chưa có key cho ${model.label} — kỳ thủ này sẽ chạy Mock (đi ngẫu nhiên).`);
        }
        if (looksLikeApiKey(document.getElementById(`cfg-${side}-name`).value)) {
            messages.push('⚠️ Ô tên đang chứa thứ trông giống API key. Tên hiển thị công khai trên overlay.');
        }

        warning.hidden = messages.length === 0;
        warning.textContent = messages.join(' ');
    });
}

// ===== Đọc lời bình =====

let ttsModels = [];

function ttsMode() {
    return document.getElementById('sel-tts-mode').value;
}

const TTS_MODE_KEY = 'xiangqi-arena.tts-mode';

/**
 * Dựng phần chọn giọng đọc.
 *
 * Chế độ được đặt TƯỜNG MINH từ localStorage, mặc định Web Speech (miễn phí). Không dựa vào
 * thuộc tính `selected` trong HTML: Chrome khôi phục giá trị select giữa các tab cùng origin,
 * nên trang mới mở có thể tự nhảy sang Gemini — tức là tự bật một lựa chọn TỐN TIỀN mà người
 * dùng không hề chọn.
 */
function setupTts() {
    const modeSelect = document.getElementById('sel-tts-mode');
    const options = document.getElementById('tts-gemini-options');
    const modelSelect = document.getElementById('sel-tts-model');
    const voiceSelect = document.getElementById('sel-tts-voice');

    ttsModels.forEach(model => {
        modelSelect.add(new Option(model.label, model.key));
    });
    TTS_VOICES.forEach(voice => voiceSelect.add(new Option(voice, voice)));
    modelSelect.value = 'gemini-2.5-flash-tts';   // rẻ nhất, đủ tốt cho lời bình

    const saved = localStorage.getItem(TTS_MODE_KEY);
    modeSelect.value = ['web', 'gemini', 'off'].includes(saved) ? saved : 'web';

    const syncVisibility = () => { options.hidden = modeSelect.value !== 'gemini'; };
    modeSelect.addEventListener('change', () => {
        localStorage.setItem(TTS_MODE_KEY, modeSelect.value);
        syncVisibility();
        if (modeSelect.value === 'gemini' && !geminiTts.isAvailable()) {
            document.getElementById('referee-text').textContent =
                'Chưa có API key Gemini — sẽ tự đọc bằng Web Speech cho tới khi bạn nhập key.';
        }
    });
    syncVisibility();
}

function speakMove(lastMove) {
    const mode = ttsMode();
    if (mode === 'off') return;

    const parts = [];
    if (lastMove.vi_text) parts.push(lastMove.vi_text);
    if (lastMove.reasoning) parts.push(lastMove.reasoning);
    if (parts.length === 0) return;
    const text = parts.join('. ');

    if (mode === 'web' || !geminiTts.isAvailable()) return speakWithWebSpeech(text);
    speakWithGemini(text);
}

function speakWithWebSpeech(text) {
    if (!synth) return;
    synth.cancel(); // dừng câu trước để không đọc dồn khi chạy tốc độ nhanh
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'vi-VN';
    utterance.rate = 1.0;
    synth.speak(utterance);
}

/**
 * Đọc bằng Gemini, KHÔNG chặn nước tiếp theo.
 *
 * Trận cờ chạy song song với tiếng: chờ đọc xong mới đi tiếp sẽ cộng thêm vài giây mỗi nước.
 * Lỗi gọi API thì tự chuyển về Web Speech và ghi chú, không được im lặng mất tiếng.
 */
function speakWithGemini(text) {
    const model = ttsModels.find(m => m.key === document.getElementById('sel-tts-model').value);
    if (!model) return speakWithWebSpeech(text);

    geminiTts.speak(text, {
        model,
        voice: document.getElementById('sel-tts-voice').value,
    }).then(result => {
        if (result.skipped) return;   // đang đọc câu trước, bỏ qua câu này
        if (!result.ok) {
            document.getElementById('referee-text').textContent =
                `Giọng Gemini lỗi (${result.error}) — tạm đọc bằng Web Speech.`;
            speakWithWebSpeech(text);
            return;
        }
        updateTtsCost();
    });
}

function updateTtsCost() {
    const cost = geminiTts.sessionCostUsd();
    const element = document.getElementById('tts-cost');
    if (!element) return;
    element.hidden = cost <= 0;
    element.textContent = `+ đọc tiếng ${formatUsd(cost)}`;
}

// Web Audio API Synthetic Piece Sound

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
            // Chỉ gửi key lên máy chủ ở chế độ Local, nơi vòng lặp trọng tài chạy server-side.
            // Chế độ Online không gửi: trình duyệt tự gọi API bằng key trong kho.
            api_key: arena.capabilities.mode === 'local' ? keyForModel(model) : undefined,
        };
    };
    const redConfig = buildConfig('red', 'Kỳ thủ Đỏ');
    const blackConfig = buildConfig('black', 'Kỳ thủ Đen');

    closeModal();

    previousFen = null;
    updateUI(await arena.reset(redConfig, blackConfig));
}
