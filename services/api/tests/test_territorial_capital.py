import copy
import json
import pytest
from app.territorial_capital import review_territorial_proposal, TerritorialInputError


def complete_packet():
    return {
      "profile_id":"CIV-TOPOS-001-synthetic",
      "territory":{"site_id":"synthetic-01", "boundary_ref":"e-geo-01", "operator":"operator-01"},
      "rights":{"land_control_evidence_ref":"e-title", "water_access_review_ref":"e-water"},
      "evidence":{"baseline_refs":["e-soil"], "source_refs":["e-field"], "provenance_method":"signed", "comparator_design":"matched-plot", "mrv_review_ref":"review-mrv", "causal_review_ref":"review-causal"},
      "method":{"version":"0.1", "scenario_design":"A/B"},
      "risk":{"risk_ids":["risk-drought"], "ultimate_bearers":["site-sponsor", "community"], "loss_generation_ledger_ref":"e-loss-01", "risk_allocation_ledger_ref":"e-allocation-01"},
      "governance":{"design_provider_id":"agency-01", "independent_reviewer_id":"reviewer-02", "consent_ref":"e-consent", "conflict_register_ref":"e-conflicts"},
      "finance":{"payer_id":"payer", "base_case_ref":"cashflow-01", "liquidity_stress_ref":"stress-01", "base_case_assumptions":{}},
      "capital":{"instrument_type":"none"},
      "simplicity_comparator":{"protocol_ref":"a-b-test", "cost_baseline_ref":"bench-01", "kill_conditions":["no benefit"]}
    }


def test_complete_packet_is_not_approval():
    out=review_territorial_proposal(complete_packet())
    assert out["evaluation"] == "REVIEW_PACKET_PRESENT_ONLY"
    assert not out["capital_authorised"] and not out["ecological_certified"]
    assert set(v["status"] for v in out["gate_results"].values()) == {"REVIEW_REQUIRED", "NOT_APPLICABLE"}


def test_missingness_fail_closed():
    packet=complete_packet()
    packet["rights"]["land_control_evidence_ref"]=""
    out=review_territorial_proposal(packet)
    assert out["gate_results"]["G0_SITE_RIGHTS"]["status"]=="HOLD"
    assert "G0_SITE_RIGHTS" in out["blocking_gates"]


def test_conflict_of_interest_fails():
    packet=complete_packet()
    packet["governance"]["independent_reviewer_id"]="agency-01"
    assert review_territorial_proposal(packet)["gate_results"]["G4_INDEPENDENCE_GOVERNANCE"]["status"]=="FAIL"


def test_no_speculative_tokens_in_base_case():
    packet=complete_packet()
    packet["finance"]["base_case_assumptions"]={"token_appreciation":True}
    assert review_territorial_proposal(packet)["gate_results"]["G5_BASE_ECONOMICS"]["status"]=="FAIL"


def test_public_retail_issuer_not_assumed():
    packet=complete_packet()
    packet["capital"]["instrument_type"]="public_retail_debt"
    assert review_territorial_proposal(packet)["gate_results"]["G6_LEGAL_CAPITAL"]["status"]=="HOLD"


def test_deterministic_replay_and_input_unchanged():
    packet=complete_packet()
    frozen=json.dumps(packet,sort_keys=True)
    assert review_territorial_proposal(packet)==review_territorial_proposal(copy.deepcopy(packet))
    assert frozen==json.dumps(packet,sort_keys=True)


def test_invalid_nonfinite_or_unknown_instrument():
    packet=complete_packet()
    packet["x"]=float("nan")
    with pytest.raises(TerritorialInputError): review_territorial_proposal(packet)
    packet=complete_packet()
    packet["capital"]["instrument_type"]="unregulated_token_sale"
    with pytest.raises(TerritorialInputError): review_territorial_proposal(packet)
