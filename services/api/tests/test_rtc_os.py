"""Synthetic RTC-OS acceptance/adversarial vectors; no real site claims."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.pru import canonical_bytes
from app.rtc_os import compile_dossier, replay_dossier, RTCInput, VERSION
ROOT = Path(__file__).resolve().parents[3]
KNOWN = frozenset({"prometheus.ai.assistive_non_authoritative"})


def packet():
    return json.loads((ROOT / "contracts/fixtures/rtc_os.synthetic.json").read_text(encoding="utf-8"))


def evaluate(p=None):
    return compile_dossier(p or packet(), known_claim_uids=KNOWN)


def test_synthetic_packet_never_creates_authority():
    out = evaluate()
    assert out["dataset"] == "SYNTHETIC_NON_CAPITAL_FACING"
    assert out["capital_readiness"] == "HOLD"
    assert out["risk_state"] == "NR" and out["ravel_shadow"] is None
    for flag in ("authoritative", "certification", "capital_authorised", "creates_rights",
                 "material_gate_effects_allowed", "production_admitted", "publication_authorised"):
        assert out[flag] is False
    assert out["source_custody"].startswith("PROPOSED_NOT_ADOPTED")
    assert out["ultimate_bearers"] == ["synthetic-community", "synthetic-sponsor"]


@pytest.mark.parametrize("kind", ["LAND", "WATER", "DATA", "CONSENT", "STEWARDSHIP"])
def test_missing_rights_hold(kind):
    p = packet()
    p["rights"] = [r for r in p["rights"] if r["kind"] != kind]
    assert "rights_unresolved:" + kind in evaluate(p)["hold_reasons"]


def test_no_baseline_blocks_improvement():
    p = packet()
    p["site"]["baseline_evidence_uids"] = []
    p["claims"][0]["kind"] = "IMPROVEMENT"
    assert evaluate(p)["claims"][0]["state"] == "NOT_ADMISSIBLE"


def test_hash_does_not_validate_measurement():
    p = packet()
    p["evidence"][0]["measurement_status"] = "INVALID"
    assert evaluate(p)["claims"][0]["state"] == "NOT_ADMISSIBLE"


def test_unknown_insurance_has_no_assumed_recovery():
    p = packet()
    p["risk_allocation"][0]["treatment"] = "TRANSFERRED"
    out = evaluate(p)
    assert out["risk_state"] == "NR"
    assert "insurance_recoverability_unknown" in out["hold_reasons"]
    assert out["risk_allocation_ledger"][0]["recoverability"] == "UNKNOWN"


def test_externalised_loss_remains_visible_and_conserved():
    out = evaluate()
    assert out["loss_generation_ledger"][0]["mitigated_loss"] == "80"
    assert out["risk_allocation_ledger"][1]["bearer_id"] == "synthetic-community"
    p = packet()
    p["risk_allocation"][1]["amount"] = "0"
    assert "loss_allocation_not_conserved" in evaluate(p)["reject_reasons"]


def test_unknown_loss_is_not_zero():
    p = packet()
    p["loss_generation"][0]["mitigated_loss"] = None
    out = evaluate(p)
    assert out["loss_generation_ledger"][0]["mitigated_loss"] is None
    assert out["risk_state"] == "NR"


@pytest.mark.parametrize("scale,state", [("E","REJECT"),("P","HOLD"),("B","EXPLORATORY"),("L","UNKNOWN")])
def test_scales_cannot_compensate_each_other(scale, state):
    p = packet()
    p["scales"][scale] = state
    assert evaluate(p)["capital_readiness"] in ("HOLD", "REJECT")


def test_bioregional_transfer_without_comparator_is_exploratory():
    p = packet()
    p["territory"]["bioregions"][0]["applicability"] = "EXPLORATORY"
    assert "bioregional_transfer_exploratory_or_conflicting" in evaluate(p)["hold_reasons"]


def test_material_scale_conflict_preserves_dissent():
    p = packet()
    p["scale_conflicts"] = [{"conflict_id":"conflict-01","source_ids":["synthetic-local","synthetic-global"],
        "affected_claim_uids":[p["claims"][0]["claim_uid"]],"material":True,"reason":"local contradicts reference class",
        "reviewer_id":None,"dissent":"retain local observation","resolved":False}]
    out = evaluate(p)
    assert "material_scale_conflict" in out["hold_reasons"]
    assert out["scale_conflicts"][0]["dissent"] == "retain local observation"


@pytest.mark.parametrize("field", ["reviewer_id", "economic_group_id"])
def test_self_review_and_common_control_rejected(field):
    p = packet()
    p["reviewer"][field] = p["reviewer"]["design_provider_id" if field == "reviewer_id" else "provider_economic_group_id"]
    assert "reviewer_conflict_of_interest" in evaluate(p)["reject_reasons"]


def test_unregistered_claim_not_admissible():
    assert compile_dossier(packet())["claims"][0]["state"] == "NOT_ADMISSIBLE"


@pytest.mark.parametrize("mode", ["P","H","Q"])
def test_non_d_outputs_do_not_change_gates(mode):
    p = packet()
    p["compute_mode"] = mode
    out = evaluate(p)
    assert "compute_verification_pending" in out["hold_reasons"]
    assert out["material_gate_effects_allowed"] is False


def test_no_action_and_lean_alternative_required():
    p = packet()
    p["alternatives"] = p["alternatives"][2:]
    assert "alternatives_incomplete" in evaluate(p)["hold_reasons"]


def test_source_drift_fails_closed():
    p = packet()
    p["sources"][1]["sha256"] = "b" * 64
    assert evaluate(p)["capital_readiness"] == "REJECT"


def test_partner_matrix_has_exact_forty_unknowns_not_a_score():
    out = evaluate()
    assert len(out["external_partner_checks"]) == 40
    assert all(v["state"] == "UNKNOWN" for v in out["external_partner_checks"].values())
    assert out["topos_partnership"] == "UNKNOWN"


def test_unbound_partner_verification_rejected():
    p = packet()
    p["partner_checks"] = [{"check_id":"T01","state":"THIRD_PARTY_VERIFIED","evidence_uids":[],
                           "reviewer_ref":None}]
    with pytest.raises(ValueError):
        evaluate(p)


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(capital_authorised=True),
    lambda p: p.update(dataset="LIVE_CAPITAL_FACING"),
    lambda p: p["site"].update(site_id="   "),
    lambda p: p["sources"].append(deepcopy(p["sources"][0])),
    lambda p: p["territory"].update(territory_id="another-site"),
    lambda p: p.update(revision=True),
    lambda p: p["loss_generation"][0].update(gross_loss=float("nan")),
])
def test_strict_types_missingness_and_authority_injection(mutate):
    p = packet()
    mutate(p)
    with pytest.raises((ValidationError, ValueError)):
        evaluate(p)


def test_expiry_and_revocation_are_not_silently_accepted():
    p = packet()
    p["as_of"] = "2028-01-01T00:00:00Z"
    assert "dossier_expired" in evaluate(p)["hold_reasons"]


def test_replay_is_exact_and_tamper_fails():
    p = packet()
    frozen = canonical_bytes(p)
    out = evaluate(p)
    envelope = {"engine":VERSION, "input":p, "input_sha256":hashlib.sha256(frozen).hexdigest(),
                "output_sha256":hashlib.sha256(canonical_bytes(out)).hexdigest()}
    assert replay_dossier(envelope, known_claim_uids=KNOWN) == canonical_bytes(out)
    assert canonical_bytes(p) == frozen and evaluate(deepcopy(p)) == out
    envelope["input"]["revision"] = 2
    with pytest.raises(ValueError, match="input hash"):
        replay_dossier(envelope, known_claim_uids=KNOWN)


def test_generated_schema_matches_implementation_and_fixture():
    import jsonschema
    schema = json.loads((ROOT / "contracts/rtc_os.dossier.schema.json").read_text())
    assert schema == RTCInput.model_json_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(packet(), schema)


def gates_packet():
    from app.controls import GateRecord, GateState, decision_digest
    from datetime import datetime
    p = packet()
    p["gate_declarations"] = [{"gate_uid":f"prometheus.runtime.G{i}@candidate-v0.1", "state":"PASSED",
        "spec_ref":f"synthetic-spec-{i}", "decision_ref":f"synthetic-decision-{i}",
        "issued_at":"2026-10-01T00:00:00Z", "expires_at":"2027-01-01T00:00:00Z",
        "evidence_uids":["synthetic-baseline"],
        "prerequisites":[] if i == 0 else [f"prometheus.runtime.G{i-1}@candidate-v0.1"]} for i in range(8)]
    for g in p["gate_declarations"]:
        record = GateRecord(g["gate_uid"], p["site"]["site_id"], GateState.PASSED, g["spec_ref"],
            g["decision_ref"], datetime.fromisoformat(g["issued_at"].replace("Z","+00:00")),
            datetime.fromisoformat(g["expires_at"].replace("Z","+00:00")),
            (("synthetic-baseline", "a"*64),), tuple(g["prerequisites"]))
        p["decision_hashes"][g["decision_ref"]] = decision_digest(record)
    return p


def test_eligible_declarations_do_not_adopt_source_or_authorise_capital():
    out = evaluate(gates_packet())
    assert all(g["candidate_eligible"] for g in out["runtime_gate_declarations"]["gates"].values())
    assert out["capital_readiness"] == "HOLD" and not out["capital_authorised"]
    assert out["source_conflicts"] and not out["gate_taxonomy"]["ordinal_crosswalk_authorised"]


@pytest.mark.parametrize("uid", ["G0", "prometheus.rtc.G0@0.1", "prometheus.runtime.G0@ACTIVE"])
def test_foreign_gate_taxonomy_cannot_inherit_pass(uid):
    p = gates_packet()
    p["gate_declarations"][0]["gate_uid"] = uid
    with pytest.raises(ValidationError):
        evaluate(p)


def test_unresolved_gate_reference_is_not_silently_dropped():
    p = gates_packet()
    p["gate_declarations"][0]["evidence_uids"].append("not-in-spine")
    with pytest.raises(ValueError, match="unresolved gate evidence"):
        evaluate(p)


def test_revoked_gate_decision_propagates_through_dependencies():
    p = gates_packet()
    p["revoked_decisions"] = ["synthetic-decision-0"]
    gates = evaluate(p)["runtime_gate_declarations"]["gates"]
    assert all(not g["candidate_eligible"] for g in gates.values())
    assert "revoked_decision" in gates["prometheus.runtime.G0@candidate-v0.1"]["reasons"]


def test_invalid_baseline_cannot_be_hidden_by_other_evidence():
    p = packet()
    p["claims"][0]["kind"] = "IMPROVEMENT"
    valid = deepcopy(p["evidence"][0]); valid["evidence_uid"] = "valid-new"
    p["evidence"].append(valid)
    p["claims"][0]["evidence_uids"] = ["valid-new"]
    p["evidence"][0]["measurement_status"] = "INVALID"
    out = evaluate(p)
    assert out["claims"][0]["state"] == "NOT_ADMISSIBLE"
    assert "baseline_measurement_not_admissible_declaration" in out["hold_reasons"]


def test_token_claim_is_excluded_even_if_caller_registers_it():
    p = packet(); p["claims"][0]["claim_uid"] = "prometheus.trbk.consumptive_access_utility"
    out = compile_dossier(p, known_claim_uids=frozenset({p["claims"][0]["claim_uid"]}))
    assert out["claims"][0]["state"] == "NOT_ADMISSIBLE"


def test_foreign_site_and_revoked_water_rights_reject():
    p = packet(); p["proposal"]["territory"]["site_id"] = "other-site"
    assert "screening_site_mismatch" in evaluate(p)["reject_reasons"]
    p = packet(); p["rights"][1]["status"] = "REVOKED"
    assert "rights_adverse:WATER" in evaluate(p)["reject_reasons"]


def test_baseline_metadata_raw_cannot_pass_gate_as_admissible():
    p = gates_packet(); p["evidence"][0]["state"] = "RAW"
    out = evaluate(p)
    assert "gate_evidence_not_admissible_declaration" in out["hold_reasons"]
    assert all(not g["candidate_eligible"] for g in out["runtime_gate_declarations"]["gates"].values())


def test_removing_prerequisites_cannot_bypass_composition_revocation():
    from app.controls import GateRecord, GateState, decision_digest
    from datetime import datetime
    p = gates_packet()
    for g in p["gate_declarations"]:
        g["prerequisites"] = []
        record = GateRecord(g["gate_uid"], p["site"]["site_id"], GateState.PASSED, g["spec_ref"],
            g["decision_ref"], datetime.fromisoformat(g["issued_at"].replace("Z","+00:00")),
            datetime.fromisoformat(g["expires_at"].replace("Z","+00:00")), (("synthetic-baseline","a"*64),), ())
        p["decision_hashes"][g["decision_ref"]] = decision_digest(record)
    p["revoked_decisions"] = ["synthetic-decision-0"]
    assert all(not g["candidate_eligible"] for g in evaluate(p)["runtime_gate_declarations"]["gates"].values())


def test_documented_insurance_cannot_override_adverse_duplicate():
    p = packet()
    p["risk_allocation"][0].update(treatment="TRANSFERRED", contract_ref="policy-1", recoverability="DOCUMENTED")
    r = {"kind":"INSURANCE", "holder_id":"synthetic-insurer", "jurisdiction":"synthetic-jurisdiction",
         "status":"DOCUMENTED", "instrument_ref":"policy-1", "review_ref":"synthetic-review"}
    p["rights"].extend([r, dict(r, status="REVOKED")])
    assert "insurance_right_adverse" in evaluate(p)["reject_reasons"]
    p["rights"][-1].update(status="DOCUMENTED", jurisdiction="other-jurisdiction")
    assert "insurance_jurisdiction_mismatch" in evaluate(p)["reject_reasons"]


def test_unknown_allocation_cannot_hide_known_loss_contradiction():
    p = packet(); p["risk_allocation"][0]["amount"] = None
    p["loss_generation"][0]["mitigated_loss"] = "200"
    assert "mitigation_exceeds_gross" in evaluate(p)["reject_reasons"]


def quant_packet():
    p = packet(); e = p["loss_generation"][0]
    p["ravel_request"] = {"horizon":e["horizon"], "scenarios":[{"event_id":e["event_id"],
        "probability":1.0, "evidence_uids":e["evidence_uids"]}], "alpha_values":[0.5]}
    return p


def test_quantitative_contract_consumes_alphas_and_binds_provenance():
    p = quant_packet(); out = evaluate(p)
    assert set(out["ravel_shadow"]["var"]) == {"0.5000"}
    assert out["risk_state"] == "NR" and not out["capital_authorised"]
    for mutate in [lambda q: q["ravel_request"].update(horizon="unrelated"),
                   lambda q: q["ravel_request"]["scenarios"][0].update(evidence_uids=["unknown"]),
                   lambda q: q["ravel_request"].update(initial_capital=100),
                   lambda q: q["ravel_request"]["scenarios"][0].update(probability=0.2)]:
        q = quant_packet(); mutate(q)
        with pytest.raises(ValueError):
            evaluate(q)


def test_declined_exact_token_identity_cannot_be_caller_registered():
    p = packet(); uid = "prometheus.token.access_utility_candidate"
    p["claims"][0]["claim_uid"] = uid
    assert compile_dossier(p, known_claim_uids=frozenset({uid}))["claims"][0]["state"] == "NOT_ADMISSIBLE"


def test_unknown_gross_loss_does_not_hide_known_allocation_mismatch():
    p = packet(); p["loss_generation"][0]["gross_loss"] = None
    p["risk_allocation"][0]["amount"] = "60"
    assert "loss_allocation_not_conserved" in evaluate(p)["reject_reasons"]


def test_quantitative_mixed_currency_aggregation_refused():
    p = quant_packet(); original = p["loss_generation"][0]
    p["loss_generation"].append(dict(original, event_id="event-usd", currency="USD"))
    p["risk_allocation"].extend(dict(a, event_id="event-usd", currency="USD") for a in list(p["risk_allocation"]))
    p["ravel_request"]["scenarios"][0]["probability"] = 0.5
    p["ravel_request"]["scenarios"].append({"event_id":"event-usd", "probability":0.5,
                                          "evidence_uids":original["evidence_uids"]})
    with pytest.raises(ValueError, match="one currency"):
        evaluate(p)


def test_quant_wire_decimal_strings_and_currency_are_explicit():
    out = evaluate(quant_packet())
    assert out["ravel_shadow"]["expected_loss"] == "80.0"
    assert out["ravel_shadow"]["currency"] == "EUR"
    expected = json.loads((ROOT / "contracts/fixtures/rtc_os.quant.synthetic.expected.json").read_text())
    assert canonical_bytes(out) == canonical_bytes(expected)


def test_golden_synthetic_output_exact_and_complete():
    expected = json.loads((ROOT / "contracts/fixtures/rtc_os.synthetic.expected.json").read_text())
    assert canonical_bytes(evaluate()) == canonical_bytes(expected)
    assert expected["evidence_spine"] and expected["alternatives"]
