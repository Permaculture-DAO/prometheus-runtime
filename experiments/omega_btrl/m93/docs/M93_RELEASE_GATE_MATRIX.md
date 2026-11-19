# M9.3 — Controlled review candidate, GO/HOLD

| Gate | Proof | Decision |
|---|---|---|
| M9.2 code introduced without redundant M6 snapshot | Parent import paths and source digests | GO local candidate |
| Lab security regression | 51 M9/M9.1/M9.2 cases + 5 M9.3 provenance checks | PASS if reproduced |
| M6 regression in snapshot | 96 pass / 2 skip without native checkout | HOLD two integrated cases |
| mTLS localhost | 2 Uvicorn processes, ephemeral CA, 1/20 advisory | PASS lab only |
| Branch against exact M6 PR #37 SHA | SHA 0778ba2a1bf91366777d4d7911fa8dafee784f25 | GO local patch; no GitHub write |
| Commit authentically signed | PR #37 existing commit unsigned | HOLD |
| Qualified independent review | Zero qualified reviews at baseline check | HOLD |
| VPS staging identity, operator consent and isolation | Not verified | HOLD |
| Multi-host distributed replay / IAM / off-host WORM audit | Not implemented | HOLD |
| GitHub merge / Holochain installation / production | Not authorized | HOLD |

Neither a successful lab test nor a verified commit gives source-custodian authorization or independent security approval.
