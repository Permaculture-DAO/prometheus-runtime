"""Regenerative real-estate shadow diagnostics; never grants rights or capital authority.

This is a subordinate research adapter, stacked on land_underwriting shadow v2.
Cash-flow shares measure *declared project outflows* only, not territorial GDP,
causal regenerative impact, land value, verified rental payments or local wealth.
"""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import hashlib
import re
import unicodedata

from .land_underwriting import evaluate_land_underwriting
from .pru import canonical_bytes

SCHEMA_VERSION = "regenerative-real-estate-shadow/v1"
REQUIRED_CONTROLS = (
    "land_access", "occupant_protection", "stewardship",
    "maintenance_reserve", "benefit_distribution", "externalities",
    "related_party", "exit_and_default",
)
STATES = frozenset(("REVIEWABLE", "UNKNOWN", "ADVERSE", "NOT_APPLICABLE"))
LOCATIONS = frozenset(("LOCAL", "NONLOCAL", "UNKNOWN"))
EVIDENCE_FLOOR = frozenset(("REVIEWABLE", "VERIFIED_INDICATOR_CANDIDATE", "ADMISSIBLE"))
MAX_ITEMS = 100
MAX_TEXT = 128
MAX_BYTES = 131072
DECIMAL_PATTERN = re.compile(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?", re.ASCII)
CURRENCY_PATTERN = re.compile(r"[A-Z]{3}", re.ASCII)


def _exact(obj, keys):
    if type(obj) is not dict or set(obj) != set(keys):
        raise ValueError("exact fields required")


def _text(value):
    if type(value) is not str or not 1 <= len(value) <= MAX_TEXT or value != value.strip():
        raise ValueError("1..128 trimmed characters required")
    if unicodedata.normalize("NFC", value) != value or any(
        unicodedata.category(ch).startswith("C") or ch in "\u2028\u2029" for ch in value
    ):
        raise ValueError("NFC text without control/format characters required")


def _rows(value):
    if type(value) is not list or len(value) > MAX_ITEMS:
        raise ValueError("bounded list required")


def _unique(rows, key):
    ids = [row[key] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate {key}")


def _known_evidence(ref, land):
    hashes = land["evidence_hashes"]
    states = land["evidence_states"]
    expected_scope = land["scope"]
    linked = any(
        g["scope"] == expected_scope and
        any(e["evidence_id"] == ref and hashes.get(ref) == e["sha256"]
            for e in g["evidence"])
        for g in land["gates"]
    )
    return ref in hashes and states.get(ref) in EVIDENCE_FLOOR and linked


def evaluate_regenerative_real_estate(payload: dict) -> dict:
    """Fail-closed diagnostics from frozen declarations; no network/clock/storage."""
    _exact(payload, ("schema_version", "land_underwriting", "safeguards",
                     "cash_outflows", "risk_links", "currency"))
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported real estate schema version")
    land = payload["land_underwriting"]
    # Re-evaluate rather than trust an unverifiable caller-provided gate result.
    preflight = evaluate_land_underwriting(land)
    currency = payload["currency"]
    if type(currency) is not str or CURRENCY_PATTERN.fullmatch(currency) is None:
        raise ValueError("ISO-like three-letter currency declaration required")
    safeguards, flows, risks = (payload[k] for k in
        ("safeguards", "cash_outflows", "risk_links"))
    for collection in (safeguards, flows, risks):
        _rows(collection)
    for record in safeguards:
        _exact(record, ("control_id", "state", "evidence_id"))
        _text(record["control_id"])
        _text(record["evidence_id"])
        if type(record["state"]) is not str or record["state"] not in STATES:
            raise ValueError("unknown safeguard state")
    _unique(safeguards, "control_id")
    for record in flows:
        _exact(record, ("event_id", "amount", "currency", "recipient_scope", "evidence_id"))
        for key in ("event_id", "evidence_id"):
            _text(record[key])
        if type(record["amount"]) is not str or DECIMAL_PATTERN.fullmatch(record["amount"]) is None:
            raise ValueError("finite bounded decimal string required")
        if record["currency"] != currency or type(record["currency"]) is not str:
            raise ValueError("currency mismatch")
        if type(record["recipient_scope"]) is not str or record["recipient_scope"] not in LOCATIONS:
            raise ValueError("unknown recipient scope")
    _unique(flows, "event_id")
    for record in risks:
        _exact(record, ("risk_id", "ultimate_bearer_id", "evidence_id"))
        for key in ("risk_id", "ultimate_bearer_id", "evidence_id"):
            _text(record[key])
    _unique(risks, "risk_id")
    if len(canonical_bytes(payload)) > MAX_BYTES:
        raise ValueError("payload exceeds max bytes")
    blocks = []
    if preflight["status"] != "GO_FOR_EXTERNAL_REVIEW":
        blocks.append("land_preflight:hold")
    by_control = {s["control_id"]: s for s in safeguards}
    for required in REQUIRED_CONTROLS:
        if required not in by_control:
            blocks.append(f"safeguard:{required}:missing")
    for record in safeguards:
        uid = record["control_id"]
        if record["state"] != "REVIEWABLE":
            blocks.append(f"safeguard:{uid}:{record['state'].lower()}")
        if not _known_evidence(record["evidence_id"], land):
            blocks.append(f"safeguard:{uid}:unusable_evidence")
    if not flows:
        blocks.append("cash_outflows:missing")
    if not risks:
        blocks.append("risk_links:missing")
    for record in flows:
        uid = record["event_id"]
        if record["recipient_scope"] == "UNKNOWN":
            blocks.append(f"cash_outflow:{uid}:recipient_unknown")
        if not _known_evidence(record["evidence_id"], land):
            blocks.append(f"cash_outflow:{uid}:unusable_evidence")
    for record in risks:
        if not _known_evidence(record["evidence_id"], land):
            blocks.append(f"risk:{record['risk_id']}:unusable_evidence")
    # Calculated only as an explicitly non-authoritative declared-cash-share diagnostic.
    # Unknown recipient classification or unusable evidence => no computed ratio.
    ratio = None
    numerator = None
    denominator = None
    flow_eligible = bool(flows) and not blocks and all(
        row["recipient_scope"] != "UNKNOWN" and _known_evidence(row["evidence_id"], land)
        for row in flows
    )
    if flow_eligible:
        with localcontext() as ctx:
            ctx.prec = 64
            ctx.rounding = ROUND_HALF_EVEN
            total = sum((Decimal(r["amount"]) for r in flows), Decimal(0))
            local = sum((Decimal(r["amount"]) for r in flows
                         if r["recipient_scope"] == "LOCAL"), Decimal(0))
            if total == 0:
                blocks.append("cash_outflows:zero_denominator")
            else:
                ratio = format((local / total).quantize(Decimal("0.000001")), ".6f")
                numerator = format(local, "f")
                denominator = format(total, "f")
    frozen = {
        "schema_version": SCHEMA_VERSION,
        "land_preflight_sha256": preflight["input_sha256"],
        "currency": currency,
        "safeguards": sorted(safeguards, key=lambda x: x["control_id"]),
        "cash_outflows": sorted(flows, key=lambda x: x["event_id"]),
        "risk_links": sorted(risks, key=lambda x: x["risk_id"]),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "SHADOW",
        "site_id": preflight["site_id"],
        "dossier_id": preflight["dossier_id"],
        "as_of": preflight["as_of"],
        "input_sha256": hashlib.sha256(canonical_bytes(frozen)).hexdigest(),
        "status": "HOLD" if blocks else "GO_FOR_EXTERNAL_REVIEW",
        "blocks": sorted(set(blocks)),
        "land_preflight": {
            "status": preflight["status"],
            "input_sha256": preflight["input_sha256"],
            "blocks": preflight["blocks"],
        },
        "cash_outflow_local_share": {
            "status": "CALLER_DECLARED_UNVERIFIED" if ratio is not None else "UNKNOWN",
            "ratio": ratio, "local_amount": numerator, "total_amount": denominator,
            "currency": currency, "basis": "declared_project_cash_outflows_only",
            "causal_attribution": False,
            "market_value": None,
        },
        "risk_links_status": "CALLER_DECLARED_NOT_VALIDATED",
        "evidence_authenticity": "NOT_ESTABLISHED",
        "regenerative_outcome": "NOT_VERIFIED",
        "source_status": "PROPOSED_NOT_ADOPTED",
        "independent_review_required": True,
        "land_value": None,
        "ecological_uplift": None,
        "trbk_entitlement": None,
        "legal_rights_created": False,
        "financial_certification": False,
        "capital_admission": False,
        "authoritative": False,
        "statement": "Reproducible SHADOW policy preflight; no legal, ecological, actuarial or capital approval.",
    }
