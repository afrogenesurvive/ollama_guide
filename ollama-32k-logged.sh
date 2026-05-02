#!/bin/bash
# sh ollama-32k-logged.sh gemma4:e2b --no-log

MODEL_BASE="$1"
ARG2="$2"
ARG3="$3"

NO_LOG=0
if [ "$ARG2" = "--no-log" ] || [ "$ARG3" = "--no-log" ]; then
    NO_LOG=1
fi

MODEL_32K=""
if [ -n "$MODEL_BASE" ]; then
    MODEL_32K="${MODEL_BASE}-32k"
fi

# If arg2 is not the no-log flag, treat it as log filename.
LOG_FILE="ollama-$(date +%Y%m%d-%H%M%S).log"
if [ -n "$ARG2" ] && [ "$ARG2" != "--no-log" ]; then
    LOG_FILE="$ARG2"
fi

if ! command -v ollama >/dev/null 2>&1; then
    echo "❌ ollama command not found in PATH"
    exit 1
fi

if [ "$NO_LOG" -eq 1 ]; then
    if [ -z "$MODEL_BASE" ]; then
        echo "Usage: $0 <base-model> [log-file] [--no-log]"
        echo "Example: $0 gemma4:e2b --no-log"
        exit 1
    fi

    TARGET_MODEL="$MODEL_BASE"
    if ollama list | grep -q "$MODEL_32K"; then
        TARGET_MODEL="$MODEL_32K"
    fi

    echo "🚀 Running without logging: $TARGET_MODEL"
    exec ollama run "$TARGET_MODEL"
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found in PATH"
    exit 1
fi

LISTEN_HOST="${LISTEN_HOST:-127.0.0.1}"
LISTEN_PORT="${LISTEN_PORT:-11435}"
UPSTREAM="${UPSTREAM:-http://127.0.0.1:11434}"

echo "🚀 Starting proxy logging to $LOG_FILE"
echo "   Listen:  http://${LISTEN_HOST}:${LISTEN_PORT}"
echo "   Upstream: ${UPSTREAM}"
echo ""
echo "Set clients to use: http://${LISTEN_HOST}:${LISTEN_PORT}"
echo "Logger lifecycle is independent from Ollama/model lifecycle."
echo "Stopping this logger will NOT stop Ollama or any loaded model."
echo "Press Ctrl+C to stop logging."

LISTEN_HOST="$LISTEN_HOST" LISTEN_PORT="$LISTEN_PORT" UPSTREAM="$UPSTREAM" \
python3 ./ollama-with-logging.py "$LOG_FILE"