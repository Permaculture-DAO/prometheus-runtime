# PRM-PRED-001 — Prospective R3 NOAA Evaluation Protocol

**Protocol ID:** `PRM-PRED-PROSPECTIVE-001@0.1-CANDIDATE`  
**Freeze proposal date:** 2026-10-17  
**Classification:** NONCANONICAL / SHADOW / REVIEW-REQUIRED  
**Human scientific preregistration:** NOT YET OBTAINED  
**Source Registry adoption:** NOT AUTHORIZED  
**No public runtime, Canon, underwriting or claims activation.**

## Exact immutable evaluation universe

| Field | Frozen rule |
|---|---|
| Purpose | Evaluate whether archived external NOAA GFS short-range point temperature predictions improve upon an independently sourced climatology; test PRM-PRED evidence gating and abstention |
| Forecast provider | NOAA/NCEP operational Global Forecast System (GFS), not PROMETHEUS |
| Forecast product | `gfs.YYYYMMDD/00/atmos/gfs.t00z.pgrb2.0p25.f{024,048,072}` and companion `.idx` |
| Nominal issue | Every day 00:00 UTC from **2026-10-20** through **2027-01-19** inclusive; date list decided now, not selected by weather |
| Lead times | Precisely +24, +48, +72 hours; no other horizon or opportunistic subsets |
| Sites | GHCNh station `USW00012839` Miami FL, `USW00013874` Atlanta GA, `USW00013889` Jacksonville FL; same fixed locations used for 2025–2026 work |
| Target variable | GFS 2-metre air temperature `TMP:2 m above ground`, station air temperature, Celsius |
| Spatial sample | Nearest 0.25° GFS gridpoint; record gridpoint coords and distance, never infer sub-grid point accuracy |
| Observation source | NOAA GHCNh station hourly temperature with documented source-specific QC rules; ±60 minutes of target; record exact timestamp offset |
| Study universe size | 92 issue dates × 3 sites × 3 leads = **828 planned forecast–site–lead events** |
| Primary comparator | NOAA official `1991–2020 HLY-TEMP-NORMAL` for the fixed station, Fahrenheit converted to Celsius; **local STANDARD time UTC−05:00** for all three sites, even in daylight-saving months |
| Secondary comparator | Preissue station-temperature persistence **only when an independently timestamped snapshot shows its value was available before the corresponding GFS product was acquired**; otherwise baseline and secondary gain remain null / HOLD |
| Primary score | Paired absolute-error improvement `abs(NOAA normal - observed) - abs(GFS - observed)` in °C per horizon |
| Secondary scores | GFS MAE, climate normal MAE, coverage and missingness by station/month/lead, spatial/temporal QC sensitivity; persistence when issue-eligible provenance exists |
| Lead-time analysis | Separate +24/+48/+72 results; do not combine them to manufacture positive skill |
| Non-cherry-picking | Analyze every scheduled issue: missing/failed cases stay in an exclusions ledger with reason codes. No backfill outside declared sources or date range |
| Paired comparison | GFS and normal must use the **same** target observation. Site, timestamp, lead and record hashes must match before scoring |

## Prospectivity and immutable receipts

A future issue qualifies for **candidate prospective evidence** only when (1) this protocol's own public Git commit precedes its nominal issue date, (2) the model forecast raw bytes and companion index are archived with immutable, independently auditable **first-seen receipt time after run initialization but before forecast valid time**, (3) station observation bytes and quality flags are archived after observation becomes available with a second arrival receipt, and (4) source URLs, length, content digest, NOAA product metadata, host identity and UTC clock provenance are preserved.

A local JSON `captured_at` or `available_at` asserted by our own script is **not independent evidence of source publication or trustworthy timestamp**. Any event failing these checks is excluded from an independently prospective claim and remains descriptive. The GFS nominal `00Z` initialization is **not** the product's public-release timestamp.

Do not claim that a protocol put into GitHub is accepted independent preregistration; source steward and an independent scientific reviewer must approve it separately.

## Primary versus secondary evidence

Primary 1991–2020 climate normal is eligible only after an independently reviewed NOAA source snapshot and documented station/time mapping. No weather station value observed before an issue date is assumed to have been *published* before that issue just because its observation timestamp precedes it. Persistence is secondary, omitted when the only available record was retrospectively harmonized.

Freeze/holdout: 2025 and 2026 backtests are **development/discovery data**. They must not be relabelled or blended into this prospective cohort. GFS operational model upgrades or NOAA station metadata changes cause a **version segment** in the audit and possible HOLD; do not conceal version changes through pooling.

## Frozen minimum review thresholds

- Target full cohort: 828, not a guarantee of availability.
- Completeness target: at least **80%** of scheduled forecast–observation pairs **for each individual site and lead**; if not met, report `HOLD_COVERAGE`. Coverage is necessary but not sufficient.
- At least **8 distinct ISO calendar weeks per site/lead** with observed pairs. These thresholds are protocol screening values, **not** an external scientific acceptance standard.
- Report total and per-site/month/lead exclusions, missingness bias, station QC, grid–station distance, observed-at versus first-seen timestamps and documented GFS model version evidence.
- Primary quantitative analysis: paired absolute-error differences by lead, with a **7-day contiguous whole-date block resampling design that preserves simultaneous three-site weather dependence**. Intervals and effective sample size need independent validation. Use a fixed RNG seed derived from the frozen dataset content digest and `PRM-PRED-PROSPECTIVE-001`; record full implementation and draws.
- Holm familywise control across three prespecified lead hypotheses **only after** valid inferential procedure is independently accepted. No significance output should be interpreted as a licence, underwriting authority or reliable causal improvement.
- For any positive finding, require positive effect against the primary comparator plus no documented safety-critical negative subgroup or systematic missing-data selection; otherwise `REVIEW_REQUIRED` / abstain.
- Do not estimate ecological, agricultural, hydrological, land-price, insurance-loss or credit-risk improvements from this atmospheric temperature experiment.

## Source lineage and approval firewall

F — NOAA raw model fields, GHCNh observations, source URLs and evidence receipts (authenticity pending).  
N — signed Canon unchanged.  
A — PRM-ARCH-DET-002@2.0 is controlling architecture.  
M — this candidate methodology, **not accepted** in machine Source Registry.  
X — read-only forecast validity information for land assessment, never an authorization.  
I — PR #29 draft branch; CI success is not governance approval.

**R0 Source Registry HOLD**, **R1 scientific review HOLD**, **R2 human code review HOLD**, **R3 prospectivity data pending**, **R4/R5 release HOLD**. No change to G0–G7, Evidence Spine admission, RAVEL risk bearer, AETERNA probabilities, PRU/RAP/TRBK rights, funding or asset valuation.

### Independent acceptance checklist

1. Source steward authenticates Source Registry and records source ID/typed authority, dependencies and sign-off.
2. NOAA/domain scientist verifies QC code/observation availability, normal-hour alignment, forecast issue vs publication, GRIB model implementation metadata and sensitivity to GFS upgrades.
3. Independent statistician validates effective sample size, weather dependency and intervals; reviews source availability/selection bias.
4. Runtime maintainer/Claude/Codex review exact PR HEAD for security, bypasses and rollback. No approval is assumed.
5. Only separately designated human authority may change branch/rollout/claims, and only after review evidence.

**Decision:** proposal frozen in version control when committed, *not yet independently preregistered or deployed*.