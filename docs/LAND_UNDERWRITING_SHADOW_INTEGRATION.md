# Land underwriting shadow reconciliation — 2026-10-17

Engineering candidate only, subordinate to the current canon and [runtime boundary](RUNTIME_BOUNDARY.md) and [RAVEL boundary](RAVEL_RUNTIME_BOUNDARY.md). HEAD and local origin/main both resolve to `6c74fb75e99da31f9bb6c76574a9ce131cfc608f`; no remote refresh was performed. The three files were initially untracked and are now staged for a candidate commit; no commit or push has been completed. The existing controls, PRU, RAVEL, controls tests and boundary documents are present and were read. Previous candidate assertions that they were absent are withdrawn. No project AGENTS.md was found in the checkout or checked ancestor locations.

The independent Claude red-team report at `independent Claude review dated 2026-10-17` was read before this targeted repair. B3 is addressed by removing the residual valuation calculation entirely. This adapter now validates bounded input completeness only. These engineering changes do not establish scientific, legal, valuation or underwriting validity, or independent reviewer acceptance.

## Exact v2 request

Call `app.land_underwriting.evaluate_land_underwriting(payload)` directly. No HTTP route, persistence, source fetch, clock read or evidence generator is added. All fields below are required; extra fields at every object level fail with ValueError. Version v1 is deliberately rejected.

| Object | Exact fields and rules |
| --- | --- |
| Request | `schema_version`, `site_id`, `dossier_id`, `as_of`, `use_case`, `scope`, `gates`, `evidence_hashes`, `evidence_states`, `decision_hashes`, `revoked_decisions`, `development` |
| Version | `land-underwriting-shadow/v2` |
| Identifiers, references, scope | Trimmed NFC strings of 1–128 characters; Unicode category C (including controls, format characters and surrogates) and line/paragraph separators rejected; no normalization/coalescing or authentication implied. Site/dossier IDs cannot contain `:` |
| Scope | Exact `LAND:<site_id>:<dossier_id>` namespace; request and every gate must match the derived scope, otherwise HOLD. Reserved colon prevents ambiguous identifier pairs |
| Dates | ASCII only, valid UTC calendar timestamps exactly `YYYY-MM-DDTHH:MM:SSZ`; gate dates may be explicit null, which blocks eligibility. Maximum decision validity interval is 366 days under a conservative candidate policy; longer intervals yield HOLD |
| Use case | `DEVELOPMENT` or `NONDEVELOPMENT` |
| Gate row | `gate_uid`, `scope`, `state`, `spec_ref`, `decision_ref`, `issued_at`, `expires_at`, `evidence`, `prerequisites` |
| Gate state | Existing `controls.GateState` values only: UNSPECIFIED, SPECIFIED, READY_FOR_TEST, PASSED, FAILED, SUSPENDED, EXPIRED |
| Gate specification/decision | Bounded text or null; null blocks eligibility |
| Gate evidence row | Exact `evidence_id`, `sha256`; unique IDs per gate, lowercase 64-character SHA256 |
| Prerequisites/revocations | Lists of unique bounded reference strings |
| Evidence/decision hashes | Dictionaries from bounded reference strings to lowercase SHA256 strings |
| Evidence states | Dictionary from bounded references to existing EvidenceState values; missing, RAW, below REVIEWABLE or REJECTED evidence cannot support eligibility |
| Development | Null for NONDEVELOPMENT; otherwise exact `currency`, `evidence_ids`, `gross_development_value`, `development_cost`, `finance_cost`, `developer_profit` |

Every list and catalog has at most 100 entries. Gate UIDs must be unique; the existing controls evaluator rejects duplicate evidence references, dangling prerequisites and dependency cycles. Total canonical request size is limited to 131072 UTF-8 bytes after bounded shape validation. Text limits are character counts; payload size counts bytes. No arbitrary nested metadata is accepted.

Currency is exactly three uppercase ASCII letters, a caller declaration with no registry or conversion claim. Each amount is explicit null or a plain nonnegative ASCII decimal string matching `(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?`. Thus the finite range is 0 through 999999999999999999.999999, with at most six fractional digits. Numeric JSON values, booleans, signs, exponents, whitespace, Unicode digits and nonfinite strings are rejected. Null remains unknown; measured zero remains zero.

## Controls and decisions

Rows become existing `controls.GateRecord` instances. `controls.evaluate_gates` uses its default REVIEWABLE evidence floor and checks declared scope, specification, `decision_digest`, evidence hashes/states, issuance, exact expiry, revocation and prerequisite DAG. Required hard IDs are `rights`, `land_use`, `environment`, `water`, `data`. Additional bounded gate rows can represent prerequisites; they must also be eligible. Empty gate input and missing required IDs produce HOLD rather than synthetic gate evidence.

A PASSED state without a bound decision/hash is ineligible. Self-consistent caller catalogs still establish integrity consistency only. They cannot authenticate a reviewer, evidence custody, site facts, legal authority or an approval. The adapter creates no decision digest for callers automatically. A caller assembling a declaration may use existing `controls.decision_digest`; changing a bound snapshot invalidates its digest.

Any missing, unknown, invalid, hash-failed, expired, revoked, scope-mismatched or otherwise ineligible gate produces `HOLD`. No caller-declared FAILED row overrides these blockers. Even an internally consistent FAILED row remains HOLD: this pure adapter cannot establish a competent explicit adverse decision and therefore never emits `NO_GO_FOR_CURRENT_PROPOSAL`. A future NO_GO path would require both dossier-wide integrity and independently established decision authority, outside this contract. A complete internally consistent snapshot can produce only `GO_FOR_EXTERNAL_REVIEW`.

