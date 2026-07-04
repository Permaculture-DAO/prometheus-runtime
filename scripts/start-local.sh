#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../services/api"
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.lock
export DATABASE_URL="sqlite:////tmp/prometheus_runtime_local.db"
export DOCUMENT_ROOT="../../../01_CANON"
export EVIDENCE_STORAGE_PATH="/tmp/prometheus-evidence"
export CLAIMS_REGISTER_PATH="../../config/claims_register.json"
export GATE_STATUS_PATH="../../config/gate_status.json"
export CANONICAL_RELEASE_PATH="../../config/canonical_release.json"
export WRITE_API_KEY="local-test-key"
uvicorn app.main:app --host 127.0.0.1 --port 8000
