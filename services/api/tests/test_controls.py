from dataclasses import replace
from datetime import datetime, timedelta, timezone
import itertools

import pytest
from pydantic import ValidationError

from app.controls import (GateState, EvidenceState, GateRecord, decision_digest,
                          evaluate_gates, transition)
from app.pru import canonical_bytes
from app.ravel_schemas import ShadowRiskRecord


# Independent literal expectations, not copied from the module's edge constants.
GATE_ALLOWED = {("UNSPECIFIED", "SPECIFIED"), ("SPECIFIED", "READY_FOR_TEST"),
    ("READY_FOR_TEST", "PASSED"), ("READY_FOR_TEST", "FAILED"),
    ("PASSED", "SUSPENDED"), ("PASSED", "EXPIRED"),
    ("FAILED", "READY_FOR_TEST"), ("SUSPENDED", "READY_FOR_TEST"),
    ("EXPIRED", "READY_FOR_TEST")}
EVIDENCE_ALLOWED = {("RAW", "IDENTIFIED"), ("IDENTIFIED", "PROVENANCE_BOUND"),
    ("PROVENANCE_BOUND", "QA_QC_CHECKED"), ("QA_QC_CHECKED", "REVIEWABLE"),
    ("REVIEWABLE", "VERIFIED_INDICATOR_CANDIDATE"),
    ("VERIFIED_INDICATOR_CANDIDATE", "ADMISSIBLE"),
    *((state, "REJECTED") for state in ("RAW", "IDENTIFIED", "PROVENANCE_BOUND",
        "QA_QC_CHECKED", "REVIEWABLE", "VERIFIED_INDICATOR_CANDIDATE"))}


@pytest.mark.parametrize("source,target", list(itertools.product(GateState, repeat=2)))
def test_all_gate_edges(source, target):
    kwargs = dict(proof_refs=("synthetic-proof",), decision_ref="synthetic-decision",
                  reason="synthetic reason")
    if (source.value, target.value) in GATE_ALLOWED:
        assert transition(source, target, **kwargs) is target
    else:
        with pytest.raises(ValueError, match="forbidden"):
            transition(source, target, **kwargs)


@pytest.mark.parametrize("source,target", list(itertools.product(EvidenceState, repeat=2)))
def test_all_evidence_edges(source, target):
    kwargs = dict(proof_refs=("synthetic-proof",), decision_ref="synthetic-decision",
                  reason="synthetic rejection")
    if (source.value, target.value) in EVIDENCE_ALLOWED:
        assert transition(source, target, **kwargs) is target
    else:
        with pytest.raises(ValueError, match="forbidden"):
            transition(source, target, **kwargs)


@pytest.mark.parametrize("source,target,kwargs", [
    (EvidenceState.RAW, EvidenceState.IDENTIFIED, {}),
    (EvidenceState.RAW, EvidenceState.IDENTIFIED, {"proof_refs": (" ",)}),
    (EvidenceState.RAW, EvidenceState.REJECTED, {"reason": " "}),
    (EvidenceState.VERIFIED_INDICATOR_CANDIDATE, EvidenceState.ADMISSIBLE,
        {"proof_refs": ("proof",)}),
    (GateState.READY_FOR_TEST, GateState.PASSED, {"proof_refs": ("proof",)}),
    ("GREEN", "PASSED", {"proof_refs": ("proof",)}),
    (EvidenceState.RAW, GateState.SPECIFIED, {"proof_refs": ("proof",)}),
])
def test_transition_requires_scoped_references_and_no_coercion(source, target, kwargs):
    with pytest.raises(ValueError):
        transition(source, target, **kwargs)


NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
EVIDENCE_HASH = "a" * 64


