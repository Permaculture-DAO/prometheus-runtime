# PRM-PRED-001 — NOAA 3-site × 3-month, 90-case external-data replay

**Date:** 2026-10-17. **Authority:** NONCANONICAL / SHADOW / R3 SCIENTIFIC ADMISSION HOLD.
**Important:** These are NOAA GFS temperature forecasts, **not** predictions made by PROMETHEUS. PROMETHEUS supplies audit, integrity, backtesting and refusal to certify unsupported skill.

## Preregistered exploratory cohort (not an independent held-out scientific study)

- Sites: Miami International airport USW00012839, Atlanta Hartsfield-Jackson airport USW00013874, Jacksonville International airport USW00013889.
- Forecast model: NOAA GFS historic operational 00 UTC issue cycles at +24 h; 2-metre temperature from archived 0.25-degree GRIB2 indexed subfields.
- Temporal slices: issue dates August 3–12, September 3–12, October 3–12 2026, 30 forecast issuance dates.
- Independent-type external reference: NOAA GHCNh station records, target-time match within ±60 minutes (actual 90 matches within −8 to +7 minutes).
- Benchmark: most recent station temperature timestamped 20–180 minutes before nominal forecast issue. Actual baseline ages 20–68 minutes; observation publication latency **not independently established**.
- GHCNh temperature quality-code field blank for all 90 matched target and baseline readings, but the NOAA quality-code interpretation and all observational corrections require independent expert review.
- Initial download chunks excluded five target readings; **continuation byte ranges recovered all five**. No values were invented or imputed. The 85-case exploratory trace is superseded and preserved.
- Endpoint remains default OFF, all sources caller declared and outside authoritative Evidence Spine.

## Corrected final descriptive sample

| Site | Valid pairs | Model GFS MAE (°C) | Candidate persistence MAE (°C) | Baseline minus GFS MAE (°C) |
|---|---:|---:|---:|---:|
| Miami | 30 | 1.024265433 | 1.570000 | +0.545734567 |
| Atlanta | 30 | 1.837966233 | 3.000000 | +1.162033767 |
| Jacksonville | 30 | 1.690702633 | 2.800000 | +1.109297367 |
| **Combined cases** | **90** | **1.517645** | **2.456667** | **+0.939022** |

PRM-PRED-BACKTEST-001 returns **POSITIVE_SAMPLE_SKILL_UNVERIFIED** at each of the three sites; this is NOT a certification, hypothesis test, or reliable generalization. The additional multi-site diagnostic PRM-PRED-REPLICATION-001 returns **DESCRIPTIVE_MULTI_SITE_NO_SIGNIFICANCE**.

Nine site-month blocks are represented. Leave-one-site-out mean site-month gain range: **+0.827516 to +1.135666 °C**; leave-one-month-out range: **+0.793664 to +1.015748 °C**. These are only descriptive resampling sensitivity checks, **not** significance tests, predictive guarantees or confidence intervals. Lack of independent holdouts and seasonality coverage remains material.

## Reconciliation of superseded results

1. Original Jacksonville 10-case result only: GFS MAE 1.091626 vs persistence 2.09 °C, using October dates only.
2. Initial 85-case three-site exploratory output missed five station observations because byte-range slices were incomplete (not necessarily because observations were absent). Its pooled GFS MAE 1.393701 and baseline 2.223529 °C are **superseded and must not be presented as the preferred result**.
3. Continuing three NOAA GHCNh byte ranges recovered the five, yielding full 90-case metrics above.

## Local evidence custody (NOT Canon)

Noncanonical dataset and scripts retained on the authorized workstation:

D:\hearth intelligence – Prometheus Sovereign Syntropy\PROMETHEUS\Evidence_Candidates\PRM_PRED_001_R3_MULTI_SITE_AUG_SEP_OCT_20261017_v2.zip

- Archive SHA256: **722e6677ca997f08f20322007e8de54a58cc7b67df7a1ca3613505f7698bffbf**
- 91 input/output files with per-file SHA256 candidate manifest: 30 GFS GRIB2 subfields; 30 GFS index files; 9 original station range slices plus 3 extensions; test scripts, requests, outputs and source references.
- ZIP structural integrity checked. Digest validates archived bytes relative to the snapshot, **not** authenticity, licensing or observation arrival time.
- Prior 85-case archive retained separately under its earlier version (never overwritten).

### Third-party sources
- GFS: https://noaa-gfs-bdp-pds.s3.amazonaws.com/
- GHCNh: https://noaa-ghcnh-pds.s3.amazonaws.com/
- NOAA GHCNh product: https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly

## HOLD criteria remain binding

R0: machine Source Registry must be authenticated and steward approval documented.
R1/R2: independent scientific and runtime reviews of the exact implementation SHA.
R3: physically independent station QC, release-time/latency provenance, NOAA data reuse terms, model version and grid-to-station representativeness, true train/test independence, exposure to additional seasons/sites/horizons, climatological comparator and dependence-aware uncertainty intervals.
R4/R5: no staging activation, claims, PRU/RAP/TRBK, financial/insurance/land valuation or runtime authority before signed governance decisions.

**Scientific result: a working real-data audit/replay pipeline, not validated weather skill or investment underwriting.**
