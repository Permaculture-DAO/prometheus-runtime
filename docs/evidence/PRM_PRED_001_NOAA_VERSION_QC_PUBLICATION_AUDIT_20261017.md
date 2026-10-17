# PRM-PRED-001 — NOAA source/version and observation-publication admissibility review

**Date:** 2026-10-17  
**Classification:** candidate scientific-source review / NONCANONICAL / R0 and R1/R3 HOLD

## A. NOAA GRIB header comparison conducted

Two *actual* NOAA GFS 00Z, +24 h, 2m-temperature GRIB2 fields were decoded with ecCodes from the read-only research cache:

| Field | 2025-02-03 00Z +24h | 2026-02-03 00Z +24h |
|---|---|---|
| Raw field SHA256 | `451f3b0512ff1666843d5a57d803dc8da44a0ed9c368727dc81b24e1201d847a` | `ea8bf09dda8a149cc1bafae97ad1bd9901ffa106833ccb483abe4ab6c004abcf` |
| centre | `kwbc` | `kwbc` |
| GRIB edition | `2` | `2` |
| tablesVersion / localTablesVersion | `2 / 1` | `2 / 1` |
| generatingProcessIdentifier | `96` | `96` |
| typeOfGeneratingProcess | `2` | `2` |
| productionStatusOfProcessedData | `0` | `0` |
| shortName / stepRange | `2t / 24` | `2t / 24` |

**Conclusion:** These GRIB metadata agree for the sampled fields; **they do NOT uniquely identify NOAA's installed GFS source-code version, physics, data assimilation or operational change history**. Do not label either archive as GFSv16 or GFSv17 based on generatingProcessIdentifier=96. Exact model version metadata remains unverified.

Authoritative verification references:

- NCEP/EMC GFS implementations: https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs/implementations.php
- NCEP/EMC GFSv17 field evaluation, including proposed Q1 FY2027 implementation window: https://www.emc.ncep.noaa.gov/users/meg/gfsv17/
- Model implementation schedules and **actual operational** change notices must be reconciled to each specific forecast issue time. A planned upgrade is not evidence that it occurred.

## B. NOAA GHCNh observation availability is not a model-issue timestamp

NOAA's GHCNh is an integrated, harmonized dataset from heterogeneous sources, not a ledger of when every temperature value was accessible to a real-time operator. GHCNh data may be updated later. An observation timestamp `2025-02-03T23:00Z` does **not** establish that it was published before a `2025-02-04T00:00Z` forecast.

- NOAA official GHCNh product: https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly
- NOAA QC documentation: https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh_DOCUMENTATION.pdf
- Documented legacy QC source group `220, 221, 222, 223, 347, 348`: code `1 = Good`; the same code is not universally semantically identical across all GHCNh sources.

**Operational consequence:** Historical persistence baselines calculated using retrospective station archives remain **caller-declared and unverified as available-at-issue**. Prospective benchmark policy uses pre-existing NOAA 1991–2020 hourly normals as PRIMARY. Persistence becomes SECONDARY only if receipt time, source identity and availability are independently evidenced.

## C. Prospective source-capture audit protocol

Before each target observation, preserve:
- full NOAA `.idx` and precisely range-requested 2m `GRIB2` bytes;
- exact raw NOAA URL for issue date, run and lead; HTTP status, `Date`, `Last-Modified`, `ETag`, `Content-Length`, byte range and SHA256;
- locally recorded first-seen UTC, independent external trusted time / signature where available, host clock status, version of capture software and no overwrite of a prior receipt;
- later NOAA GHCNh observation source snapshot, original record + source-specific QC, observation timestamp, source fetch receipt, temporal/spatial matching notes;
- independent normals file hash, station metadata and conversion mapping (Fahrenheit to Celsius; local STANDARD time, no DST shift).

HTTP `Last-Modified` and `Date` alone are **not** authenticated forecasts of original publication time; S3 object replacements can alter timestamps. Obtain independent review of availability evidence rather than promoting it automatically.

## D. Source/Governance boundary

The project's uploaded `PRM-ROOT-SOURCES-001` manifest identifies `PROMETHEUS_SOURCE_REGISTRY_v1_0.yaml` as controlling machine registry and suggests `prometheus-canon/governance/sources/`. A read-only inspection of the accessible Canon clone and GitHub search did **not** locate a verifiable controlling registry. This is a **missing-authority blocker**, not a licence to create a replacement source registry.

- R0: HOLD until source steward produces authenticated registry and approved source IDs/hashes.
- R1/R3: HOLD pending independent NOAA/domain scientific review of version, QC and publication-latency claims.
- R2: code candidate only, draft PR, CI not sufficient for source approval.
- R4/R5: HOLD; no runtime enablement, merge, public forecast-skill claim or land/finance/insurance use.
