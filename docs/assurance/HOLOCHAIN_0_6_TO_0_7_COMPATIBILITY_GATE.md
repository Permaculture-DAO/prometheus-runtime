# Holochain 0.6.1 → 0.7 Compatibility Gate

Status: HOLD / migration not authorized
Date: 2026-09-27

## Current baseline

The Genesis runtime/deployment candidate remains pinned to Holochain conductor/core `0.6.1` and `hc` `0.6.1`. A dependency update that moves the JavaScript client onto a Holochain 0.7 line is therefore an architecture/runtime migration, not a routine dependency refresh.

## Rule

Do not merge a 0.7-line client/runtime dependency into the Genesis candidate merely because unit CI passes. The migration requires an explicit compatibility decision and end-to-end evidence.

## Required compatibility matrix

Evaluate and record at minimum:

- conductor/core version;
- `hc` CLI version;
- HDK/HDI versions;
- Holonix/Nix baseline;
- Rust toolchain;
- JavaScript/TypeScript Holochain client;
- hApp/DNA bundle compatibility;
- admin websocket API;
- app websocket API;
- authentication/signing behavior;
- zome-call behavior;
- bridge/runtime adapter behavior;
- console/UI behavior;
- sandbox creation/reuse;
- persistence and action-hash/receipt semantics;
- CI and clean-checkout build;
- backup/restore and rollback.

## Required test path

`clean checkout → build → sandbox/conductor → install/enable hApp → app websocket → runtime adapter → read-only bridge → console ingress → smoke proof → evidence write/read path → restart → rollback test`

No step may rely on an already-running stale process or undeclared local dependency.

## Security review

Before migration approval, confirm that the new line does not weaken loopback-only Holochain admin/app interfaces, capability/authentication controls, evidence identity, real-data admission, secret handling or fail-closed version checks.

## Dependency strategy

Security fixes that can be applied while retaining compatibility with the approved 0.6.1 Genesis line should be assessed separately from the 0.7 migration. Do not use a security patch as an implicit architecture migration vehicle.

## Exit criteria

Migration can be proposed for approval only when:

1. the matrix is complete;
2. clean-checkout end-to-end tests pass;
3. persisted evidence compatibility/migration is demonstrated;
4. rollback is demonstrated;
5. claim/canonical semantics are unchanged or separately change-controlled;
6. the Release/Gate review explicitly authorizes the version-line change.

## Claim boundary

Runtime migration evidence is engineering evidence only. It does not establish scientific validation, field validation, certification, ecological outcome, token rights or financial value.
