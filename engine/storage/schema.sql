-- Lược đồ cơ sở dữ liệu đấu trường cờ tướng AI.
--
-- Mục tiêu: lưu đủ để REPLAY một trận mà không cần gọi lại API. Vì vậy mỗi nước đi lưu
-- kèm fen_after — chỉ cần đọc chuỗi này là dựng lại được thế cờ, không phải chạy lại engine
-- hay hỏi lại AI.

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- Một dòng cho mỗi model tham gia. Elo tính theo model_key (không theo tên hiển thị,
-- vì tên có thể sửa tuỳ ý trong giao diện).
CREATE TABLE IF NOT EXISTS players (
    model_key   TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    provider    TEXT,
    elo         REAL NOT NULL DEFAULT 1500,
    matches     INTEGER NOT NULL DEFAULT 0,
    wins        INTEGER NOT NULL DEFAULT 0,
    losses      INTEGER NOT NULL DEFAULT 0,
    draws       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matches (
    id              TEXT PRIMARY KEY,
    red_model_key   TEXT NOT NULL,
    black_model_key TEXT NOT NULL,
    red_name        TEXT NOT NULL,
    black_name      TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    -- ongoing | red_win | black_win | draw
    status          TEXT NOT NULL DEFAULT 'ongoing',
    winner_side     TEXT,
    result_reason   TEXT,
    -- Lý do dừng ngoài luật cờ: move_limit, cost_budget, interrupted
    stopped_reason  TEXT,
    total_plies     INTEGER NOT NULL DEFAULT 0,
    initial_fen     TEXT NOT NULL,
    -- Thống kê chốt lại khi trận kết thúc, để truy vấn bảng xếp hạng không phải quét bảng moves
    red_accuracy    REAL,
    black_accuracy  REAL,
    red_blunders    INTEGER NOT NULL DEFAULT 0,
    black_blunders  INTEGER NOT NULL DEFAULT 0,
    red_illegal     INTEGER NOT NULL DEFAULT 0,
    black_illegal   INTEGER NOT NULL DEFAULT 0,
    red_cost_usd    REAL,
    black_cost_usd  REAL,
    elo_applied     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (red_model_key) REFERENCES players (model_key),
    FOREIGN KEY (black_model_key) REFERENCES players (model_key)
);

CREATE INDEX IF NOT EXISTS idx_matches_started ON matches (started_at DESC);

CREATE TABLE IF NOT EXISTS moves (
    match_id        TEXT NOT NULL,
    ply             INTEGER NOT NULL,
    side            TEXT NOT NULL,          -- 'w' hoặc 'b'
    ucci            TEXT NOT NULL,
    vi_notation     TEXT NOT NULL,
    -- Thế cờ SAU nước đi: nguồn duy nhất để replay, không cần engine hay API
    fen_after       TEXT NOT NULL,
    in_check_after  INTEGER NOT NULL DEFAULT 0,
    cp_before       INTEGER,
    cp_after        INTEGER,
    cp_loss         INTEGER,
    quality         TEXT,
    accuracy        REAL,
    engine_bestmove TEXT,
    engine_pv       TEXT,                   -- danh sách nước, ngăn cách bằng dấu cách
    analysis        TEXT,                   -- phân tích kỹ thuật của AI
    taunt           TEXT,                   -- câu thoại cho khán giả
    attempts        TEXT,                   -- JSON: mọi nước AI đã thử, kể cả nước sai luật
    referee_override TEXT,                  -- nước trọng tài chọn thay, NULL nếu không có
    error           TEXT,
    latency_ms      INTEGER,
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    cost_usd        REAL,
    PRIMARY KEY (match_id, ply),
    FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE
);
