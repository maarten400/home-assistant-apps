#!/usr/bin/with-contenv bash
set -e

export NOD_DATA_DIR="/share/nod"
mkdir -p "$NOD_DATA_DIR"

MODEL_PROVIDER="${MODEL_PROVIDER:-ollama}"
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
OLLAMA_AUTO_DISCOVER="${OLLAMA_AUTO_DISCOVER:-true}"
FALLBACK_MODEL="${FALLBACK_MODEL:-}"
MODEL_BASE_URL="${MODEL_BASE_URL:-}"
MODEL_NAME="${MODEL_NAME:-}"
MODEL_API_KEY="${MODEL_API_KEY:-}"
DRY_RUN="${DRY_RUN:-false}"

discover_ollama_model() {
  local models
  models="$(curl -fsS --max-time 10 "${OLLAMA_URL%/}/api/tags" 2>/dev/null || true)"

  if [ -z "$models" ]; then
    echo "WARNING: Could not reach Ollama at $OLLAMA_URL/api/tags"
    return 1
  fi

  printf '%s' "$models" | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | head -n 1 \
    | cut -d'"' -f4
}

if [ "$MODEL_PROVIDER" = "ollama" ]; then
  if [ -z "$MODEL_NAME" ]; then
    if [ "$OLLAMA_AUTO_DISCOVER" = "true" ]; then
      if MODEL_NAME="$(discover_ollama_model)"; then
        echo "Discovered Ollama model: $MODEL_NAME"
      elif [ -n "$FALLBACK_MODEL" ]; then
        MODEL_NAME="$FALLBACK_MODEL"
        echo "WARNING: Ollama model discovery failed; using fallback model: $MODEL_NAME"
      else
        echo "ERROR: Ollama model discovery failed and no fallback_model is configured."
        exit 1
      fi
    elif [ -n "$FALLBACK_MODEL" ]; then
      MODEL_NAME="$FALLBACK_MODEL"
      echo "Ollama auto-discovery is disabled; using fallback model: $MODEL_NAME"
    else
      echo "ERROR: Ollama auto-discovery is disabled and neither model_name nor fallback_model is configured."
      exit 1
    fi
  fi

  MODEL_BASE_URL="${OLLAMA_URL%/}/v1"
  MODEL_API_KEY="${MODEL_API_KEY:-ollama}"
  MODEL_PROVIDER="openai-compatible"
fi

export LLM_PROVIDER="$MODEL_PROVIDER"
export LLM_MODEL="$MODEL_NAME"
export OPENAI_COMPATIBLE_BASE_URL="$MODEL_BASE_URL"
export OPENAI_COMPATIBLE_API_KEY="$MODEL_API_KEY"

if [ "$DRY_RUN" = "true" ]; then
  echo "=== Nod add-on dry run ==="
  echo "Model provider: $MODEL_PROVIDER"
  echo "Model: $MODEL_NAME"
  echo "Base URL: $MODEL_BASE_URL"
  echo "Ollama auto-discovery: $OLLAMA_AUTO_DISCOVER"
  echo "API key configured: $([ -n "$MODEL_API_KEY" ] && echo yes || echo no)"

  if [ "$MODEL_PROVIDER" = "openai-compatible" ] && [ -n "$MODEL_BASE_URL" ]; then
    if curl -fsS --max-time 10 "${MODEL_BASE_URL%/}/models" >/dev/null 2>&1; then
      echo "Connection test: OK"
    else
      echo "Connection test: FAILED"
      exit 1
    fi
  fi

  echo "Dry run complete. Nod was not started."
  exit 0
fi

# Optional custom environment variables, one KEY=VALUE per line
if [ -n "${EXTRA_ENV:-}" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    export "$line"
  done <<< "$EXTRA_ENV"
fi

cd /opt/nod
exec pnpm start
