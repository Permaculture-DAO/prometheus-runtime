"""PROMETHEUS Regenerative Territorial Capital OS — deterministic shadow screening.

Application-level proof of concept for CIV-TOPOS-001. A result is never a
scientific certificate, legal determination, accreditation, risk rating, or
capital approval. No network services, writable production routes, or LLM calls.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

VERSION = "RTC-OS-SHADOW-0.1"


class TerritorialInputError(ValueError):
    """Invalid basic input encoding; substantive missingness is returned as HOLD."""


def _present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None and value is not False


def _section(payload: Mapping[str, Any], name: str) -> dict:
    value = payload.get(name)
    return dict(value) if isinstance(value, dict) else {}


def review_territorial_proposal(payload: Mapping[str, Any]) -> dict:
    """Evaluate declared packet completeness and explicit red flags.

    A provided document reference is *not* independently verified; thus a
    complete packet advances only to REVIEW_REQUIRED and never to PASS.
    """
    if not isinstance(payload, Mapping):
        raise TerritorialInputError("proposal must be a mapping")
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TerritorialInputError("proposal must be finite and JSON serialisable") from exc
    if len(encoded) > 2_000_000:
        raise TerritorialInputError("proposal exceeds 2 MB shadow screening limit")
    data_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    terr = _section(payload, "territory")
    ev = _section(payload, "evidence")
    rights = _section(payload, "rights")
    finance = _section(payload, "finance")
    risk = _section(payload, "risk")
    governance = _section(payload, "governance")
    method = _section(payload, "method")
    comparator = _section(payload, "simplicity_comparator")
    all_gates = {}

    def gate(gid: str, needed: dict[str, Any], *, errors: list[str] | None = None, not_applicable: bool = False) -> None:
        missing = [key for key, val in needed.items() if not _present(val)]
        issues = sorted(set(missing + (errors or [])))
        if errors:
            status = "FAIL"
        elif not_applicable:
            status = "NOT_APPLICABLE"
        elif missing:
            status = "HOLD"
        else:
            status = "REVIEW_REQUIRED"
        all_gates[gid] = {"status": status, "issues": issues}

    gate("G0_SITE_RIGHTS", {
        "territory.boundary_ref": terr.get("boundary_ref"),
        "territory.site_id": terr.get("site_id"),
        "rights.land_control_evidence_ref": rights.get("land_control_evidence_ref"),
        "rights.water_access_review_ref": rights.get("water_access_review_ref"),
    })
    gate("G1_EVIDENCE", {
        "evidence.baseline_refs": ev.get("baseline_refs"),
        "evidence.source_refs": ev.get("source_refs"),
        "evidence.provenance_method": ev.get("provenance_method"),
        "method.version": method.get("version"),
    })
    gate("G2_DESIGN_RISK", {
        "method.scenario_design": method.get("scenario_design"),
        "risk.risk_ids": risk.get("risk_ids"),
        "risk.ultimate_bearers": risk.get("ultimate_bearers"),
        "territory.operator": terr.get("operator"),
    })
    gate("G3_CAUSAL_MRV", {
        "evidence.comparator_design": ev.get("comparator_design"),
        "evidence.mrv_review_ref": ev.get("mrv_review_ref"),
        "evidence.causal_review_ref": ev.get("causal_review_ref"),
    })
    author = governance.get("design_provider_id")
    reviewer = governance.get("independent_reviewer_id")
    cois = ["reviewer_is_design_provider"] if _present(author) and author == reviewer else []
    gate("G4_INDEPENDENCE_GOVERNANCE", {
        "governance.consent_ref": governance.get("consent_ref"),
        "governance.conflict_register_ref": governance.get("conflict_register_ref"),
        "governance.independent_reviewer_id": reviewer,
    }, errors=cois)

    assumptions = finance.get("base_case_assumptions")
    assumptions = assumptions if isinstance(assumptions, dict) else {}
    prohibited = [label for label in (
        "unverified_carbon_premium", "token_appreciation", "unconfirmed_grant",
        "unverified_regenerative_uplift", "unverified_land_rezoning",
    ) if assumptions.get(label)]
    gate("G5_BASE_ECONOMICS", {
        "finance.payer_id": finance.get("payer_id"),
        "finance.base_case_ref": finance.get("base_case_ref"),
        "finance.liquidity_stress_ref": finance.get("liquidity_stress_ref"),
        "risk.loss_generation_ledger_ref": risk.get("loss_generation_ledger_ref"),
        "risk.risk_allocation_ledger_ref": risk.get("risk_allocation_ledger_ref"),
    }, errors=[f"prohibited_base_case:{key}" for key in prohibited])

    capital = _section(payload, "capital")
    instrument = capital.get("instrument_type", "none")
    valid_instruments = {"none", "private", "public_retail_debt", "grant", "concession"}
    if instrument not in valid_instruments:
        raise TerritorialInputError("unknown instrument_type; explicit instrument taxonomy required")
    is_none = instrument == "none"
    is_public = instrument == "public_retail_debt"
    gate("G6_LEGAL_CAPITAL", {} if is_none else {
        "capital.issuer_id": capital.get("issuer_id"),
        "capital.legal_review_ref": capital.get("legal_review_ref"),
        "capital.investor_or_beneficiary_protection_ref": capital.get("investor_or_beneficiary_protection_ref"),
        **({"capital.public_issuer_authority_ref": capital.get("public_issuer_authority_ref"),
           "capital.debt_sustainability_ref": capital.get("debt_sustainability_ref")}
           if is_public else {}),
    }, not_applicable=is_none)
    gate("G7_SIMPLICITY_FALSIFIABILITY", {
        "simplicity_comparator.protocol_ref": comparator.get("protocol_ref"),
        "simplicity_comparator.cost_baseline_ref": comparator.get("cost_baseline_ref"),
        "simplicity_comparator.kill_conditions": comparator.get("kill_conditions"),
    })

    blocking = sorted(k for k, v in all_gates.items() if v["status"] in {"FAIL", "HOLD"})
    return {
        "engine": VERSION,
        "profile_id": payload.get("profile_id"),
        "input_sha256": data_hash,
        "mode": "SHADOW_NON_AUTHORITATIVE",
        "evaluation": "INCOMPLETE_OR_BLOCKED" if blocking else "REVIEW_PACKET_PRESENT_ONLY",
        "capital_authorised": False,
        "ecological_certified": False,
        "independent_accreditation": False,
        "legal_opinion_created": False,
        "gate_results": all_gates,
        "blocking_gates": blocking,
        "permitted_action": "INDEPENDENT_HUMAN_REVIEW_ONLY",
        "claims_policy": "EVALUATION_NOT_CERTIFICATION",
    }