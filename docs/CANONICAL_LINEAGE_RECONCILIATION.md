# Canonical lineage reconciliation

## The discrepancy

`config/canonical_release.json` previously declared `canonical_root:
PROMETHEUS-CANON-ROOT-v7.0` and `canonical_release: PROMETHEUS-CWP-v7.0-20260704`.
The org's published, signed canon (`Permaculture-DAO/prometheus-canon`, mirrored in
`Permaculture-DAO/prometheus-canonical-releases/CURRENT_RELEASE`) is
`v1.1.2-genesis` — the Prometheus v1.1 Genesis Institutional Canonical Line. The
two identifiers never cross-referenced each other, and `prometheus-canon` contains
no mention of a `v7.0` line anywhere.

## Decision

Confirmed by the founder/steward (Uwohali), 2026-07-05: **the v1.1 Genesis line is
the authoritative canon root.** `canonical_root` and `canonical_release` in this
file now point at `PROMETHEUS-CANON-ROOT-v1.1` / `v1.1.2-genesis`.

The other `v7.0.x`-labelled fields in this file (`runtime_build`,
`documentary_patch`, `audit_convergence_patch`, `erratum_register`) are left
unchanged. They appear to be internal runtime build and documentary-patch tracking
identifiers with their own local documentary trail, distinct from canon identity —
they are **not** canon-authority claims and must not be read as such. If those
labels are meant to align to the v1.1 line's own versioning, that is a separate
follow-up for whoever owns that documentary track, not something inferred here.

## Rule going forward

Only `canonical_root` and `canonical_release` in this file assert canon authority.
Any new field that looks like it could be read as a competing canon identifier
must either point at the v1.1 Genesis line or be clearly namespaced as
internal-only (e.g. `*_internal_build`, `*_patch_id`) so it cannot be mistaken for
canon.
