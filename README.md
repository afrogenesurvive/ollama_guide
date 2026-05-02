# ollama_guide

how to setup and run models with ollama locally

# Terminal 1: Start Ollama server (one-time per session)

ollama serve

# Or if using the app, just ensure it's running in menu bar

# Terminal 2: Verify your model is available

ollama list

# Should show: my-gemma4-32k (or whatever you named it)

---

# Add this to your ~/.zshrc to start Ollama automatically when you open a terminal:

# Auto-start Ollama if not running

if ! pgrep -x "ollama" > /dev/null; then
open -a Ollama

# If using the app # Or: ollama serve > /dev/null 2>&1 &

fi

---

# Step 1: Create your 32K model (one-time only)

./create-32k-model.sh gemma4:e2b my-gemma4-32k

# make executable chmod +x create-32k-model.sh

# This creates a permanent model called my-gemma4-32k that always uses 32K context.

# Or other models

# ./create-32k-model.sh llama3.2:3b

# ./create-32k-model.sh qwen2.5-coder:7b

# Step 2: Run the logging script whenever you want to use it

./ollama-with-logging.sh my-gemma4-32k my-session.log

# make excutable chmod +x ollama-with-logging.sh

# Combined execute

./ollama-32k-logged.sh gemma4:e2b

# make excutable chmod +x ollama-32k-logged.sh

# check running models

ollama ps
