# PRM-PRED-001 — Prospective cohort freeze and NOAA source-review handoff

**2026-10-17 · Candidate only · Not a human-approved scientific preregistration**.

## Frozen protocol identity

- Candidate protocol: `docs/methodology/PRM_PRED_001_PROSPECTIVE_PROTOCOL_v0_1_FROZEN_CANDIDATE.md`.
- First public Git commit containing protocol text: `d8eda9b5994f162f56f27f3b5f82bbe78b97ac3e`. Git source history provides an externally inspectable code/document change record, **not** a human signature, certified trusted timestamp, or accepted Canon source.
- Future issue population: **2026-10-20 00Z to 2027-01-19 00Z**, inclusive, 92 daily NOAA GFS operational 00Z cycles. Exactly **828 forecast×site×lead events** across NOAA stations USW00012839, USW00013874, USW00013889 and +24/+48/+72h horizons.
- Deterministically generated `PLANNED_EVENTS_828.json` schedule SHA256:
  `a2e8f08d8c9687a4a8cee1b63a0437b969642295ccb395e64cc58bc4e853b1f0`.
- Local noncanonical candidate archive:
  `D:\hearth intelligence – Prometheus Sovereign Syntropy\PROMETHEUS\Evidence_Candidates\PRM_PRED_001_FROZEN_FUTURE_SCHEDULE_828_20261017.zip`.
- Archive SHA256: `db16e153de1dfcc705bbdefeb921fd3a3f10ee0b0fb7f62b0a6941a72599ce4c`; ZIP size **9,140 bytes**, ZIP structural integrity tested; contains protocol, 828 planned records and a per-file candidate manifest.

## Pre-issue capture constraint — what the code really does

`services/api/app/predictability_prospective_guard.py`:

- derives the schedule *without looking at any NOAA forecast or observed outcomes*;
- screens only dates inside frozen window, nominal 00Z issue, allowed three stations and +24/+48/+72h;
- requires exact 00Z NOAA S3 GFS field **and corresponding index URL** for issue date and lead (not just arbitrary URLs on an allowed domain);
- requires local first-seen receipt times after nominal issue and before target and within an exploratory 12-hour upper bound;
- forbids target station observations taken outside ±60 minutes of target and snapshots claiming acquisition before the physical measurement;
- maintains official NOAA 1991–2020 hourly climate normal as PRIMARY comparator; timestamped persistence is only SECONDARY with pre-issue receipt chronology;
- returns **`LOCAL_CHRONOLOGY_PLAUSIBLE_UNVERIFIED` at best**, never independent source authenticity, trusted timestamp attestation, validated skill, investment gate or production approval. Missing observations remain HOLD.

**No future NOAA data have yet been captured under this protocol.** No background service, scheduled download, cron job, release flag, merge or deploy was created. No production runtime has changed.

## New source-version insight

Read-only ecCodes metadata inspection of 2025-02-03 and 2026-02-03 NOAA GFS +24h 2m-temperature GRIB2 fields:

- 2025 field SHA256: `451f3b0512ff1666843d5a57d803dc8da44a0ed9c368727dc81b24e1201d847a`.
- 2026 field SHA256: `ea8bf09dda8a149cc1bafae97ad1bd9901ffa106833ccb483abe4ab6c004abcf`.
- Both report `centre=kwbc`, `edition=2`, `generatingProcessIdentifier=96`, table versions `2/1`, `shortName=2t`, `stepRange=24`.
- These field metadata **cannot attest** whether GFS source/assimilation/physics versions were identical. NOAA's public GFSv17 evaluation describes a candidate future upgrade; a planned Q1FY27 deployment must not be treated as an already operational release.
- Official NOAA implementation history: https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs/implementations.php
- Official GFSv17 evaluation: https://www.emc.ncep.noaa.gov/users/meg/gfsv17/

## Independence and governance prerequisites

**R0 HOLD:** exact active machine Source Registry (named by controlling uploaded `PRM-ROOT-SOURCES-001`) not authenticated from GitHub and inspected local mirror. Steward must provide signed accepted copy.

**R1 HOLD:** independent scientific reviewer/NOAA dataset expert must verify GHCNh data first-publication behavior, source-conditional QC, normal standard-time mapping, forecast product release, software version and source usage terms.

**R2:** candidate pure software locally tested; exact-head CI and independent architecture review required. Claude/Codex have not formally reviewed the new code.

**R3 HOLD:** prospective planned issue days are FUTURE; no observed paired scores can be calculated now; no independently trusted event receipts or time series have been recorded. Do not use 2025/2026 retrospective data for this prospective sample.

**R4/R5 HOLD:** no Canon amendment, runtime SHADOW enablement, live deployment, land/financial/insurance validation, guaranteed prediction or TRBK token capital rights. Raw data/receipts future ingestion requires a separate approved, authenticated collector, including rollback and retention policy.
