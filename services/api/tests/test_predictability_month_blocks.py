"""PRM-PRED-001 deterministic whole-month-resampling regressions (synthetic only)."""
from copy import deepcopy
import pytest

from app.predictability_backtest import BacktestInput
from app.predictability_month_blocks import month_block_sensitivity
from test_predictability_backtest import fixture


def paired(sites=("X", "Y")):
    p = []
    c = []
    for site in sites:
        a = fixture()
        a["dataset_id"] = f"synthetic-{site}-persist"
        a["site_id"] = site
        for event in a["cases"]:
            event["site_id"] = site
            event["case_id"] = site + "-" + event["case_id"]
        b = deepcopy(a)
        b["dataset_id"] = f"synthetic-{site}-normal"
        for event in b["cases"]:
            event["baseline"] = 20.0
        p.append(BacktestInput.model_validate(a))
        c.append(BacktestInput.model_validate(b))
    return {"PERSISTENCE":p, "NOAA_1991_2020_HOURLY_NORMAL":c}


def test_repeatable_and_requires_more_temporal_blocks():
    values = paired()
    a=month_block_sensitivity(values,iterations=256)
    b=month_block_sensitivity(values,iterations=256)
    assert a==b
    lead=a["lead_results"][0]
    assert lead["events"]==60
    assert lead["monthly_blocks"]==3
    assert lead["years"]==1
    assert lead["status"]=="INSUFFICIENT_INDEPENDENT_TEMPORAL_BLOCKS"
    assert lead["validated_horizon_hours"] is None
    assert not a["scientific_certification"]


def test_whole_month_resampling_retains_declared_scope():
    result=month_block_sensitivity(paired(),iterations=128)["lead_results"][0]
    assert result["month_blocks"]==["2026-04", "2026-05", "2026-06"]
    assert result["block_scheme"] == "resample_whole_calendar_months_keep_all_sites_and_within_month_events"
    assert result["interval_meaning"]=="exploratory_resampling_distribution_not_confidence_interval"
    assert result["persistence_difference_interval"]==[3.0,3.0]
    assert result["climate_difference_interval"]==[-1.0,-1.0]


def test_reject_different_forecast_events():
    co=paired()
    co["NOAA_1991_2020_HOURLY_NORMAL"][0].cases[0].forecast=999
    with pytest.raises(ValueError,match="differ"):
        month_block_sensitivity(co)


def test_missing_baseline_cannot_be_silenced():
    co=paired()
    co.pop("PERSISTENCE")
    with pytest.raises(ValueError,match="both baselines"):
        month_block_sensitivity(co)


def test_missing_event_fails():
    co=paired()
    co["PERSISTENCE"][0].cases.pop()
    with pytest.raises(ValueError,match="mismatched"):
        month_block_sensitivity(co)


def test_duplicate_event_fails():
    co=paired()
    co["PERSISTENCE"][0].cases.append(deepcopy(co["PERSISTENCE"][0].cases[0]))
    with pytest.raises(ValueError,match="duplicate event"):
        month_block_sensitivity(co)


@pytest.mark.parametrize("n",[0,8,127,8193,3.14,True])
def test_draws_bound_and_type(n):
    with pytest.raises(ValueError,match="iterations"):
        month_block_sensitivity(paired(),iterations=n)
