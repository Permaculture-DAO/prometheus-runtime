# M9.3 — Signing and independent review gate

- M6 PR #37 commit: `0778ba2a1bf91366777d4d7911fa8dafee784f25`; GitHub verification `unsigned` at M9.3 check.
- **Do not create a test key and call it a maintainer signature.** Signing must use the legitimate maintainer-controlled account/key or a formally documented exception accepted by repository policy.
- Publish an add-only M9.3 branch after explicit authorization; do not force push to PR #37. Prefer incremental PR with base branch `review/omega-btrl-m6-shadow`, then reconcile against `main` after the base PR is reviewed.
- A reviewer should be a named qualified human independent of the author/release promoter, disclose conflicts, and review the exact branch HEAD SHA and threat model.
- CODEOWNERS in runtime points to `@Uwohali`, which alone is not evidence of independent review.
- Record signed commit verification, source SHA, CI logs, issues, reviewer verdict, release operator sign-off and rollback evidence before proposing a merge.
- Cryptographic verification of the commit is necessary but insufficient: Canon custody, governance and third-party security checks remain separate.
