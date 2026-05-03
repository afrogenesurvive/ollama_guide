#!/bin/bash

# Usage: ./create-32k-model.sh <base-model-name> [custom-name]
# Example: ./create-32k-model.sh gemma4:e2b my-gemma4-32k

BASE_MODEL="$1"
CUSTOM_NAME="${2:-${BASE_MODEL}-32k}"

if [ -z "$BASE_MODEL" ]; then
    echo "Usage: $0 <base-model-name> [custom-name]"
    echo "Example: $0 gemma4:e2b my-gemma4-32k"
    exit 1
fi

# Create a temporary Modelfile

# PARAMETER num_predict 1024 
cat > /tmp/Modelfile-${CUSTOM_NAME} << EOF
FROM ${BASE_MODEL}
PARAMETER num_ctx 32768
PARAMETER num_predict 2048
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_keep 32

# System prompt for coding agent
SYSTEM """
You are a coding assistant. Help users write, debug, and refactor code.
Core rules:
- Do NOT output any <thinking> tags or internal monologue.
- Do NOT use chain-of-thought reasoning in your response.
- Give the answer immediately.
- Never explain how you arrived at the answer step-by-step.
"""
EOF

# SYSTEM You are an expert coding assistant. Help users write, debug, and refactor code. Always explain your reasoning before making changes.


# Create the model
echo "Creating model ${CUSTOM_NAME} from ${BASE_MODEL} with 32K context..."
ollama create ${CUSTOM_NAME} -f /tmp/Modelfile-${CUSTOM_NAME}

# Clean up
rm /tmp/Modelfile-${CUSTOM_NAME}

echo "✅ Model ${CUSTOM_NAME} created successfully"
echo "Use this model from your desktop app or Copilot configuration."