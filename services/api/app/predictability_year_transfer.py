"""PRM-PRED-001: descriptive *retrospective* calendar-matched year transfer.

This only tests whether externally sourced NOAA forecast-vs-observation errors
differ across sampled years. It does NOT establish model stationarity, a
prospective holdout, scientific confidence, business utility or release authority.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Sequence
from .predictability_backtest import BacktestInput


def year_separated_replay(
    cohorts: dict[str, Sequence[BacktestInput]],
    *,
    baseline_kind: str,
) -> dict:
    if set(cohorts) != {"2025", "2026"}:
        raise ValueError("exact years 2025 and 2026 required")
    if baseline_kind not in {"PERSISTENCE", "NOAA_1991_2020_HOURLY_NORMAL"}:
        raise ValueError("unsupported comparator kind")
    indexed = {}
    metadata = set()
    versions = {}
    missing_years=[]
    for year, datasets in sorted(cohorts.items()):
        if not datasets:
            raise ValueError("empty year dataset")
        seen_sites=set()
        indexed[year]={}
        versions[year]=set()
        for req in datasets:
            if req.site_id in seen_sites:
                raise ValueError("duplicate site cohort within year")
            seen_sites.add(req.site_id)
            if not req.cases:
                raise ValueError("empty case set")
            metadata.add((req.model_id,req.variable,req.unit))
            versions[year].add(req.model_version)
            for case in req.cases:
                if str(case.issue_time.year)!=year:
                    raise ValueError("issue year outside labeled cohort")
                if case.baseline_issue_time>case.issue_time:
                    raise ValueError("future comparator")
                # Matching nominal issue *month and day*, site, and lead only.
                # Station observations and forecast values are year-specific.
                key=(case.site_id,case.issue_time.month,case.issue_time.day,case.lead_hours)
                if key in indexed[year]:
                    raise ValueError("duplicate nominal site/date/lead in year")
                indexed[year][key]=(case,req.model_version)
        if len(seen_sites)<1:missing_years.append(year)
    if len(metadata)!=1:
        raise ValueError("different model family, variable or unit")
    common=set(indexed["2025"])&set(indexed["2026"])
    if not common:
        raise ValueError("no calendar-matched site/date/lead events across years")
    grouped=defaultdict(list)
    for key in sorted(common):
        for year in ("2025","2026"):
            case,_=indexed[year][key]
            grouped[case.lead_hours].append((
                year,
                abs(case.forecast-case.observed),
                abs(case.baseline-case.observed)
            ))
    results=[]
    for lead,entries in sorted(grouped.items()):
        years={}
        for year in ("2025","2026"):
            errors=[(m,b) for y,m,b in entries if y==year]
            n=len(errors)
            years[year]={
                "matched_events":n,
                "NOAA_model_mae":round(sum(m for m,b in errors)/n,6),
                "declared_baseline_mae":round(sum(b for m,b in errors)/n,6),
                "sample_mae_advantage":round(sum(b-m for m,b in errors)/n,6)
            }
        results.append({
            "lead_hours":lead, "matched_pairs_between_years":years["2025"]["matched_events"],
            "year_summaries":years,
            "descriptive_model_mae_change_2026_minus_2025":round(
                years["2026"]["NOAA_model_mae"]-years["2025"]["NOAA_model_mae"],6),
            "claim_classification":"RETROSPECTIVE_CALENDAR_MATCH_ONLY",
            "model_version_equivalence_not_verified":True,
            "validated_transferability":False,
            "investment_authority":False,
        })
    return {
        "method_id":"PRM-PRED-YEAR-TRANSFER-001@0.1-CANDIDATE",
        "baseline_kind":baseline_kind,
        "mode":"SHADOW_ONLY",
        "common_nominal_events":len(common),
        "unmatched_in_2025":len(set(indexed["2026"])-common),
        "unmatched_in_2026":len(set(indexed["2025"])-common),
        "model_versions_by_year":{y:sorted(versions[y]) for y in ("2025","2026")},
        "operational_model_version_continuity_independently_verified":False,
        "prospective_validation":False,
        "preregistration_prior_to_2025_sample":False,
        "true_independent_holdout":False,
        "scientific_significance_established":False,
        "risk_gates_modified":False,
        "results":results
    }
