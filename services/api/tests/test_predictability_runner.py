"""Local hash and data-rights checks with synthetic-only fixture."""
import hashlib
import json

import pytest
from scripts.run_predictability_backtest import run
from test_predictability_backtest import fixture


def test_source_bytes_match_and_are_reported(tmp_path):
    source = tmp_path / "synthetic-source.bin"
    source.write_bytes(b"SYNTHETIC ONLY - NO EXTERNAL DATA")
    request = fixture()
    request["dataset_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    result = run(path, source)
    assert result["local_source_blob_sha256_verified"]
    assert not result["licence_authenticity_verified"]
    assert not result["source_authenticity_verified"]
    assert result["lead_results"][0]["status"] == "POSITIVE_SAMPLE_SKILL_UNVERIFIED"


def test_mismatched_hash_is_blocked(tmp_path):
    source = tmp_path / "synthetic-source.bin"
    source.write_bytes(b"tampered")
    path = tmp_path / "request.json"
    path.write_text(json.dumps(fixture()), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        run(path, source)


def test_rights_not_permitted_are_blocked(tmp_path):
    source = tmp_path / "synthetic-source.bin"
    source.write_bytes(b"authorized? no")
    request = fixture()
    request["dataset_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    request["license_declared"] = "UNKNOWN"
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    with pytest.raises(ValueError, match="rights"):
        run(path, source)
