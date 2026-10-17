# PRM-PRED-001 — R0 Archive Registry Recovery Audit

2026-10-17 | NONCANONICAL CANDIDATE | R0 HOLD, steward acceptance absent.

## Source recovery
User-supplied Addestramento.zip contains two byte-identical original machine registry YAML copies: at Addestramento/PROMPT MASTER DI PROMETHEUS/PROMETHEUS_SOURCE_REGISTRY_v1_0.yaml and at _releases/2026-10-08_Civilizational_Current_Source_Reconciliation/github_mirror/governance/sources/PROMETHEUS_SOURCE_REGISTRY_v1_0.yaml. 4106 bytes; SHA256 8e72b98dbaa127f6f8d11e064aceb1012cf0ba98d47bf7aedbe8706a88bb6d0e. Embedded effective date 2026-10-07 and root PRM-ARCH-DET-002.

## Hash reconciliation
Matching uploaded files: Canon Full Corpus SHA256 6f0140a9821e2546cf70665409845c7e77ccc9bd6a89a824bfb77f8319e362f8 and Master Prompt v3 SHA256 94d5d9b5514fc463462d33579adef3376006bbaec111794651bf51ee0c35f760.

Four separate uploaded versions DIFFER from hashes in the archived machine registry, although original archive root copies and release github_mirror copies MATCH:
- Architecture PRM-ARCH-DET-002 registry bbc6423b38f5a3b70d7b2e486fae1b51ddc1cbba654ce48c756cea5e8d56d138 vs separate upload 83f42dcac3f9053b...
- AETERNA PRM-RISK-AETERNA-001 registry 6c4cfffe4e8834794366ac24dbe6ae87add2fd1c822e187994e1211a1b8ecbcf vs upload 1fc0656f60a7...
- RAVEL PRM-RISK-RAVEL-OP-002 registry 3fdb7e1727e464fca484edab75f05b70fdf782c1787328f735e6b6250848a423 vs upload ea5c228ff48c...
- Civilizational PRM-CIV-APP-006 registry 1096fdb0688c659af48cf8afa64b2a2b4e33fb6774762b0cd40831d50a80a355 vs upload 3710dbc02b63...

The four uploaded versions correspond to pre_patch copies, while archive root and github_mirror match the registry and post_patch copies contain additional different revisions. These facts do NOT prove which candidate had final authority, supersession approval or signature. Registry contains no PRM-PRED-001 entry.

## Disposition
R0 is now SOURCE_FILE_FOUND_HASH_RECONCILABLE_CURRENT_AUTHORITY_UNVERIFIED / HOLD. Custodian must authenticate provenance, reconcile pre_patch/root/post_patch against authorized release signatures and accept current registry before PRM-PRED source registration. Do not change Canon or fabricate a machine registry in GitHub. The read-only audit report and original recovered registry are preserved separately.