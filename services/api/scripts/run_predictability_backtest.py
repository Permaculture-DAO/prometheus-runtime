"""Offline reproducibility wrapper for PRM-PRED-001 shadow backtests.

No data download and no elevated source authority. Validates local source *bytes*,
not the authenticity of the data or the copyright/licence declaration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from app.predictability_backtest import BacktestInput, backtest_shadow


def run(request_path: Path, source_path: Path) -> dict:
    request_obj = json.loads(request_path.read_text(encoding="utf-8"))
    request = BacktestInput.model_validate(request_obj)
    raw_source = source_path.read_bytes()
    actual_sha = hashlib.sha256(raw_source).hexdigest()
    if actual_sha != request.dataset_sha256:
        raise ValueError("source blob SHA-256 mismatch; fail closed")
    # A digest of an unrelated file is not evidence of the scored cases.
    # Bind every scored field to the exact local source blob before evaluation.
    try:
        source_document = json.loads(raw_source.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("source blob must contain a UTF-8 JSON dataset") from exc
    expected_fields = ("dataset_id", "site_id", "model_id", "model_version",
                       "variable", "unit", "reference_source", "cases")
    if not isinstance(source_document, dict) or set(source_document) != set(expected_fields):
        raise ValueError("source dataset schema mismatch")
    for field in expected_fields:
        if source_document[field] != request_obj[field]:
            raise ValueError("source data mismatch: scored cases are not bound to source blob")
    if request.license_declared != "PERMITTED":
        raise ValueError("source data usage rights not affirmatively declared; fail closed")
    result = backtest_shadow(request)
    result["local_source_blob_sha256_verified"] = True
    result["licence_authenticity_verified"] = False
    result["source_authenticity_verified"] = False
    result["source_filename"] = source_path.name
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--source-blob", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output already exists: refusing to overwrite prior evidence")
    result = run(args.request, args.source_blob)
    # Exclusive creation preserves previous review artifacts without silent overwrite.
    with args.out.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
