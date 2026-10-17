# PROMETHEUS REI — MRV and causal evidence preflight protocol v0.1
**Date:** 2026-10-17  
**Classification:** PROPOSED SCIENTIFIC REVIEW PROTOCOL / SHADOW / NOT ADOPTED

This is the **P2 protocol-design deliverable**, not an operational sensor adapter, scientific standard, lab method, or authoritative causal-inference implementation. It is subordinate to the signed Canon, `PRM-ARCH-DET-002@2.0`, the relevant registered MRV methodology, Civilizational Venture Studio application scope and approved legal/consent/data policy. It is linked to the proposed [REI source PR](https://github.com/Permaculture-DAO/prometheus-canon/pull/26) and runtime [REI PR #32](https://github.com/Permaculture-DAO/prometheus-runtime/pull/32).

## 1. Evidence record fields proposed (NOT an accepted schema)

`project_id`; `site_id`; `metric_id`; `measurement_id`; `observation_time_utc`; `sampling_window_start/end`; `latitude/longitude_reference_or_privacy_preserving_area_id`; `geospatial_precision_class`; `method_id@version`; `instrument_id`; `calibration_certificate_ref`; `operator_id`; `specimen_chain_of_custody_ref`; `raw_data_digest`; `raw_data_location_access_policy`; `unit`; `uncertainty_model`; `quality_flags`; `missingness_reason`; `evidence_state`; `reviewer_id`; `review_decision_ref`; `review_timestamp_utc`. Do not require exact private geo coordinates in the public Canon or open PRs.

Every content hash proves identity of a declared byte stream only, not sampling reliability or evidence truth. Dataset provenance and a qualified person need an independently verifiable chain. Sensor raw data, photographs, geodata or third-party personal information may be restricted; protect privacy, intellectual property and informed participation.

## 2. A temporal and counterfactual boundary

Pre-register **before** collecting impact data:
1. The target population, land/site boundary, decision objective, precise intervention and expected causal mechanism.
2. Outcome indicator and direct observation technique; unit, sensor calibration, precision, seasonality, units and missing data policy.
3. Baseline period and measurement procedure, including independent verification of baseline quality.
4. Comparison/counterfactual: matched control parcel, suitable randomized design when possible, synthetic control or independently reviewed time-series; explain confounding and selection bias.
5. Spatial leakage, displaced impacts, boundary effects, intervention spillover and maintenance duration.
6. Statistical model, sample size/power or justified feasible design, confidence/uncertainty intervals, sensitivity analysis, multiple-testing policy, falsification/negative controls.
7. Reporting rules for null, adverse, ambiguous or heterogeneous effects and independent replication. No single-site pilot implies global validity.

A baseline is NOT a counterfactual. Comparing before/after alone is not enough to attribute a causal improvement where other factors (seasonal weather, market conditions, land use shifts, labor, public subsidy, soil variability) may explain outcomes.

## 3. Application-specific proposed metrics; no verified performance

- **Agriculture:** soil organic carbon concentration, bulk density, depth, coarse-fragment fraction, and **equivalent soil mass** for comparable stocks (especially if management changes bulk density); soil type, season and time, erosion, infiltration, yields net of input cost, biodiversity and water use; laboratory/field calibration and appropriate controls.
- **Real estate and land:** verified physical improvement condition, building energy consumption adjusted for occupancy/weather where defensible, lifecycle maintenance, tenant well-being/access/affordability and habitat baseline. Property appreciation is not ecological causation.
- **Energy:** metered kWh, outage/curtailment, lifecycle greenhouse gases with precise system boundary, capacity factors, energy justice/access, grid emission counterfactual. Gross generation is not net avoided emissions.
- **Infrastructure:** delivered service reliability, maintenance downtime/cost over lifecycle, accessibility and community impacts, fiscal externalities and cost allocation; only after legally valid asset access and procurement evaluation.

## 4. Candidate claims taxonomy and stop rules

| State | Permissible language in a SHADOW report | No-go claim |
| --- | --- | --- |
| `HYPOTHESIS` | "Proposed benefit; untested" | "Regeneration achieved" |
| `OBSERVATION_CANDIDATE` | "Caller reported observation, unauthenticated" | "Independently measured improvement" |
| `CAUSAL_CANDIDATE` | "Impact estimation requires domain review" | "Activity caused X improvement" |
| `VALUATION_CANDIDATE` | "Independent valuation required" | "Capital appreciation/economic premium established" |
| Missing, stale, conflicting | `UNKNOWN` plus evidence reasons | Inferred zero or favorable score |

Every real-world positive claim needs at least qualified measurement authentication, temporal and spatial reconciliation, method review, uncertainty, baseline and valid causal design if attributing to the intervention. Domain expert signatures are separate from source steward or code author.

## 5. Field protocol for a Sicily pilot (candidate, not site approval)

A single-site pre-pilot could establish a reference timeline, site map with privacy controls, qualified baseline sampling, explicit indicators, instruments and sample logs, version-pinned field methods, weather observations and cost log. All land, water, regulatory and consent rights must be verified first. Non-site-specific sampling is only a design stage; no raw site data are invented here.

A 12-month observation window can describe seasonal signals but may be insufficient for slow soil carbon stock changes or biodiversity impact attribution. Mark these `NOT YET ESTIMABLE` and extend to multi-year follow-up or replication as qualified agronomic analysis recommends. Do not use a 12-month grant time horizon as proof of permanence.

## 6. Adversarial review cases and data acceptance

- Tampered evidence hash / replay across sites / mismatched UTC sampling dates -> HOLD.
- Uncalibrated sensor with numbers that look plausible -> HOLD.
- Baseline and comparison site not comparable -> causal HOLD.
- Intervention measured only during favorable season -> quality HOLD.
- Social rights, tenancy or ecological displacement unresolved -> claim HOLD irrespective of cash returns.
- Claimed economic value from carbon/soil observations without market/legal appraisal -> valuation HOLD.
- Real site raw evidence publicly exposing protected location or person data -> privacy HOLD.

## 7. Method anchors and effective-date caveats

- IPCC 2019 Refinement, Vol. 4 chapter 2, soil carbon stock comparison and equivalent mass: https://www.ipcc-nggip.iges.or.jp/public/2019rf/vol4.html
- ISO 14064-2:2019 remains current for project-level GHG quantification, monitoring and reporting, but reference alone is not compliance: https://www.iso.org/standard/66454.html
- GHG Protocol Land Sector and Removals Standard (published version v1.1, effective date **2027-01-01**). Claim/applicability must be checked for the observation date: https://ghgprotocol.org/land-sector-and-removals-standard
- An MRV protocol is not a credit issuing standard, nor independent causal evidence without a competent study design and field audit.

## 8. Next implementation only after method review

A future scientific data adapter may accept typed measurement records and reviewer proofs, then pass audited claims through the REI deterministic boundary, but **must not** change `regenerative_economic_intelligence.py` to accept scientific claims based solely on matching text IDs. Independent trained measurement professionals, privacy/legal specialists and scientific reviewers must sign off.

**GO:** draft MRV protocol and synthetic schema adversarial review.  
**HOLD:** live sensor ingestion/claim certification, carbon credits, causal impact or financial price, production admission.
