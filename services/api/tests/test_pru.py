import copy
from decimal import localcontext
import pytest
from app.pru import canonical_bytes, dry_run, replay


INPUT = {"v_base": "100", "legal_gate": "1", "mrv_gate": "1",
         "u_max": "0.9", "g_z": "1", "conf_total": "0.8"}
GOLDEN = {"method_version": "pru-shadow-zero-uplift-v0.1",
          "status": "synthetic_dry_run", "shadow_value": "80",
          "unknown_inputs": [], "zero_condition_flags": [],
          "u_max_effective": "0", "capital_value": "0",
          "capital_value_status": "policy_not_admitted_not_a_measurement",
          "authoritative": False, "certification": False, "creates_rights": False}


@pytest.mark.parametrize("field", ["v_base", "legal_gate", "mrv_gate", "conf_total"])
def test_controlling_zero_conditions(field):
    result = dry_run({**INPUT, field: "0"})
    assert result["shadow_value"] == "0"
    assert result["zero_condition_flags"] == [field]
    assert result["capital_value"] == "0"


@pytest.mark.parametrize("field", list(INPUT))
def test_unknown_is_not_an_observed_zero(field):
    result = dry_run({**INPUT, field: None})
    assert result["shadow_value"] is None
    assert result["status"] == "unknown"
    assert result["unknown_inputs"] == [field]
    assert field not in result["zero_condition_flags"]


@pytest.mark.parametrize("field, value", [("v_base", "-1"), ("v_base", "NaN"),
    ("v_base", "Infinity"), ("conf_total", "1.1"), ("g_z", "1.1"),
    ("legal_gate", "0.5"), ("mrv_gate", True), ("u_max", "-0.1")])
def test_invalid_inputs_fail_closed(field, value):
    with pytest.raises(ValueError):
        dry_run({**INPUT, field: value})


def test_no_silent_default_or_human_weight():
    with pytest.raises(ValueError):
        dry_run({**INPUT, "human_state_weight": "1"})
    with pytest.raises(ValueError):
        dry_run({name: value for name, value in INPUT.items() if name != "legal_gate"})


def test_gate_mutation_never_creates_capital_admission():
    assert dry_run(INPUT) == GOLDEN
    assert dry_run({**INPUT, "legal_gate": "0"})["shadow_value"] == "0"
    assert dry_run(INPUT)["capital_value"] == "0"


def test_known_zero_does_not_hide_another_unknown():
    result = dry_run({**INPUT, "legal_gate": "0", "conf_total": None})
    assert result["shadow_value"] is None
    assert result["unknown_inputs"] == ["conf_total"]
    assert result["zero_condition_flags"] == ["legal_gate"]


def test_frozen_golden_replay_and_tampering():
    bundle = {"method_version": GOLDEN["method_version"], "inputs": INPUT,
              "input_sha256": "67aed8f9937dc78d86c96705430bddd7062d6df797688c92bf56a17bb4aa02e7",
              "expected": GOLDEN}
    assert replay(bundle) == canonical_bytes(GOLDEN)
    with localcontext() as ctx:
        ctx.prec = 3
        assert replay(bundle) == canonical_bytes(GOLDEN)
    ordered = copy.deepcopy(bundle)
    ordered["inputs"] = dict(reversed(list(INPUT.items())))
    assert replay(ordered) == replay(bundle)
    altered = copy.deepcopy(bundle)
    altered["inputs"]["legal_gate"] = "0"
    with pytest.raises(ValueError, match="input hash mismatch"):
        replay(altered)
    altered = copy.deepcopy(bundle)
    altered["expected"]["capital_value"] = "80"
    with pytest.raises(ValueError, match="golden output mismatch"):
        replay(altered)
    altered = copy.deepcopy(bundle)
    altered["method_version"] = "unreviewed-successor"
    with pytest.raises(ValueError, match="version mismatch"):
        replay(altered)
