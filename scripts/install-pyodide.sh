#!/bin/bash
# Cài Pyodide (CPython biên dịch sang WebAssembly) để lõi Python chạy được trong trình duyệt.
#
# Tự host thay vì gọi CDN: bản online không lệ thuộc dịch vụ ngoài, và chạy được cả khi
# không có mạng. Thư mục kết quả KHÔNG vào git (xem .gitignore) vì file .wasm gần 10MB là
# blob nhị phân, mỗi lần nâng phiên bản sẽ nằm lại vĩnh viễn trong lịch sử git.
#
# Cách dùng:  ./scripts/install-pyodide.sh
# Kết quả:    web/vendor/pyodide/

set -euo pipefail

cd "$(dirname "$0")/.."
VENDOR_DIR="web/vendor/pyodide"
WORK_DIR=".pyodide-download"
RELEASE_API="https://api.github.com/repos/pyodide/pyodide/releases/latest"

# Chỉ những file trình duyệt thật sự cần. Bản tải về còn kèm khai báo TypeScript và
# trình chạy dòng lệnh — vô dụng ở đây và chiếm chỗ.
KEEP=(pyodide.js pyodide.mjs pyodide.asm.mjs pyodide.asm.wasm python_stdlib.zip
      pyodide-lock.json package.json)

if [ -f "$VENDOR_DIR/pyodide.asm.wasm" ]; then
    echo "✅ Pyodide đã có sẵn tại $VENDOR_DIR"
    exit 0
fi

echo "🔎 Tìm release mới nhất..."
TAG="$(curl -fsSL "$RELEASE_API" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
echo "   Phiên bản: $TAG"

# Bản "core" (~7MB nén) đủ cho trình duyệt. Bản đầy đủ 426MB kèm hàng trăm gói khoa học
# mà dự án này không dùng gói nào.
ASSET="pyodide-core-$TAG.tar.bz2"
URL="https://github.com/pyodide/pyodide/releases/download/$TAG/$ASSET"

rm -rf "$WORK_DIR" && mkdir -p "$WORK_DIR"
echo "⬇️  Tải $ASSET ..."
curl -fsSL -o "$WORK_DIR/core.tar.bz2" "$URL"
tar -xjf "$WORK_DIR/core.tar.bz2" -C "$WORK_DIR"

mkdir -p "$VENDOR_DIR"
for name in "${KEEP[@]}"; do
    if [ -f "$WORK_DIR/pyodide/$name" ]; then
        cp "$WORK_DIR/pyodide/$name" "$VENDOR_DIR/$name"
    fi
done
rm -rf "$WORK_DIR"

echo "$TAG" > "$VENDOR_DIR/VERSION"
echo "✅ Xong: $VENDOR_DIR ($(du -sh "$VENDOR_DIR" | cut -f1))"
