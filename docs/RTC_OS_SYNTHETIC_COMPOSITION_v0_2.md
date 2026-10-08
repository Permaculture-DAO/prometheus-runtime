# RTC-OS synthetic application composition v0.2

Status: PROPOSED / SHADOW / NON-CAPITAL-FACING. This is executable engineering evidence, not adopted source, science, legal approval or a deployed service.

## Boundaries and dependency order

Reuse the existing PR #23 branch rather than duplicate the implementation. Its import collection failure was corrected at 46c0814. Existing candidate-controls/PRU work from runtime #22 is a dependency, not a merged main release. Review/merge order: canon methodological/source decisions → runtime #21 DDL-before-state → runtime #22 controls → runtime #23 RTC composition → console #9 → ops #19.

Signed Canon v1.1.2-genesis remains governing. Canon #20 and #21 are draft proposals. #21's source/branch is not edited or activated. Exact original source pins are input requirements, not adoption evidence. Source-root patch candidates with different upstream versions require competent reconciliation. The source proposal's declined access-token assertion is excluded under ARD001/TOD001; neither this module nor its outputs changes external token/payment wording.

## Implemented vertical slice

- Closed, strict JSON schema: territory/site, contextual versus exploratory bioregions, lawful-data reference, evidence/claim identities, baseline/counterfactual, rights map, E/P/B/L vector, material conflicts and preserved dissent, no-action/lean/regenerative alternatives.
- Evidence Spine references carry site, method/version, SHA256 and declared measurement/lifecycle status. A digest does not validate measurement. Unknown or declined claim identities cannot become admissible.
- Loss Generation Ledger and Risk Allocation Ledger remain separate. Decimal conservation checks preserve every ultimate bearer, including externalised community loss. Unknown loss/recovery stays null/NR. Contradictory or revoked insurance cannot be overridden by a positive duplicate.
- Qualified runtime gate identity prevents joins to the RTC proposal's different G0–G7 vocabulary. The existing pure evaluator handles declared digests, expiry, revocation and graph consistency. A separate, explicitly proposed RTC conjunctive set policy requires every runtime gate; no ordinal crosswalk or new governing DAG is asserted.
- Narrow optional Ravel baseline arithmetic binds scenarios to loss-ledger event IDs, horizon and evidence and consumes all supplied alpha values. It is NOT the complete existing /ravel/shadow contract. Calibration still needs independent review; risk remains NR. No speculative capital or recovery inputs are silently ignored.
- Forty partner checks default to UNKNOWN; no score or partnership assertion.
- Local input hash, chained audit hash, frozen as-of time, exact golden output and replay. No wall-clock reads, network, database writes, HTTP route, signing or changes to persisted enums.

All outputs retain literal false authority/certification/rights/capital/production/publication flags. Caller declarations and reference strings are not authenticated provenance or independently qualified review. Root adoption/reconciliation is unconditionally HOLD in this candidate. Mathematical success cannot remove it.

## Run locally (WSL, repository root)

Use the already prepared Python environment with requirements.lock and requirements-dev.lock. From repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/rtc_os.py contracts/fixtures/rtc_os.synthetic.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/api python -m pytest -q services/api/tests
python scripts/validate_contracts.py
```

Output goes to stdout only. To replay, provide an envelope with exactly engine, input, input_sha256, output_sha256. The output hash binds the full canonical result (including its audit hash), not just the displayed readiness. Known claim identities come from the existing semantic registry. Replay with different semantics must fail equality.

The console candidate's rtc-os.html imports a compiled synthetic output locally, verifies its audit SHA using WebCrypto, and uses textContent only. It has no networking or persistence. Importing it is not a server-side verification or new public intake capability.

## Material gates not implemented by software authority

No real territorial pilot, title/water opinion, baseline field validation, causal MRV, independent accreditation, signed adoption, deploy admission, capital decision, off-host recovery or partner access is claimed. Those remain separately owned gates. No production process, Cloudflare cache, Windows startup or public WordPress page is changed by this patch.

## Rollback

No persistent migration or external API change exists. Revert this candidate's composition/fixtures/CLI and console viewer commits on review branches; retain compatible existing imports, routes and historical source identifiers. Do not delete or replace signed tags or old source bundles.
