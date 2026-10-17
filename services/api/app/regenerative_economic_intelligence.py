"""REI SHADOW: deterministic, sector-aware claim and risk-link preflight.

Composes existing Regenerative Real Estate -> Land -> Controls; does not
create another gate engine, validate evidence authenticity, or admit capital.
Other sectors remain HOLD until their own reviewed adapters are available.
"""
import hashlib
import re

from .land_underwriting import _time
from .pru import canonical_bytes
from .regenerative_real_estate import (
    MAX_BYTES, _exact, _known_evidence, _rows, _text, _unique,
    evaluate_regenerative_real_estate,
)

SCHEMA_VERSION = "regenerative-economic-intelligence-shadow/v1"
SECTORS = frozenset(("REAL_ESTATE", "AGRICULTURE", "ENERGY", "INFRASTRUCTURE"))
DIMENSIONS = frozenset((
    "FINANCIAL", "PRODUCTIVE", "ECOLOGICAL", "SOCIAL", "GOVERNANCE", "RISK",
))
EPISTEMIC_STATES = frozenset((
    "HYPOTHESIS", "OBSERVATION_CANDIDATE",
    "CAUSAL_CANDIDATE", "VALUATION_CANDIDATE",
))
MODES = frozenset(("D", "P", "H", "Q"))
DECIMAL_PATTERN = re.compile(
    r"-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?", re.ASCII
)


def _reference_or_null(value):
    if value is not None:
        _text(value)


