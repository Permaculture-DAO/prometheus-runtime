"""Synthetic-only year-transfer comparison must never promote skill."""
from copy import deepcopy
import pytest
from app.predictability_backtest import BacktestInput
from app.predictability_year_transfer import year_separated_replay
from test_predictability_backtest import fixture


def sample(year,site="S"):
    request=fixture()
    request["dataset_id"]=f"SYN-{year}-{site}"
    request["site_id"]=site
    request["model_version"]=f"v{year}-UNVERIFIED"
    request["training_data_cutoff"]="2024-01-01T00:00:00Z"
    for c in request["cases"]:
        c["site_id"]=site
        c["case_id"]=site+"-"+str(year)+"-"+c["case_id"]
        for key in ("issue_time","valid_time","observation_available_time",
                    "baseline_issue_time"):
            c[key]=c[key].replace("2026-",f"{year}-")
    return BacktestInput.model_validate(request)


def cohorts():
    return {"2025":[sample(2025)],"2026":[sample(2026)]}


def test_year_matching_is_repeatable_and_not_scientific_claim():
    r=year_separated_replay(cohorts(),baseline_kind="PERSISTENCE")
    assert r==year_separated_replay(cohorts(),baseline_kind="PERSISTENCE")
    assert r["common_nominal_events"]==30
    assert r["true_independent_holdout"] is False
    assert r["prospective_validation"] is False
    assert r["results"][0]["validated_transferability"] is False


def test_nonmatching_values_and_year_versions_are_not_automatically_pooled():
    pair=cohorts()
    pair["2025"][0].cases[0].forecast=999
    r=year_separated_replay(pair,baseline_kind="NOAA_1991_2020_HOURLY_NORMAL")
    assert r["results"][0]["year_summaries"]["2025"]["NOAA_model_mae"] != \
           r["results"][0]["year_summaries"]["2026"]["NOAA_model_mae"]
    assert not r["operational_model_version_continuity_independently_verified"]


def test_required_pair_of_years():
    with pytest.raises(ValueError,match="exact years"):
        year_separated_replay({"2025":[sample(2025)]},baseline_kind="PERSISTENCE")


def test_mismatched_units_rejected():
    co=cohorts();co["2025"][0].unit="kelvin"
    with pytest.raises(ValueError,match="different model"):
        year_separated_replay(co,baseline_kind="PERSISTENCE")


def test_duplicate_site_rejected():
    co=cohorts();co["2025"].append(deepcopy(co["2025"][0]))
    with pytest.raises(ValueError,match="duplicate site"):
        year_separated_replay(co,baseline_kind="PERSISTENCE")


def test_no_matching_issue_day_refuses_inference():
    co=cohorts()
    for c in co["2025"][0].cases:
        # Shift distinct 2025 months forward by three while preserving uniqueness.
        # The other year's Apr/May/Jun issues cannot match Jul/Aug/Sep.
        for attr in ("issue_time","valid_time","observation_available_time",
                     "baseline_issue_time"):
            old=getattr(c,attr)
            setattr(c,attr,old.replace(month=old.month+3))
    with pytest.raises(ValueError,match="no calendar-matched"):
        year_separated_replay(co,baseline_kind="PERSISTENCE")


def test_reject_undocumented_comparator():
    with pytest.raises(ValueError,match="unsupported"):
        year_separated_replay(cohorts(),baseline_kind="SYNTHETIC-EASY")


def test_error_on_false_year_label():
    co=cohorts();co["2025"][0].cases[0].issue_time=co["2026"][0].cases[0].issue_time
    with pytest.raises(ValueError,match="issue year"):
        year_separated_replay(co,baseline_kind="PERSISTENCE")
