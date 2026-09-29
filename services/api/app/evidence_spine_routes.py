from __future__ import annotations

import hashlib
import json
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .models import (
    EvidenceCandidate,
    EvidencePackageRecord,
    ReviewAttestationRecord,
    AdmissibilityDecisionRecord,
    AuditLog,
)
from .schemas import EvidencePackageIn
from .security import require_write_key


def _package_hash(payload: EvidencePackageIn) -> str:
    material = payload.model_dump(mode="json")
    raw = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()



def _known_claim_uids(settings) -> set[str]:
    try:
        registry = json.loads(settings.semantic_claims_registry_path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return {item.get("claim_uid") for item in registry.get("claims", []) if item.get("claim_uid")}


def _claims_registry_hash(settings) -> str | None:
    try:
        raw = settings.semantic_claims_registry_path.read_bytes()
    except Exception:
        return None
    return hashlib.sha256(raw).hexdigest()

def build_evidence_spine_router(settings, SessionLocal) -> APIRouter:
    router = APIRouter()

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @router.get("/v1/evidence/spine/status")
    def evidence_spine_status(db: Session = Depends(get_db)):
        return {
            "stage": "P2.2-candidate",
            "runtime_stage": settings.runtime_stage,
            "production_admitted": settings.production_admitted,
            "holochain_enabled": settings.holochain_enabled,
            "counts": {
                "evidence_candidates": db.query(EvidenceCandidate).count(),
                "evidence_packages": db.query(EvidencePackageRecord).count(),
                "review_attestations": db.query(ReviewAttestationRecord).count(),
                "admissibility_decisions": db.query(AdmissibilityDecisionRecord).count(),
            },
            "flow": [
                "observation",
                "evidence_package",
                "holochain_candidate",
                "review_attestation",
                "admissibility_decision",
                "bridge_read_only",
                "console_display",
            ],
            "authority_boundary": "admissibility_only_no_value",
            "authoritative": False,
            "certification": False,
            "statement": settings.runtime_statement,
            "semantic_claim_registry": {
                "available": bool(_known_claim_uids(settings)),
                "known_claims": len(_known_claim_uids(settings)),
                "status": "candidate_not_canonical",
            },
        }

    @router.post("/v1/evidence/packages", dependencies=[Depends(require_write_key(settings))], status_code=201)
    def create_evidence_package(payload: EvidencePackageIn, db: Session = Depends(get_db)):
        if db.get(EvidencePackageRecord, payload.package_uid) is not None:
            raise HTTPException(status_code=409, detail="evidence package already exists")
        known = _known_claim_uids(settings)
        if not known:
            raise HTTPException(status_code=503, detail="semantic claim registry unavailable")
        unknown = [uid for uid in payload.claim_uids if uid not in known]
        if unknown:
            raise HTTPException(status_code=422, detail={"unknown_claim_uids": unknown})
        package_hash = _package_hash(payload)
        item = EvidencePackageRecord(
            id=payload.package_uid,
            subject_uid=payload.subject_uid,
            claim_uids=payload.claim_uids,
            place_context_version=payload.place_context_version,
            system_boundary_version=payload.system_boundary_version,
            observation_refs=payload.observation_refs,
            method_refs=payload.method_refs,
            raw_data_hashes=payload.raw_data_hashes,
            transformed_data_hashes=payload.transformed_data_hashes,
            package_hash=package_hash,
            claims_registry_hash=_claims_registry_hash(settings) or "",
            missing_data_statement=payload.missing_data_statement,
            adverse_event_statement=payload.adverse_event_statement,
            status="candidate",
        )
        db.add(item)
        db.add(AuditLog(event_type="evidence_package_created", object_id=item.id, payload={"package_hash": package_hash}))
        db.commit()
        return {
            "package_uid": item.id,
            "package_hash": package_hash,
            "claims_registry_hash": item.claims_registry_hash,
            "status": item.status,
            "authoritative_for_mrv": False,
            "statement": settings.runtime_statement,
        }

    @router.get("/v1/evidence/packages/{package_uid}")
    def get_evidence_package(package_uid: str, db: Session = Depends(get_db)):
        item = db.get(EvidencePackageRecord, package_uid)
        if item is None:
            raise HTTPException(status_code=404, detail="evidence package not found")
        return {
            "package_uid": item.id,
            "subject_uid": item.subject_uid,
            "claim_uids": item.claim_uids,
            "place_context_version": item.place_context_version,
            "system_boundary_version": item.system_boundary_version,
            "observation_refs": item.observation_refs,
            "method_refs": item.method_refs,
            "package_hash": item.package_hash,
            "claims_registry_hash": item.claims_registry_hash,
            "missing_data_statement": item.missing_data_statement,
            "adverse_event_statement": item.adverse_event_statement,
            "status": item.status,
            "authoritative_for_mrv": False,
            "statement": settings.runtime_statement,
        }

    return router
