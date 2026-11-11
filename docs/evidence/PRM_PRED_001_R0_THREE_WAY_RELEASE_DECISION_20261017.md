# PRM-PRED-001 — R0 release authority decision dossier (2026-10-17)

**Classification:** evidence candidate / noncanonical / NOT a Source Registry update.  
**Disposition:** R0 `HOLD_PENDING_AUTHORITY_ADOPTION`. **Do not merge PR #29 or deploy.**

## Controlled evidence recovered

Original user-supplied `Addestramento.zip` contains two byte-identical copies of `PROMETHEUS_SOURCE_REGISTRY_v1_0.yaml`, including its 2026-10-08 `github_mirror/governance/sources/` location. Registry SHA256: `8e72b98dbaa127f6f8d11e064aceb1012cf0ba98d47bf7aedbe8706a88bb6d0e`. Registry effective date 2026-10-07, global architecture ID `PRM-ARCH-DET-002`. Existence and matching bytes are **not proof of current steward-adopted authority**.

The archive's 2026-10-08 `PATCH_REPORT.json` asserts `semantic_architecture_change=false` and records post-patch hashes. Its `post_patch/PROMETHEUS_SOURCE_ROOT_v2_0_SHA256SUMS.txt` matches all four post-patch file hashes and the SHA256SUMS hash recorded by the report. This establishes internal historical package consistency; it **does not independently prove the patch's semantic claim or an authorized release**.

## Deterministic three-way source revision matrix

| Source ID | registry / root SHA256 | pre_patch = separately uploaded SHA256 | post_patch SHA256 |
|---|---|---|---|
| PRM-ARCH-DET-002 | `bbc6423b38f5a3b70d7b2e486fae1b51ddc1cbba654ce48c756cea5e8d56d138` | `83f42dcac3f9053b011eeb2b2963862d23c9ab0be35ee467499c99dcafd1e1c7` | `37696d97a6d9e577e2124e6fb0d9f6e379f2e8e1bf8d02c781c9f2b4da6b4c6d` |
| PRM-RISK-AETERNA-001 | `6c4cfffe4e8834794366ac24dbe6ae87add2fd1c822e187994e1211a1b8ecbcf` | `1fc0656f60a73ef6c067e7a1a15e83e28dfdddd68575202ce47ad5e0ebd767d3` | `36250bdf86b558af92373f5495b480549378a06792a02eeb20986b7c7339c2d5` |
| PRM-RISK-RAVEL-OP-002 | `3fdb7e1727e464fca484edab75f05b70fdf782c1787328f735e6b6250848a423` | `ea5c228ff48ca1e30738aaa2eea8cf88e8c70c38726096ba43c0a6f03f3a9ff5` | `053b66d59c6efcea4847b51fc4c696e941dae4bf8cf68ae258d5538a2861c4bd` |
| PRM-CIV-APP-006 | `1096fdb0688c659af48cf8afa64b2a2b4e33fb6774762b0cd40831d50a80a355` | `3710dbc02b63f43d74b7aa03fd2fa584e27ef26a9e0866add2139a296ea99ece` | `a49d9a96caab444fec1c973a09736b201e0039ff534f3f798e1d92120d0e659a` |

The Root Source Manifest also has different `root`, `pre_patch` and `post_patch` digests. The separately uploaded Manifest matches `pre_patch`.

## Normalized content differences: root to post_patch

- Global architecture: separates a combined human-facing governance/capital line into two lines.
- AETERNA: separates one combined defect/version mismatch line; changes a human-facing title from `Aeterna Risk Synergy` to `Aeterna RISK SYNERGY`.
- RAVEL: no differing UTF-8 text lines after line-ending normalization, despite changed serialized bytes.
- Civilizational source: one empty line added. Many byte changes are explained by serialization/line-ending differences.

These findings **support** the archived patch author's claim of editorial/human-facing changes; they do not prove all semantics or authority automatically.

## Steward decisions required, in order

1. Authenticate who adopted the controlling registry, at which Git commit and release date, with review/signature or explicitly executed governance acceptance.
2. Determine whether the old registry-matched `root` is still authoritative or whether the `post_patch` release was adopted. No automatic precedence from filenames or timestamps.
3. If `post_patch` approved, emit a **new controlled** registry/manifest/hash release without rewriting original snapshots, resolve upstream dependencies, version and supersession, and obtain independently recorded acceptance.
4. If approval is unavailable, retain all three series as historical evidence and R0 HOLD; **never** silently mark PRM-PRED-001 registered.
5. Request separate R1 science review of NOAA data/QC/latency and R2 code review at exact PR head before any bounded shadow collection proposal.

## Prohibited automatic actions

No edits to Canon, source registry, authority lattice, core architecture, AETERNA, RAVEL, public runtime, Holochain write path, land/capital insurance claims or production collector. The current PR remains draft/non-authoritative.

**Gate result:** recovered and reproducibly reconciled historic source hashes; current acceptance still missing. `R0=HOLD`, `R1=HOLD`, `R2_SOFTWARE=PASS_TECHNICAL_ONLY`, `R3–R5=HOLD`.
