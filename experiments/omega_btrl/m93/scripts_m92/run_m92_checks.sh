#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="$PWD:$PWD/m93"
python -m pytest m93/tests_m92 m93/tests -q -o addopts=''
python -m pytest tests -q -o addopts=''
python m93/scripts_m92/loopback_mtls_multiworker.py
