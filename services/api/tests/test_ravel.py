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
)


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