def gate(uid="mrv", **changes):
    return replace(GateRecord(uid, "synthetic-use-v1", GateState.PASSED,
        spec_ref="synthetic-spec-v1", decision_ref="decision:" + uid,
        issued_at=NOW - timedelta(hours=1), expires_at=NOW + timedelta(hours=1),
        evidence=(("synthetic-evidence", EVIDENCE_HASH),)), **changes)


def evaluate(records, **kwargs):
    defaults = dict(as_of=NOW, scope="synthetic-use-v1",
        evidence_hashes={"synthetic-evidence": EVIDENCE_HASH},
        evidence_states={"synthetic-evidence": EvidenceState.ADMISSIBLE},
        decision_hashes={g.decision_ref: decision_digest(g) for g in records})
    return evaluate_gates(tuple(records), **(defaults | kwargs))


def test_deterministic_snapshot_reordering_and_no_authority():
    upstream = gate()
    downstream = gate("ravel", prerequisites=("mrv",))
    original = (upstream, downstream)
    before = [g.snapshot() for g in original]
    result = evaluate(original)
    assert canonical_bytes(result) == canonical_bytes(evaluate(tuple(reversed(original))))
    assert [g.snapshot() for g in original] == before
    assert all(row["candidate_eligible"] for row in result["gates"].values())
    assert all(result[name] is False for name in ("authoritative", "capital_admission",
        "underwriting_approval", "certification", "creates_rights"))
    assert result["references_status"] == "caller_declared_not_authenticated"


def test_frozen_gate_decision_and_literal_golden_output():
    record = gate()
    frozen = "e3dc9c499adf0c85afd2d113188dafecc1dbdd321def9c1267d941aae39bb998"
    assert decision_digest(record) == frozen
    expected = {"method_version": "candidate-controls-v0.1",
        "as_of": "2026-10-06T12:00:00+00:00", "scope": "synthetic-use-v1",
        "gates": {"mrv": {"state": "PASSED", "candidate_eligible": True,
                            "reasons": [], "blocked_by": []}},
        "references_status": "caller_declared_not_authenticated",
        "authoritative": False, "capital_admission": False,
        "underwriting_approval": False, "certification": False, "creates_rights": False}
    assert canonical_bytes(evaluate((record,), decision_hashes={record.decision_ref: frozen})) == canonical_bytes(expected)
    mutated = replace(record, spec_ref="different-spec")
    result = evaluate((mutated,), decision_hashes={record.decision_ref: frozen})
    assert result["gates"]["mrv"]["reasons"] == ["decision_snapshot_mismatch"]


@pytest.mark.parametrize("state", [s for s in GateState if s is not GateState.PASSED])
def test_every_unpassed_upstream_blocks_downstream(state):
    result = evaluate((gate(state=state), gate("ravel", prerequisites=("mrv",))))
    assert not result["gates"]["mrv"]["candidate_eligible"]
    assert result["gates"]["ravel"]["blocked_by"] == ["mrv"]


@pytest.mark.parametrize("change,reason", [
    ({"scope": "different-use"}, "scope_mismatch"),
    ({"spec_ref": None}, "missing_specification"),
    ({"decision_ref": None}, "missing_decision"),
    ({"evidence": ()}, "missing_evidence"),
    ({"issued_at": None}, "missing_validity_interval"),
    ({"expires_at": None}, "missing_validity_interval"),
    ({"issued_at": NOW + timedelta(minutes=1)}, "future_decision"),
    ({"expires_at": NOW}, "expired_decision"),
])
def test_missing_future_expired_and_wrong_scope_fail_closed(change, reason):
    result = evaluate((gate(**change), gate("ravel", prerequisites=("mrv",))))
    assert reason in result["gates"]["mrv"]["reasons"]
    assert result["gates"]["ravel"]["blocked_by"] == ["mrv"]


def test_exact_expiry_and_revocation_without_mutation():
    record = gate()
    result = evaluate((record,), as_of=record.expires_at)
    assert result["gates"]["mrv"]["state"] == "EXPIRED"
    assert record.state is GateState.PASSED
    result = evaluate((record,), revoked_decisions=frozenset({record.decision_ref}))
    assert result["gates"]["mrv"]["reasons"] == ["revoked_decision"]


