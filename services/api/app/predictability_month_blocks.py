"""PRM-PRED-001: frozen, dependence-aware exploratory month-block bootstrap.

This is a RESEARCH diagnostic, NOT independent statistical inference,
forecast certification, validated horizon, investment/insurance underwriting,
or a capital gate. Whole months are resampled together across all sites
to preserve within-month temporal and cross-site co-movement.
"""
from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
from math import floor, isfinite
import json
import random
from typing import Sequence

from .predictability_backtest import BacktestInput


def _percentile(sorted_values: list[float], fraction: float) -> float:
    p = (len(sorted_values) - 1) * fraction
    i = floor(p)
    j = min(i + 1, len(sorted_values) - 1)
    return sorted_values[i] + (sorted_values[j] - sorted_values[i]) * (p - i)


def month_block_sensitivity(
    cohorts: dict[str, Sequence[BacktestInput]],
    *,
    iterations: int = 2048,
) -> dict:
    """Compare two fixed baseline cohorts on the EXACT same forecast events.

    The reproducible month-block resampling is for stress/sensitivity ONLY.
    With fewer than 12 distinct months AND 2 years it must abstain from
    even labelling the interval provisionally inference-ready.
    """
    labels = {"PERSISTENCE", "NOAA_1991_2020_HOURLY_NORMAL"}
    if set(cohorts) != labels:
        raise ValueError("both baselines are mandatory")
    if type(iterations) is not int or not (128 <= iterations <= 8192):
        raise ValueError("iterations must be integer 128..8192")
    indexed = {}
    for label, datasets in cohorts.items():
        records: dict[tuple, tuple] = {}
        for req in datasets:
            for case in req.cases:
                key = (case.site_id, case.case_id, case.lead_hours)
                if key in records:
                    raise ValueError("duplicate event within cohort")
                records[key] = (
                    case.issue_time, case.valid_time,
                    case.observation_available_time,
                    case.forecast, case.observed, case.baseline
                )
        indexed[label] = records
    if not indexed["PERSISTENCE"] or set(indexed["PERSISTENCE"]) != set(indexed["NOAA_1991_2020_HOURLY_NORMAL"]):
        raise ValueError("missing or mismatched paired forecast events")
    blocks: dict[int, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    fingerprint: list[list] = []
    for key in sorted(indexed["PERSISTENCE"]):
        p = indexed["PERSISTENCE"][key]
        c = indexed["NOAA_1991_2020_HOURLY_NORMAL"][key]
        if p[:5] != c[:5]:
            raise ValueError("paired forecast, observation or timestamps differ")
        issue, valid, available, forecast, observed, pers = p
        climate = c[5]
        block = valid.strftime("%Y-%m")
        improvement_p = abs(pers-observed)-abs(forecast-observed)
        improvement_c = abs(climate-observed)-abs(forecast-observed)
        if not all(isfinite(v) for v in (improvement_p, improvement_c)):
            raise ValueError("non-finite numerical error")
        blocks[key[2]][block].append((improvement_p,improvement_c))
        fingerprint.append([str(key), str(issue), str(valid), forecast, observed, pers, climate])
    digest=sha256(json.dumps(fingerprint,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()
    results=[]
    for lead, months in sorted(blocks.items()):
        keys=sorted(months)
        values=[months[m] for m in keys]
        seed=int(sha256(f"{digest}:{lead}:month-block-v0.1".encode()).hexdigest()[:16],16)
        rng=random.Random(seed)
        draws=[[],[]]
        for _ in range(iterations):
            selected=[values[rng.randrange(len(values))] for _ in keys]
            samples=[pair for block in selected for pair in block]
            for x in (0,1):
                draws[x].append(sum(pair[x] for pair in samples)/len(samples))
        bounds=[]
        for collection in draws:
            ordered=sorted(collection)
            bounds.append([round(_percentile(ordered,0.025),6),
                           round(_percentile(ordered,0.975),6)])
        years={m[:4] for m in keys}
        provisional=len(keys)>=12 and len(years)>=2
        results.append({
            "lead_hours":lead,
            "events":sum(map(len,values)),
            "monthly_blocks":len(keys),
            "years":len(years),
            "month_blocks":keys,
            "persistence_difference_interval":bounds[0],
            "climate_difference_interval":bounds[1],
            "interval_meaning":"exploratory_resampling_distribution_not_confidence_interval",
            "block_scheme":"resample_whole_calendar_months_keep_all_sites_and_within_month_events",
            "status":"EXPLORATORY_ONLY_REVIEW_REQUIRED" if provisional else "INSUFFICIENT_INDEPENDENT_TEMPORAL_BLOCKS",
            "statistical_significance_verified":False,
            "validated_horizon_hours":None,
            "financial_authority":False,
        })
    return {
        "method_id":"PRM-PRED-MONTH-BLOCK-001@0.1-CANDIDATE",
        "sample_sha256":digest,
        "random_seed_policy":"sha256 frozen paired event set + lead",
        "draws_per_lead":iterations,
        "algorithm":"Python random.Random Mersenne Twister, explicit deterministic local replay",
        "mode":"SHADOW_ONLY",
        "independent_source_authentication":False,
        "scientific_certification":False,
        "risk_and_canonical_gates_unchanged":True,
        "lead_results":results,
    }
