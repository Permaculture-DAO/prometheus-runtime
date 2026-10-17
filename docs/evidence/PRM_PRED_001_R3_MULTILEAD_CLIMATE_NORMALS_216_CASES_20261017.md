# PRM-PRED-001 — NOAA multi-lead R3, official climate normals, and benchmark dependence

**Executed 2026-10-17 · Candidate external-data experiment · Canon unchanged · R3 SCIENTIFIC HOLD.**

## Critical distinction

This experiment scores **NOAA GFS**, not meteorological forecasts produced by PROMETHEUS. PRM-PRED-001 is an audit and limit-of-validity tool. These sample scores do not establish statistical significance, independence, permitted use for land underwriting or any financial, insurance, regulatory or environmental claims.

## Input and provenance

- 3 NOAA GHCNh station IDs: USW00012839 (Miami FL), USW00013874 (Atlanta GA), USW00013889 (Jacksonville FL).
- 24 archived NOAA GFS issue dates: Aug 3–10, Sep 3–10 and Oct 3–10, 2026, 00 UTC issue cycles.
- Forecast horizons **+24, +48 and +72 hours**, 2-meter temperature from NOAA 0.25° GRIB2 operational archive. Unique forecast–station events: **216**, 72 per horizon, 24 per site/horizon.
- Target observations NOAA GHCNh; candidate temporally matched to within 60 minutes; reference actual source publication lag and NOAA QC interpretation are **not independently verified**.
- Comparator A: last candidate recorded station observation 20–180 minutes **before** GFS issue (persistence).
- Comparator B: actual NOAA **1991–2020 Hourly Climate Normals**, file per station, HLY-TEMP-NORMAL in Fahrenheit converted to °C. NOAA normals are expressed in **local standard time**, not DST and not UTC; all three study sites use EST = UTC−05:00. Thus an Aug 06 00 UTC forecast target matches the **Aug 05 19:00 local-standard** normal. Normal data predates forecast issuance.
- Official normals source: https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/
- Documentation: https://www.ncei.noaa.gov/pub/data/cdo/documentation/normals-hourly-1991-2020_documentation.pdf
- NOAA GFS public archive: https://noaa-gfs-bdp-pds.s3.amazonaws.com/
- NOAA GHCNh archive: https://noaa-ghcnh-pds.s3.amazonaws.com/

Exact source JSON and SHA-256 matched by offline PRM-PRED runner for each station and comparator. NOAA source authenticity, legal reuse provenance, forecast preavailability, target-observation latency, spatial representativeness, model-run versions, holdout independence and observational quality still require external review.

## Pooled descriptive mean absolute error (MAE, °C)

| Forecast horizon | Events | NOAA GFS | Issue-time persistence | NOAA 1991–2020 hourly climate normal |
|---|---:|---:|---:|---:|
| +24 h | 72 | **1.436420** | 2.208333 | 2.165741 |
| +48 h | 72 | **2.081551** | 2.472222 | 2.127469 |
| +72 h | 72 | **2.003429** | 2.812500 | 2.172685 |

These are *two baselines on the same 216 events*, not 432 independent forecasts.

**Warning:** At +48 h, NOAA GFS improvement versus climate normal is only +0.045918 °C over the pooled sample. Atlanta (+48h) GFS MAE 2.790558 °C vs normal MAE 2.657407 °C; Jacksonville (+48h) 2.081935 °C vs normal 1.926852 °C. On these sites the GFS sample is worse than the normal. There are several negative site-month blocks at all lead times, even when pooled results are favourable.

## Software tests and conservative classification

- Existing PRM-PRED-BACKTEST-001 per-site result at each horizon: **INSUFFICIENT_HOLDOUT_COVERAGE** (24 events per site/horizon, below the provisional minimum 30).
- PRM-PRED-REPLICATION-001 per-horizon site-month output: **DESCRIPTIVE_MULTI_SITE_NO_SIGNIFICANCE**, no confidence intervals computed.
- New pure and read-only PRM-PRED-BENCHMARK-001 @0.1 candidate guard compares **identical observation/forecast event sets** against both baselines, detects mismatch/cherry-picking, and emits **NON_UNIFORM_SITE_MONTH_SKILL** at +24, +48 and +72 hours. It never returns a validated forecast horizon, capital permission or scientific certificate.
- All input statuses are caller-declared unless separately authenticated by authoritative evidence controls; API shadow remains off by default.

## Immutable local evidence snapshot — NOT canonical

`D:\hearth intelligence – Prometheus Sovereign Syntropy\PROMETHEUS\Evidence_Candidates\PRM_PRED_001_R3_3SITES_3LEADS_NORMALS_20261017.zip`

- ZIP bytes: **39,847,372**
- ZIP SHA-256: **c39da2c46d4c6d95e3f8af90edd1069d1bfd74d8745a025edfb7a9dd96e7980b**
- 165 tracked source/results/protocol files with per-file hashes and ZIP structural test passed.
- Prior 24-hour and 90-case experimental archives remain independently preserved, not overwritten.

## Source-bound R0–R5 governance

- **R0 HOLD:** authoritative machine Source Registry and steward source type/ID classification not yet authenticated.
- **R1 HOLD:** paper hypothesis (Zhang et al., 2026), independent scientific peer review and preregistered validation design outstanding.
- **R2 SOFTWARE CANDIDATE:** tests and CI on exact PR HEAD required; Claude/Codex independent reviews not presumed.
- **R3 SCIENTIFIC HOLD:** three nearby months, three sites, 24 issue dates, dependence/correlation, benchmark quality and actual release-time metadata not independently reviewed. Expand to additional seasons, longer horizons, additional independent stations and uncertainty/calibration methods.
- **R4 HOLD:** no application source promotion or shadow staging without explicit steward decision.
- **R5 HOLD:** no public runtime deploy; no finance, land, credit, insurance, TRBK or regulatory statements of validity.

**The 129 ± 7 day upper-bound proposal is atmospheric theory, not a model validation threshold and is not hardcoded in PRM-PRED.**
