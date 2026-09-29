from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class ReleaseState(Base):
    __tablename__ = "release_state"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    canonical_root: Mapped[str] = mapped_column(String(128), unique=True)
    canonical_release: Mapped[str] = mapped_column(String(128))
    runtime_build_id: Mapped[str] = mapped_column(String(128))
    runtime_statement: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class EvidenceCandidate(Base):
    __tablename__ = "evidence_candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    site_id: Mapped[str] = mapped_column(String(128), index=True)
    evidence_type: Mapped[str] = mapped_column(String(80), index=True)
    source_uri: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    method_id: Mapped[str] = mapped_column(String(128))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="candidate", index=True)
    canonical_root: Mapped[str] = mapped_column(String(128))
    release_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(128), default="runtime")
    object_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidencePackageRecord(Base):
    __tablename__ = "evidence_packages"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject_uid: Mapped[str] = mapped_column(String(128), index=True)
    claim_uids: Mapped[list] = mapped_column(JSON, default=list)
    place_context_version: Mapped[str] = mapped_column(String(128))
    system_boundary_version: Mapped[str] = mapped_column(String(128))
    observation_refs: Mapped[list] = mapped_column(JSON, default=list)
    method_refs: Mapped[list] = mapped_column(JSON, default=list)
    raw_data_hashes: Mapped[list] = mapped_column(JSON, default=list)
    transformed_data_hashes: Mapped[list] = mapped_column(JSON, default=list)
    package_hash: Mapped[str] = mapped_column(String(64), index=True)
    claims_registry_hash: Mapped[str] = mapped_column(String(64), index=True)
    holochain_commit_status: Mapped[str] = mapped_column(String(32), default="not_committed", index=True)
    holochain_entry_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_data_statement: Mapped[str] = mapped_column(Text)
    adverse_event_statement: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="candidate", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ReviewAttestationRecord(Base):
    __tablename__ = "review_attestations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    reviewer_uid: Mapped[str] = mapped_column(String(128))
    scope: Mapped[str] = mapped_column(Text)
    coi_status: Mapped[str] = mapped_column(String(32))
    subject_refs: Mapped[list] = mapped_column(JSON, default=list)
    decision: Mapped[str] = mapped_column(String(32))
    limitations: Mapped[str] = mapped_column(Text)
    independent_for_scope: Mapped[bool] = mapped_column(default=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AdmissibilityDecisionRecord(Base):
    __tablename__ = "admissibility_decisions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject_uid: Mapped[str] = mapped_column(String(128), index=True)
    claim_uid: Mapped[str] = mapped_column(String(256), index=True)
    evidence_package_refs: Mapped[list] = mapped_column(JSON, default=list)
    review_attestation_refs: Mapped[list] = mapped_column(JSON, default=list)
    legal_gate: Mapped[bool] = mapped_column(default=False)
    mrv_gate: Mapped[bool] = mapped_column(default=False)
    confidence: Mapped[float] = mapped_column(default=0.0)
    decision: Mapped[str] = mapped_column(String(32))
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    authority_boundary: Mapped[str] = mapped_column(String(64), default="admissibility_only_no_value")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
