"""PRM-PRED-001@0.1: deterministic, non-authoritative predictability SHADOW boundary.

Candidate only: not a forecast model, independent data verifier, rating, certification,
or financial/land decision. Caller declarations are not independently authenticated.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _json_iso_datetime(value):
    if not isinstance(value, str):
        raise ValueError("ISO-8601 datetime string with timezone required")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


JsonDatetime = Annotated[datetime, BeforeValidator(_json_iso_datetime)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class ModelRef(StrictInput):
    model_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=128)
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    method_class: Literal["D", "P", "H", "Q"]


class EvidenceRef(StrictInput):
    evidence_id: str = Field(min_length=1, max_length=128)
    data_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_cutoff: JsonDatetime
    source_type: Literal["OBSERVATION", "HINDCAST", "SCENARIO", "PAPER"]
    geospatial_valid: bool
    licence_valid: bool


class EvaluationRef(StrictInput):
    independent_holdout: bool
    baseline_id: str | None
    skill_metric: str | None
    skill_value: float | None
    threshold_policy_id: str | None
    threshold_value: float | None
    score_direction: Literal["HIGHER_IS_BETTER", "LOWER_IS_BETTER"]
    calibration_state: Literal["PASS", "FAIL", "UNKNOWN", "NOT_ASSESSED"]
    validated_max_horizon_hours: float | None = Field(ge=0)
    evaluated_at: JsonDatetime
    valid_until: JsonDatetime


class PredictabilityInput(StrictInput):
    forecast_id: str = Field(min_length=1, max_length=128)
    site_id: str = Field(min_length=1, max_length=128)
    issued_at: JsonDatetime
    target_at: JsonDatetime
    as_of: JsonDatetime  # explicit replay clock: never use datetime.now()
    forecast_kind: Literal["CHRONOLOGICAL", "CONDITIONAL_STATISTICAL", "LONG_HORIZON_SCENARIO"]
    domain: Literal["ATMOSPHERE", "WATER", "SOIL", "AGROFORESTRY", "ECOLOGY", "LAND_VALUE", "FINANCE"]
    variable: str = Field(min_length=1, max_length=128)
    model: ModelRef
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=250)
    evaluation: EvaluationRef
    policy_version: str = Field(min_length=1, max_length=128)
    data_version: str = Field(min_length=1, max_length=128)
    mode: Literal["SHADOW"]
    human_review_required: Literal[True]

    @model_validator(mode="after")
    def require_timezone_and_unique_evidence(self):
        dates = [self.issued_at, self.target_at, self.as_of,
                 self.evaluation.evaluated_at, self.evaluation.valid_until]
        dates += [e.observation_cutoff for e in self.evidence]
        if any(x.tzinfo is None or x.utcoffset() is None for x in dates):
            raise ValueError("all dates require explicit timezone offsets")
        if len({e.evidence_id for e in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate evidence IDs are not allowed")
        return self


def evaluate_predictability(payload: PredictabilityInput) -> dict:
    """Pure deterministic evaluator: no I/O, clock, persistence, or gate mutations."""
    canonical = payload.model_dump(mode="json")
    digest = sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    issue, target, as_of = payload.issued_at, payload.target_at, payload.as_of
    ev = payload.evaluation
    lead = (target - issue).total_seconds() / 3600
    reasons: set[str] = set()

    if lead <= 0 or as_of < issue:
        reasons.add("INVALID_TIME_ORDER")
    if ev.evaluated_at > issue or ev.valid_until < ev.evaluated_at:
        reasons.add("FUTURE_EVALUATION_OR_INVALID_VALIDITY")
    if any(rec.observation_cutoff > issue for rec in payload.evidence):
        reasons.add("FUTURE_INFORMATION_LEAKAGE")
    if all(rec.source_type not in ("OBSERVATION", "HINDCAST") for rec in payload.evidence):
        reasons.add("NO_EMPIRICAL_EVIDENCE")

    if reasons.intersection({"INVALID_TIME_ORDER", "FUTURE_INFORMATION_LEAKAGE",
                              "FUTURE_EVALUATION_OR_INVALID_VALIDITY"}):
        state = "REJECTED"
    elif any(not rec.geospatial_valid for rec in payload.evidence):
        state = "OUT_OF_DOMAIN"
        reasons.add("INVALID_GEOSPATIAL_SCOPE")
    elif any(not rec.licence_valid for rec in payload.evidence):
        state = "UNKNOWN"
        reasons.add("DATA_RIGHTS_UNVERIFIED")
    elif as_of > ev.valid_until:
        state = "STALE"
        reasons.add("EVALUATION_EXPIRED")
    elif ev.validated_max_horizon_hours is not None and lead > ev.validated_max_horizon_hours:
        state = "OUT_OF_DOMAIN"
        reasons.add("HORIZON_NOT_VALIDATED")
    elif (not ev.independent_holdout or ev.calibration_state != "PASS" or
          not ev.baseline_id or not ev.skill_metric or not ev.threshold_policy_id or
          ev.validated_max_horizon_hours is None or ev.skill_value is None or
          ev.threshold_value is None or "NO_EMPIRICAL_EVIDENCE" in reasons):
        state = "UNKNOWN"
        reasons.add("INDEPENDENT_VALIDATION_MISSING_OR_UNVERIFIED")
    elif ((ev.score_direction == "HIGHER_IS_BETTER" and ev.skill_value < ev.threshold_value) or
          (ev.score_direction == "LOWER_IS_BETTER" and ev.skill_value > ev.threshold_value)):
        state = "INSUFFICIENT_SKILL"
        reasons.add("INSUFFICIENT_SKILL_VS_DECLARED_BASELINE")
    else:
        state = "SHADOW_ONLY"
        reasons.add("WITHIN_CALLER_DECLARED_BOUND_NOT_INDEPENDENTLY_VERIFIED")

    return {
        "status": state,
        "reason_codes": sorted(reasons),
        "lead_hours": round(lead, 6) if math.isfinite(lead) else None,
        "declared_validated_max_horizon_hours": ev.validated_max_horizon_hours,
        "forecast_id": payload.forecast_id,
        "input_sha256": digest,
        "as_of_utc": as_of.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy_version": payload.policy_version,
        "data_version": payload.data_version,
        "mode": "SHADOW",
        "authority": "evaluation_not_certification",
        "provenance_status": "caller_declared_not_authenticated",
        "independent_skill_verified_by_runtime": False,
        "human_review_required": True,
        "investment_authorised": False,
        "credit_authorised": False,
        "certification": False,
        "capital_gate_modified": False,
        "method_id": "PRM-PRED-001@0.1-CANDIDATE",
    }
