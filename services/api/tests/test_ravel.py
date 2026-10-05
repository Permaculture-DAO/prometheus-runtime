from app.ravel import (
    ScenarioLoss,
    CapitalLayer,
    ProtectionContract,
    allocate_waterfall,
    apply_transfers,
    expected_loss,
    expected_shortfall,
    rr_delta,
    shadow_state,
    aggregate_by_economic_group,
    urbc,
    RavelModelError,
    normalise_scenarios,
    risk_transfer_effectiveness,
)
import pytest


@pytest.mark.parametrize("probabilities", [[0.2, 0.3], [0.7, 0.7], [0.0], [1.2], [-0.2], [float("nan")], [float("inf")]])
def test_declared_probabilities_are_not_relative_weights(probabilities):
    scenarios = [ScenarioLoss(str(i), p, 10, 10) for i, p in enumerate(probabilities)]
    with pytest.raises(RavelModelError, match="probabilit"):
        expected_loss(scenarios)


def test_probability_roundoff_is_accepted_without_rescaling():
    scenarios = [ScenarioLoss("a", 0.1, 10, 10), ScenarioLoss("b", 0.2, 10, 10),
                 ScenarioLoss("c", 0.7000000000000001, 10, 10)]
    assert normalise_scenarios(scenarios) == scenarios


def test_declared_probability_sum_tolerance_boundary():
    near = [ScenarioLoss("a", 0.5, 10, 10), ScenarioLoss("b", 0.5 + 0.5e-9, 10, 10)]
    assert normalise_scenarios(near) == near
    beyond = [near[0], ScenarioLoss("b", 0.5 + 2e-9, 10, 10)]
    with pytest.raises(RavelModelError, match="sum to 1"):
        normalise_scenarios(beyond)


@pytest.mark.parametrize("field", ["baseline_scenarios", "regenerative_scenarios"])
def test_incomplete_probability_distribution_rejected_http(client, field):
    body = request_body()
    body[field][0]["probability"] = 0.5
    response = client.post("/v1/ravel/shadow", json=body)
    assert response.status_code == 422
    assert "sum to 1" in response.json()["detail"]


@pytest.mark.parametrize("after, expected", [(0, 1), (80, 0.2), (100, 0), (150, -0.5)])
def test_rte_preserves_adverse_risk_changes(after, expected):
    assert risk_transfer_effectiveness(before_metric=100, after_metric=after) == pytest.approx(expected)


def test_rte_rejects_zero_baseline_and_overflow():
    with pytest.raises(RavelModelError, match="undefined"):
        risk_transfer_effectiveness(before_metric=0, after_metric=1)
    with pytest.raises(RavelModelError, match="finite"):
        risk_transfer_effectiveness(before_metric=1e-308, after_metric=1e308)


def test_expected_loss_and_tail():
    scenarios = [
        ScenarioLoss("base", 0.9, 10, 10, 100),
        ScenarioLoss("tail", 0.1, 100, 80, 20),
    ]
    assert abs(expected_loss(scenarios) - 17.0) < 1e-9
    assert abs(expected_shortfall(scenarios, 0.95) - 80.0) < 1e-9


def test_rr_delta():
    assert abs(rr_delta(baseline_metric=100, regenerative_metric=80) - 0.2) < 1e-9


def test_waterfall_conserves_loss():
    layers = [
        CapitalLayer("equity", "sponsor", "first_loss", 0, 20, 0),
        CapitalLayer("junior", "junior_fund", "mezzanine", 20, 10, 1),
        CapitalLayer("senior", "senior_lender", "senior", 30, 40, 2),
    ]
    out = allocate_waterfall(55, layers)
    assert out["by_bearer"]["equity"] == 20
    assert out["by_bearer"]["junior"] == 10
    assert out["by_bearer"]["senior"] == 25
    assert out["conservation_error"] < 1e-9


def test_transfer_moves_but_does_not_erase_loss():
    before = {"senior": 25.0, "equity": 20.0}
    contracts = [
        ProtectionContract(
            "policy-1",
            provider_bearer_id="insurer",
            receiver_bearer_id="senior",
            attachment=5,
            limit=20,
            effectiveness=1,
            basis_factor=1,
            counterparty_factor=0.8,
            legal_factor=1,
        )
    ]
    out = apply_transfers(before, contracts)
    assert abs(sum(out["by_bearer"].values()) - sum(before.values())) < 1e-9
    assert out["by_bearer"]["insurer"] == 16.0
    assert out["by_bearer"]["senior"] == 9.0
    assert abs(out["transfers"][0]["rte_loss_share"] - (16.0 / 25.0)) < 1e-9
    assert out["transfers"][0]["receiver_loss_before"] == 25.0
    assert out["transfers"][0]["receiver_loss_after"] == 9.0


def test_affiliates_aggregate_before_urbc():
    losses = {"insurer_a": 20.0, "reinsurer_b": 10.0, "senior": 10.0}
    groups = aggregate_by_economic_group(
        losses,
        {"insurer_a": "group_x", "reinsurer_b": "group_x", "senior": "group_y"},
    )
    assert groups == {"group_x": 30.0, "group_y": 10.0}
    assert abs(urbc(groups) - (0.75**2 + 0.25**2)) < 1e-9


