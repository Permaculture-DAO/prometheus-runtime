"""Bounded pure shadow adapter. Caller declarations never confer authority."""
from datetime import datetime, timedelta, timezone
import hashlib
import re
import unicodedata

from .controls import EvidenceState, GateRecord, GateState, evaluate_gates
from .pru import canonical_bytes

SCHEMA_VERSION = "land-underwriting-shadow/v2"
GATES = ("rights", "land_use", "environment", "water", "data")
AMOUNTS = ("gross_development_value", "development_cost", "finance_cost", "developer_profit")
MAX_DECISION_VALIDITY_DAYS = 366
MAX_ROWS = 100
MAX_TEXT = 128
MAX_PAYLOAD_BYTES = 131072


def _exact(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("exact fields required")


def _text(value):
    if type(value) is not str or not 1 <= len(value) <= MAX_TEXT or value != value.strip():
        raise ValueError("trimmed text of 1..128 characters required")
    if unicodedata.normalize("NFC", value) != value or any(
            unicodedata.category(c).startswith("C") or c in "\u2028\u2029" for c in value):
        raise ValueError("NFC text without control, format or surrogate characters required")


def _list(value):
    if type(value) is not list or len(value) > MAX_ROWS:
        raise ValueError("list of at most 100 entries required")


def _ids(value):
    _list(value)
    for item in value:
        _text(item)
    if len(set(value)) != len(value):
        raise ValueError("duplicate reference")


def _sha(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("lowercase SHA256 required")


def _time(value):
    if type(value) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value) is None:
        raise ValueError("ASCII UTC timestamp required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid calendar timestamp") from exc


def _catalog(value, kind):
    if type(value) is not dict or len(value) > MAX_ROWS:
        raise ValueError("catalog of at most 100 entries required")
    for key, item in value.items():
        _text(key)
        if kind == "hash":
            _sha(item)
        elif type(item) is not str or item not in EvidenceState._value2member_map_:
            raise ValueError("existing EvidenceState required")
    return dict(value) if kind == "hash" else {k: EvidenceState(v) for k, v in value.items()}


def evaluate_land_underwriting(payload: dict) -> dict:
    """Evaluate frozen declarations; no clock, I/O, evidence creation or approval."""
    _exact(payload, ("schema_version", "site_id", "dossier_id", "as_of", "use_case",
                     "scope", "gates", "evidence_hashes", "evidence_states",
                     "decision_hashes", "revoked_decisions", "development"))
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema version")
    for key in ("site_id", "dossier_id", "scope"):
        _text(payload[key])
    # Colon is reserved to keep the namespace unambiguous for identifier pairs.
    if any(":" in payload[key] for key in ("site_id", "dossier_id")):
        raise ValueError("site and dossier IDs must not contain colon")
    expected_scope = f"LAND:{payload['site_id']}:{payload['dossier_id']}"
    as_of = _time(payload["as_of"])
    if type(payload["use_case"]) is not str or payload["use_case"] not in ("DEVELOPMENT", "NONDEVELOPMENT"):
        raise ValueError("invalid use case")
    hashes = _catalog(payload["evidence_hashes"], "hash")
    states = _catalog(payload["evidence_states"], "state")
    decisions = _catalog(payload["decision_hashes"], "hash")
    _ids(payload["revoked_decisions"])
    _list(payload["gates"])
    records = []
    for row in payload["gates"]:
        _exact(row, ("gate_uid", "scope", "state", "spec_ref", "decision_ref",
                     "issued_at", "expires_at", "evidence", "prerequisites"))
        for key in ("gate_uid", "scope"):
            _text(row[key])
        for key in ("spec_ref", "decision_ref"):
            if row[key] is not None:
                _text(row[key])
        if type(row["state"]) is not str or row["state"] not in GateState._value2member_map_:
            raise ValueError("existing GateState required")
        _ids(row["prerequisites"])
        _list(row["evidence"])
        evidence = []
        for item in row["evidence"]:
            _exact(item, ("evidence_id", "sha256"))
            _text(item["evidence_id"])
            _sha(item["sha256"])
            evidence.append((item["evidence_id"], item["sha256"]))
        record = GateRecord(row["gate_uid"], row["scope"], GateState(row["state"]),
            row["spec_ref"], row["decision_ref"],
            None if row["issued_at"] is None else _time(row["issued_at"]),
            None if row["expires_at"] is None else _time(row["expires_at"]),
            tuple(evidence), tuple(row["prerequisites"]))
        record.snapshot()
        records.append(record)
    if len({g.gate_uid for g in records}) != len(records):
        raise ValueError("duplicate gate UID")
    diagnostic = {"status": "NOT_APPLICABLE", "inputs": None, "value": None,
                  "warnings": []}
    development = payload["development"]
    amounts_complete = True
    if payload["use_case"] == "NONDEVELOPMENT":
        if development is not None:
            raise ValueError("nondevelopment requires null diagnostic inputs")
    else:
        _exact(development, ("currency", "evidence_ids", *AMOUNTS))
        if type(development["currency"]) is not str or re.fullmatch(r"[A-Z]{3}", development["currency"]) is None:
            raise ValueError("ASCII currency required")
        _ids(development["evidence_ids"])
        for key in AMOUNTS:
            value = development[key]
            if value is not None and (type(value) is not str or re.fullmatch(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?", value) is None):
                raise ValueError("bounded decimal string or null required")
            amounts_complete = amounts_complete and value is not None
        diagnostic.update(status="UNKNOWN", inputs={k: development[k] for k in ("currency", *AMOUNTS)})
    # All structures are shallow and bounded before serialization, including strings.
    if len(canonical_bytes(payload)) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload exceeds 131072 UTF-8 bytes")
    controls = evaluate_gates(tuple(records), as_of=as_of, scope=expected_scope,
        evidence_hashes=hashes, evidence_states=states, decision_hashes=decisions,
        revoked_decisions=frozenset(payload["revoked_decisions"])) if records else None
    rows = controls["gates"] if controls else {}
    blocks = [f"{uid}:missing_required_gate" for uid in GATES if uid not in rows]
    blocks += [f"{uid}:{reason}" for uid, row in rows.items() for reason in row["reasons"]]
    if payload["scope"] != expected_scope:
        blocks.append("scope:site_dossier_mismatch")
    for g in records:
        if g.issued_at is not None and g.expires_at is not None and (
                g.expires_at - g.issued_at > timedelta(days=MAX_DECISION_VALIDITY_DAYS)):
            blocks.append(f"{g.gate_uid}:validity_interval_exceeds_policy")
    # No authenticated competence/authority is available in this pure adapter.
    # Even an intact caller-declared FAILED decision therefore remains HOLD.
    if development is not None:
        refs = development["evidence_ids"]
        if not refs or any(ref not in hashes or ref not in states or states[ref] not in
            (EvidenceState.REVIEWABLE, EvidenceState.VERIFIED_INDICATOR_CANDIDATE, EvidenceState.ADMISSIBLE) for ref in refs):
            blocks.append("development:unusable_evidence")
        bound_refs = {ref for g in records for ref, sha in g.evidence
                      if hashes.get(ref) == sha and g.scope == expected_scope}
        if any(ref not in bound_refs for ref in refs):
            blocks.append("development:orphan_evidence")
        if not amounts_complete:
            blocks.append("development:unknown_amount")
        if not blocks:
            diagnostic["status"] = "INPUTS_COMPLETE"
    # Normalize unordered declaration collections for input hashing and byte replay.
    frozen = dict(payload)
    frozen["gates"] = sorted((dict(row, evidence=sorted(row["evidence"], key=lambda e: e["evidence_id"]),
                                  prerequisites=sorted(row["prerequisites"])) for row in payload["gates"]), key=lambda g: g["gate_uid"])
    frozen["revoked_decisions"] = sorted(payload["revoked_decisions"])
    if development is not None:
        frozen["development"] = dict(development, evidence_ids=sorted(development["evidence_ids"]))
    return {"schema_version": SCHEMA_VERSION, "mode": "SHADOW",
        "site_id": payload["site_id"], "dossier_id": payload["dossier_id"],
        "as_of": payload["as_of"], "scope": payload["scope"], "use_case": payload["use_case"],
        "input_sha256": hashlib.sha256(canonical_bytes(frozen)).hexdigest(),
        "status": "HOLD" if blocks else "GO_FOR_EXTERNAL_REVIEW",
        "blocks": sorted(blocks), "controls": controls,
        "development_input_diagnostic": diagnostic,
        "land_value": None, "valuation_status": "valuation_not_admitted",
        "time_basis": {"status": "caller_declared", "as_of": payload["as_of"],
            "freshness_verified": False, "max_decision_validity_days": MAX_DECISION_VALIDITY_DAYS,
            "gate_intervals": {row["gate_uid"]: {key: row[key] for key in ("issued_at", "expires_at")}
                               for row in sorted(payload["gates"], key=lambda row: row["gate_uid"])}},
        "references_status": "caller_declared_not_authenticated",
        "independent_reviewer_authority_required": True, "source_verification_required": True,
        "legal_professional_review": "HOLD", "authoritative": False,
        "underwriting_approval": False, "capital_admission": False,
        "certification": False, "creates_rights": False,
        "statement": "Shadow candidate eligibility only; no land valuation, ecological uplift or TRBK entitlement."}
