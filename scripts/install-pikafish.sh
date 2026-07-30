#!/bin/bash
# Cài Pikafish (engine cờ tướng mã nguồn mở, GPL) làm trọng tài chấm điểm nước đi.
# Miễn phí, chạy local bằng CPU, không có chi phí API.
#
# Cách dùng:  ./scripts/install-pikafish.sh
# Kết quả:    engine/bin/pikafish + engine/bin/pikafish.nnue

set -euo pipefail

cd "$(dirname "$0")/.."
BIN_DIR="engine/bin"
WORK_DIR=".pikafish-download"
# Tên asset có kèm ngày phát hành (vd Pikafish.2026-01-02.7z) nên phải hỏi GitHub API,
# không thể dùng URL latest/download cố định.
RELEASE_API="https://api.github.com/repos/official-pikafish/Pikafish/releases/latest"

mkdir -p "$BIN_DIR"

if [ -x "$BIN_DIR/pikafish" ] && [ -f "$BIN_DIR/pikafish.nnue" ]; then
    echo "✅ Pikafish đã có sẵn tại $BIN_DIR"
    exit 0
fi

if ! command -v 7z &> /dev/null; then
    echo "❌ Thiếu 7z. Cài bằng: brew install p7zip"
    exit 1
fi

echo "🔎 Tìm release mới nhất..."
ASSET_URL="$(curl -fsSL "$RELEASE_API" \
    | grep -o '"browser_download_url": *"[^"]*\.7z"' \
    | head -1 | sed 's/.*"\(https[^"]*\)"/\1/')"

if [ -z "$ASSET_URL" ]; then
    echo "❌ Không tìm được asset .7z trong release mới nhất."
    exit 1
fi

echo "📥 Tải $(basename "$ASSET_URL") (~55MB)..."
rm -rf "$WORK_DIR" && mkdir -p "$WORK_DIR"
curl -fsSL -o "$WORK_DIR/pikafish.7z" "$ASSET_URL"

echo "📦 Giải nén..."
7z x -y -o"$WORK_DIR/extracted" "$WORK_DIR/pikafish.7z" > /dev/null

# Tìm binary macOS phù hợp kiến trúc máy (apple-silicon hoặc x86-64)
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
    BINARY_PATTERN="*apple*silicon*"
else
    BINARY_PATTERN="*apple*x86*"
fi

BINARY_PATH="$(find "$WORK_DIR/extracted" -type f -name "$BINARY_PATTERN" ! -name "*.nnue" | head -1)"
NNUE_PATH="$(find "$WORK_DIR/extracted" -type f -name "*.nnue" | head -1)"

if [ -z "$BINARY_PATH" ]; then
    echo "⚠️  Không tìm thấy binary macOS trong release (kiến trúc: $ARCH)."
    echo "   Chuyển sang build từ source..."
    rm -rf "$WORK_DIR/src-build"
    git clone --depth 1 https://github.com/official-pikafish/Pikafish.git "$WORK_DIR/src-build"
    MAKE_ARCH=$([ "$ARCH" = "arm64" ] && echo "apple-silicon" || echo "x86-64-bmi2")
    make -C "$WORK_DIR/src-build/src" -j build ARCH="$MAKE_ARCH"
    BINARY_PATH="$WORK_DIR/src-build/src/pikafish"
    [ -z "$NNUE_PATH" ] && NNUE_PATH="$(find "$WORK_DIR/src-build" -name "*.nnue" | head -1)"
fi

if [ -z "$NNUE_PATH" ]; then
    echo "❌ Không tìm thấy file NNUE (.nnue) — engine không chạy được không có nó."
    exit 1
fi

cp "$BINARY_PATH" "$BIN_DIR/pikafish"
cp "$NNUE_PATH" "$BIN_DIR/pikafish.nnue"
chmod +x "$BIN_DIR/pikafish"

# macOS Gatekeeper chặn binary tải từ internet -> bỏ cờ quarantine
xattr -d com.apple.quarantine "$BIN_DIR/pikafish" 2>/dev/null || true

echo "🔍 Kiểm tra engine..."
if printf 'uci\nquit\n' | "$BIN_DIR/pikafish" 2>/dev/null | grep -q "uciok"; then
    echo "✅ Pikafish hoạt động: $BIN_DIR/pikafish"
    rm -rf "$WORK_DIR"
    echo "   Thêm vào .env nếu cần:  PIKAFISH_PATH=engine/bin/pikafish"
else
    echo "❌ Engine không phản hồi 'uciok'. Giữ lại $WORK_DIR để kiểm tra."
    exit 1
fi