def test_forged_pass_hash_mutation_and_catalog_missing():
    original = gate(state=GateState.FAILED)
    forged = replace(original, state=GateState.PASSED)
    result = evaluate((forged,), decision_hashes={original.decision_ref: decision_digest(original)})
    assert result["gates"]["mrv"]["reasons"] == ["decision_snapshot_mismatch"]
    assert not evaluate((gate(),), decision_hashes={})["gates"]["mrv"]["candidate_eligible"]
    for catalog in ({}, {"synthetic-evidence": "b" * 64}):
        result = evaluate((gate(),), evidence_hashes=catalog)
        assert result["gates"]["mrv"]["reasons"] == ["evidence_hash_mismatch"]


@pytest.mark.parametrize("records", [
    (), (gate(), gate()), (gate(prerequisites=("unknown",)),),
    (gate(prerequisites=("mrv",)),),
    (gate(prerequisites=("b",)), gate("b", prerequisites=("mrv",))),
    (gate(prerequisites=("b", "b")), gate("b")),
    (gate(issued_at=NOW.replace(tzinfo=None)),),
    (gate(expires_at=NOW - timedelta(hours=2)),),
    (gate(evidence=(("e", "not-a-sha"),)),),
    (gate(evidence=(("e", EVIDENCE_HASH), ("e", EVIDENCE_HASH))),),
])
def test_invalid_graphs_and_dates_are_rejected(records):
    with pytest.raises(ValueError):
        evaluate(records)


def test_timezones_are_normalized_and_explicit():
    offset = timezone(timedelta(hours=2))
    assert canonical_bytes(evaluate((gate(),))) == canonical_bytes(
        evaluate((gate(),), as_of=NOW.astimezone(offset)))
    with pytest.raises(ValueError):
        evaluate((gate(),), as_of=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("states", [{}, {"synthetic-evidence": EvidenceState.REJECTED},
                                   {"synthetic-evidence": "ADMISSIBLE"}])
def test_rejected_unknown_untyped_evidence_blocks_even_with_matching_hash(states):
    result = evaluate((gate(), gate("ravel", prerequisites=("mrv",))), evidence_states=states)
    assert "evidence_state_unusable" in result["gates"]["mrv"]["reasons"]
    assert result["gates"]["ravel"]["blocked_by"] == ["mrv"]


RISK = dict(risk_uid="TEST-risk", subject_uid="TEST-site", hazard="declared drought",
    exposure="synthetic crop", vulnerability="uncalibrated", financial_state="unknown",
    model_version="v0.1-synthetic", evidence_refs=["synthetic-not-field-evidence"],
    ultimate_bearers=["declared-not-legally-verified"], assumptions=["synthetic only"],
    missing_data_statement="No site calibration, contract or underwriting decision")


def test_risk_envelope_preserves_unknown_and_policy_zero():
    record = ShadowRiskRecord(**RISK)
    assert record.financial_state == "unknown"
    assert record.vrrc == 0 and record.vrrc_status == "not_admitted"
    assert record.capital_admission is False and record.underwriting_approval is False


@pytest.mark.parametrize("change", [{"vrrc": 1.0}, {"vrrc": True}, {"vrrc": "0"},
    {"underwriting_approval": True}, {"capital_admission": 0}, {"capital_admission": "false"},
    {"authority": "certified"}, {"mode": "production"}, {"rating": "AAA-R"},
    {"human_state_weight": 1}, {"missing_data_statement": " "},
    {"ultimate_bearers": []}, {"evidence_refs": [" "]}])
def test_risk_envelope_rejects_authority_coercion_and_blank_fields(change):
    with pytest.raises(ValidationError):
        ShadowRiskRecord(**(RISK | change))
