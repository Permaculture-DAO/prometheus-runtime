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
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .settings import Settings
from .db import Base, build_engine, build_session_factory
from .models import ReleaseState, EvidenceCandidate, AuditLog
from .schemas import EvidenceCandidateIn, EvaluationRequest, EvaluationResponse
from .security import require_write_key
from .ingestion import adapter_by_id, ingestion_gate_status
from .evidence_batch import verify_synthetic_evidence_batch
from .ravel import (
    ScenarioLoss,
    CapitalLayer,
    ProtectionContract,
    RavelModelError,
    shadow_state,
    rr_delta,
    allocate_waterfall,
    apply_transfers,
    aggregate_by_economic_group,
    reconcile_economic_groups,
    urbc,
)
from .ravel_schemas import RavelShadowRequest, RavelShadowResponse
from .evidence_spine_routes import build_evidence_spine_router
from .review_routes import build_review_router


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
        try:
            # Inspect a stored release before any schema DDL. A rejected canon
            # transition must not add tables to an older database either.
            if inspect(engine).has_table(ReleaseState.__tablename__):
                with SessionLocal() as db:
                    stored = db.scalar(select(ReleaseState))
                    if stored is not None and (
                        stored.canonical_root != settings.canonical_root
                        or stored.canonical_release != settings.canonical_release
                    ):
                        raise RuntimeError(
                            "release-state mismatch: explicit reviewed migration or a "
                            "separate database is required; stored schema was not changed"
                        )
            Base.metadata.create_all(engine)
            with SessionLocal() as db:
                existing = db.scalar(select(ReleaseState))
                if existing is not None and (
                    existing.canonical_root != settings.canonical_root
                    or existing.canonical_release != settings.canonical_release
                ):
                    raise RuntimeError(
                        "release-state mismatch: configured canonical root/release differs "
                        "from the stored database; explicit reviewed migration or a separate "
                        "database is required; existing release and evidence were not changed"
                    )
                if existing is None:
                    db.add(ReleaseState(canonical_root=settings.canonical_root, canonical_release=settings.canonical_release, runtime_build_id=settings.runtime_build_id, runtime_statement=settings.runtime_statement))
                    db.add(AuditLog(event_type="runtime_started", payload={"runtime_build_id": settings.runtime_build_id, "admission_mode": settings.admission_mode}))
                    db.commit()
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="h•eart•h Prometheus Runtime", version="7.0.3", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type","X-API-Key"])
    app.include_router(build_evidence_spine_router(settings, SessionLocal))
    app.include_router(build_review_router(settings, SessionLocal))

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

    @app.get("/v1/ingestion/adapters")
    def ingestion_adapters():
        return ingestion_gate_status(settings)

    @app.post("/v1/ingestion/intake/{adapter_id}", dependencies=[Depends(require_write_key(settings))])
    def ingestion_intake(adapter_id: str, payload: dict):
        adapter = adapter_by_id(settings, adapter_id)
        if adapter is None:
            raise HTTPException(status_code=404, detail="adapter not found")
        if not settings.s4_ingestion_enabled or not adapter.enabled or not settings.s4_live_ingestion_admitted:
            raise HTTPException(
                status_code=423,
                detail={
                    "status": "locked",
                    "adapter_id": adapter_id,
                    "reason": "S4 ingestion is declared but not admitted",
                    "statement": settings.runtime_statement,
                    "production_admitted": settings.production_admitted,
                    "live_ingestion_admitted": settings.s4_live_ingestion_admitted,
                },
            )
        raise HTTPException(status_code=423, detail="live ingestion remains gated")

    @app.get("/v1/evidence/batches/synthetic")
    def synthetic_evidence_batch():
        if not settings.synthetic_evidence_batch_path.exists():
            raise HTTPException(status_code=404, detail="synthetic evidence batch package not found")
        batch = load_json(settings.synthetic_evidence_batch_path, {})
        errors = verify_synthetic_evidence_batch(batch)
        if errors:
            raise HTTPException(status_code=500, detail={"status": "invalid", "errors": errors})
        return batch

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

    @app.get("/v1/ravel/status")
    def ravel_status():
        return {
            "name": "PROMETHEUS Ravel",
            "expansion": "Risk Allocation, Vulnerability, Exposure & Loss",
            "mode": "shadow_underwriting",
            "methodology_status": "candidate",
            "authoritative": False,
            "certification": False,
            "underwriting_approval": False,
            "capital_facing": False,
            "vrrc": 0.0,
            "vrrc_status": "not_admitted",
            "invariants": [
                "loss reduction != loss allocation",
                "no risk disappears through representation",
                "no regenerative risk credit without causal evidence",
                "Ravel signals/calculates; governance decides",
            ],
            "statement": settings.runtime_statement,
        }

    @app.post("/v1/ravel/shadow", response_model=RavelShadowResponse)
    def ravel_shadow(payload: RavelShadowRequest):
        try:
            baseline = [
                ScenarioLoss(
                    scenario_id=x.scenario_id,
                    probability=x.probability,
                    gross_loss=x.gross_loss,
                    mitigated_loss=x.mitigated_loss,
                    recovery_value=x.recovery_value,
                )
                for x in payload.baseline_scenarios
            ]
            regenerative = [
                ScenarioLoss(
                    scenario_id=x.scenario_id,
                    probability=x.probability,
                    gross_loss=x.gross_loss,
                    mitigated_loss=x.mitigated_loss,
                    recovery_value=x.recovery_value,
                )
                for x in payload.regenerative_scenarios
            ]
            baseline_state = shadow_state(
                baseline,
                alpha_values=payload.alpha_values,
                initial_capital=payload.initial_capital,
                impairment_threshold=payload.impairment_threshold,
            )
            regenerative_state = shadow_state(
                regenerative,
                alpha_values=payload.alpha_values,
                initial_capital=payload.initial_capital,
                impairment_threshold=payload.impairment_threshold,
            )
            delta = {
                "expected_loss": rr_delta(
                    baseline_metric=baseline_state["expected_loss"],
                    regenerative_metric=regenerative_state["expected_loss"],
                )
            }
            for alpha in payload.alpha_values:
                key = f"{alpha:.4f}"
                delta[f"expected_shortfall_{key}"] = rr_delta(
                    baseline_metric=baseline_state["expected_shortfall"][key],
                    regenerative_metric=regenerative_state["expected_shortfall"][key],
                )
            if baseline_state.get("ppci") is not None and baseline_state["ppci"] > 0:
                delta["ppci"] = rr_delta(
                    baseline_metric=baseline_state["ppci"],
                    regenerative_metric=regenerative_state["ppci"],
                )
            else:
                delta["ppci"] = None

            allocation = None
            if payload.allocation_loss is not None:
                layers = [
                    CapitalLayer(
                        bearer_id=x.bearer_id,
                        economic_group_id=x.economic_group_id,
                        layer_type=x.layer_type,
                        attachment=x.attachment,
                        limit=x.limit,
                        priority=x.priority,
                    )
                    for x in payload.capital_layers
                ]
                waterfall = allocate_waterfall(payload.allocation_loss, layers)
                contracts = [
                    ProtectionContract(
                        contract_id=x.contract_id,
                        provider_bearer_id=x.provider_bearer_id,
                        receiver_bearer_id=x.receiver_bearer_id,
                        attachment=x.attachment,
                        limit=x.limit,
                        effectiveness=x.effectiveness,
                        basis_factor=x.basis_factor,
                        counterparty_factor=x.counterparty_factor,
                        legal_factor=x.legal_factor,
                    )
                    for x in payload.transfer_contracts
                ]
                after_transfer = apply_transfers(waterfall["by_bearer"], contracts)
                bearer_to_group = reconcile_economic_groups(layers, payload.bearer_to_group)
                # Missing provider ownership cannot be interpreted as diversification.
                unknown = set(after_transfer["by_bearer"]) - set(bearer_to_group) - {"UNALLOCATED_RESIDUAL"}
                if unknown:
                    raise RavelModelError("economic group required for every risk bearer")
                tolerance = 1e-9 * max(1.0, payload.allocation_loss)
                if waterfall["conservation_error"] > tolerance or after_transfer["conservation_error"] > tolerance:
                    raise RavelModelError("loss conservation failed")
                if waterfall["residual"] > 0:
                    raise RavelModelError("URBC requires complete allocation; residual loss is unresolved")
                group_losses = aggregate_by_economic_group(
                    after_transfer["by_bearer"], bearer_to_group
                )
                allocation = {
                    "waterfall": waterfall,
                    "after_transfer": after_transfer,
                    "ultimate_risk_bearer_groups": group_losses,
                    "urbc": urbc(group_losses),
                }

            return RavelShadowResponse(
                baseline=baseline_state,
                regenerative=regenerative_state,
                rr_delta=delta,
                allocation=allocation,
                scenario_provenance={
                    "baseline": [{"scenario_id": s.scenario_id, "horizon": s.horizon, "model_version": s.model_version, "evidence_refs": s.evidence_refs} for s in payload.baseline_scenarios],
                    "regenerative": [{"scenario_id": s.scenario_id, "horizon": s.horizon, "model_version": s.model_version, "evidence_refs": s.evidence_refs} for s in payload.regenerative_scenarios],
                    "verification_status": "caller_declared_not_verified",
                },
                assumptions=[
                    "candidate methodology; not validated underwriting",
                    "each scenario distribution must sum to 1 within absolute tolerance 1e-9; it is never rescaled",
                    "shared horizon and provenance are caller-declared; causal baseline matching is not verified",
                    "VRRC remains zero/not-admitted",
                    "no model output creates legal or capital consequences",
                ],
            )
        except RavelModelError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics(db: Session = Depends(get_db)):
        count = db.query(EvidenceCandidate).count()
        body = f"prometheus_runtime_up 1\nprometheus_evidence_candidates_total {count}\n"
        return PlainTextResponse(body, media_type="text/plain; version=0.0.4")


    return app

app=create_app()
