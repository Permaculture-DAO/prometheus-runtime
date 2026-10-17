# PRM-PRED-001 — Capture Pre-Activation Review

2026-10-17 | Candidate implementation only | NO COLLECTOR ACTIVATION.

## Function implemented
The offline pure module services/api/app/predictability_capture_receipt.py validates externally provided NOAA GFS raw index and GRIB2 bytes; exact 00Z S3 product path; single 2m temperature entry with increasing offsets; HTTP 200 index and HTTP 206 exact range, field length and GRIB envelope; raw SHA256; and bounded local first-seen chronology. It labels all supplied HTTP headers and local clock timestamps UNTRUSTED. No network request, storage service, timer, scheduled workflow, Canon admission or runtime deploy is implemented.

Real stored NOAA 2026-02-03 +24h indexed GRIB field replay: indexed bytes 417569191–418459236; actual field 890046 bytes; length and field digest match the saved archived NOAA field SHA256 ea8bf09dda8a149cc1bafae97ad1bd9901ffa106833ccb483abe4ab6c004abcf.

## Mandatory pre-activation gates
1. R0: authenticate recovered active Source Registry, reconcile multiple versions and obtain steward signoff.
2. R1: independent scientific confirmation of GHCNh source-specific QC, historical data revision/publication lag, climatology LST=UTC-5 conversion for the three study sites, GFS operational model versions and legal use terms.
3. R2: maintainer/Claude/Codex security review of exact HEAD; verify no source trust bypass or data poisoning, immutable independent audit receipts, host clock synchronization, retry policy, rate limits, data retention and STOP/rollback.
4. R3: acquire a reviewed independent timestamp attestation mechanism (e.g. validated RFC3161 responses or equivalent trusted third party). HTTP Date/ETag/Last-Modified and a local time string alone DO NOT prove first-publication timing.
5. Establish observable before-issue station snapshots if using persistence comparator. A 00Z collector cannot retrospectively prove an earlier station reading was available before 00Z; use NOAA 1991–2020 hourly normal as primary comparator.
6. Obtain explicit human written authorization for any separately deployed, default-off evidence-collection collector and disaster-recovery runbook. This is NOT authorization to enable main runtime, Canon amendments, forecast-skill claims, land, credit, insurance, capital or token authority.

## Status
Collector not started or scheduled; future NOAA data not acquired under frozen protocol. R0, independent source validation, model scientific approval and governance activation remain HOLD.