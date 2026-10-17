"""Adapter must be informational and never open investment gates."""
from app.predictability import PredictabilityInput
from app.predictability_land_adapter import land_predictability_context


def synthetic_input():
    return PredictabilityInput.model_validate({
        "forecast_id": "SYNTHETIC", "site_id": "SYNTHETIC",
        "issued_at": "2026-01-01T00:00:00Z", "target_at": "2026-01-02T00:00:00Z",
        "as_of": "2026-01-01T00:00:00Z", "forecast_kind": "CHRONOLOGICAL",
        "domain": "WATER", "variable": "soil_moisture",
        "model": {"model_id": "m", "version": "v0", "model_sha256": "a"*64, "method_class": "P"},
        "evidence": [{"evidence_id": "synthetic", "data_sha256": "a"*64,
                      "observation_cutoff": "2025-12-01T00:00:00Z",
                      "source_type": "HINDCAST", "geospatial_valid": True, "licence_valid": True}],
        "evaluation": {"independent_holdout": True, "baseline_id": "synthetic",
                       "skill_metric": "MAE", "skill_value": 1.0, "threshold_policy_id": "synthetic",
                       "threshold_value": 2.0, "score_direction": "LOWER_IS_BETTER",
                       "calibration_state": "PASS", "validated_max_horizon_hours": 48,
                       "evaluated_at": "2025-12-01T00:00:00Z", "valid_until": "2026-12-01T00:00:00Z"},
        "policy_version": "v0", "data_version": "v0", "mode": "SHADOW",
        "human_review_required": True,
    })


def test_positive_caller_declared_skill_grants_no_rights():
    result = land_predictability_context(synthetic_input())
    assert result["predictability_state"] == "SHADOW_ONLY"
    assert result["land_value"] is None and result["estimated_loss"] is None
    assert result["can_admit_land_investment"] is False
    assert result["can_admit_credit_or_insurance"] is False
    assert result["can_modify_gates"] is False
    assert result["risk_bearer"] == "UNKNOWN_REQUIRES_EXPLICIT_RAVEL_ASSESSMENT"


def test_shadow_adapter_is_deterministic():
    a = land_predictability_context(synthetic_input())
    assert a == land_predictability_context(synthetic_input())
    assert a["authority"] == "NON_AUTHORITATIVE_READ_ONLY"
