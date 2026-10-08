"""Pure candidate controls; references/decisions are caller-declared, not authenticated.

Derived from canon candidate 0857425, RAVEL_FORMAL_SPEC_v0.1 section 13.
No routes, persistence, clock reads, governance actions or financial admission.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import re
from typing import Mapping

from .pru import canonical_bytes


class GateState(str, Enum):
    UNSPECIFIED = "UNSPECIFIED"
    SPECIFIED = "SPECIFIED"
    READY_FOR_TEST = "READY_FOR_TEST"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class EvidenceState(str, Enum):
    RAW = "RAW"
    IDENTIFIED = "IDENTIFIED"
    PROVENANCE_BOUND = "PROVENANCE_BOUND"
    QA_QC_CHECKED = "QA_QC_CHECKED"
    REVIEWABLE = "REVIEWABLE"
    VERIFIED_INDICATOR_CANDIDATE = "VERIFIED_INDICATOR_CANDIDATE"
    ADMISSIBLE = "ADMISSIBLE"
    REJECTED = "REJECTED"


GATE_EDGES = frozenset({
    (GateState.UNSPECIFIED, GateState.SPECIFIED),
    (GateState.SPECIFIED, GateState.READY_FOR_TEST),
    (GateState.READY_FOR_TEST, GateState.PASSED),
    (GateState.READY_FOR_TEST, GateState.FAILED),
    (GateState.PASSED, GateState.SUSPENDED),
    (GateState.PASSED, GateState.EXPIRED),
    *((state, GateState.READY_FOR_TEST) for state in
      (GateState.FAILED, GateState.SUSPENDED, GateState.EXPIRED)),
})
_LIFECYCLE = tuple(EvidenceState)[:-1]
EVIDENCE_EDGES = frozenset(zip(_LIFECYCLE, _LIFECYCLE[1:])) | frozenset(
    (state, EvidenceState.REJECTED) for state in _LIFECYCLE[:-1])


def _text(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


def transition(source, target, *, proof_refs: tuple[str, ...] = (),
               decision_ref: str | None = None, reason: str | None = None):
    """Validate an edge only. Caller retains the old record and appends a new one."""
    if type(source) is GateState and type(target) is GateState:
        edges = GATE_EDGES
        decision_required = target in (GateState.PASSED, GateState.FAILED)
        rejection = target in (GateState.FAILED, GateState.SUSPENDED, GateState.EXPIRED)
    elif type(source) is EvidenceState and type(target) is EvidenceState:
        edges = EVIDENCE_EDGES
        decision_required = target is EvidenceState.ADMISSIBLE
        rejection = target is EvidenceState.REJECTED
    else:
        raise ValueError("typed lifecycle states required; no traffic-light coercion")
    if (source, target) not in edges:
        raise ValueError("forbidden transition")
    if rejection:
        if not _text(reason):
            raise ValueError("reason required")
    elif not proof_refs or not all(_text(ref) for ref in proof_refs):
        raise ValueError("proof references required")
    if decision_required and not _text(decision_ref):
        raise ValueError("decision reference required")
    return target


def _utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class GateRecord:
    gate_uid: str
    scope: str
    state: GateState
    spec_ref: str | None = None
    decision_ref: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    evidence: tuple[tuple[str, str], ...] = ()
    prerequisites: tuple[str, ...] = ()

    def snapshot(self) -> dict:
        if not _text(self.gate_uid) or not _text(self.scope) or type(self.state) is not GateState:
            raise ValueError("gate UID, scope and typed state required")
        if len(set(self.prerequisites)) != len(self.prerequisites):
            raise ValueError("duplicate prerequisite")
        if any(not _text(uid) for uid in self.prerequisites):
            raise ValueError("invalid prerequisite")
        if len({uid for uid, _ in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate evidence UID")
        if any(not _text(uid) or not isinstance(sha, str) or
               re.fullmatch(r"[0-9a-f]{64}", sha) is None for uid, sha in self.evidence):
            raise ValueError("evidence UID and lowercase SHA256 required")
        issued = _utc(self.issued_at) if self.issued_at is not None else None
        expiry = _utc(self.expires_at) if self.expires_at is not None else None
        if issued and expiry and self.expires_at <= self.issued_at:
            raise ValueError("expiry must be after issuance")
        return {"gate_uid": self.gate_uid, "scope": self.scope, "state": self.state.value,
                "spec_ref": self.spec_ref, "decision_ref": self.decision_ref,
                "issued_at": issued, "expires_at": expiry,
                "evidence": sorted(self.evidence), "prerequisites": sorted(self.prerequisites)}


def decision_digest(record: GateRecord) -> str:
    """Integrity binding of the declared decision; NOT its signature or authenticity."""
    return hashlib.sha256(canonical_bytes(record.snapshot())).hexdigest()


def evaluate_gates(records: tuple[GateRecord, ...], *, as_of: datetime, scope: str,
                   evidence_hashes: Mapping[str, str],
                   evidence_states: Mapping[str, EvidenceState],
                   decision_hashes: Mapping[str, str],
                   revoked_decisions: frozenset[str] = frozenset()) -> dict:
    """Re-evaluate a frozen declaration snapshot without changing any record.

    The catalogs are supplied by the caller too. Matching them gives integrity
    consistency only, never reviewer qualification, custody or independent truth.
    """
    as_of_text = _utc(as_of)
    if not _text(scope) or not records or len(records) > 1000:
        raise ValueError("nonempty scope and 1..1000 records required")
    by_uid = {record.gate_uid: record for record in records}
    if len(by_uid) != len(records):
        raise ValueError("duplicate gate UID")
    for record in records:
        record.snapshot()
        if any(uid not in by_uid for uid in record.prerequisites):
            raise ValueError("unknown prerequisite")
    # Iterative topological sort avoids input-order sensitivity and recursive limits.
    pending = set(by_uid)
    results = {}
    while pending:
        ready = sorted(uid for uid in pending if all(dep in results for dep in by_uid[uid].prerequisites))
        if not ready:
            raise ValueError("cyclic gate dependencies")
        for uid in ready:
            record = by_uid[uid]
            reasons = []
            state = record.state.value
            if record.state is not GateState.PASSED:
                reasons.append("state_not_passed")
            if record.scope != scope:
                reasons.append("scope_mismatch")
            if not _text(record.spec_ref):
                reasons.append("missing_specification")
            if not _text(record.decision_ref):
                reasons.append("missing_decision")
            elif record.decision_ref in revoked_decisions:
                reasons.append("revoked_decision")
            elif decision_hashes.get(record.decision_ref) != decision_digest(record):
                reasons.append("decision_snapshot_mismatch")
            if record.issued_at is None or record.expires_at is None:
                reasons.append("missing_validity_interval")
            else:
                if record.issued_at > as_of:
                    reasons.append("future_decision")
                if as_of >= record.expires_at:
                    reasons.append("expired_decision")
                    if record.state is GateState.PASSED:
                        state = GateState.EXPIRED.value
            if not record.evidence:
                reasons.append("missing_evidence")
            elif any(evidence_hashes.get(ref) != sha for ref, sha in record.evidence):
                reasons.append("evidence_hash_mismatch")
            if any(type(evidence_states.get(ref)) is not EvidenceState or
                   evidence_states[ref] is EvidenceState.REJECTED for ref, _ in record.evidence):
                reasons.append("evidence_state_unusable")
            blocked_by = sorted(dep for dep in record.prerequisites
                                if not results[dep]["candidate_eligible"])
            if blocked_by:
                reasons.append("prerequisite_not_eligible")
            results[uid] = {"state": state, "candidate_eligible": not reasons,
                            "reasons": sorted(reasons), "blocked_by": blocked_by}
            pending.remove(uid)
    return {"method_version": "candidate-controls-v0.1", "as_of": as_of_text,
            "scope": scope, "gates": dict(sorted(results.items())),
            "references_status": "caller_declared_not_authenticated",
            "authoritative": False, "capital_admission": False,
            "underwriting_approval": False, "certification": False,
            "creates_rights": False}