def test_vrrc_is_zero_in_shadow_state():
    scenarios = [ScenarioLoss("s1", 1.0, 10, 8, 95)]
    out = shadow_state(scenarios, initial_capital=100, impairment_threshold=0.1)
    assert out["vrrc"] == 0.0
    assert out["vrrc_status"] == "not_admitted"
    assert out["authority_boundary"] == "evaluation_not_certification"


def request_body():
    scenario = {"scenario_id": "TEST-s1", "probability": 1, "gross_loss": 100, "mitigated_loss": 100,
                "horizon": "1y", "model_version": "synthetic-v0.1", "evidence_refs": ["TEST-fixture"]}
    return {"baseline_scenarios": [scenario.copy()], "regenerative_scenarios": [scenario.copy()],
            "allocation_loss": 100, "capital_layers": [
                {"bearer_id": "A", "economic_group_id": "G", "layer_type": "equity", "attachment": 0, "limit": 50, "priority": 0},
                {"bearer_id": "B", "economic_group_id": "G", "layer_type": "senior", "attachment": 50, "limit": 50, "priority": 1}]}


def test_conflicting_common_control_is_rejected_http(client):
    body = request_body()
    body["bearer_to_group"] = {"B": "H"}
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422
    body["bearer_to_group"] = {"B": "G"}
    response = client.post("/v1/ravel/shadow", json=body)
    assert response.status_code == 200
    assert response.json()["allocation"]["urbc"] == 1


def test_self_transfer_rejected():
    with pytest.raises(RavelModelError, match="self-transfer"):
        apply_transfers({"A": 100}, [ProtectionContract("p", "A", "A", 0, 100, 1, 1, 1, 1)])


def test_reserved_bearer_rejected_http(client):
    body = request_body()
    body["capital_layers"] = [{"bearer_id": "UNALLOCATED_RESIDUAL", "economic_group_id": "G", "layer_type": "equity", "attachment": 0, "limit": 40, "priority": 0}]
    response = client.post("/v1/ravel/shadow", json=body)
    assert response.status_code == 422
    assert "reserved" in response.json()["detail"]


@pytest.mark.parametrize("factor", ["effectiveness", "basis_factor", "counterparty_factor", "legal_factor"])
def test_omitted_protection_factor_is_rejected_http(client, factor):
    body = request_body()
    contract = {"contract_id": "p", "provider_bearer_id": "C", "receiver_bearer_id": "A", "attachment": 0, "limit": 50,
                "effectiveness": 1, "basis_factor": 1, "counterparty_factor": 1, "legal_factor": 1}
    del contract[factor]
    body["transfer_contracts"] = [contract]
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422


def test_provenance_preserved_and_mismatched_horizons_rejected_http(client):
    body = request_body()
    body["regenerative_scenarios"][0]["horizon"] = "10y"
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422
    body["regenerative_scenarios"][0]["horizon"] = "1y"
    response = client.post("/v1/ravel/shadow", json=body)
    assert response.status_code == 200
    assert response.json()["scenario_provenance"]["baseline"][0]["evidence_refs"] == ["TEST-fixture"]
    assert response.json()["scenario_provenance"]["verification_status"] == "caller_declared_not_verified"


def test_missing_provider_group_or_unallocated_loss_blocks_urbc_http(client):
    body = request_body()
    body["transfer_contracts"] = [{"contract_id": "p", "provider_bearer_id": "C", "receiver_bearer_id": "A", "attachment": 0, "limit": 50,
                "effectiveness": 1, "basis_factor": 1, "counterparty_factor": 1, "legal_factor": 1}]
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422
    body["bearer_to_group"] = {"C": "G"}
    response = client.post("/v1/ravel/shadow", json=body)
    assert response.status_code == 200
    assert response.json()["allocation"]["urbc"] == 1
    body["allocation_loss"] = 200
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422


def test_unknown_scenario_fields_are_not_silently_ignored_http(client):
    body = request_body()
    body["baseline_scenarios"][0]["unrecognised_units"] = "USD"
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422


def test_reserved_protection_provider_rejected_http(client):
    body = request_body()
    body["transfer_contracts"] = [{"contract_id": "p", "provider_bearer_id": "UNALLOCATED_RESIDUAL", "receiver_bearer_id": "A", "attachment": 0, "limit": 50,
                "effectiveness": 1, "basis_factor": 1, "counterparty_factor": 1, "legal_factor": 1}]
    assert client.post("/v1/ravel/shadow", json=body).status_code == 422


def test_roundoff_does_not_manufacture_unknown_risk_bearer_http(client):
    body = request_body()
    body["allocation_loss"] = 0.9
    body["capital_layers"] = [{"bearer_id": str(i), "economic_group_id": "G", "layer_type": "synthetic", "attachment": a, "limit": l, "priority": i}
                             for i, (a, l) in enumerate([(0, 0.1), (0.1, 0.7), (0.8, 0.1)])]
    response = client.post("/v1/ravel/shadow", json=body)
    assert response.status_code == 200
    assert response.json()["allocation"]["urbc"] == 1


@pytest.mark.parametrize("reverse", [False, True])
def test_chained_transfers_cannot_depend_on_json_order(reverse):
    contracts = [ProtectionContract("p1", "B", "A", 0, 50, 1, 1, 1, 1),
                 ProtectionContract("p2", "C", "B", 0, 50, 1, 1, 1, 1)]
    if reverse:
        contracts.reverse()
    with pytest.raises(RavelModelError, match="chained protection"):
        apply_transfers({"A": 100}, contracts)
