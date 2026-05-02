#!/bin/bash

# Usage: ./ollama-with-logging.sh <model-name> [log-file]
# Example: ./ollama-with-logging.sh gemma4:e2b-32k

MODEL="$1"
LOG_FILE="${2:-ollama-performance-$(date +%Y%m%d-%H%M%S).log}"

if [ -z "$MODEL" ]; then
    echo "Usage: $0 <model-name> [log-file]"
    echo "Example: $0 gemma4:e2b-32k my-session.log"
    exit 1
fi

echo "🚀 Starting Ollama with model: $MODEL"
echo "📝 Logging to: $LOG_FILE"
echo "========================================="

# Function to log with timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Start logging session
log_with_timestamp "=== Ollama Session Started ==="
log_with_timestamp "Model: $MODEL"
log_with_timestamp "System: $(uname -msr)"
log_with_timestamp "RAM: $(sysctl hw.memsize | awk '{print $2/1073741824 " GB"}')"

# Check if model exists
if ! ollama list | grep -q "$MODEL"; then
    log_with_timestamp "❌ ERROR: Model '$MODEL' not found in ollama list"
    log_with_timestamp "Available models:"
    ollama list | tee -a "$LOG_FILE"
    exit 1
fi

# Run the model with verbose logging and capture everything
log_with_timestamp "✅ Starting interactive session..."

# Create a named pipe for capturing output
mkfifo /tmp/ollama-pipe-$$

# Start ollama in verbose mode and tee to both terminal and log
ollama run "$MODEL" --verbose 2>&1 | while IFS= read -r line; do
    # Check if line contains performance metrics
    if echo "$line" | grep -qE "(eval rate|prompt eval rate|eval count|prompt eval count)"; then
        log_with_timestamp "📊 METRIC: $line"
    elif echo "$line" | grep -qE "(total duration|load duration|prompt eval duration|eval duration)"; then
        log_with_timestamp "⏱️  TIMING: $line"
    else
        log_with_timestamp "💬 OUTPUT: $line"
    fi
    
    # Always show in terminal
    echo "$line"
done

# Clean up
rm /tmp/ollama-pipe-$$

log_with_timestamp "=== Ollama Session Ended ==="