## Input completeness and deterministic output

There is no monetary calculation, subtraction, residual value or Decimal computation. `development_input_diagnostic` has fields `status`, `inputs`, `value`, `warnings`. Status is `INPUTS_COMPLETE` only for a complete unblocked DEVELOPMENT declaration; otherwise it is `UNKNOWN`. NONDEVELOPMENT is `NOT_APPLICABLE`, with null inputs. `value` is always null and warnings are empty. The top-level `land_value` is always null and `valuation_status` is always `valuation_not_admitted`. Supplied amounts are echoed solely as caller-declared inputs. A future valuation method needs separate independent methodological and legal/professional review.

Development evidence references must be nonempty, resolve to the caller's hash/state catalogs at REVIEWABLE or above, and occur in a gate snapshot with the exact site/dossier scope and matching catalog hash. Orphan catalog entries cannot support completeness. All gates must pass integrity checks for INPUTS_COMPLETE. This does not bind the supplied monetary amounts to evidence content or verify their truth; those remain explicit source-authority gaps.

`as_of` is caller declared, never an authoritative clock. `time_basis` exposes `status: caller_declared`, the exact supplied `as_of`, `freshness_verified: false`, `max_decision_validity_days: 366`, and `gate_intervals` mapping each gate UID to its supplied `issued_at` and `expires_at` timestamps (including nulls). The adapter checks only consistency relative to declared time and caps intervals; it cannot assert true freshness. A backdated internally consistent short-window snapshot may still be eligible for external review. No present-time freshness claim follows.

The output includes the request identity, `input_sha256`, status, sorted blocks, existing controls result (or null without records), the input diagnostic, null land value and valuation status, time basis and authority limitations. `input_sha256` hashes the complete validated request with canonical JSON, sorting gate rows by UID, evidence by ID, and prerequisite/revocation/development-reference lists. Map insertion order is immaterial. Decimal strings are preserved, so `0` and `0.0` remain distinct declarations. Non-NFC input is rejected rather than silently normalized. Replaying fixed inputs produces identical hashes and canonical output bytes; no output shares mutable request objects.

Mode is always SHADOW. References are always `caller_declared_not_authenticated`. Independent reviewer authority and source verification requirements are true; legal/professional review remains HOLD. All authority/admission/certification/rights flags are false, even for complete fabricated catalogs. No land value, fair market value, PRU v_base, ecological premium/uplift or TRBK entitlement is computed. RAVEL loss modeling and PRU arithmetic are not invoked; only `pru.canonical_bytes` is reused. No authentication, source registry or field coalescing is added.

## Integration lanes and unresolved sources

- **Codex engineering:** implements and tests only these three candidates in the isolated worktree. No canonical source, registry, config, controls/PRU/RAVEL code or DNA change; no commit, push, PR, branch switch or deployment.
- **Claude adversarial review:** independently challenge B2/B3 repairs, forged complete catalogs, rejection precedence, dependency policy, numerical boundaries and source claims. Independent engineering review found no code blocker to opening a DRAFT PR; it is not scientific, legal or governance approval.
- **Desktop Commander local verification:** inspect compatibility and provenance without importing/promoting sources, writing integrations or executing commitments. No external write action, DNA change or REAL data activation was performed.

hApp #31 and #33 are read-only compatibility targets only. Their authoritative definitions and API/source mapping were not supplied or established by this work; compatibility is unverified. No Holochain DNA or hApp behavior is changed or asserted. Existing controls and runtime outputs do not establish site title, planning permission, environmental constraints, water rights, survey quality or development economics. Verified source documents, provenance/custody, reviewer credentials and authority, jurisdiction-specific legal/professional review and independent underwriting review remain gaps. Source labels or hashes alone do not close them.

**Asset-Light Site Readiness** is a commercial hypothesis for packaging documented gaps and external review readiness, not verified demand, site investability, valuation, legal clearance or a capital product. Test its usefulness with reviewers before adding infrastructure. Remove this candidate if adversarial review rejects its semantics or no review workflow needs it; simplify to an existing reviewed controls/package component when it provides equivalent behavior. Do not create a parallel authority system or source registry to preserve this prototype.

## Actual validation

No dependencies were added. Targeted and full regression suites use the existing interpreter:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/api python -m pytest -q -p no:cacheprovider services/api/tests/test_land_underwriting.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/api python -m pytest -q -p no:cacheprovider
```

Exact targeted result: `14 passed, 1 warning, 160 subtests passed in 0.15s` (exit 0).

The first Codex-local full test attempt stalled inside a Starlette/AnyIO TestClient and was interrupted (exit 130); an isolated diagnostic attempt also timed out. No existing HTTP code was changed. A separate complete Desktop Commander/WSL rerun against the revised worktree, using the existing isolated Python environment, completed with 281 passed, 160 subtests passed, one Starlette deprecation warning, exit 0. Preserve both receipts and investigate the intermittent harness hang without claiming it is fixed.

A separate non-HTTP regression run selected existing test functions/classes through read-only AST inspection, excluding 25 functions with a `client` fixture argument or direct `TestClient(...)` usage (31 parameterized cases). It invoked the same interpreter's `-m pytest -q -p no:cacheprovider` with those selected node IDs. Exact result: `250 passed, 1 warning, 160 subtests passed in 0.58s` (exit 0). The warning in both completed runs is the existing Starlette/AnyIO BlockingPortal deprecation.

Tests include scope replay, FAILED precedence across corrupted/unknown gates, validity boundary and caller backdating disclosure, orphan evidence, NFC/control rejection and pinned deterministic hash replay. They use synthetic declarations only; they establish engineering behavior, never source authenticity or legal/methodological acceptance.
