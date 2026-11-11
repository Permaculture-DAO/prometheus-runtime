"""Synthetic-only local ingestion controls; no external data."""
import hashlib
import json

import pytest
from scripts.run_predictability_backtest import run
from test_predictability_backtest import fixture


FIELDS = ("dataset_id", "site_id", "model_id", "model_version",
          "variable", "unit", "reference_source", "cases")


def request_and_source(tmp_path):
    request = fixture()
    raw = {key: request[key] for key in FIELDS}
    source = tmp_path / "synthetic-source.json"
    source.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
    request["dataset_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    return request, path, source


def test_exact_source_verified_and_never_certified(tmp_path):
    _, request_path, source_path = request_and_source(tmp_path)
    result = run(request_path, source_path)
    assert result["local_source_blob_sha256_verified"]
    assert not result["licence_authenticity_verified"]
    assert not result["source_authenticity_verified"]
    assert result["lead_results"][0]["status"] == "POSITIVE_SAMPLE_SKILL_UNVERIFIED"


def test_tampered_source_is_rejected(tmp_path):
    _, request_path, source_path = request_and_source(tmp_path)
    source_path.write_text('{"cases":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        run(request_path, source_path)


def test_unrelated_scored_cases_are_rejected_even_if_sha_valid(tmp_path):
    req, request_path, source_path = request_and_source(tmp_path)
    req["cases"][0]["forecast"] += 999.0
    request_path.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(ValueError, match="source data mismatch"):
        run(request_path, source_path)


def test_unrelated_source_blob_is_rejected_even_if_sha_declared(tmp_path):
    req, request_path, source_path = request_and_source(tmp_path)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["cases"][0]["observed"] = 99.0
    source_path.write_text(json.dumps(source), encoding="utf-8")
    req["dataset_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    request_path.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(ValueError, match="source data mismatch"):
        run(request_path, source_path)


def test_rights_not_permitted_are_blocked(tmp_path):
    req, path, source = request_and_source(tmp_path)
    req["license_declared"] = "UNKNOWN"
    path.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(ValueError, match="rights"):
        run(path, source)


def test_source_schema_extras_fail_closed(tmp_path):
    req, path, source = request_and_source(tmp_path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    raw["undisclosed_field"] = 1
    source.write_text(json.dumps(raw), encoding="utf-8")
    req["dataset_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    path.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(ValueError, match="source dataset schema mismatch"):
        run(path, source)
