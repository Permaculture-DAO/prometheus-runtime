"""Synthetic regression tests; no empirical forecast-skill claim."""
from copy import deepcopy
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.predictability import PredictabilityInput, evaluate_predictability
from app.predictability_routes import build_predictability_router
from app.settings import Settings


def sample():
    h = "a" * 64
    return {
        "forecast_id": "SYN-001", "site_id": "SYNTHETIC-ONLY",
        "issued_at": "2026-09-01T00:00:00Z",
        "target_at": "2026-09-03T00:00:00Z",
        "as_of": "2026-09-01T03:00:00Z",
        "forecast_kind": "CHRONOLOGICAL", "domain": "ATMOSPHERE",
        "variable": "precipitation",
        "model": {"model_id": "synthetic", "version": "0", "model_sha256": h, "method_class": "P"},
        "evidence": [{"evidence_id": "syn-hindcast", "data_sha256": h,
                      "observation_cutoff": "2026-08-01T00:00:00Z",
                      "source_type": "HINDCAST",
                      "geospatial_valid": True, "licence_valid": True}],
        "evaluation": {
            "independent_holdout": True,
            "baseline_id": "syn-persistence",
            "skill_metric": "syn-skill",
            "skill_value": 0.2,
            "threshold_policy_id": "syn-caller-declared-not-authoritative",
            "threshold_value": 0.1,
            "score_direction": "HIGHER_IS_BETTER",
            "calibration_state": "PASS",
            "validated_max_horizon_hours": 72.0,
            "evaluated_at": "2026-08-20T00:00:00Z",
            "valid_until": "2026-09-30T00:00:00Z",
        },
        "policy_version": "synthetic-v0", "data_version": "synthetic-v0",
        "mode": "SHADOW", "human_review_required": True,
    }


def evaluate(data):
    return evaluate_predictability(PredictabilityInput.model_validate(data))


def test_replay_deterministic_and_never_authoritative():
    a, b = evaluate(sample()), evaluate(sample())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["status"] == "SHADOW_ONLY"
    assert a["human_review_required"] is True
    assert a["investment_authorised"] is False
    assert a["independent_skill_verified_by_runtime"] is False


def test_independent_holdout_missing():
    x=sample(); x["evaluation"]["independent_holdout"] = False
    assert evaluate(x)["status"] == "UNKNOWN"


def test_future_observation_blocked():
    x=sample(); x["evidence"][0]["observation_cutoff"] = "2026-09-02T00:00:00Z"
    assert evaluate(x)["status"] == "REJECTED"


def test_future_model_evaluation_blocked():
    x=sample(); x["evaluation"]["evaluated_at"] = "2026-09-04T00:00:00Z"
    assert evaluate(x)["status"] == "REJECTED"


def test_horizon_outside_holdout():
    x=sample(); x["target_at"] = "2026-12-31T00:00:00Z"
    assert evaluate(x)["status"] == "OUT_OF_DOMAIN"


def test_bad_geography():
    x=sample(); x["evidence"][0]["geospatial_valid"] = False
    assert evaluate(x)["status"] == "OUT_OF_DOMAIN"


def test_unlicensed_data():
    x=sample(); x["evidence"][0]["licence_valid"] = False
    assert evaluate(x)["status"] == "UNKNOWN"


def test_score_direction_is_respected():
    x=sample(); x["evaluation"].update(
        skill_value=3.0, threshold_value=2.0, score_direction="LOWER_IS_BETTER")
    assert evaluate(x)["status"] == "INSUFFICIENT_SKILL"
    x["evaluation"]["skill_value"] = 1.0
    assert evaluate(x)["status"] == "SHADOW_ONLY"


def test_stale_assessment():
    x=sample(); x["as_of"] = "2026-10-01T00:00:00Z"
    assert evaluate(x)["status"] == "STALE"


def test_unmeasured_skill_and_paper_only():
    x=sample(); x["evaluation"]["skill_value"] = None
    assert evaluate(x)["status"] == "UNKNOWN"
    x=sample(); x["evidence"][0]["source_type"] = "PAPER"
    assert evaluate(x)["status"] == "UNKNOWN"


@pytest.mark.parametrize("key,value", [
    ("mode", "PRODUCTION"), ("human_review_required", False),
    ("guaranteed_horizon_days", 129),
])
def test_authority_or_unrecognized_input_is_rejected(key,value):
    x=sample(); x[key] = value
    with pytest.raises(ValidationError):
        PredictabilityInput.model_validate(x)


def test_duplicate_and_naive_dates_rejected():
    x=sample(); x["evidence"].append(deepcopy(x["evidence"][0]))
    with pytest.raises(ValidationError):
        PredictabilityInput.model_validate(x)
    x=sample(); x["issued_at"] = "2026-09-01T00:00:00"
    with pytest.raises(ValidationError):
        PredictabilityInput.model_validate(x)


def test_feature_flag_disabled_even_with_key():
    s=Settings(write_api_key="test-key", predictability_shadow_enabled=False)
    app=FastAPI(); app.include_router(build_predictability_router(s))
    with TestClient(app) as c:
        r=c.post("/shadow/predictability/evaluate",json=sample(),headers={"X-API-Key":"test-key"})
        assert r.status_code == 423


def test_enabled_route_requires_key():
    s=Settings(write_api_key="test-key", predictability_shadow_enabled=True)
    app=FastAPI(); app.include_router(build_predictability_router(s))
    with TestClient(app) as c:
        assert c.post("/shadow/predictability/evaluate",json=sample()).status_code == 401
        r=c.post("/shadow/predictability/evaluate",json=sample(),headers={"X-API-Key":"test-key"})
        assert r.status_code == 200 and r.json()["status"] == "SHADOW_ONLY"
