from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import timezone
from pathlib import Path
from uuid import uuid4
import json
import hashlib
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .settings import Settings
from .db import Base, build_engine, build_session_factory
from .models import ReleaseState, EvidenceCandidate, AuditLog
from .schemas import EvidenceCandidateIn, EvaluationRequest, EvaluationResponse
from .security import require_write_key


def load_json(path: Path, fallback: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback




def verify_document_integrity(settings: Settings) -> dict:
    manifest_path = settings.document_integrity_manifest_path
    if not manifest_path.exists():
        if settings.document_integrity_required:
            raise RuntimeError(f"document integrity manifest missing: {manifest_path}")
        return {"status": "not-required", "checked": 0, "errors": []}
    manifest = load_json(manifest_path, {"files": []})
    errors: list[str] = []
    checked = 0
    for item in manifest.get("files", []):
        rel = item.get("path")
        expected = item.get("sha256")
        if not rel or not expected:
            errors.append("invalid manifest item")
            continue
        path = settings.document_root / rel
        if not path.exists():
            errors.append(f"missing document: {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        checked += 1
        if actual != expected:
            errors.append(f"hash mismatch: {rel}")
    if errors and settings.document_integrity_required:
        raise RuntimeError("canonical document integrity failure: " + "; ".join(errors))
    return {"status": "pass" if not errors else "fail", "checked": checked, "errors": errors}

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = build_engine(settings.database_url)
    SessionLocal = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.evidence_storage_path.mkdir(parents=True, exist_ok=True)
        app.state.document_integrity = verify_document_integrity(settings)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            existing = db.scalar(select(ReleaseState).where(ReleaseState.canonical_root == settings.canonical_root))
            if existing is None:
                db.add(ReleaseState(canonical_root=settings.canonical_root, canonical_release=settings.canonical_release, runtime_build_id=settings.runtime_build_id, runtime_statement=settings.runtime_statement))
                db.add(AuditLog(event_type="runtime_started", payload={"runtime_build_id": settings.runtime_build_id, "admission_mode": settings.admission_mode}))
                db.commit()
        yield
        engine.dispose()

    app = FastAPI(title="h•eart•h Prometheus Runtime", version="7.0.3", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type","X-API-Key"])

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @app.get("/health/live")
    def live():
        return {"status":"live","runtime_build_id":settings.runtime_build_id,"runtime_stage":settings.runtime_stage,"production_admitted":settings.production_admitted}

    @app.get("/health/ready")
    def ready(db: Session = Depends(get_db)):
        db.execute(text("SELECT 1"))
        return {"status":"ready","canonical_root":settings.canonical_root,"runtime_stage":settings.runtime_stage,"production_admitted":settings.production_admitted,"status_qualifier":settings.status_qualifier,"statement":settings.runtime_statement}

    @app.get("/v1/status")
    def status_view():
        gates = load_json(settings.gate_status_path, {"gates":[]})
        return {
            "canonical_root": settings.canonical_root,
            "canonical_release": settings.canonical_release,
            "runtime_build_id": settings.runtime_build_id,
            "documentary_patch": settings.documentary_patch,
            "audit_convergence_patch": settings.audit_convergence_patch,
            "runtime_stage": settings.runtime_stage,
            "status_qualifier": settings.status_qualifier,
            "build_completed": settings.build_completed,
            "locally_tested": settings.locally_tested,
            "production_admitted": settings.production_admitted,
            "legal_admitted": settings.legal_admitted,
            "market_admitted": settings.market_admitted,
            "independent_assurance": settings.independent_assurance,
            "runtime_statement": settings.runtime_statement,
            "admission_mode": settings.admission_mode,
            "holochain_enabled": settings.holochain_enabled,
            "payment_pathways": {"P1":settings.p1_enabled,"P2":settings.p2_enabled,"P3":settings.p3_enabled,"P4":settings.p4_enabled},
            "gate_review": gates,
            "document_integrity": getattr(app.state, "document_integrity", {"status": "unknown"}),
        }

    @app.get("/v1/integrity")
    def integrity_view():
        return getattr(app.state, "document_integrity", {"status": "unknown", "checked": 0, "errors": []})

    @app.get("/v1/canonical-root")
    def canonical_root():
        return load_json(settings.canonical_release_path, {"canonical_root":settings.canonical_root})

    @app.get("/v1/claims")
    def claims():
        return load_json(settings.claims_register_path, {"claims":[]})

    @app.get("/v1/gates")
    def gate_status():
        return load_json(settings.gate_status_path, {"gates":[]})

    @app.get("/v1/canon/files")
    def canon_files():
        root=settings.document_root
        if not root.exists(): return {"files":[]}
        files=[]
        for p in sorted(root.rglob("*")):
            if p.is_file():
                files.append({"path":str(p.relative_to(root)).replace("\\","/"),"bytes":p.stat().st_size})
        return {"files":files}

    @app.post("/v1/evidence/candidates", dependencies=[Depends(require_write_key(settings))], status_code=201)
    def create_evidence_candidate(payload: EvidenceCandidateIn, db: Session = Depends(get_db)):
        candidate=EvidenceCandidate(
            id=str(uuid4()), site_id=payload.site_id, evidence_type=payload.evidence_type,
            source_uri=payload.source_uri, sha256=payload.sha256, method_id=payload.method_id,
            captured_at=payload.captured_at.astimezone(timezone.utc), metadata_json=payload.metadata,
            status="candidate", canonical_root=settings.canonical_root, release_id=settings.canonical_release,
        )
        db.add(candidate)
        db.add(AuditLog(event_type="evidence_candidate_created", object_id=candidate.id, payload={"site_id":payload.site_id,"evidence_type":payload.evidence_type,"sha256":payload.sha256}))
        db.commit()
        return {"id":candidate.id,"status":candidate.status,"authoritative":False,"statement":settings.runtime_statement}

    @app.get("/v1/evidence/candidates/{candidate_id}")
    def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
        item=db.get(EvidenceCandidate,candidate_id)
        if item is None: raise HTTPException(status_code=404,detail="candidate not found")
        return {"id":item.id,"site_id":item.site_id,"evidence_type":item.evidence_type,"sha256":item.sha256,"method_id":item.method_id,"captured_at":item.captured_at,"status":item.status,"authoritative":False}

    @app.post("/v1/runtime/evaluate", response_model=EvaluationResponse)
    def evaluate(payload: EvaluationRequest):
        blockers=["runtime outputs are non-authoritative","independent review is not attached","legal and market admission are not implied"]
        if payload.claim_id:
            register=load_json(settings.claims_register_path,{"claims":[]})
            claim=next((c for c in register.get("claims",[]) if c.get("id")==payload.claim_id),None)
            if claim is None: blockers.append("claim ID is absent from the current register")
            elif claim.get("status","").lower() in {"pilot-required","design; no-go live","pre-instrument"}: blockers.append(f"claim status remains {claim.get('status')}")
        return EvaluationResponse(result="candidate review package prepared; no admission decision made", blockers=blockers)

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics(db: Session = Depends(get_db)):
        count = db.query(EvidenceCandidate).count()
        body = f"prometheus_runtime_up 1\nprometheus_evidence_candidates_total {count}\n"
        return PlainTextResponse(body, media_type="text/plain; version=0.0.4")


    return app

app=create_app()
