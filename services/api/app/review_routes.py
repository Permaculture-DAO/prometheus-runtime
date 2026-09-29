from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .models import (
    EvidencePackageRecord,
    ReviewAttestationRecord,
    AdmissibilityDecisionRecord,
    AuditLog,
)
from .schemas import ReviewAttestationIn, AdmissibilityDecisionIn
from .security import require_write_key


def build_review_router(settings, SessionLocal) -> APIRouter:
    router = APIRouter()

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @router.post("/v1/reviews", dependencies=[Depends(require_write_key(settings))], status_code=201)
    def create_review(payload: ReviewAttestationIn, db: Session = Depends(get_db)):
        if db.get(ReviewAttestationRecord, payload.review_uid) is not None:
            raise HTTPException(status_code=409, detail="review already exists")
        if payload.coi_status == "conflicted" and payload.decision == "pass":
            raise HTTPException(status_code=422, detail="conflicted reviewer cannot pass the same scope")
        if payload.coi_status == "independent" and payload.independent_for_scope is not True:
            raise HTTPException(status_code=422, detail="independent status requires independent_for_scope=true")
        item = ReviewAttestationRecord(
            id=payload.review_uid,
            reviewer_uid=payload.reviewer_uid,
            scope=payload.scope,
            coi_status=payload.coi_status,
            subject_refs=payload.subject_refs,
            decision=payload.decision,
            limitations=payload.limitations,
            independent_for_scope=payload.independent_for_scope,
            reviewed_at=payload.reviewed_at.astimezone(timezone.utc),
        )
        db.add(item)
        db.add(AuditLog(event_type="review_attestation_created", object_id=item.id, payload={
            "coi_status": item.coi_status,
            "decision": item.decision,
        }))
        db.commit()
        return {
            "review_uid": item.id,
            "decision": item.decision,
            "independent_for_scope": item.independent_for_scope,
            "authoritative": False,
            "statement": settings.runtime_statement,
        }

    @router.get("/v1/reviews/{review_uid}")
    def get_review(review_uid: str, db: Session = Depends(get_db)):
        item = db.get(ReviewAttestationRecord, review_uid)
        if item is None:
            raise HTTPException(status_code=404, detail="review not found")
        return {
            "review_uid": item.id,
            "reviewer_uid": item.reviewer_uid,
            "scope": item.scope,
            "coi_status": item.coi_status,
            "subject_refs": item.subject_refs,
            "decision": item.decision,
            "limitations": item.limitations,
            "independent_for_scope": item.independent_for_scope,
            "reviewed_at": item.reviewed_at,
            "authoritative": False,
        }

    @router.post("/v1/admissibility/decisions", dependencies=[Depends(require_write_key(settings))], status_code=201)
    def create_admissibility_decision(payload: AdmissibilityDecisionIn, db: Session = Depends(get_db)):
        if db.get(AdmissibilityDecisionRecord, payload.decision_uid) is not None:
            raise HTTPException(status_code=409, detail="decision already exists")

        packages = [db.get(EvidencePackageRecord, ref) for ref in payload.evidence_package_refs]
        reviews = [db.get(ReviewAttestationRecord, ref) for ref in payload.review_attestation_refs]
        blockers = []

        if any(item is None for item in packages):
            blockers.append("one or more evidence packages are missing")
        if any(item is None for item in reviews):
            blockers.append("one or more review attestations are missing")
        if packages and any(item is not None and payload.claim_uid not in item.claim_uids for item in packages):
            blockers.append("claim_uid is not linked by every evidence package")

        independent_pass = any(
            item is not None
            and item.independent_for_scope
            and item.coi_status == "independent"
            and item.decision == "pass"
            for item in reviews
        )
        if payload.require_independent_review and not independent_pass:
            blockers.append("independent passing review not established")
        if payload.confidence < payload.confidence_threshold:
            blockers.append("confidence threshold not met")

        legal_gate = bool(payload.legal_gate and payload.legal_review_ref)
        if not legal_gate:
            blockers.append("legal gate not established")

        mrv_gate = (
            all(item is not None for item in packages)
            and all(item is not None for item in reviews)
            and (independent_pass or not payload.require_independent_review)
            and payload.confidence >= payload.confidence_threshold
        )
        decision = "admissible" if legal_gate and mrv_gate and not blockers else "blocked"

        item = AdmissibilityDecisionRecord(
            id=payload.decision_uid,
            subject_uid=payload.subject_uid,
            claim_uid=payload.claim_uid,
            evidence_package_refs=payload.evidence_package_refs,
            review_attestation_refs=payload.review_attestation_refs,
            legal_gate=legal_gate,
            mrv_gate=mrv_gate,
            confidence=payload.confidence,
            decision=decision,
            blockers=blockers,
            authority_boundary="admissibility_only_no_value",
        )
        db.add(item)
        db.add(AuditLog(event_type="admissibility_decision_created", object_id=item.id, payload={
            "claim_uid": item.claim_uid,
            "decision": item.decision,
            "legal_gate": item.legal_gate,
            "mrv_gate": item.mrv_gate,
        }))
        db.commit()
        return {
            "decision_uid": item.id,
            "decision": item.decision,
            "legal_gate": item.legal_gate,
            "mrv_gate": item.mrv_gate,
            "confidence": item.confidence,
            "blockers": item.blockers,
            "authority_boundary": item.authority_boundary,
            "authoritative": False,
            "certification": False,
            "statement": settings.runtime_statement,
        }

    @router.get("/v1/admissibility/decisions/{decision_uid}")
    def get_admissibility_decision(decision_uid: str, db: Session = Depends(get_db)):
        item = db.get(AdmissibilityDecisionRecord, decision_uid)
        if item is None:
            raise HTTPException(status_code=404, detail="decision not found")
        return {
            "decision_uid": item.id,
            "subject_uid": item.subject_uid,
            "claim_uid": item.claim_uid,
            "evidence_package_refs": item.evidence_package_refs,
            "review_attestation_refs": item.review_attestation_refs,
            "legal_gate": item.legal_gate,
            "mrv_gate": item.mrv_gate,
            "confidence": item.confidence,
            "decision": item.decision,
            "blockers": item.blockers,
            "authority_boundary": item.authority_boundary,
            "authoritative": False,
            "certification": False,
        }

    return router
