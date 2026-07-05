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

## Boot-document integrity — VERIFIED 2026-07-05

The four `*_v7.0*` documents in `document_integrity.json` are **real and hash-correct**.
Verified against the source `PROMETHEUS_v7_0_3_AUDIT_CONVERGENCE_PATCH` (`01_CANON/`):
all four SHA-256 and byte-lengths match the recorded values exactly —

| Document | Bytes | SHA-256 (recorded == actual) |
|---|---|---|
| `01_Canonical_White_Paper_v7.0_EN.docx` | 442199 | `1bd348bf…c221bd0f` ✓ |
| `02_Canonical_White_Paper_FULL_v7.0_EN.docx` | 475852 | `17e06917…b4b30bf8` ✓ |
| `03_Canonical_White_Paper_FULL_CORPUS_v7.0.1_EN.docx` | 3881717 | `c9e31b60…5833b63d` ✓ |
| `04_Master_Audit_Prompt_DEFINITIVE_v7.0.3_EN.md` | 11239 | `e5ac8407…034bb935` ✓ |

So the runtime's boot-time fail-closed integrity gate points at a genuine,
internally-coherent `v7.0.x` document set — not phantom paths. This confirms the
"mapped, not merged" posture: the v7.0.x documentary track is real and verifiable, and
subordinate to the v1.1 Genesis canon authority.

## Optional future follow-up (steward-owned, not blocking)

These v7.0.x boot documents are distinct from the published `v1.1.2-genesis` white paper
(different content, different hashes). Re-anchoring the runtime to verify the v1.1 canon
documents *directly* would require the actual v1.1 canon DOCX set + regenerated hashes —
a canon-custody + deploy-mounting decision, deliberately **not** inferred or fabricated
here. Until then the mapping (v7.0.x runtime track ⊂ v1.1 canon authority) is the
governing arrangement.

## Rule going forward

`canon_authority` is the only field that asserts canon authority, and it must always
resolve to the v1.1 Genesis line. Every `v7.0.x` label in this repo is an internal
runtime/documentary identifier subordinate to that authority, and must not be read as
a competing canon.
