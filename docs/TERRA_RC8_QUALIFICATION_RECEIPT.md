# TERRA RC8 — qualification receipt
Status: TEST_ONLY / HOLD_REAL / HOLD_PRODUCTION. Internal qualification, not independent assurance.
Frozen RC7 runtime 2e216c7887a87902b23f759d4333bcf0e4c62808; canon cbfa12103460510eec255c9f5720a221f618ba5f. All four RC7 CI checks completed successfully. PR review lists empty on inspection.

## Synthetic benchmark
scripts/terra_rc8_benchmark.py (final script commit 8cde1e74e51e4fde8e893c22159ee208ce714cf1) executed in isolated WSL Python environment. Eight raw rows, six unique evidence entries, four distinct parcel identifiers, one conflict and one stale observation. Initial 7/8 checks: exact evidence oracle had FLOIE and FL-LAND in wrong lexical order. Diagnostic replay confirmed same values and provenance, only order differed. Corrected oracle, no engine change; 8/8 checks passed. Reconciliation and delta hashes unchanged across correction. Initial report SHA256 acd9ea2479a426b4517c43bee657c6d17dbd8e1849c2bd0edcf7172ef61e7c92; corrected report SHA256 55e620162bca484d597721ae9a8490bd3e017368330b0cf5711e644eba49b141. Reconciliation elapsed 0.0031s in one observed run, not a comparative performance result.
Expert/spreadsheet comparison NOT_RUN, human review time UNKNOWN, complexity comparison NOT_MEASURED. A hand-authored oracle from the same review session is not independent validation.

## Qualification manifest
docs/TERRA_RC8_QUALIFICATION_MANIFEST.json, commit 389cbfe23c67f106f6c1441dec39826e287b7bf0: 27 runtime and 7 canon changed files, individual SHA256 from WSL clean tracked worktrees at the listed inputs. Excludes the manifest and subsequent receipt/delta. Unsigned, not a full release package.

## Source admission documentary delta
USGS 3DEP 1/3 arc-second: catalog https://data.usgs.gov/datacatalog/data/USGS%3A3a81321b-c153-416f-98b7-cc8e5f0e17c3 public-domain label. Official FAQ https://www.usgs.gov/faqs/what-projection-horizontal-datum-vertical-datum-and-resolution-a-usgs-digital-elevation-model identifies geographic coordinates, NAD83 and typically NAVD88. Official accuracy FAQ https://www.usgs.gov/faqs/what-vertical-accuracy-3d-elevation-program-3dep-dems reports approximately 0.82 m RMSE for contiguous US product as of 2022, not site-specific accuracy. Product metadata https://www.usgs.gov/ngp-standards-and-specifications/3dep-product-metadata. No local tile selected or downloaded; site-specific provenance/accuracy and admission UNKNOWN.
USFWS NWI state downloads https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data offers Florida state packages and project metadata with mapping location/time. Disclaimer https://www.fws.gov/page/wetlands-geodatabase-disclaimer and limitations https://www.fws.gov/page/wetlands-data-limitations-exclusions-and-precautions prohibit interpreting mapped presence/absence as regulatory determination. No data downloaded, version or local coverage verified, no legal conclusion. Both sources HOLD_REAL. PRYCD rights still unresolved.

## Interface review
Bridge src/policy.mjs blob da2c29aeae93a9b0e04030d98ca7972577c36180: explicit GET allowlist does not contain TERRA, standard boundary/non-offering/canonical_source envelope. Console README blob 19eaf7a74fe3afa7a00534c3c69d8baad6b42c9a: pilot display only. Proposed future read-only route GET /terra/status, fixed upstream candidate path /v1/terra/status, preserve qualifiers, deny on invalid/missing response, do not cache a stale positive claim. No route change, deployment or frontend implementation. Independent approval required.

## Decision
Internal synthetic qualification PASS. Independent review, expert comparison, dataset-specific admission, actual archive reconciliation, Bridge/Console review and authorized release remain pending. No new runtime kernel. No data acquisition, rights, capital or production admission.
