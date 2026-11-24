# TERRA RC1 — standalone synthetic runtime candidate

No external connections, REAL inputs, service endpoints or production deployment. This is a sidecar prototype, not yet wired to existing S3–S6 or Evidence Spine. Existing runtime gate configurations stay unchanged.

From this directory:
`python3 -m unittest -v`
`python3 terra.py fixture.json`

Contract: nonempty JSON list, max 1000 observations / 1 MB; exact string fields and synthetic identifiers. See terra.py for enforced contract. Exact APN per test jurisdiction only; no real deduplication or title claims. Acreage converted exactly to square feet; USD to cent precision. Preserve observations and same-day conflicts. No actual property represented. Result always HOLD; no capital or legal authority.

Next: approved Source Registry/lineage, integration ADR, real-data rights, licensed adapters, reviewed S3–S6 interface, CI and security review. No deployment or scheduling.


RC2 update: the normalization core now resides in services/api/app/terra_property_core.py. This directory remains the historical CLI/test compatibility entrypoint. See docs/TERRA_RC2_RUNTIME_INTEGRATION.md for the separate native offline adapter and S6 reference packaging. No live ingestion or production integration.
