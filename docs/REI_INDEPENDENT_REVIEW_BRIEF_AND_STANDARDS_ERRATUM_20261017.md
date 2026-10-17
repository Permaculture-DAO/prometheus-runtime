# Independent review brief — REI P1/P2 (2026-10-17)

This is a **request** for independent review, NOT a signed reviewer opinion. Review must be performed by a qualified person separate from source author and implementing assistant. The reviewer's name, credentials, conflicts, evidence inspected, conclusions, and signed exact-head reference remain PENDING.

Review exact files in this branch:
- services/api/app/rei_ravel_ledger_shadow.py
- services/api/tests/test_rei_ravel_ledger_shadow.py
- services/api/tests/test_rei_ravel_adversarial_review.py
- docs/REI_RAVEL_DUAL_LEDGER_SHADOW_RECONCILIATION.md
- docs/REI_MRV_CAUSAL_EVIDENCE_PROTOCOL_v0_1_SHADOW.md

Separate the independent assessments:
1. **P1 actuarial/model:** under unchanged AETERNA/RAVEL scope, test event loss conservation and transfer conservation, unknown/fabricated ultimate bearers, claims payment/enforceability, evidence source authentication, scenario calibration, tail dependency, actor-level economic group consolidation and sensitivity to arbitrary declared data.
2. **P1 engineering/security:** bounded input, character normalization, numeric edge cases, exact reproducibility, missingness and fail-closed behavior. A numeric GO is not insurance assurance.
3. **P2 scientific/MRV:** study design preregistration, unit and measurement ontology, soil carbon concentration vs stocks and equivalent soil mass, calibration, sampling chain of custody, control sites, selection bias, missingness, uncertainty, leakage, permanence and independent replication. No causal/valuation claim without competent domain acceptance.
4. **Governance:** validate authority lattice and source IDs, Source Root PR #18 pending, Land Source PR #25 pending, REI Source PR #26 pending, code PRs #26/#31/#32/#33 pending. Review signing custody. Main and REAL write paths must remain untouched.
5. **Disposition:** P0/P1/P2 severities, reproduction steps, source citations, independent reviewer identity/credentials, conflicts and signed decision for EXACT reviewed commit. Do not claim source ratification or independent signoff solely from successful tests.

### Mandatory reference correction
The older docs/REI_RAVEL_DUAL_LEDGER_SHADOW_RECONCILIATION.md mentions U.S. ASOP No. 47 as a reference without disclosing its obsolete status. **ASOP 47 and ASOP 46 were repealed on May 1, 2025 and replaced by ASOP No. 58 (Enterprise Risk Management)**, where applicable. Primary sources:
- https://www.actuarialstandardsboard.org/asops/enterprise-risk-management-58/
- https://www.actuarialstandardsboard.org/asops/asop-nos-46-47-risk-evaluation-risk-treatment-repealed/

ASOP 58 is not a substitute for site-specific insurance, legal enforceability, suitability or actuarial pricing review. These are **U.S. actuarial standards** where the standard's scope applies.

For P2, ISO 14064-2:2019 remains current for project-level greenhouse-gas monitoring/reductions, and GHG Protocol Land Sector and Removals Standard v1.1 was published with stated effective date Jan 1, 2027. Verify which standard applies to the specific activity/claim and date; neither makes the REI protocol compliant by default.
- https://www.iso.org/standard/66454.html
- https://ghgprotocol.org/land-sector-and-removals-standard
- https://www.ipcc-nggip.iges.or.jp/public/2019rf/vol4.html

### Current engineering review finding
Prior P1 code blocked exactly spelled `UNKNOWN`/`UNALLOCATED` placeholders but failed to block case variants in bearer identifiers. In this review branch, reserved identifiers are matched case-insensitively and separate negative tests assert HOLD. This **does not** authenticate an arbitrary nonreserved bearer such as `fictional-company`. The synthetic review test explicitly demonstrates `GO_FOR_EXTERNAL_REVIEW` for fabricated identifiers, proving that independent identity and evidence authentication are still missing.

All material source-adoption, actuarial, regulatory, financial, environmental and real-world authorization gates remain **HOLD**.
