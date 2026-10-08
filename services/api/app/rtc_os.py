"""RTC-OS v0.2: pure, synthetic-only application composition; no authority path.

References proposed PRM-RTC-APP-001@0.1 at c5ee7be and CIV-TOPOS-001.
Reuses controls, EvidenceState, legacy packet screening and Ravel arithmetic.
No routes, DB writes, network, wall-clock reads, secrets or legal determinations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Context, Decimal, localcontext
import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .controls import EvidenceState, GateRecord, GateState, evaluate_gates
from .pru import canonical_bytes
from .ravel import ScenarioLoss, shadow_state
from .territorial_capital import review_territorial_proposal

VERSION = "RTC-OS-SHADOW-0.2"
Text = Annotated[str, StringConstraints(min_length=1, max_length=2048, pattern=r"\S")]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Money = Annotated[str, StringConstraints(pattern=r"^(0|[1-9][0-9]{0,17})(\.[0-9]{1,12})?$")]
EvidenceStatus = Literal["RAW", "IDENTIFIED", "PROVENANCE_BOUND", "QA_QC_CHECKED",
                         "REVIEWABLE", "VERIFIED_INDICATOR_CANDIDATE", "ADMISSIBLE", "REJECTED"]
SOURCE_PINS = {
    "PRM-CANON-SIGNED@v1.1.2-genesis": "f3862005bc4d6e8e4cba0f2a7646e67dff758fcd28c8411046eb5d04875f9540",
    "PRM-RTC-APP-001@0.1": "c868662c12b9f0e9c8ee1af938c277042a087adb415f9f70dd6d4480e2c2712f",
    "PRM-ARCH-DET-002@2.0": "83f42dcac3f9053b011eeb2b2963862d23c9ab0be35ee467499c99dcafd1e1c7",
    "PRM-RISK-AETERNA-001@1.1": "1fc0656f60a73ef6c067e7a1a15e83e28dfdddd68575202ce47ad5e0ebd767d3",
    "PRM-RISK-RAVEL-OP-002@1.1": "ea5c228ff48ca1e30738aaa2eea8cf88e8c70c38726096ba43c0a6f03f3a9ff5",
    "PRM-CIV-APP-006@6.2": "3710dbc02b63f43d74b7aa03fd2fa584e27ef26a9e0866add2139a296ea99ece",
}
SOURCE_CUSTODY = "PROPOSED_NOT_ADOPTED; signed Canon alone remains governing"
# These namespaces intentionally cannot be joined by bare gate ordinals.
GateUID = Annotated[str, StringConstraints(pattern=r"^prometheus\.runtime\.G[0-7]@candidate-v0\.1$")]
RUNTIME_GATE_UIDS = frozenset(f"prometheus.runtime.G{i}@candidate-v0.1" for i in range(8))
SOURCE_CONFLICTS = (
    "source21_upstream_pins_vs_source_root_patch_candidates_unreconciled",
    "source21_TRBK_consumptive_utility_proposal_excluded_by_ARD001_TOD001",
    "source21_application_gate_ordinals_not_equivalent_to_runtime_gate_taxonomy",
)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class SourceReference(Record):
    record_key: Text
    sha256: Digest


class BioregionalStrategyProfile(Record):
    strategy_id: Text
    boundary_refs: list[Text] = Field(min_length=1, max_length=100)
    reference_class_refs: list[Text] = Field(max_length=100)
    applicability: Literal["CONTEXTUAL", "EXPLORATORY", "UNKNOWN"]
    conflicts: list[Text] = Field(default_factory=list, max_length=100)


class TerritoryProfile(Record):
    territory_id: Text
    boundary_ref: Text
    jurisdictions: list[Text] = Field(min_length=1, max_length=100)
    bioregions: list[BioregionalStrategyProfile] = Field(min_length=1, max_length=100)


class SiteProfile(Record):
    site_id: Text
    territory_id: Text
    operator_id: Text
    lawful_data_access_ref: Text | None
    baseline_evidence_uids: list[Text] = Field(max_length=1000)
    counterfactual_ref: Text | None


class EvidenceReference(Record):
    evidence_uid: Text
    site_id: Text
    sha256: Digest
    method_id: Text
    method_version: Text
    state: EvidenceStatus
    measurement_status: Literal["UNKNOWN", "INVALID", "REVIEW_PENDING", "DECLARED_VALID"]


class ClaimReference(Record):
    claim_uid: Annotated[str, StringConstraints(pattern=r"^prometheus\.[a-z0-9_.]+$")]
    evidence_uids: list[Text] = Field(max_length=1000)
    kind: Literal["OBSERVATION", "IMPROVEMENT", "RISK"]
    proposed_wording: Text


class RightRecord(Record):
    kind: Literal["LAND", "WATER", "DATA", "CONSENT", "STEWARDSHIP", "CASHFLOW", "INSURANCE"]
    holder_id: Text
    jurisdiction: Text
    status: Literal["UNKNOWN", "DISPUTED", "DOCUMENTED", "REVOKED"]
    instrument_ref: Text | None
    review_ref: Text | None


class ScaleVector(Record):
    E: Literal["PASSED", "HOLD", "REJECT", "UNKNOWN"]
    P: Literal["PASSED", "HOLD", "REJECT", "UNKNOWN"]
    B: Literal["PASSED", "EXPLORATORY", "HOLD", "UNKNOWN"]
    L: Literal["PASSED", "HOLD", "REJECT", "UNKNOWN"]


class ScaleConflict(Record):
    conflict_id: Text
    source_ids: list[Text] = Field(min_length=1, max_length=100)
    affected_claim_uids: list[Text] = Field(min_length=1, max_length=100)
    material: bool
    reason: Text
    reviewer_id: Text | None
    dissent: Text
    resolved: bool = False


class Alternative(Record):
    option_id: Text
    kind: Literal["NO_ACTION", "LEAN_INTERVENTION", "REGENERATIVE", "OTHER"]
    constraints: list[Text] = Field(max_length=100)
    maintenance_ref: Text | None


class LossGeneration(Record):
    event_id: Text
    risk_id: Text
    hazard: Text
    trigger: Text
    gross_loss: Money | None
    mitigated_loss: Money | None
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    horizon: Text
    evidence_uids: list[Text] = Field(min_length=1, max_length=1000)


class RiskAllocation(Record):
    event_id: Text
    bearer_id: Text
    amount: Money | None
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    horizon: Text
    treatment: Literal["RETAINED", "TRANSFERRED", "EXTERNALISED"]
    contract_ref: Text | None
    recoverability: Literal["UNKNOWN", "UNSUPPORTED", "DOCUMENTED"]
    evidence_uids: list[Text] = Field(min_length=1, max_length=1000)


class Reviewer(Record):
    reviewer_id: Text
    design_provider_id: Text
    economic_group_id: Text
    provider_economic_group_id: Text
    qualification_ref: Text | None
    mandate_ref: Text | None
    conflict_ref: Text | None


class PartnerCheck(Record):
    check_id: Annotated[str, StringConstraints(pattern=r"^T(0[1-9]|[1-3][0-9]|40)$")]
    state: Literal["OBSERVED", "DOCUMENTED", "THIRD_PARTY_VERIFIED", "ASSUMED", "UNKNOWN", "INCOMPATIBLE"]
    evidence_uids: list[Text] = Field(max_length=1000)
    reviewer_ref: Text | None


class GateDeclaration(Record):
    gate_uid: GateUID
    state: Literal["UNSPECIFIED", "SPECIFIED", "READY_FOR_TEST", "PASSED", "FAILED", "SUSPENDED", "EXPIRED"]
    spec_ref: Text | None
    decision_ref: Text | None
    issued_at: AwareDatetime | None
    expires_at: AwareDatetime | None
    evidence_uids: list[Text] = Field(max_length=1000)
    prerequisites: list[GateUID] = Field(max_length=100)


class RTCScenario(Record):
    event_id: Text
    probability: float = Field(ge=0, le=1)
    evidence_uids: list[Text] = Field(min_length=1, max_length=1000)


class RTCQuantRequest(Record):
    """Narrow ledger-bound baseline arithmetic, NOT the full /ravel/shadow contract."""
    horizon: Text
    scenarios: list[RTCScenario] = Field(min_length=1, max_length=1000)
    alpha_values: list[float] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_distribution(self):
        if len({s.event_id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("duplicate quantitative event")
        if any(not 0 < alpha < 1 for alpha in self.alpha_values):
            raise ValueError("alpha must be strictly between zero and one")
        keys = [f"{alpha:.4f}" for alpha in self.alpha_values]
        if (len(set(keys)) != len(keys) or any(
                Decimal(str(alpha)) != Decimal(key) for alpha, key in zip(self.alpha_values, keys))):
            raise ValueError("alpha identities require distinct exact four-decimal levels")
        if abs(sum(s.probability for s in self.scenarios) - 1) > 1e-9:
            raise ValueError("scenario probability sum must equal one")
        return self


class RTCInput(Record):
    schema_version: Literal["0.2"]
    dataset: Literal["SYNTHETIC_NON_CAPITAL_FACING"]
    dossier_id: Text
    revision: int = Field(ge=1)
    as_of: AwareDatetime
    expires_at: AwareDatetime
    previous_audit_sha256: Digest | None
    source_root_state: Literal["VALID_CANDIDATE", "INVALID", "DEGRADED", "UNKNOWN"]
    sources: list[SourceReference] = Field(min_length=1, max_length=100)
    territory: TerritoryProfile
    site: SiteProfile
    evidence: list[EvidenceReference] = Field(max_length=1000)
    claims: list[ClaimReference] = Field(max_length=1000)
    rights: list[RightRecord] = Field(max_length=1000)
    scales: ScaleVector
    scale_conflicts: list[ScaleConflict] = Field(default_factory=list, max_length=100)
    alternatives: list[Alternative] = Field(min_length=1, max_length=100)
    loss_generation: list[LossGeneration] = Field(max_length=1000)
    risk_allocation: list[RiskAllocation] = Field(max_length=1000)
    reviewer: Reviewer | None
    partner_checks: list[PartnerCheck] = Field(default_factory=list, max_length=40)
    compute_mode: Literal["D", "P", "H", "Q"]
    deterministic_receipt_ref: Text | None
    proposal: dict[str, Any]
    gate_declarations: list[GateDeclaration] = Field(default_factory=list, max_length=100)
    decision_hashes: dict[str, Digest] = Field(default_factory=dict)
    revoked_decisions: list[Text] = Field(default_factory=list, max_length=100)
    ravel_request: RTCQuantRequest | None = None

    @model_validator(mode="after")
    def unique_identities(self):
        for items, field in ((self.sources, "record_key"), (self.evidence, "evidence_uid"),
                             (self.claims, "claim_uid"), (self.loss_generation, "event_id"),
                             (self.partner_checks, "check_id"), (self.alternatives, "option_id"),
                             (self.scale_conflicts, "conflict_id"), (self.gate_declarations, "gate_uid")):
            ids = [getattr(item, field) for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {field}")
        if self.site.territory_id != self.territory.territory_id:
            raise ValueError("site/territory mismatch")
        return self


def _hash(value: dict) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _decimal_strings(value):
    """Wire floats as decimal text: Python/JS must hash identical JSON values."""
    if isinstance(value, float):
        return str(value)
    if isinstance(value, dict):
        return {k: _decimal_strings(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decimal_strings(v) for v in value]
    return value


def compile_dossier(payload: dict, *, known_claim_uids: frozenset[str] = frozenset()) -> dict:
    """Compile caller declarations; hashes/labels are never authenticated authority."""
    raw = canonical_bytes(payload)
    if len(raw) > 2_000_000:
        raise ValueError("RTC input exceeds 2 MB")
    packet = RTCInput.model_validate_json(raw)
    hold, reject = ["source_adoption_and_reconciliation_pending"], []
    pins = {p.record_key: p.sha256 for p in packet.sources}
    for key, expected in SOURCE_PINS.items():
        if key not in pins:
            hold.append("missing_source:" + key)
        elif pins[key] != expected:
            reject.append("source_hash_mismatch:" + key)
    if set(pins) - set(SOURCE_PINS):
        hold.append("unregistered_source")
    if packet.source_root_state != "VALID_CANDIDATE":
        hold.append("source_root_unresolved")
    if packet.as_of >= packet.expires_at:
        hold.append("dossier_expired")
    if packet.compute_mode != "D" or not packet.deterministic_receipt_ref:
        hold.append("compute_verification_pending")
    if not packet.site.lawful_data_access_ref:
        hold.append("lawful_data_access_unknown")
    if not packet.site.counterfactual_ref or not packet.site.baseline_evidence_uids:
        hold.append("baseline_counterfactual_missing")
    by_evidence = {e.evidence_uid: e for e in packet.evidence}
    for e in packet.evidence:
        if e.site_id != packet.site.site_id:
            reject.append("evidence_site_mismatch:" + e.evidence_uid)
    if any(uid not in by_evidence for uid in packet.site.baseline_evidence_uids):
        hold.append("baseline_reference_unresolved")
    elif any(by_evidence[uid].state != "ADMISSIBLE" or
             by_evidence[uid].measurement_status != "DECLARED_VALID"
             for uid in packet.site.baseline_evidence_uids):
        hold.append("baseline_measurement_not_admissible_declaration")
    for kind in ("LAND", "WATER", "DATA", "CONSENT", "STEWARDSHIP"):
        records = [r for r in packet.rights if r.kind == kind]
        if not records or any(r.status != "DOCUMENTED" or not r.instrument_ref or not r.review_ref for r in records):
            hold.append("rights_unresolved:" + kind)
        if any(r.status in ("DISPUTED", "REVOKED") for r in records):
            reject.append("rights_adverse:" + kind)
    scales = packet.scales.model_dump()
    for scale, state in scales.items():
        if state == "REJECT":
            reject.append("scale_rejected:" + scale)
        elif state != "PASSED":
            hold.append("scale_unresolved:" + scale)
    if any(b.applicability != "CONTEXTUAL" or b.conflicts for b in packet.territory.bioregions):
        hold.append("bioregional_transfer_exploratory_or_conflicting")
    if any(c.material and (not c.resolved or not c.reviewer_id) for c in packet.scale_conflicts):
        hold.append("material_scale_conflict")
    kinds = {a.kind for a in packet.alternatives}
    if not {"NO_ACTION", "LEAN_INTERVENTION", "REGENERATIVE"} <= kinds:
        hold.append("alternatives_incomplete")
    rv = packet.reviewer
    if not rv or not rv.qualification_ref or not rv.mandate_ref or not rv.conflict_ref:
        hold.append("independent_review_pending")
    elif rv.reviewer_id == rv.design_provider_id or rv.economic_group_id == rv.provider_economic_group_id:
        reject.append("reviewer_conflict_of_interest")
    claims = []
    for c in packet.claims:
        reasons = []
        if c.claim_uid not in known_claim_uids:
            reasons.append("unregistered_claim")
        if (".trbk." in c.claim_uid or c.claim_uid.endswith(".trbk") or
                c.claim_uid == "prometheus.token.access_utility_candidate"):
            reasons.append("token_claim_outside_RTC_scope_ARD001_TOD001")
        if not c.evidence_uids or any(uid not in by_evidence for uid in c.evidence_uids):
            reasons.append("unresolved_evidence")
        elif any(by_evidence[uid].state != "ADMISSIBLE" or
                 by_evidence[uid].measurement_status != "DECLARED_VALID" for uid in c.evidence_uids):
            reasons.append("evidence_not_admissible_declaration")
        if c.kind == "IMPROVEMENT" and (not packet.site.baseline_evidence_uids or not packet.site.counterfactual_ref):
            reasons.append("no_baseline_counterfactual")
        elif c.kind == "IMPROVEMENT" and any(
                uid not in by_evidence or by_evidence[uid].state != "ADMISSIBLE" or
                by_evidence[uid].measurement_status != "DECLARED_VALID"
                for uid in packet.site.baseline_evidence_uids):
            reasons.append("baseline_measurement_not_admissible_declaration")
        claims.append({"claim_uid": c.claim_uid, "state": "NOT_ADMISSIBLE" if reasons else "REVIEW_REQUIRED",
                       "reasons": reasons, "publication_authorised": False})
        if reasons:
            hold.append("claim_not_admissible:" + c.claim_uid)
    legacy = review_territorial_proposal(packet.proposal)
    hold.extend("screening:" + gid for gid in legacy["blocking_gates"])
    legacy_territory = packet.proposal.get("territory")
    if not isinstance(legacy_territory, dict) or legacy_territory.get("site_id") != packet.site.site_id:
        reject.append("screening_site_mismatch")
    reject.extend("screening_failed:" + gid for gid, value in legacy["gate_results"].items()
                  if value["status"] == "FAIL")
    if not packet.loss_generation or not packet.risk_allocation:
        hold.append("two_ledgers_missing")
    events = {e.event_id: e for e in packet.loss_generation}
    risk_state = "SHADOW_DECLARATIONS_ONLY"
    with localcontext(Context(prec=50)):
        for allocation in packet.risk_allocation:
            if allocation.event_id not in events:
                reject.append("allocation_unknown_event:" + allocation.event_id)
                continue
            event = events[allocation.event_id]
            if allocation.currency != event.currency or allocation.horizon != event.horizon:
                reject.append("ledger_unit_or_horizon_mismatch")
            if any(uid not in by_evidence for uid in allocation.evidence_uids):
                hold.append("allocation_evidence_unresolved")
            if allocation.treatment == "TRANSFERRED" and (
                    allocation.recoverability != "DOCUMENTED" or not allocation.contract_ref):
                risk_state = "NR"
                hold.append("insurance_recoverability_unknown")
            if allocation.treatment == "TRANSFERRED" and not any(
                    r.kind == "INSURANCE" and r.status == "DOCUMENTED" and
                    r.instrument_ref == allocation.contract_ref and r.review_ref for r in packet.rights):
                risk_state = "NR"
                hold.append("insurance_right_unresolved")
            if allocation.treatment == "TRANSFERRED":
                matching = [r for r in packet.rights if r.kind == "INSURANCE" and
                            r.instrument_ref == allocation.contract_ref]
                if any(r.status in ("REVOKED", "DISPUTED") for r in matching):
                    reject.append("insurance_right_adverse")
                if any(r.jurisdiction not in packet.territory.jurisdictions for r in matching):
                    reject.append("insurance_jurisdiction_mismatch")
        for event in packet.loss_generation:
            related = [a for a in packet.risk_allocation if a.event_id == event.event_id]
            if any(uid not in by_evidence for uid in event.evidence_uids):
                hold.append("loss_evidence_unresolved")
            if (event.gross_loss is not None and event.mitigated_loss is not None and
                    Decimal(event.mitigated_loss) > Decimal(event.gross_loss)):
                reject.append("mitigation_exceeds_gross")
            if event.gross_loss is None or event.mitigated_loss is None or not related or any(a.amount is None for a in related):
                risk_state = "NR"
                hold.append("risk_missingness")
            if event.mitigated_loss is not None and related and all(a.amount is not None for a in related):
                if sum((Decimal(a.amount) for a in related), Decimal(0)) != Decimal(event.mitigated_loss):
                    reject.append("loss_allocation_not_conserved")
    quant = None
    if packet.ravel_request is None:
        risk_state = "NR"
        hold.append("probabilities_not_defensible")
    else:
        request = packet.ravel_request
        if {s.event_id for s in request.scenarios} != set(events):
            raise ValueError("quantitative scenarios must bind the complete loss ledger")
        if len({e.currency for e in events.values()}) != 1:
            raise ValueError("quantitative scenarios require one currency; no implicit FX")
        if any(events[s.event_id].horizon != request.horizon or
               not set(s.evidence_uids) <= set(events[s.event_id].evidence_uids) or
               any(uid not in by_evidence for uid in s.evidence_uids) for s in request.scenarios):
            raise ValueError("quantitative horizon/evidence does not bind the loss ledger")
        if any(e.gross_loss is None or e.mitigated_loss is None for e in events.values()):
            hold.append("quantitative_loss_unknown")
        else:
            # Only declared baseline arithmetic; losses come from the bound ledger.
            quant = _decimal_strings(shadow_state([ScenarioLoss(s.event_id, s.probability,
                float(events[s.event_id].gross_loss), float(events[s.event_id].mitigated_loss), None)
                for s in request.scenarios], alpha_values=request.alpha_values))
            quant["currency"] = next(iter(events.values())).currency
            quant["numeric_encoding"] = "decimal_strings_from_declared_float_arithmetic"
        # Arithmetic can be shown, but a caller-supplied distribution is not calibration.
        risk_state = "NR"
        hold.append("probability_calibration_independent_review_pending")
    gates = None
    if packet.gate_declarations:
        if any(uid not in by_evidence for g in packet.gate_declarations for uid in g.evidence_uids):
            raise ValueError("unresolved gate evidence reference")
        records = tuple(GateRecord(
            g.gate_uid, packet.site.site_id, GateState(g.state), g.spec_ref, g.decision_ref,
            g.issued_at, g.expires_at,
            tuple((uid, by_evidence[uid].sha256) for uid in g.evidence_uids),
            tuple(g.prerequisites)) for g in packet.gate_declarations)
        gates = evaluate_gates(
            records, as_of=packet.as_of, scope=packet.site.site_id,
            evidence_hashes={uid: e.sha256 for uid, e in by_evidence.items()},
            evidence_states={uid: EvidenceState(e.state) for uid, e in by_evidence.items()},
            decision_hashes=packet.decision_hashes, revoked_decisions=frozenset(packet.revoked_decisions))
        if {g.gate_uid for g in records} != RUNTIME_GATE_UIDS:
            hold.append("runtime_candidate_gate_set_incomplete")
        if any(by_evidence[uid].state != "ADMISSIBLE" or
               by_evidence[uid].measurement_status != "DECLARED_VALID"
               for g in packet.gate_declarations for uid in g.evidence_uids):
            hold.append("gate_evidence_not_admissible_declaration")
        if any(not g["candidate_eligible"] for g in gates["gates"].values()):
            hold.append("gate_declarations_not_eligible")
        # RTC composition requires every runtime gate, conjunctively. This local
        # policy does not invent an authoritative ordinal dependency crosswalk.
        for g in packet.gate_declarations:
            if any(by_evidence[uid].state != "ADMISSIBLE" or
                   by_evidence[uid].measurement_status != "DECLARED_VALID" for uid in g.evidence_uids):
                gate = gates["gates"][g.gate_uid]
                gate["candidate_eligible"] = False
                gate["reasons"] = sorted(set(gate["reasons"] + ["rtc_evidence_unusable"]))
        failed = sorted(uid for uid, g in gates["gates"].items() if not g["candidate_eligible"])
        incomplete = {g.gate_uid for g in records} != RUNTIME_GATE_UIDS
        if failed or incomplete:
            for gate in gates["gates"].values():
                gate["candidate_eligible"] = False
                gate["reasons"] = sorted(set(gate["reasons"] + ["rtc_gate_set_not_eligible"]))
                gate["blocked_by"] = sorted(set(gate["blocked_by"] + failed))
        gates["composition_policy"] = "rtc-noncompensating-runtime-set@0.2 (PROPOSED)"
    else:
        hold.append("runtime_candidate_gate_declarations_missing")
    partner = {f"T{i:02}": {"state": "UNKNOWN", "references_status": "caller_declared_not_authenticated"}
               for i in range(1, 41)}
    for check in packet.partner_checks:
        if check.state in ("DOCUMENTED", "THIRD_PARTY_VERIFIED") and (
                not check.evidence_uids or any(uid not in by_evidence for uid in check.evidence_uids)
                or not check.reviewer_ref):
            raise ValueError("partner verification declaration requires resolvable evidence and reviewer")
        partner[check.check_id]["state"] = check.state
    result = {
        "engine": VERSION, "dataset": packet.dataset, "dossier_id": packet.dossier_id,
        "revision": packet.revision, "as_of": packet.as_of.astimezone(timezone.utc).isoformat(),
        "expires_at": packet.expires_at.astimezone(timezone.utc).isoformat(),
        "input_sha256": hashlib.sha256(raw).hexdigest(), "source_pins": pins,
        "source_custody": SOURCE_CUSTODY, "scales": scales,
        "evidence_spine": [e.model_dump() for e in packet.evidence],
        "territory": packet.territory.model_dump(), "site": packet.site.model_dump(),
        "alternatives": [a.model_dump() for a in packet.alternatives],
        "source_conflicts": list(SOURCE_CONFLICTS),
        "scale_conflicts": [c.model_dump(mode="json") for c in packet.scale_conflicts],
        "rights_map": [r.model_dump() for r in packet.rights],
        "claims": claims, "application_screening": legacy, "runtime_gate_declarations": gates,
        "gate_taxonomy": {"id": "prometheus.runtime@candidate-v0.1",
                          "source": "runtime/config/gate_status.json",
                          "ordinal_crosswalk_authorised": False},
        "loss_generation_ledger": [e.model_dump() for e in packet.loss_generation],
        "risk_allocation_ledger": [a.model_dump() for a in packet.risk_allocation],
        "ultimate_bearers": sorted({a.bearer_id for a in packet.risk_allocation}),
        "risk_state": risk_state, "ravel_shadow": quant,
        "external_partner_checks": partner, "topos_partnership": "UNKNOWN",
        "capital_readiness": "REJECT" if reject else "HOLD" if hold else "REVIEW_REQUIRED",
        "hold_reasons": sorted(set(hold)), "reject_reasons": sorted(set(reject)),
        "authoritative": False, "certification": False, "capital_authorised": False,
        "creates_rights": False, "material_gate_effects_allowed": False,
        "production_admitted": False, "publication_authorised": False,
        "previous_audit_sha256": packet.previous_audit_sha256,
    }
    result["audit_sha256"] = _hash(result)
    return result


def replay_dossier(bundle: dict, *, known_claim_uids: frozenset[str] = frozenset()) -> bytes:
    if set(bundle) != {"engine", "input", "input_sha256", "output_sha256"} or bundle["engine"] != VERSION:
        raise ValueError("invalid RTC replay envelope")
    if _hash(bundle["input"]) != bundle["input_sha256"]:
        raise ValueError("replay input hash mismatch")
    result = compile_dossier(bundle["input"], known_claim_uids=known_claim_uids)
    if _hash(result) != bundle["output_sha256"]:
        raise ValueError("replay output hash mismatch")
    return canonical_bytes(result)
