"""PRM-PRED-001: offline shadow validation on caller-supplied, time-frozen samples.

This helper does not verify source authenticity, infer independent holdout status,
change existing gates, or certify forecast performance. Never use it for automated
capital, land, credit, or insurance decisions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
import json
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return result


Time = Annotated[datetime, BeforeValidator(_timestamp)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class ForecastCase(Strict):
    case_id: str = Field(min_length=1, max_length=128)
    site_id: str = Field(min_length=1, max_length=128)
    issue_time: Time
    valid_time: Time
    observation_available_time: Time
    # Baseline prediction must have been generated no later than the model forecast.
    baseline_issue_time: Time
    forecast: float
    baseline: float
    observed: float
    lead_hours: int = Field(gt=0, le=24 * 60)


class BacktestInput(Strict):
    dataset_id: str = Field(min_length=1, max_length=128)
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    site_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    variable: str = Field(min_length=1, max_length=128)
    unit: str = Field(min_length=1, max_length=40)
    frozen_as_of: Time
    training_data_cutoff: Time
    evaluated_holdout: Literal["CALLER_DECLARED"]
    license_declared: Literal["PERMITTED", "UNKNOWN", "RESTRICTED"]
    reference_source: str = Field(min_length=1, max_length=256)
    cases: list[ForecastCase] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def check_input(self):
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate case_id")
        if any(case.site_id != self.site_id for case in self.cases):
            raise ValueError("site mismatch")
        for case in self.cases:
            if case.issue_time >= case.valid_time:
                raise ValueError("issue must precede target")
            if case.baseline_issue_time > case.issue_time:
                raise ValueError("baseline look-ahead")
            if case.observation_available_time < case.valid_time:
                raise ValueError("observation precedes valid time")
            if case.observation_available_time > self.frozen_as_of:
                raise ValueError("verification after frozen as-of")
            if self.training_data_cutoff >= case.issue_time:
                raise ValueError("training data cutoff must precede forecast issue")
            actual_lead = (case.valid_time - case.issue_time).total_seconds() / 3600
            if abs(actual_lead - case.lead_hours) > 1e-9:
                raise ValueError("lead does not match issue and target")
        return self


def backtest_shadow(request: BacktestInput) -> dict:
    """Compute replayable MAE improvement by lead, with conservative data sufficiency.

    Passing metrics are *descriptive*, NOT admissible evidence, verified models or a
    valid maximum forecast horizon. Source authenticity and spatial quality remain unverified.
    """
    frozen = request.model_dump(mode="json")
    input_hash = sha256(json.dumps(frozen, sort_keys=True, separators=(",", ":"),
                                   allow_nan=False).encode("utf-8")).hexdigest()
    grouped: dict[int, list[ForecastCase]] = {}
    for case in request.cases:
        grouped.setdefault(case.lead_hours, []).append(case)
    results = []
    for lead, samples in sorted(grouped.items()):
        count = len(samples)
        n_months = len({(c.valid_time.year, c.valid_time.month) for c in samples})
        model_mae = sum(abs(c.forecast - c.observed) for c in samples) / count
        baseline_mae = sum(abs(c.baseline - c.observed) for c in samples) / count
        gain = baseline_mae - model_mae
        if request.license_declared != "PERMITTED":
            status = "HOLD_DATA_RIGHTS"
        elif count < 30 or n_months < 3:
            status = "INSUFFICIENT_HOLDOUT_COVERAGE"
        elif baseline_mae <= 0:
            status = "BASELINE_NONINFORMATIVE"
        elif gain <= 0:
            status = "NOT_BETTER_THAN_BASELINE"
        else:
            # This is NOT an independent confidence interval or a policy authorization.
            status = "POSITIVE_SAMPLE_SKILL_UNVERIFIED"
        assert all(isfinite(x) for x in (model_mae, baseline_mae, gain))
        results.append({"lead_hours": lead, "cases": count, "distinct_months": n_months,
                        "model_mae": round(model_mae, 9),
                        "baseline_mae": round(baseline_mae, 9),
                        "absolute_mae_improvement": round(gain, 9),
                        "status": status})
    return {"method_id": "PRM-PRED-BACKTEST-001@0.1-CANDIDATE",
            "dataset_id": request.dataset_id, "input_sha256": input_hash,
            "data_source_verified": False, "evidence_authenticated": False,
            "independent_holdout_verified": False, "financial_authority": False,
            "scientific_certification": False, "human_review_required": True,
            "mode": "SHADOW_ONLY", "metric": "MAE", "unit": request.unit,
            "as_of_utc": request.frozen_as_of.astimezone(timezone.utc).isoformat(),
            "lead_results": results}
