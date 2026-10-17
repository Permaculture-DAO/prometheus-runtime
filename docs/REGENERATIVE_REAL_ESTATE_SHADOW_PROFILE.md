# PROMETHEUS Regenerative Real Estate — SHADOW policy profile v0.1

**Date:** 2026-10-17  
**Status:** PROPOSED / SHADOW / NON-AUTHORITATIVE / NON-OFFERING  
**Branch:** stacked on `feat/land-underwriting-reconciled-20261017`, signed land-underwriting commit `ca64d0aca10305403dafdd859f0116bc13090ac8`.
**Related governance:** Canon Draft PR #25 `PRM-LAND-APP-001@0.1`, not adopted; Source Root PR #18 not adopted. Do not edit either signed record.

## 1. Product decision, not constitutional amendment

Test an **Evidence, Rights, Risk & Territorial-Value Readiness** desk-only service before offering land acquisition, tokenisation or marketplace operations. This profile adds a declaration-based anti-extraction review on top of the existing `app.land_underwriting.evaluate_land_underwriting` shadow preflight; it does not introduce an authority layer, a substitute for PRU/RAP or an alternate Aeterna/Ravel method.

The initial buyer hypothesis is a landowner, cooperative, community-land-steward, permitted developer, foundation, municipal team, or regulated/advised finance participant seeking a reproducible dossier. Actual buyer, payment and professional eligibility are UNKNOWN. Compare with competent advisers plus a signed spreadsheet, not with an artificially weak baseline.

**Method hierarchy:** signed Canon > valid law/instruments for legal matters; controlling PRM-ARCH-DET-002; PRM-CIV-APP-006 as registered within scope; Aeterna/Ravel where validated; land application Draft PR #25 PROPOSED; this non-controlling prototype; implementation reports.

## 2. Bounded runnable function

```python
from app.regenerative_real_estate import evaluate_regenerative_real_estate
result = evaluate_regenerative_real_estate(frozen_request)
```

No REST route, database, live sensor writes, actor custody, timer, source fetch, price feed, marketplace, wallet or release gate. No new dependencies. The function calls the existing `evaluate_land_underwriting(land_underwriting)` rather than trusting a caller-provided status; existing `controls.evaluate_gates` remains the sole gate engine. The land preflight is `land-underwriting-shadow/v2`, including exact LAND namespace, 5 hard land gates and integrity checks.

Top-level strict JSON fields: `schema_version`, `land_underwriting`, `safeguards`, `cash_outflows`, `risk_links`, `currency`.

`schema_version` = `regenerative-real-estate-shadow/v1`; same bounded payload rules as existing land preflight.

`safeguards`: 8 unique `{control_id,state,evidence_id}` records for `land_access`, `occupant_protection`, `stewardship`, `maintenance_reserve`, `benefit_distribution`, `externalities`, `related_party`, `exit_and_default`. States are `REVIEWABLE / UNKNOWN / ADVERSE / NOT_APPLICABLE`. Any missing, UNKNOWN, ADVERSE or NOT_APPLICABLE item forces HOLD; the latter is **not** an unreviewed waiver. Complete caller declarations are only eligible for external review, never evidence of compliance.

`cash_outflows`: unique `{event_id,amount,currency,recipient_scope,evidence_id}` rows. Decimal is nonnegative, bounded to 18 integer and 6 decimal digits; JSON numeric values are not accepted. `recipient_scope` is `LOCAL / NONLOCAL / UNKNOWN`; unknown => HOLD, no ratio. This is a declaration about **project cash outflows**, not money permanently retained, community income, tax incidence, value-add, territorial multiplier, housing affordability, or net externalities. Partial flows may overstate local share; auditing and completeness of the accounting universe are **not established**. The diagnostic ratio is never a gate score.

`risk_links`: unique `{risk_id,ultimate_bearer_id,evidence_id}` linkage declarations. Absence => HOLD. A named ultimate bearer is not a tested Ravel Risk Object, actuarial calculation, actual risk transfer or compensation proof.

All referenced evidence IDs must exist in the land preflight caller-declared catalogs with evidence state REVIEWABLE or above and be referenced on an in-scope land gate with matching SHA256. Matching SHA256 only checks self-consistency. The chain of custody, document integrity at source, legal validity, calibration, evidence authenticity and independent reviewer competence remain **not established**.

Input order permutations produce the same SHA256 and canonical JSON output for bounded records. Exact spellings, decimal strings and as-of are preserved.

## 3. Controls, result and limitations

`HOLD` if land-underwriting preflight is HOLD, any required safeguard fails, evidence reference is orphaned, outflow recipient is unknown, risk linkage is absent, or denominator is zero. Otherwise: `GO_FOR_EXTERNAL_REVIEW`, meaning candidate integrity completeness for **external specialist assessment only**.

