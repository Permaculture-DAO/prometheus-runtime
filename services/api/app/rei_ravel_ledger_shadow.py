"""REI/RAVEL dual-ledger declaration consistency SHADOW adapter.

No evidence-authentication, insurance coverage, actuarial approval, or risk reduction
is established by mathematically reconciling a caller-supplied snapshot.
"""
from decimal import Decimal, localcontext
import hashlib
import re

from .land_underwriting import _time
from .pru import canonical_bytes
from .regenerative_real_estate import _exact, _rows, _text, _unique, MAX_BYTES

SCHEMA_VERSION = "rei-ravel-two-ledger-shadow/v1"
DECIMAL = re.compile(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?", re.ASCII)
CURRENCY = re.compile(r"[A-Z]{3}", re.ASCII)
UNALLOCATED = frozenset(("UNALLOCATED", "UNKNOWN", "UNALLOCATED_RESIDUAL"))


def _amount(value):
    if value is None:
        return None
    if type(value) is not str or DECIMAL.fullmatch(value) is None:
        raise ValueError("nonnegative bounded decimal string or null required")
    return Decimal(value)


def _refs(value):
    _rows(value)
    if not value:
        raise ValueError("at least one declared evidence reference required")
    for ref in value:
        _text(ref)
    if len(value) != len(set(value)):
        raise ValueError("duplicate evidence reference")


def evaluate_ledger_consistency(payload: dict) -> dict:
    """Returns only HOLD or GO_FOR_EXTERNAL_REVIEW, never risk authority."""
    _exact(payload, (
        "schema_version", "project_id", "as_of", "currency",
        "generation", "allocation", "transfers",
    ))
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported ledger version")
    _text(payload["project_id"])
    _time(payload["as_of"])
    if type(payload["currency"]) is not str or CURRENCY.fullmatch(payload["currency"]) is None:
        raise ValueError("three-letter ASCII currency declaration required")
    gen, alloc, transfers = (payload[key] for key in ("generation", "allocation", "transfers"))
    for rows in (gen, alloc, transfers):
        _rows(rows)
    if not gen or not alloc:
        raise ValueError("generation and allocation are required")

    for row in gen:
        _exact(row, ("event_id", "risk_id", "gross_loss", "prevented_loss",
                     "residual_loss", "evidence_ids"))
        _text(row["event_id"])
        _text(row["risk_id"])
        _refs(row["evidence_ids"])
        for key in ("gross_loss", "prevented_loss", "residual_loss"):
            _amount(row[key])
    _unique(gen, "event_id")
    for row in alloc:
        _exact(row, ("event_id", "bearer_id", "before_transfer",
                     "after_transfer", "evidence_ids"))
        _text(row["event_id"])
        _text(row["bearer_id"])
        _refs(row["evidence_ids"])
        _amount(row["before_transfer"])
        _amount(row["after_transfer"])
    if len({(r["event_id"], r["bearer_id"]) for r in alloc}) != len(alloc):
        raise ValueError("duplicate event-bearer allocation")
    for row in transfers:
        _exact(row, ("transfer_id", "event_id", "from_bearer_id", "to_bearer_id",
                     "amount", "evidence_ids"))
        for key in ("transfer_id", "event_id", "from_bearer_id", "to_bearer_id"):
            _text(row[key])
        if row["from_bearer_id"] == row["to_bearer_id"]:
            raise ValueError("self-transfer prohibited")
        _refs(row["evidence_ids"])
        _amount(row["amount"])
    _unique(transfers, "transfer_id")
    if len(canonical_bytes(payload)) > MAX_BYTES:
        raise ValueError("payload too large")

    events = {row["event_id"]: row for row in gen}
    allocation_ids = {(r["event_id"], r["bearer_id"]) for r in alloc}
    blocks = []
    for row in alloc:
        if row["event_id"] not in events:
            blocks.append(f"allocation:{row['event_id']}:unknown_event")
        if row["bearer_id"] in UNALLOCATED:
            blocks.append(f"allocation:{row['event_id']}:unallocated_bearer")
    for row in transfers:
        if row["event_id"] not in events:
            blocks.append(f"transfer:{row['transfer_id']}:unknown_event")
        if ((row["event_id"], row["from_bearer_id"]) not in allocation_ids or
                (row["event_id"], row["to_bearer_id"]) not in allocation_ids):
            blocks.append(f"transfer:{row['transfer_id']}:orphan_bearer")
        if row["from_bearer_id"] in UNALLOCATED or row["to_bearer_id"] in UNALLOCATED:
            blocks.append(f"transfer:{row['transfer_id']}:unallocated_bearer")
        if row["amount"] is None:
            blocks.append(f"transfer:{row['transfer_id']}:unknown_amount")

    summaries = {}
    with localcontext() as ctx:
        ctx.prec = 70
        for uid in sorted(events):
            event = events[uid]
            rows = [r for r in alloc if r["event_id"] == uid]
            ts = [r for r in transfers if r["event_id"] == uid]
            gross = _amount(event["gross_loss"])
            prevented = _amount(event["prevented_loss"])
            residual = _amount(event["residual_loss"])
            complete = all(value is not None for value in (gross, prevented, residual))
            if not complete:
                blocks.append(f"event:{uid}:unknown_system_loss")
            elif prevented > gross or gross - prevented != residual:
                blocks.append(f"event:{uid}:generation_conservation_failed")
            if not rows:
                blocks.append(f"event:{uid}:missing_allocation")
            allocation_complete = bool(rows) and all(
                _amount(r["before_transfer"]) is not None and
                _amount(r["after_transfer"]) is not None for r in rows)
            if not allocation_complete:
                blocks.append(f"event:{uid}:unknown_allocation")
            if complete and allocation_complete:
                before_sum = sum((_amount(r["before_transfer"]) for r in rows), Decimal(0))
                after_sum = sum((_amount(r["after_transfer"]) for r in rows), Decimal(0))
                if before_sum != residual or after_sum != residual:
                    blocks.append(f"event:{uid}:allocation_conservation_failed")
                # Require that each bearer's change equals declared transfer flows.
                for r in rows:
                    bearer = r["bearer_id"]
                    outflows = sum((_amount(t["amount"]) for t in ts
                                    if t["from_bearer_id"] == bearer and
                                    t["amount"] is not None), Decimal(0))
                    inflows = sum((_amount(t["amount"]) for t in ts
                                   if t["to_bearer_id"] == bearer and
                                   t["amount"] is not None), Decimal(0))
                    if (_amount(r["before_transfer"]) - outflows + inflows !=
                            _amount(r["after_transfer"])):
                        blocks.append(f"event:{uid}:transfer_flow_mismatch:{bearer}")
            summaries[uid] = {
                "risk_id": event["risk_id"],
                "numeric_consistency": (
                    "DECLARATIONS_RECONCILABLE" if not any(
                        b.startswith(f"event:{uid}:") for b in blocks
                    ) and complete and allocation_complete
                    else "INCOMPLETE_OR_CONTRADICTORY"
                ),
                "gross_loss_declared": event["gross_loss"],
                "prevented_loss_declared": event["prevented_loss"],
                "residual_loss_declared": event["residual_loss"],
                "source_authenticity_verified": False,
                "prevention_effect_verified": False,
                "transfer_contract_verified": False,
            }

    # Never present a favorable per-event numeric label when any linked
    # event/transfer/bearer declaration blocks the dossier.
    if blocks:
        for summary in summaries.values():
            summary["numeric_consistency"] = "INCOMPLETE_OR_CONTRADICTORY"

    frozen = {
        "schema_version": SCHEMA_VERSION,
        "project_id": payload["project_id"], "as_of": payload["as_of"],
        "currency": payload["currency"],
        "generation": sorted((dict(r, evidence_ids=sorted(r["evidence_ids"]))
                               for r in gen), key=lambda r: r["event_id"]),
        "allocation": sorted((dict(r, evidence_ids=sorted(r["evidence_ids"]))
                               for r in alloc), key=lambda r: (r["event_id"], r["bearer_id"])),
        "transfers": sorted((dict(r, evidence_ids=sorted(r["evidence_ids"]))
                              for r in transfers), key=lambda r: r["transfer_id"]),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "SHADOW",
        "status": "HOLD" if blocks else "GO_FOR_EXTERNAL_REVIEW",
        "blocks": sorted(set(blocks)),
        "project_id": payload["project_id"],
        "as_of": payload["as_of"],
        "currency": payload["currency"],
        "input_sha256": hashlib.sha256(canonical_bytes(frozen)).hexdigest(),
        "event_summaries": summaries,
        "evidence_authenticity": "NOT_ESTABLISHED",
        "loss_reduction_verified": False,
        "loss_allocation_verified": False,
        "ultimate_bearers_legally_verified": False,
        "actuarial_calibration": "NOT_PERFORMED",
        "financial_risk_transfer": "NOT_VERIFIED",
        "source_status": "PROPOSED_NOT_ADOPTED",
        "authoritative": False, "capital_admission": False,
        "insurance_binding": False, "underwriting_approval": False,
        "certification": False,
        "statement": "Declared loss and transfer arithmetic only; no validated risk reduction or allocation.",
    }
