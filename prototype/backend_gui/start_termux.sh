#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"
command -v python >/dev/null || { echo "Python missing. Run: pkg install python"; exit 1; }
command -v ffmpeg >/dev/null || { echo "FFmpeg missing. Run: pkg install ffmpeg"; exit 1; }
export AIVE_HOST="${AIVE_HOST:-0.0.0.0}"
export AIVE_PORT="${AIVE_PORT:-8080}"
export AIVE_WORKERS="${AIVE_WORKERS:-2}"
echo "Starting AIVideoEdit Alpha Stack on port $AIVE_PORT with $AIVE_WORKERS workers..."
exec python stack.py
