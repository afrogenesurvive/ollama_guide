#!/bin/bash

MODEL_BASE="$1"
MODEL_32K="${MODEL_BASE}-32k"
LOG_FILE="${2:-ollama-$(date +%Y%m%d-%H%M%S).log}"

# Check if the 32K model already exists
if ! ollama list | grep -q "$MODEL_32K"; then
    echo "📦 32K model not found. Creating $MODEL_32K..."
    ./create-32k-model.sh "$MODEL_BASE" "$MODEL_32K"
fi

# Run with logging
echo "🚀 Running $MODEL_32K with logging to $LOG_FILE"
./ollama-with-logging.sh "$MODEL_32K" "$LOG_FILE"