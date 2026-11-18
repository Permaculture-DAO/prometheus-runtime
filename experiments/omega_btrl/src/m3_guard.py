"""M3 synthetic-only non-authoritative hardening wrapper.

This is NOT a replacement for independent host trust services, personal
independence diligence, key custody, or native PROMETHEUS admission.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from .trust_boundary import TrustedStore, TrustRoot, closed_result, evaluate

REQUIRED_ROLES = frozenset({
    "SOURCE_CUSTODIAN", "POLICY_AUTHORITY", "EVIDENCE_ATTESTOR",
    "INDEPENDENT_REVIEWER", "HUMAN_AUTHORITY", "REVOCATION_AUTHORITY",
})


def baseline_issues(store: Any) -> list[str]:
    """Check cryptographic key aliasing and the narrow synthetic trust profile.

    Key uniqueness is necessary but not sufficient for role independence.
    This function does NOT establish principal ownership of a key.
    """
    if not isinstance(store, TrustedStore):
        return ["HOST_TRUST_STORE_UNAVAILABLE"]
    try:
        roots = store.roots
        if not isinstance(roots, dict) or len(roots) != len(REQUIRED_ROLES):
            return ["TRUST_ROOT_SET_INVALID"]
        roles, public_keys, problems = [], [], []
        for key_id, root in roots.items():
            if not isinstance(key_id, str) or not isinstance(root, TrustRoot):
                problems.append("TRUST_ROOT_RECORD_INVALID")
                continue
            if key_id != root.principal_id or root.role not in REQUIRED_ROLES:
                problems.append("TRUST_ROOT_IDENTITY_OR_ROLE_INVALID")
            if not isinstance(root.public_key, bytes) or len(root.public_key) != 32:
                problems.append("TRUST_ROOT_PUBLIC_KEY_INVALID")
            else:
                public_keys.append(root.public_key)
            roles.append(root.role)
        if len(roles) != len(REQUIRED_ROLES) or set(roles) != REQUIRED_ROLES:
            problems.append("TRUST_ROLE_COVERAGE_INVALID")
        if len(set(public_keys)) != len(public_keys):
            problems.append("TRUST_KEY_REUSED_ACROSS_ROLES")
        if len(public_keys) != len(REQUIRED_ROLES):
            problems.append("TRUST_ROOT_PUBLIC_KEY_COUNT_INVALID")
        return sorted(set(problems))
    except (TypeError, ValueError, AttributeError):
        return ["TRUST_BASELINE_MALFORMED"]


def evaluate_m3(candidate: Any, store: TrustedStore | None = None,
                *, now: datetime | None = None) -> dict:
    """Evaluate case only if the independently installed trust profile is sound.

    Does not grant capability tokens, mutate original case, write a runtime
    admissibility decision, or perform physical/financial/legal actions.
    """
    issues = baseline_issues(store)
    if issues:
        try:
            cid = candidate.get("assurance_case_id") if isinstance(candidate, dict) else None
        except Exception:
            cid = None
        return closed_result(reasons=issues, case_id=cid)
    return evaluate(candidate, store, now=now)