Outputs intentionally hardcoded:
- `mode: SHADOW`, `source_status: PROPOSED_NOT_ADOPTED`
- `evidence_authenticity: NOT_ESTABLISHED`
- `regenerative_outcome: NOT_VERIFIED`
- `capital_admission: false`, `financial_certification: false`
- `authoritative: false`, `legal_rights_created: false`
- `land_value: null`, `ecological_uplift: null`, `trbk_entitlement: null`.

Example: synthetic/local EUR 30 and nonlocal EUR 20 produce a caller-declared `0.600000` outflow share. This is **not** a 60% verified territorial value retention result, and not a financial underwriting claim. Missing flow classification yields `null`, never 0.

**Risk and claims:** UNKNOWN != ZERO. LOSS REDUCTION != LOSS ALLOCATION. TRANSFER != ELIMINATION. ECOLOGICAL RESILIENCE != CASH-FLOW SOLVENCY. Financial cost to local employees does not establish wealth retention. A positive economic diagnostic cannot override a failed occupant-protection, title, maintenance, consent or environmental gate.

## 4. Research reference classes and competitor counterfactual

- Hirano & Stiglitz (2022), [CEPR land speculation and endogenous phase transitions](https://cepr.org/voxeu/columns/land-speculation-booms-and-busts-endogenous-phase-transitions-model-economic): theoretical analysis of land speculation and productive-capital crowding-out; does not establish that this product solves the model.
- E. F. Schumacher, [Think About Land](https://centerforneweconomics.org/publications/think-about-land/), and [How to Abolish Land Speculation](https://centerforneweconomics.org/publications/how-to-abolish-land-speculation/): anti-speculation institutional proposals; not operative law.
- [Center for Land Economics](https://landeconomics.org/problem): advocacy/theory requiring independent empirical evaluation.
- [Appalachian Regional Commission coal studies](https://www.arc.gov/report/an-economic-analysis-of-the-appalachian-coal-industry-ecosystem/), and *Who Owns Appalachia?*: ownership concentration, fiscal/economic dependence and local value capture as distinct causal hypotheses; avoid monocausal explanations.
- [Propy](https://propy.com/home/): digital closing, title and escrow positioning; consumer/title compliance is jurisdiction-specific.
- [RealT](https://realt.co/) and [RMM](https://rmm.realtoken.network/): tokenised exposure and lending/DeFi functions, not verified regeneration; Detroit property and tenancy issues require adversarial case review including the April 2026 independent fiduciary agreement ([Outlier Media](https://outliermedia.org/realt-detroit-crypto-landlord-nuisance-abatement-agreement/)).

**Differentiation hypothesis:** a rights-, maintenance-, risk- and evidence-first review dossier may be more useful to clients than a tokenisation-first asset marketplace. Must be validated with real buyers against low-tech diligence baselines. Do not imply platform partnership or benchmark endorsement.

## 5. Falsifiable validation programme

| Hypothesis | Experiment | Preliminary stopping rule (to preregister with actual client) |
| --- | --- | --- |
| H1 source/gate quality | professional review of 10 synthetic/sanitised dossiers | any critical false GO without disclosure -> HOLD and repair |
| H2 anti-extraction relevance | independent review of 8 safeguard fields, including dissent | irreproducible source, missing actor or tenant rights -> HOLD |
| H3 buyer willingness to pay | 6 qualified customer discovery interviews + priced offer | no contract/budget signal -> redesign or retire; interviews are not sales |
| H4 risk transparency | Ravel two-ledger reconciliation, independent check | any transfer called 'elimination' -> reject |
| H5 simpler alternative | blinded comparison vs professional spreadsheet | no measurable extra utility net of cost -> simplify/retire |
| H6 quantum benefit | constrained optimisation benchmark vs mature MIP solver | no robust quality/cost advantage -> Q remains SHADOW |

Pilot candidates: Sicily/Italy, Florida/Georgia, and Appalachia as a case for historical causal analysis. No site, title or operator is admitted by geography.

## 6. Code/review lanes

- This PR: `services/api/app/regenerative_real_estate.py`, corresponding synthetic tests and this review doc.
- Existing land-underwriting signed Draft PR #26 remains untouched.
- Source Root PR #18, Canon PR #25, hApp DNA/REAL gate PRs and existing Aeterna/Ravel are **not** amended.
- No canonical source proposal or active registry mutation; if beneficial, prepare an application-profile ADR after reviewer approval.
- Qualified legal/title, property/valuation, soil/ecology, tenant protection, security, model-risk, local stewardship and finance reviewers must sign off on use in a real site.
- No production deployment, no token use, no investment recommendation.

## 7. Targeted regression

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/api python -m pytest -q -p no:cacheprovider services/api/tests/test_regenerative_real_estate.py
```

Tests use synthetic data; a passing test establishes code consistency, not economic or scientific validity. Preserve failing results, timestamps, version/commit provenance and rollback. Delete this adapter if it duplicates qualified controls or cannot beat the simpler workflow.
