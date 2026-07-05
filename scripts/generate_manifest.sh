#!/usr/bin/env bash
# Regenerates MANIFEST.SHA256 from the git-tracked tree only.
# Run from repo root. Never hand-edit MANIFEST.SHA256.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

out="MANIFEST.SHA256"
tmp="$(mktemp)"

git ls-files -z -- . ":(exclude)$out" | sort -z | while IFS= read -r -d '' f; do
  sha256sum "$f"
done > "$tmp"

mv "$tmp" "$out"
echo "Wrote $(wc -l < "$out") entries to $out"
