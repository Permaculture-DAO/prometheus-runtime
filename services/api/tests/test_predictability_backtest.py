"""Synthetic fixtures only; not empirical validation."""
from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from app.predictability_backtest import BacktestInput, backtest_shadow


def fixture():
    cases = []
    for month in (4, 5, 6):
        for day in range(1, 11):
            valid = datetime(2026, month, day, 12, tzinfo=timezone.utc)
            issue = valid - timedelta(days=2)
            cases.append({
                "case_id": f"case-{month}-{day}", "site_id": "SYNTHETIC",
                "issue_time": issue.isoformat(), "valid_time": valid.isoformat(),
                "baseline_issue_time": (issue - timedelta(hours=1)).isoformat(),
                "observation_available_time": (valid + timedelta(hours=2)).isoformat(),
                "forecast": 19.0, "baseline": 16.0, "observed": 20.0, "lead_hours": 48,
            })
    return {
        "dataset_id": "SYNTHETIC-UNVERIFIED", "dataset_sha256": "a" * 64,
        "site_id": "SYNTHETIC", "model_id": "MODEL-SYN", "model_version": "v0",
        "variable": "temperature_2m", "unit": "C", "frozen_as_of": "2026-08-01T00:00:00Z",
        "training_data_cutoff": "2026-03-01T00:00:00Z",
        "evaluated_holdout": "CALLER_DECLARED", "license_declared": "PERMITTED",
        "reference_source": "SYNTHETIC-NOT-REAL", "cases": cases,
    }


def run(data):
    return backtest_shadow(BacktestInput.model_validate(data))


def test_positive_is_only_candidate():
    a = run(fixture())
    assert a == run(fixture())
    result = a["lead_results"][0]
    assert result["cases"] == 30 and result["distinct_months"] == 3
    assert result["model_mae"] == 1 and result["baseline_mae"] == 4
    assert result["status"] == "POSITIVE_SAMPLE_SKILL_UNVERIFIED"
    assert a["independent_holdout_verified"] is False and a["financial_authority"] is False


def test_insufficient_coverage_abstains():
    f = fixture()
    f["cases"] = f["cases"][:9]
    assert run(f)["lead_results"][0]["status"] == "INSUFFICIENT_HOLDOUT_COVERAGE"


def test_worse_model_rejected_by_comparison():
    f = fixture()
    for c in f["cases"]:
        c["forecast"] = 13.0
    assert run(f)["lead_results"][0]["status"] == "NOT_BETTER_THAN_BASELINE"


def test_rights_are_gate():
    f = fixture()
    f["license_declared"] = "RESTRICTED"
    assert run(f)["lead_results"][0]["status"] == "HOLD_DATA_RIGHTS"


def test_future_observations_not_allowed():
    f = fixture()
    f["cases"][0]["observation_available_time"] = "2026-10-01T00:00:00Z"
    with pytest.raises(ValidationError, match="verification after frozen as-of"):
        BacktestInput.model_validate(f)


def test_lead_lying_not_allowed():
    f = fixture()
    f["cases"][0]["lead_hours"] = 72
    with pytest.raises(ValidationError, match="lead does not match"):
        BacktestInput.model_validate(f)


def test_leaky_baseline_not_allowed():
    f = fixture()
    f["cases"][0]["baseline_issue_time"] = "2026-10-01T00:00:00Z"
    with pytest.raises(ValidationError, match="baseline look-ahead"):
        BacktestInput.model_validate(f)


def test_training_cutoff_not_future():
    f = fixture()
    f["training_data_cutoff"] = "2026-12-01T00:00:00Z"
    with pytest.raises(ValidationError, match="training data cutoff"):
        BacktestInput.model_validate(f)


def test_duplicate_case_and_cross_site_rejected():
    f = fixture()
    f["cases"][1]["case_id"] = f["cases"][0]["case_id"]
    with pytest.raises(ValidationError, match="duplicate case_id"):
        BacktestInput.model_validate(f)
    f = fixture()
    f["cases"][0]["site_id"] = "OTHER"
    with pytest.raises(ValidationError, match="site mismatch"):
        BacktestInput.model_validate(f)


def test_unknown_fields_disallowed():
    f = fixture()
    f["authoritative"] = True
    with pytest.raises(ValidationError):
        BacktestInput.model_validate(f)


def test_timezone_required():
    f = fixture()
    f["cases"][0]["valid_time"] = "2026-04-01T12:00:00"
    with pytest.raises(ValidationError, match="timezone"):
        BacktestInput.model_validate(f)
