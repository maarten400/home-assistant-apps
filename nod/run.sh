#!/usr/bin/with-contenv bash
set -e

export NOD_DATA_DIR="/share/nod"
mkdir -p "$NOD_DATA_DIR"

MODEL_PROVIDER="${MODEL_PROVIDER:-ollama}"
OLLAMA_URL="${OLLAMA_URL:-http://192.168.1.10:11434}"
OLLAMA_AUTO_DISCOVER="${OLLAMA_AUTO_DISCOVER:-true}"
OLLAMA_MODEL="${OLLAMA_MODEL:-}"
FALLBACK_MODEL="${FALLBACK_MODEL:-}"

CLAUDE_SUBSCRIPTION_ENABLED="${CLAUDE_SUBSCRIPTION_ENABLED:-true}"
CLAUDE_SUBSCRIPTION_TOKEN="${CLAUDE_SUBSCRIPTION_TOKEN:-}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-5}"
CLAUDE_PROXY_PORT="${CLAUDE_PROXY_PORT:-3457}"
CLAUDE_PROXY_COMMAND="${CLAUDE_PROXY_COMMAND:-}"

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

  printf '%s' "$models" \
    | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | cut -d'"' -f4 \
    | head -n 1
}

start_claude_subscription_proxy() {
  if [ "$CLAUDE_SUBSCRIPTION_ENABLED" != "true" ]; then
    echo "ERROR: Claude subscription proxy is disabled."
    return 1
  fi

  if [ -z "$CLAUDE_SUBSCRIPTION_TOKEN" ]; then
    echo "ERROR: claude_subscription_token is required for model_provider=claude-subscription."
    return 1
  fi

  if [ -z "$CLAUDE_PROXY_COMMAND" ]; then
    echo "ERROR: claude_proxy_command is required. Example: node /opt/ocp/ocp --host 127.0.0.1 --port 3457"
    return 1
  fi

  export CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_SUBSCRIPTION_TOKEN"

  echo "Starting local Claude subscription proxy on 127.0.0.1:${CLAUDE_PROXY_PORT}"
  bash -c "$CLAUDE_PROXY_COMMAND" &
  CLAUDE_PROXY_PID=$!

  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${CLAUDE_PROXY_PORT}/health" >/dev/null 2>&1; then
      echo "Claude subscription proxy is ready."
      return 0
    fi

    if ! kill -0 "$CLAUDE_PROXY_PID" 2>/dev/null; then
      echo "ERROR: Claude subscription proxy exited during startup."
      return 1
    fi

    sleep 1
  done

  echo "ERROR: Claude subscription proxy did not become ready within 30 seconds."
  kill "$CLAUDE_PROXY_PID" 2>/dev/null || true
  return 1
}

case "$MODEL_PROVIDER" in
  ollama)
    if [ -z "$OLLAMA_MODEL" ]; then
      if [ "$OLLAMA_AUTO_DISCOVER" = "true" ]; then
        if OLLAMA_MODEL="$(discover_ollama_model)"; then
          echo "Discovered Ollama model: $OLLAMA_MODEL"
        elif [ -n "$FALLBACK_MODEL" ]; then
          OLLAMA_MODEL="$FALLBACK_MODEL"
          echo "WARNING: Ollama model discovery failed; using fallback model: $OLLAMA_MODEL"
        else
          echo "ERROR: Ollama model discovery failed and no fallback_model is configured."
          exit 1
        fi
      elif [ -n "$FALLBACK_MODEL" ]; then
        OLLAMA_MODEL="$FALLBACK_MODEL"
        echo "Ollama auto-discovery is disabled; using fallback model: $OLLAMA_MODEL"
      else
        echo "ERROR: Ollama auto-discovery is disabled and neither ollama_model nor fallback_model is configured."
        exit 1
      fi
    fi

    export LLM_PROVIDER="openai-compatible"
    export LLM_MODEL="$OLLAMA_MODEL"
    export OPENAI_COMPATIBLE_BASE_URL="${OLLAMA_URL%/}/v1"
    export OPENAI_COMPATIBLE_API_KEY="${MODEL_API_KEY:-ollama}"
    ;;

  claude-subscription)
    if ! start_claude_subscription_proxy; then
      exit 1
    fi

    export LLM_PROVIDER="openai-compatible"
    export LLM_MODEL="$CLAUDE_MODEL"
    export OPENAI_COMPATIBLE_BASE_URL="http://127.0.0.1:${CLAUDE_PROXY_PORT}/v1"
    export OPENAI_COMPATIBLE_API_KEY="local-claude-subscription"
    ;;

  openai-compatible)
    if [ -z "$MODEL_BASE_URL" ] || [ -z "$MODEL_NAME" ]; then
      echo "ERROR: model_base_url and model_name are required for model_provider=openai-compatible."
      exit 1
    fi

    export LLM_PROVIDER="openai-compatible"
    export LLM_MODEL="$MODEL_NAME"
    export OPENAI_COMPATIBLE_BASE_URL="$MODEL_BASE_URL"
    export OPENAI_COMPATIBLE_API_KEY="${MODEL_API_KEY:-}"
    ;;

  *)
    echo "ERROR: Unsupported model_provider: $MODEL_PROVIDER"
    exit 1
    ;;
esac

if [ "$DRY_RUN" = "true" ]; then
  echo "=== Nod add-on dry run ==="
  echo "Model provider: $MODEL_PROVIDER"
  echo "Model: ${LLM_MODEL:-not set}"
  echo "Base URL: ${OPENAI_COMPATIBLE_BASE_URL:-not set}"
  echo "Ollama auto-discovery: $OLLAMA_AUTO_DISCOVER"
  echo "Claude subscription proxy enabled: $CLAUDE_SUBSCRIPTION_ENABLED"
  echo "Claude subscription token configured: $([ -n "$CLAUDE_SUBSCRIPTION_TOKEN" ] && echo yes || echo no)"
  echo "Dry run complete. Nod was not started."
  exit 0
fi

if [ -n "${EXTRA_ENV:-}" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    export "$line"
  done <<< "$EXTRA_ENV"
fi

cd /opt/nod
exec pnpm start
