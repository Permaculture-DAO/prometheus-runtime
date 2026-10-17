"""PRM-PRED-001: deterministic diagnostic against benchmark-selection bias.

Read-only OFFLINE scientific candidate, never a certification, risk score,
land value, credit approval, actuarial finding or production gate.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Sequence
from .predictability_backtest import BacktestInput


def audit_benchmark_dependence(cohorts: dict[str, Sequence[BacktestInput]]) -> dict:
    needed = {"PERSISTENCE", "NOAA_1991_2020_HOURLY_NORMAL"}
    if set(cohorts) != needed:
        raise ValueError("both declared baselines must be supplied exactly")
    by_kind = {}
    metadata = set()
    for kind, datasets in cohorts.items():
        if not datasets:
            raise ValueError("empty benchmark cohort")
        cases = {}
        for request in datasets:
            metadata.add((request.model_id,request.model_version,request.variable,request.unit))
            for case in request.cases:
                key=(case.site_id,case.case_id,case.lead_hours)
                if key in cases:
                    raise ValueError("duplicate observation in a benchmark cohort")
                cases[key]=(case,request.dataset_sha256)
        by_kind[kind]=cases
    if len(metadata)!=1:
        raise ValueError("model, variable or unit mismatch")
    if set(by_kind["PERSISTENCE"]) != set(by_kind["NOAA_1991_2020_HOURLY_NORMAL"]):
        raise ValueError("forecast event sets differ across comparators")
    by_lead=defaultdict(list)
    for key in sorted(by_kind["PERSISTENCE"]):
        left=by_kind["PERSISTENCE"][key][0]
        right=by_kind["NOAA_1991_2020_HOURLY_NORMAL"][key][0]
        comparable=("site_id","issue_time","valid_time","observation_available_time",
                    "forecast","observed","lead_hours")
        if any(getattr(left,f)!=getattr(right,f) for f in comparable):
            raise ValueError("forecast or observation differs between baselines")
        gain_p=abs(left.baseline-left.observed)-abs(left.forecast-left.observed)
        gain_c=abs(right.baseline-right.observed)-abs(right.forecast-right.observed)
        by_lead[left.lead_hours].append((left.site_id,left.valid_time.strftime("%Y-%m"),
                                         gain_p,gain_c))
    result=[]
    for lead,rows in sorted(by_lead.items()):
        n=len(rows)
        site_month=defaultdict(list)
        site=defaultdict(list)
        for s,m,p,c in rows:
            site_month[(s,m)].append((p,c))
            site[s].append((p,c))
        blocks={f"{s}|{m}":{"persistence":round(sum(a for a,b in v)/len(v),6),
                           "climate":round(sum(b for a,b in v)/len(v),6)}
                for (s,m),v in sorted(site_month.items())}
        all_p=sum(p for _,_,p,_ in rows)/n
        all_c=sum(c for _,_,_,c in rows)/n
        any_bad=any(item["persistence"]<=0 or item["climate"]<=0
                    for item in blocks.values())
        if all_p<=0 or all_c<=0:
            state="FAILS_AT_LEAST_ONE_AGGREGATE_BENCHMARK"
        elif any_bad:
            state="NON_UNIFORM_SITE_MONTH_SKILL"
        else:
            state="DESCRIPTIVE_GAIN_NO_SIGNIFICANCE"
        result.append({
            "lead_hours":lead,"events":n,"site_month_blocks":len(blocks),
            "average_mae_improvement_vs_persistence":round(all_p,6),
            "average_mae_improvement_vs_climate":round(all_c,6),
            "site_month_improvements":blocks,
            "status":state,"scientifically_usable_horizon":None,
            "independent_holdout_verified":False,
            "risk_gates_admitted":False,
        })
    return {"method_id":"PRM-PRED-BENCHMARK-001@0.1-CANDIDATE",
            "authority":"evaluation_not_certification",
            "mode":"SHADOW_ONLY",
            "baseline_origin_independently_verified":False,
            "scientific_certification":False,
            "financial_or_land_authority":False,
            "lead_results":result}
