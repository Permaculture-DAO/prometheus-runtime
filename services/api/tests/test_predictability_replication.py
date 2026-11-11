"""Synthetic-only tests of cross-site/month descriptive uncertainty safeguards."""
from copy import deepcopy
import pytest
from app.predictability_backtest import BacktestInput
from app.predictability_replication import replication_summary
from test_predictability_backtest import fixture


def make(site, error=19.0):
    req = fixture()
    req["site_id"] = site
    req["dataset_id"] = site+"-SYNTHETIC"
    for case in req["cases"]:
        case["site_id"] = site
        case["forecast"] = error
    return BacktestInput.model_validate(req)


def test_one_site_insufficient():
    r = replication_summary([make("A")])
    x = r["lead_results"][0]
    assert x["status"] == "INSUFFICIENT_SPATIOTEMPORAL_REPLICATION"
    assert x["sites"] == 1
    assert r["forecast_skill_certified"] is False


def test_multiple_sites_remain_descriptive_only():
    a, b = make("A",19),make("B",22)
    r = replication_summary([a,b])
    assert r == replication_summary([a,b])
    x = r["lead_results"][0]
    assert x["cases"] == 60 and x["sites"] == 2 and x["distinct_months"] == 3
    assert x["status"] == "DESCRIPTIVE_MULTI_SITE_NO_SIGNIFICANCE"
    assert r["statistical_confidence_intervals_computed"] is False
    assert len(x["leave_one_site_out_block_gain"]) == 2
    assert len(x["leave_one_month_out_block_gain"]) == 3


def test_different_units_or_models_cannot_mix():
    a,b = make("A"),make("B")
    b.unit = "kelvin"
    with pytest.raises(ValueError,match="different metrics"):
        replication_summary([a,b])


def test_duplicate_site_rejected():
    with pytest.raises(ValueError,match="repeated site_id"):
        replication_summary([make("A"),make("A")])


def test_no_inputs_rejected():
    with pytest.raises(ValueError,match="at least one"):
        replication_summary([])
