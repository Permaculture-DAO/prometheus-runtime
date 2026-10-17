"""Synthetic-only cross-benchmark negative and immutability tests."""
from copy import deepcopy
import pytest
from app.predictability_backtest import BacktestInput
from app.predictability_benchmark_guard import audit_benchmark_dependence
from test_predictability_backtest import fixture


def sample(site="SYN"):
    p=fixture();p["site_id"]=site;p["dataset_id"]=site+"-PERSISTENCE"
    for c in p["cases"]:c["site_id"]=site
    q=deepcopy(p);q["dataset_id"]=site+"-CLIMATE"
    for c in q["cases"]:c["baseline"]=21.0
    return (BacktestInput.model_validate(p),BacktestInput.model_validate(q))


def data(site="SYN"):
    a,b=sample(site)
    return {"PERSISTENCE":[a],"NOAA_1991_2020_HOURLY_NORMAL":[b]}


def test_two_baselines_report_non_certifying_status():
    r=audit_benchmark_dependence(data())
    assert r == audit_benchmark_dependence(data())
    assert r["scientific_certification"] is False
    assert r["financial_or_land_authority"] is False
    assert r["lead_results"][0]["scientifically_usable_horizon"] is None


def test_no_false_skill_when_climate_is_superior():
    cohorts=data()
    climate=cohorts["NOAA_1991_2020_HOURLY_NORMAL"][0]
    for c in climate.cases:c.baseline=20.0
    result=audit_benchmark_dependence(cohorts)["lead_results"][0]
    assert result["status"]=="FAILS_AT_LEAST_ONE_AGGREGATE_BENCHMARK"


def test_no_cherry_picked_baseline_omission():
    with pytest.raises(ValueError,match="both declared"):
        audit_benchmark_dependence({"PERSISTENCE":data()["PERSISTENCE"]})


def test_false_forecast_across_baselines_rejected():
    cohorts=data()
    cohorts["NOAA_1991_2020_HOURLY_NORMAL"][0].cases[0].forecast=99
    with pytest.raises(ValueError,match="forecast or observation"):
        audit_benchmark_dependence(cohorts)


def test_mismatched_case_set_rejected():
    cohorts=data()
    cohorts["NOAA_1991_2020_HOURLY_NORMAL"][0].cases.pop()
    with pytest.raises(ValueError,match="event sets differ"):
        audit_benchmark_dependence(cohorts)


def test_duplicate_events_rejected():
    cohorts=data()
    cohorts["PERSISTENCE"][0].cases.append(deepcopy(cohorts["PERSISTENCE"][0].cases[0]))
    with pytest.raises(ValueError,match="duplicate observation"):
        audit_benchmark_dependence(cohorts)


def test_heterogeneous_sites_are_supported_without_scope_promotion():
    a,b=sample("A");c,d=sample("B")
    out=audit_benchmark_dependence({
      "PERSISTENCE":[a,c],"NOAA_1991_2020_HOURLY_NORMAL":[b,d]})
    assert out["lead_results"][0]["site_month_blocks"]==6
    assert out["authority"]=="evaluation_not_certification"
