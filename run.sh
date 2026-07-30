#!/bin/bash

echo "=========================================================="
echo " ♟️  AI vs AI Cờ Tướng (Xiangqi Studio) Startup Script  ♟️ "
echo "=========================================================="

cd "$(dirname "$0")"

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    exit 1
fi

# Create virtualenv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Virtual Environment (venv)..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install --quiet -r requirements.txt

# Run server
echo "🚀 Launching Xiangqi Studio Server on http://localhost:5000..."
python3 server.py
