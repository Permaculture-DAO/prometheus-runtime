#!/bin/sh
set -eu
REF="${HOLOCHAIN_HOLONIX_REF:-main-0.6}"
REQ="${HOLOCHAIN_REQUIRED_VERSION:-0.6.1}"
exec nix --extra-experimental-features 'nix-command flakes' develop "github:holochain/holonix?ref=${REF}" --command sh -lc '
  set -eu
  ACTUAL=$(holochain --version 2>&1 || true)
  echo "Detected: $ACTUAL"
  echo "$ACTUAL" | grep -F "'"${REQ}"'" >/dev/null || { echo "Required Holochain version '"${REQ}"' not detected" >&2; exit 64; }
  exec holochain --config-path /runtime/conductor-config.yaml
'
