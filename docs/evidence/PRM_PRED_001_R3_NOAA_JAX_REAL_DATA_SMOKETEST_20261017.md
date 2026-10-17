# PRM-PRED-001 — NOAA Jacksonville real-data smoke evaluation (R3 candidate)

**2026-10-17 | Noncanonical candidate evidence | Scientific admission HOLD.**

This exploratory comparison uses real NOAA GFS forecasts, **not PROMETHEUS-generated forecasts**. PRM-PRED is only the shadow evaluator; it has not independently authenticated the observation or calibrated a forecast. The 129 ± 7 day scientific hypothesis is unrelated to these daily errors.

## Data and method
- NOAA operational GFS 00 UTC cycles 2026-10-03 through 2026-10-12; +24h 2-meter air temperature; nearest 0.25-degree grid point ~4.9 km from station USW00013889 (Jacksonville FL). Each model field extracted by NOAA GFS public index byte range.
- NOAA GHCNh hourly station USW00013889 temperature; nearest verification record ±60 minutes, generally 4 minutes before the target time.
- Comparator: latest recorded observation 20–180 minutes before forecast issue time (candidate issue-time persistence). Actual real-time availability latency was not independently verified.
- NOAA sources: https://noaa-gfs-bdp-pds.s3.amazonaws.com/ and https://noaa-ghcnh-pds.s3.amazonaws.com/ ; product https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly.
- Frozen dataset/replay as-of 2026-10-16T23:00Z; source JSON matched by contents and SHA256. Unavailable cases are excluded, not imputed.

## Corrected exploratory result

| Metric | Result |
|---|---:|
| Matched cases | 10 (one calendar month, one site) |
| Forecast lead | +24 hours |
| NOAA GFS MAE | **1.091626 °C** |
| Issue-time persistence MAE | **2.090000 °C** |
| Descriptive MAE difference | +0.998374 °C in favour of GFS |
| PRM-PRED output state | **INSUFFICIENT_HOLDOUT_COVERAGE** |
| Independent source/QC review | NOT DONE |
| Financial, ecological, investment or insurance admission | NONE |

NO statistical confidence or generalization is established from 10 correlated cases. This reports a NOAA model-versus-persistence comparison, NOT a PROMETHEUS forecasting improvement.

### Preliminary comparator superseded
The first trace used a roughly 48-hour-old comparator and excluded one early baseline. Its 9-case GFS MAE 1.098942222 °C and baseline MAE 1.333333333 °C are historically preserved as **superseded**; the corrected same-issuance comparator and 10-case result above are preferred.

## Local candidate evidence custody (not signed Canon)
Independent archive on authorized workstation:

D:\hearth intelligence – Prometheus Sovereign Syntropy\PROMETHEUS\Evidence_Candidates\PRM_PRED_001_R3_NOAA_JAX_20261017.zip

- ZIP SHA256: a8f34fea0229367d1b810d10fe369083cabb51833ff7290d18b9de4d5d9c7a1c
- Bound source-case JSON SHA256: aab1d07341eaf210edfe8c10123131c263e04d3e6f50725a8c310507013cbd2b
- Contains 19 source/derived/script files and a candidate SHA256 inventory; ZIP integrity check passed.
- Raw GRIB slices and station observation bytes are retained. NOAA forecast public cloud availability is not guaranteed permanently.
- Hash matching alone does not authenticate NOAA identity, license, station QC, model provenance or a scientific holdout.

## R3 next gates (remain HOLD)
1. Expand to multiple months and sites, preregister baselines and quality filters; retain forecasts issued before observations and explicitly evaluate station reporting latency.
2. Add temporal-dependence-aware confidence intervals and independently chosen holdout. For probabilistic forecasts add calibration and proper scoring.
3. Independent scientist/reviewer verifies raw forecast decoding, spatial matching, original data rights, versioning, missingness and observational QC.
4. Source steward and runtime maintainers sign review of exact branch; no merge or public deploy before explicit approval.

**Status: Real-data I/O and shadow scoring demonstrated; scientific R3 NOT passed.**