def evaluate_regenerative_economic_intelligence(payload: dict) -> dict:
    """Check declared dossier coherence; never issue substantive approval."""
    _exact(payload, (
        "schema_version", "sector", "project_id", "as_of",
        "real_estate", "metrics", "risk_ledger_links",
    ))
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported REI schema")
    if type(payload["sector"]) is not str or payload["sector"] not in SECTORS:
        raise ValueError("unknown sector")
    _text(payload["project_id"])
    _time(payload["as_of"])
    _rows(payload["metrics"])
    _rows(payload["risk_ledger_links"])
    blocks = []
    land = None
    real_estate_result = None
    if payload["sector"] == "REAL_ESTATE":
        if type(payload["real_estate"]) is not dict:
            raise ValueError("real estate adapter requires its exact input")
        real_estate_result = evaluate_regenerative_real_estate(payload["real_estate"])
        land = payload["real_estate"]["land_underwriting"]
        if real_estate_result["status"] != "GO_FOR_EXTERNAL_REVIEW":
            blocks.append("real_estate:hold")
        if real_estate_result["site_id"] != payload["project_id"]:
            blocks.append("identity:project_site_mismatch")
        if real_estate_result["as_of"] != payload["as_of"]:
            blocks.append("time:as_of_mismatch")
    else:
        if payload["real_estate"] is not None:
            raise ValueError("non-real-estate sector cannot reuse land eligibility")
        blocks.append("domain_adapter:not_implemented")

    metrics = payload["metrics"]
    risks = payload["risk_ledger_links"]
    if not metrics:
        blocks.append("metrics:missing")
    for row in metrics:
        _exact(row, (
            "metric_id", "dimension", "epistemic_state", "compute_mode",
            "declared_value", "unit", "evidence_ids", "method_ref",
            "baseline_evidence_id", "counterfactual_evidence_id",
        ))
        for key in ("metric_id", "method_ref"):
            _text(row[key])
        for key, allowed in (("dimension", DIMENSIONS),
                             ("epistemic_state", EPISTEMIC_STATES),
                             ("compute_mode", MODES)):
            if type(row[key]) is not str or row[key] not in allowed:
                raise ValueError("invalid metric classification")
        value = row["declared_value"]
        if value is not None and (
            type(value) is not str or DECIMAL_PATTERN.fullmatch(value) is None
        ):
            raise ValueError("bounded decimal declaration or null required")
        if row["unit"] is not None:
            _text(row["unit"])
        if (value is None) != (row["unit"] is None):
            raise ValueError("unit and declared value must both be present or null")
        for key in ("baseline_evidence_id", "counterfactual_evidence_id"):
            _reference_or_null(row[key])
        refs = row["evidence_ids"]
        _rows(refs)
        for ref in refs:
            _text(ref)
        if len(set(refs)) != len(refs):
            raise ValueError("duplicate metric evidence ID")
    _unique(metrics, "metric_id")
    for row in risks:
        _exact(row, (
            "risk_id", "loss_event_id", "loss_generation_ref",
            "risk_allocation_ref", "ultimate_risk_bearer_id", "evidence_id",
        ))
        for value in row.values():
            _text(value)
    _unique(risks, "risk_id")
    _unique(risks, "loss_event_id")
    if len(canonical_bytes(payload)) > MAX_BYTES:
        raise ValueError("REI request exceeds 131072 bytes")

    for row in metrics:
        mid = row["metric_id"]
        refs = list(row["evidence_ids"])
        refs += [row[k] for k in ("baseline_evidence_id", "counterfactual_evidence_id")
                 if row[k] is not None]
        if not row["evidence_ids"]:
            blocks.append(f"metric:{mid}:missing_evidence")
        if land is None or any(not _known_evidence(ref, land) for ref in refs):
            blocks.append(f"metric:{mid}:unusable_evidence")
        if row["epistemic_state"] == "OBSERVATION_CANDIDATE" and row["declared_value"] is None:
            blocks.append(f"metric:{mid}:unknown_measurement")
        if row["epistemic_state"] in ("CAUSAL_CANDIDATE", "VALUATION_CANDIDATE"):
            # Self-consistent evidence does NOT establish attribution/valuation.
            blocks.append(f"metric:{mid}:independent_method_review_required")
        if row["compute_mode"] != "D":
            # P/H/Q requires a separately proven D boundary: absent in this adapter.
            blocks.append(f"metric:{mid}:deterministic_verification_missing")
    expected_risk_ids = (
        {row["risk_id"] for row in payload["real_estate"]["risk_links"]}
        if land is not None else set()
    )
    supplied_risk_ids = {row["risk_id"] for row in risks}
    if expected_risk_ids != supplied_risk_ids:
        blocks.append("risk:lower_adapter_set_mismatch")
    if not risks:
        blocks.append("risk:two_ledger_links_missing")
    lower_bearers = (
        {row["risk_id"]: row["ultimate_bearer_id"] for row in
         payload["real_estate"]["risk_links"]}
        if land is not None else {}
    )
    for row in risks:
        uid = row["risk_id"]
        if lower_bearers.get(uid) != row["ultimate_risk_bearer_id"]:
            blocks.append(f"risk:{uid}:ultimate_bearer_mismatch")
        if land is None or not _known_evidence(row["evidence_id"], land):
            blocks.append(f"risk:{uid}:unusable_evidence")

    # Only D-stage *declaration checks* are performed; this cannot validate
    # evidence custody, legal truth, source adoption, or RAVEL two-ledger facts.
    blocked = bool(blocks)
    frozen = {
        "schema_version": SCHEMA_VERSION,
        "sector": payload["sector"],
        "project_id": payload["project_id"],
        "as_of": payload["as_of"],
        "real_estate_input_sha256": (
            real_estate_result["input_sha256"] if real_estate_result else None
        ),
        "metrics": sorted(
            (dict(row, evidence_ids=sorted(row["evidence_ids"])) for row in metrics),
            key=lambda row: row["metric_id"],
        ),
        "risk_ledger_links": sorted(risks, key=lambda row: row["risk_id"]),
    }
    counts = {d: 0 for d in sorted(DIMENSIONS)}
    for row in metrics:
        counts[row["dimension"]] += 1
    local_diagnostic = (
        real_estate_result["cash_outflow_local_share"]
        if real_estate_result else None
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "SHADOW",
        "sector": payload["sector"],
        "project_id": payload["project_id"],
        "as_of": payload["as_of"],
        "input_sha256": hashlib.sha256(canonical_bytes(frozen)).hexdigest(),
        "status": "HOLD" if blocked else "GO_FOR_EXTERNAL_REVIEW",
        "blocks": sorted(set(blocks)),
        "components": {
            "real_estate": {
                "status": real_estate_result["status"],
                "input_sha256": real_estate_result["input_sha256"],
            } if real_estate_result else None,
            "ravel": "UNAUTHENTICATED_REFERENCE_LINKS_ONLY",
            "aeterna": "METHODOLOGY_NOT_EXECUTED",
        },
        "declared_metric_counts": counts,
        "cash_outflow_local_share": {
            "status": "WITHHELD_DUE_TO_HOLD" if blocked else (
                local_diagnostic["status"] if local_diagnostic else "UNKNOWN"
            ),
            "ratio": None if blocked or local_diagnostic is None else local_diagnostic["ratio"],
            "basis": "caller_declared_project_cash_outflows_not_local_wealth",
        },
        "two_ledger_linkage": "DECLARED_NOT_AUDITED",
        "source_status": "PROPOSED_NOT_ADOPTED",
        "evidence_authenticity": "NOT_ESTABLISHED",
        "causal_attribution_verified": False,
        "ecological_outcome_verified": False,
        "financial_value_verified": False,
        "risk_reduction_verified": False,
        "underwriting_approval": False,
        "capital_admission": False,
        "legal_rights_created": False,
        "certification": False,
        "trbk_entitlement": None,
        "valuation": None,
        "composite_regeneration_score": None,
        "authoritative": False,
        "independent_review_required": True,
        "statement": (
            "SHADOW dossier-coherence preflight; no sector admission, "
            "causal impact, valuation, insurance or capital authorization."
        ),
    }
