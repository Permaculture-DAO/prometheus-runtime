"""PRM-PRED-001 exploratory replication summary; not a statistical confidence interval.

Pure deterministic site/month sensitivity diagnostics. All inputs are caller-declared;
neither observed outcomes nor model skill are independently verified by this component.
"""
from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
import json
from typing import Sequence

from .predictability_backtest import BacktestInput, backtest_shadow


def replication_summary(inputs: Sequence[BacktestInput]) -> dict:
    if not inputs:
        raise ValueError("at least one input dataset is required")
    sites = set()
    values: list[tuple[str, str, int, float, float]] = []
    metadata = {(r.variable, r.unit, r.model_id, r.model_version) for r in inputs}
    if len(metadata) != 1:
        raise ValueError("cannot aggregate different metrics, models or units")
    seen = set()
    for req in inputs:
        if req.site_id in sites:
            raise ValueError("repeated site_id inputs: prepare one frozen cohort per site")
        sites.add(req.site_id)
        for case in req.cases:
            key = (req.site_id, case.issue_time, case.valid_time, case.lead_hours)
            if key in seen:
                raise ValueError("duplicate forecast verification event")
            seen.add(key)
            values.append((req.site_id, case.valid_time.strftime("%Y-%m"),
                           case.lead_hours,
                           abs(case.forecast-case.observed),
                           abs(case.baseline-case.observed)))
    by_lead = defaultdict(list)
    for row in values:
        by_lead[row[2]].append(row)
    outputs = []
    for lead, rows in sorted(by_lead.items()):
        site_month = defaultdict(list)
        for site, month, _, err, base in rows:
            site_month[(site, month)].append((err, base))
        block_gains = {
            key: sum(base-err for err, base in vals)/len(vals)
            for key, vals in site_month.items()
        }
        by_site = defaultdict(list)
        for (site, month), gain in block_gains.items():
            by_site[site].append(gain)
        site_gains = {s:sum(vals)/len(vals) for s, vals in by_site.items()}
        months = {month for (_,month) in site_month}
        cases = len(rows)
        mean_model = sum(err for *_,err,base in rows)/cases
        mean_base = sum(base for *_,err,base in rows)/cases
        # The leave-one-site / leave-one-month results measure sample sensitivity only.
        drop_site = {
            site: sum(g for (s,m),g in block_gains.items() if s!=site)/
                  max(1,sum(s!=site for (s,m) in block_gains))
            for site in by_site if len(by_site)>1
        }
        drop_month = {
            month: sum(g for (s,m),g in block_gains.items() if m!=month)/
                   max(1,sum(m!=month for (s,m) in block_gains))
            for month in months if len(months)>1
        }
        status = ("INSUFFICIENT_SPATIOTEMPORAL_REPLICATION"
                  if (len(by_site)<2 or len(months)<3 or cases<60
                      or len(site_month)<6)
                  else "DESCRIPTIVE_MULTI_SITE_NO_SIGNIFICANCE")
        outputs.append({
            "lead_hours":lead, "cases":cases,
            "sites":len(by_site), "distinct_months":len(months),
            "site_month_blocks":len(site_month),
            "case_weighted_model_mae":round(mean_model,6),
            "case_weighted_baseline_mae":round(mean_base,6),
            "sample_case_weighted_difference":round(mean_base-mean_model,6),
            "site_month_gains":{s+"|"+m:round(g,6)
                                for (s,m),g in sorted(block_gains.items())},
            "equal_site_mean_gains":{s:round(g,6) for s,g in sorted(site_gains.items())},
            "leave_one_site_out_block_gain":{s:round(g,6) for s,g in sorted(drop_site.items())},
            "leave_one_month_out_block_gain":{m:round(g,6) for m,g in sorted(drop_month.items())},
            "status":status,
        })
    identity=[{"site":r.site_id,"blob":r.dataset_sha256,"dataset":r.dataset_id}
              for r in sorted(inputs,key=lambda x:x.site_id)]
    digest=sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"method_id":"PRM-PRED-REPLICATION-001@0.1-CANDIDATE",
            "cohort_sha256":digest,"mode":"SHADOW_ONLY",
            "data_verified":False,"independent_validation":False,
            "statistical_confidence_intervals_computed":False,
            "authority":"evaluation_not_certification","forecast_skill_certified":False,
            "land_and_capital_gates_modified":False,
            "lead_results":outputs}
