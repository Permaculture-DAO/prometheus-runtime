"""Read-only land-risk context, never an investment or land gate decision.

This adapter reuses PRM-PRED-001 and does not implement or change G0-G7, RAVEL,
AETERNA, evidence admission, ecological credits, prices or any land title.
"""
from __future__ import annotations

from .predictability import PredictabilityInput, evaluate_predictability


def land_predictability_context(payload: PredictabilityInput) -> dict:
    evaluation = evaluate_predictability(payload)
    return {
        "source": "PRM-PRED-001@0.1-CANDIDATE",
        "site_id": payload.site_id,
        "forecast_id": payload.forecast_id,
        "forecast_domain": payload.domain,
        "forecast_variable": payload.variable,
        "predictability_state": evaluation["status"],
        "predictability_reasons": evaluation["reason_codes"],
        "input_sha256": evaluation["input_sha256"],
        "risk_category": "PREDICTIVE_MODEL_AND_INFORMATION_UNCERTAINTY",
        "risk_state": "UNVERIFIED_SHADOW_INPUT",
        "risk_bearer": "UNKNOWN_REQUIRES_EXPLICIT_RAVEL_ASSESSMENT",
        "residual_risk": "NOT_ASSESSED",
        "unmodelled_risk": "NOT_ASSESSED",
        "estimated_loss": None,
        "land_value": None,
        "forecast_skill_independently_verified": False,
        "can_admit_land_investment": False,
        "can_admit_credit_or_insurance": False,
        "can_set_pru_or_vrrc": False,
        "can_modify_gates": False,
        "next_action": "HUMAN_REVIEW_AND_DOMAIN_SPECIFIC_EVIDENCE_REQUIRED",
        "authority": "NON_AUTHORITATIVE_READ_ONLY",
    }
