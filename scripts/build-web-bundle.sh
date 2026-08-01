#!/bin/bash
# Đóng gói lõi Python thành zip để Pyodide giải nén trong trình duyệt.
#
# Chỉ gói phần CHẠY ĐƯỢC trong trình duyệt. Các module dùng subprocess (Pikafish) hoặc
# SQLite (lưu trận) nằm ngoài — gói vào cũng chỉ để vỡ lúc chạy, và làm người đọc mã tưởng
# bản online có những tính năng đó.
#
# Cách dùng:  ./scripts/build-web-bundle.sh
# Kết quả:    web/vendor/engine-core.zip

set -euo pipefail

cd "$(dirname "$0")/.."
OUT="web/vendor/engine-core.zip"
WORK_DIR=".web-bundle-build"

# Danh sách tường minh, không dùng ký tự đại diện: thêm module mới vào bundle phải là một
# quyết định có ý thức, vì mọi thứ ở đây đều tải về máy người dùng.
# engine/ không có __init__.py — là namespace package, Python 3 tự nhận.
FILES=(
    engine/browser_bridge.py
    engine/model_registry.py
    engine/prompt_builder.py
    engine/referee.py
    engine/xiangqi/__init__.py
    engine/xiangqi/attack_detection.py
    engine/xiangqi/board.py
    engine/xiangqi/game_rules.py
    engine/xiangqi/move_generation.py
    engine/xiangqi/notation.py
    engine/providers/__init__.py
    engine/providers/base_provider.py
    engine/providers/external_provider.py
    engine/providers/human_provider.py
    engine/providers/mock_provider.py
    engine/analysis/__init__.py
    engine/analysis/move_quality_scorer.py
    engine/storage/__init__.py
    engine/storage/elo_rating.py
)

rm -rf "$WORK_DIR"
for path in "${FILES[@]}"; do
    if [ ! -f "$path" ]; then
        echo "❌ Thiếu $path — danh sách trong script này đã lệch so với mã nguồn"
        exit 1
    fi
    mkdir -p "$WORK_DIR/$(dirname "$path")"
    cp "$path" "$WORK_DIR/$path"
done

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$WORK_DIR" && zip -qr "../$OUT" engine)
rm -rf "$WORK_DIR"

echo "✅ Xong: $OUT ($(du -h "$OUT" | cut -f1), ${#FILES[@]} file)"
