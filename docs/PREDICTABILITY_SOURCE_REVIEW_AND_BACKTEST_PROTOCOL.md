# PRM-PRED-001 — scientific/source intake and SHADOW backtesting protocol

**Classification: PROPOSED / NON-CANONICAL / NON-AUTHORITATIVE.** This is a review request, not an adopted Source Registry entry or source promotion. No signed Canon is changed.

## Source hierarchy
1. Signed Genesis Canon and legal rights outrank runtime code.
2. PRM-ARCH-DET-002@2.0 governs D/P/H/Q.
3. AETERNA, RAVEL and the land application retain their existing authority boundaries and gates.
4. PRM-PRED-001@0.1 is a supplementary forecast-use envelope, not a second G0-G7 or PRU/RAP control.
5. Code and synthetic tests cannot establish a verified scientific source or production release.

**Source review request:** registry steward must check ID collision, M/X/I classification, upstream hashes, dependencies, branch conflicts, approval workflow. Until then this identity is a candidate implementation label only.

## Scientific claim boundary
Zhang et al., A New Approach to Estimating the Limit of Predictability (2026), DOI https://doi.org/10.1007/s00376-026-5621-8.

Authors propose 129 ± 7 days as an idealized *atmospheric chronological* predictability upper limit, under contested assumptions. Not demonstrated: 129-day operational forecasts; a universal land/finance/agroforestry forecasting horizon; actuarial credit or insurance admission. Falsification requires independent assessment of the proposed radiation-noise mechanism, alternative physical assumptions, and chronological versus statistical predictability.

Never hardcode 129, 57 or 14 as a capability or acceptance threshold.

## Data candidates (not ingested or validated)
- Open-Meteo Previous Runs: historic forecast at fixed 1–7 day lead. https://open-meteo.com/en/docs/previous-runs-api
- Open-Meteo Single Runs: preserves forecast issue time; stitched historical forecasts are not adequate to reconstruct a specific forecast information set without additional checks.
- ECMWF S2S reforecasts: a separate subseasonal probabilistic task. https://www.ecmwf.int/en/research/projects/s2s
- Prefer quality-controlled independent station observations as reference where possible. Reanalysis is a model-informed comparison, not an independent physical observation.

Check access, licence (including commercial restrictions), issue-time availability, geographic applicability, model version drift, QC flags and missingness before use.

## Offline backtest
services/api/app/predictability_backtest.py is a pure, offline function. No route, database update, file write, token, claim or live data access. Inputs are time-frozen and caller-declared: forecasts, matched baselines, target observations, timestamps, model/data references and usage rights.

It calculates deterministic mean absolute error (MAE) by exact lead hour. Outcomes include HOLD_DATA_RIGHTS, INSUFFICIENT_HOLDOUT_COVERAGE, BASELINE_NONINFORMATIVE, NOT_BETTER_THAN_BASELINE and POSITIVE_SAMPLE_SKILL_UNVERIFIED.

POSITIVE_SAMPLE_SKILL_UNVERIFIED does not imply independent authentication, forecast calibration, robust skill, adequate statistical confidence or authority. The thresholds of 30 samples and three separate months are provisional smoke-checks, not scientific assurance.

Scientific review must preregister the baseline, non-overlapping time and geography holdouts, missing-data strategy, variable/units, forecast issued-at and observed-at metadata, uncertainty method and proper scores. For correlated weather time series, use block-bootstrap or equivalent dependence-aware confidence intervals. MAE applies to point forecasts, not probabilistic calibration.

## Land / RAVEL boundary
predictability_land_adapter.py emits only a read-only uncertainty note, with land_value=null, estimated_loss=null and explicit UNKNOWN risk bearer. It cannot grant land/credit/insurance rights, create a G0-G7 pass, quantify actuarial loss, issue PRU or VRRC, or claim risk transfer. Mapping to genuine RAVEL loss/risk-bearer records requires new data and independent human approval.

## Gate register
| Gate | Status |
|---|---|
| R0 source registry | HOLD pending steward reconciliation |
| R1 literature and falsification protocol | CANDIDATE written; independent reviewer outstanding |
| R2 isolated implementation | CANDIDATE; GitHub CI required for updated head |
| R3 authentic empirical backtest | HOLD; no independently validated field/forecast dataset |
| R4 application adoption | HOLD pending steward/maintainer |
| R5 production/public financial claims | HOLD |
| R6 Canon amendment | NOT REQUESTED |

Production default remains PREDICTABILITY_SHADOW_ENABLED=false. Any enablement, merge or release requires explicit separate governance decision.
