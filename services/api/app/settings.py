from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    canonical_root: str = os.getenv("CANONICAL_ROOT", "PROMETHEUS-CANON-ROOT-v7.0")
    canonical_release: str = os.getenv("CANONICAL_RELEASE", "PROMETHEUS-CWP-v7.0-20260704")
    runtime_build_id: str = os.getenv("RUNTIME_BUILD_ID", "PROMETHEUS-RUNTIME-v7.0.1-20260704")
    documentary_patch: str = os.getenv("DOCUMENTARY_PATCH", "PROMETHEUS-DOC-PATCH-v7.0.3-20260704")
    audit_convergence_patch: str = os.getenv("AUDIT_CONVERGENCE_PATCH", "PROMETHEUS-AUDIT-CONVERGENCE-v7.0.3-20260704")
    runtime_stage: str = os.getenv("RUNTIME_STAGE", "development")
    status_qualifier: str = os.getenv("STATUS_QUALIFIER", "development runtime; production admission gated")
    build_completed: bool = os.getenv("BUILD_COMPLETED", "true").lower() == "true"
    locally_tested: bool = os.getenv("LOCALLY_TESTED", "true").lower() == "true"
    production_admitted: bool = os.getenv("PRODUCTION_ADMITTED", "false").lower() == "true"
    legal_admitted: bool = os.getenv("LEGAL_ADMITTED", "false").lower() == "true"
    market_admitted: bool = os.getenv("MARKET_ADMITTED", "false").lower() == "true"
    independent_assurance: str = os.getenv("INDEPENDENT_ASSURANCE", "unsigned")
    runtime_statement: str = os.getenv("RUNTIME_STATEMENT", "evaluation, not certification")
    admission_mode: str = os.getenv("ADMISSION_MODE", "closed")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////tmp/prometheus_runtime.db")
    write_api_key: str = os.getenv("WRITE_API_KEY", "")
    allowed_origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",") if x.strip())
    document_root: Path = Path(os.getenv("DOCUMENT_ROOT", "/documents"))
    evidence_storage_path: Path = Path(os.getenv("EVIDENCE_STORAGE_PATH", "/tmp/prometheus-evidence"))
    claims_register_path: Path = Path(os.getenv("CLAIMS_REGISTER_PATH", "/app/config/claims_register.json"))
    gate_status_path: Path = Path(os.getenv("GATE_STATUS_PATH", "/app/config/gate_status.json"))
    canonical_release_path: Path = Path(os.getenv("CANONICAL_RELEASE_PATH", "/app/config/canonical_release.json"))
    document_integrity_manifest_path: Path = Path(os.getenv("DOCUMENT_INTEGRITY_MANIFEST_PATH", "/app/config/document_integrity.json"))
    document_integrity_required: bool = os.getenv("DOCUMENT_INTEGRITY_REQUIRED", "false").lower() == "true"
    p1_enabled: bool = os.getenv("P1_ATTESTATION_ENABLED", "false").lower() == "true"
    p2_enabled: bool = os.getenv("P2_TRBK_ENABLED", "false").lower() == "true"
    p3_enabled: bool = os.getenv("P3_PROCESSOR_ENABLED", "false").lower() == "true"
    p4_enabled: bool = os.getenv("P4_CUSTODY_EXCHANGE_ENABLED", "false").lower() == "true"
    holochain_enabled: bool = os.getenv("HOLOCHAIN_ENABLED", "false").lower() == "true"
    s4_ingestion_enabled: bool = os.getenv("S4_INGESTION_ENABLED", "false").lower() == "true"
    s4_live_ingestion_admitted: bool = os.getenv("S4_LIVE_INGESTION_ADMITTED", "false").lower() == "true"
    s4_ttn_mock_enabled: bool = os.getenv("S4_TTN_MOCK_ENABLED", "false").lower() == "true"
    s4_manual_mock_enabled: bool = os.getenv("S4_MANUAL_MOCK_ENABLED", "false").lower() == "true"
    s4_lab_mock_enabled: bool = os.getenv("S4_LAB_MOCK_ENABLED", "false").lower() == "true"
    synthetic_evidence_batch_path: Path = Path(os.getenv("SYNTHETIC_EVIDENCE_BATCH_PATH", "/app/evidence/batches/synthetic_batch_0001.json"))
