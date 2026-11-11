#!/usr/bin/with-contenv bash
set -e

export NOD_DATA_DIR="/share/nod"
mkdir -p "$NOD_DATA_DIR"

if [ -n "${MODEL_API_KEY:-}" ]; then
  export MODEL_API_KEY
fi

cd /opt/nod
exec pnpm start
