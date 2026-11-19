# M9.3 — Signing and independent review gate

- M6 PR #37 commit: `0778ba2a1bf91366777d4d7911fa8dafee784f25`; GitHub verification `unsigned` at M9.3 check.
- **Do not create a test key and call it a maintainer signature.** Signing must use the legitimate maintainer-controlled account/key or a formally documented exception accepted by repository policy.
- Publish an add-only M9.3 branch after explicit authorization; do not force push to PR #37. Prefer incremental PR with base branch `review/omega-btrl-m6-shadow`, then reconcile against `main` after the base PR is reviewed.
- A reviewer should be a named qualified human independent of the author/release promoter, disclose conflicts, and review the exact branch HEAD SHA and threat model.
- CODEOWNERS in runtime points to `@Uwohali`, which alone is not evidence of independent review.
- Record signed commit verification, source SHA, CI logs, issues, reviewer verdict, release operator sign-off and rollback evidence before proposing a merge.
- Cryptographic verification of the commit is necessary but insufficient: Canon custody, governance and third-party security checks remain separate.

## M9.7 CI compatibility correction (review required)

The signed M9.3 head exposed two legacy CI blockers on PR #38: the M6 workflow
does not yet allow the new M9.3 workflow path, and the native S0 validator rejects
five empty Python namespace files. A follow-up, independently signed corrective
commit proposes **37 added M9.3 files and exactly one existing workflow modified**
relative to base M6. The M9.3 diff validator permits only that single pre-existing
CI workflow modification, not native code or any other pre-existing file. This
amends the earlier add-only constraint explicitly and requires maintainer consent
and independent review; it is not a completed security review or merge approval.
