"""A read-only sidecar projection; never a native AdmissibilityDecision."""
from __future__ import annotations
from hashlib import sha256
from typing import Any
from .trust_boundary import canonical

OUTCOMES = frozenset(("ELIGIBLE_FOR_REVIEW", "HOLD", "NO_GO"))


def make_advice(result: Any) -> dict:
    if not isinstance(result, dict):
        result = {}
    outcome = result.get("decision")
    bad_authority_flags = any(result.get(k) is not False for k in
                              ("action_authorised", "certification",
                               "capital_authorised", "rights_created"))
    if outcome not in OUTCOMES or bad_authority_flags:
        outcome = "HOLD"
        issues = ["INVALID_OR_UNSAFE_ASSURANCE_OUTPUT"]
    else:
        issues = [x for x in result.get("issues", []) if isinstance(x, str)][:100] if isinstance(result.get("issues"), list) else ["INVALID_ISSUE_FIELD"]
        if issues == ["INVALID_ISSUE_FIELD"]:
            outcome = "HOLD"
    case_id = result.get("case_id") if isinstance(result.get("case_id"), str) else None
    case_id = case_id[:128] if case_id else None
    core = {"review_outcome": outcome, "case_id": case_id,
            "issues": issues,
            "mode": "SYNTHETIC_ONLY_READ_ONLY",
            "authority_boundary": "RECOMMENDATION_ONLY_NO_NATIVE_ADMISSION",
            "action_authorised": False,
            "certification": False,
            "capital_authorised": False,
            "rights_created": False,
            "native_admissibility_written": False,
            "runtime_mutation_permitted": False,
            "authoritative": False}
    return {"advice_uid": "omega_"+sha256(canonical(core)).hexdigest()[:24], **core}
