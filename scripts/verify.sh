#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python scripts/validate_runtime.py
if command -v docker >/dev/null 2>&1; then
  docker compose --env-file .env.local config >/dev/null
  echo "Compose configuration: PASS"
fi
