# ollama_guide

Local Ollama setup for creating a 32K-context model and using it from desktop tools.

## Scope

This repo no longer includes request logging or CLI prompt workflows.
Use your model from:

- Ollama desktop app
- Copilot/client integrations that connect to your local Ollama instance

## 1) Ensure Ollama is running

If you use the desktop app, just make sure it is open.

## 2) Create a 32K model (one-time)

```bash
chmod +x ./create-32k-model.sh
./create-32k-model.sh gemma4:e2b my-gemma4-32k
```

You can also build from other base models:

```bash
./create-32k-model.sh llama3.2:3b
./create-32k-model.sh qwen2.5-coder:7b
```

## 3) Use it from your desktop app or Copilot

Select the created model (for example, `my-gemma4-32k`) in your app/integration settings.

## Optional: auto-open Ollama app in shell sessions

Add this to your `~/.zshrc` if desired:

```bash
if ! pgrep -x "ollama" > /dev/null; then
	open -a Ollama
fi
```
