# Canonical lineage reconciliation

## The two lineages

- **Canon authority (governing):** the org's signed **v1.1 Genesis Institutional
  Canonical Line** — `PROMETHEUS-CANON-ROOT-v1.1`, held in
  `Permaculture-DAO/prometheus-canon`, published/signed as `v1.1.2-genesis` in
  `Permaculture-DAO/prometheus-canonical-releases`.
- **Runtime internal documentary track (subordinate):** this runtime is natively
  built on an internal **`v7.0.x`** documentary system — `PROMETHEUS-CANON-ROOT-v7.0`
  / `PROMETHEUS-CWP-v7.0-20260704`, with its own gate review
  (`PROMETHEUS-GR-v7.0-002`), runtime build (`PROMETHEUS-RUNTIME-v7.0.1`),
  documentary/audit patches, erratum register, and the four boot-verified documents
  in [`../config/document_integrity.json`](../config/document_integrity.json).

## Decision (founder/steward, 2026-07-05)

**The v1.1 Genesis line is the canon authority. The runtime keeps its internal
`v7.0.x` documentary track, subordinate to and mapped onto v1.1.** The two are
*mapped, not merged*: the runtime's config and boot-time integrity remain internally
`v7.0.x`-coherent, while every canon-authority claim resolves to v1.1 Genesis.

This supersedes an earlier partial attempt (PR #8) that flipped only
`canonical_release.json`'s `canonical_root` to v1.1, which left the runtime config
internally inconsistent (one file v1.1, all others — `gate_status.json`,
`claims_register.json`, `document_integrity.json`, `.env.example`, `settings.py` —
still v7.0). That flip has been reverted; coherence is restored by keeping the whole
runtime track on `v7.0.x` and recording the v1.1 authority explicitly via the new
`canon_authority` field.

## What is `v7.0.x` vs what is canon

| Field / artifact | Lineage | Meaning |
|---|---|---|
| `canon_authority` (canonical_release.json) | **v1.1** | The governing canon. Sole canon-authority reference. |
| `canonical_root` / `canonical_release` | v7.0.x | The runtime's internal documentary release it boots against. |
| `gate_status.json` `canonical_root`, `gate_review` | v7.0.x | Internal gate review of the v7.0.x documentary set. |
| `document_integrity.json` files + hashes | v7.0.x | The internal documents the runtime fail-closes against at boot. |
| `runtime_build`, `documentary_patch`, `audit_convergence_patch`, `erratum_register` | v7.0.x | Internal build/documentary tracking identifiers. |

## Open follow-up (not blocking, steward-owned)

The runtime boots against the four `*_v7.0*` documents in `document_integrity.json`,
whose hashes are distinct from the published `v1.1.2-genesis` white paper. If/when the
runtime should verify against the v1.1 canon documents directly, that requires the
actual v1.1 canon DOCX set + regenerated hashes — a canon-custody + deploy-mounting
action, deliberately **not** inferred or fabricated here.

## Rule going forward

`canon_authority` is the only field that asserts canon authority, and it must always
resolve to the v1.1 Genesis line. Every `v7.0.x` label in this repo is an internal
runtime/documentary identifier subordinate to that authority, and must not be read as
a competing canon.
