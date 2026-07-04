#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
command -v docker >/dev/null 2>&1 || { echo "Docker is required" >&2; exit 1; }
docker compose --env-file .env.local up --build -d
docker compose ps
printf '
Runtime UI: http://localhost:8080
'
