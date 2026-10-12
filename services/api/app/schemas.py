from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator
import re

class EvidenceCandidateIn(BaseModel):
    site_id: str = Field(min_length=1, max_length=128)
    evidence_type: str = Field(min_length=1, max_length=80)
    source_uri: str = Field(min_length=1, max_length=2048)
    sha256: str
    method_id: str = Field(min_length=1, max_length=128)
    captured_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        value = value.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return value

class EvaluationRequest(BaseModel):
    claim_id: str | None = None
    evidence_candidate_ids: list[str] = Field(default_factory=list, max_length=100)
    requested_use: str = Field(default="internal review", max_length=200)

class EvaluationResponse(BaseModel):
    authoritative: bool = False
    certification: bool = False
    message: str = "evaluation, not certification"
    result: str
    blockers: list[str]


class EvidencePackageIn(BaseModel):
    package_uid: str = Field(min_length=3, max_length=80)
    subject_uid: str = Field(min_length=1, max_length=128)
    claim_uids: list[str] = Field(min_length=1, max_length=50)
    place_context_version: str = Field(min_length=1, max_length=128)
    system_boundary_version: str = Field(min_length=1, max_length=128)
    observation_refs: list[str] = Field(min_length=1, max_length=500)
    method_refs: list[str] = Field(min_length=1, max_length=100)
    raw_data_hashes: list[str] = Field(min_length=1, max_length=1000)
    transformed_data_hashes: list[str] = Field(default_factory=list, max_length=1000)
    missing_data_statement: str = Field(min_length=1, max_length=4000)
    adverse_event_statement: str = Field(min_length=1, max_length=4000)

    @field_validator("package_uid")
    @classmethod
    def validate_package_uid(cls, value: str) -> str:
        if not re.fullmatch(r"ep_[A-Za-z0-9_-]+", value):
            raise ValueError("package_uid must start with ep_")
        return value

    @field_validator("claim_uids")
    @classmethod
    def validate_claim_uids(cls, values: list[str]) -> list[str]:
        for value in values:
            if not re.fullmatch(r"prometheus\.[a-z0-9_.-]+", value):
                raise ValueError("claim_uids must use semantic prometheus.* identities")
        return values

    @field_validator("raw_data_hashes", "transformed_data_hashes")
    @classmethod
    def validate_hashes(cls, values: list[str]) -> list[str]:
        for value in values:
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("data hashes must be 64 lowercase hexadecimal characters")
        return values

class ReviewAttestationIn(BaseModel):
    review_uid: str = Field(min_length=3, max_length=80)
    reviewer_uid: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=1000)
    coi_status: str
    subject_refs: list[str] = Field(min_length=1, max_length=100)
    decision: str
    limitations: str = Field(min_length=1, max_length=4000)
    reviewed_at: datetime
    independent_for_scope: bool

    @field_validator("coi_status")
    @classmethod
    def validate_coi_status(cls, value: str) -> str:
        if value not in {"independent", "advisory_only", "conflicted"}:
            raise ValueError("invalid coi_status")
        return value

    @field_validator("decision")
    @classmethod
    def validate_review_decision(cls, value: str) -> str:
        if value not in {"pass", "conditional", "fail", "not_reviewed"}:
            raise ValueError("invalid review decision")
        return value

class AdmissibilityDecisionIn(BaseModel):
    decision_uid: str = Field(min_length=4, max_length=80)
    subject_uid: str = Field(min_length=1, max_length=128)
    claim_uid: str = Field(min_length=1, max_length=256)
    evidence_package_refs: list[str] = Field(min_length=1, max_length=100)
    review_attestation_refs: list[str] = Field(default_factory=list, max_length=100)
    legal_gate: bool = False
    legal_review_ref: str | None = Field(default=None, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    require_independent_review: bool = True

    @field_validator("decision_uid")
    @classmethod
    def validate_decision_uid(cls, value: str) -> str:
        if not re.fullmatch(r"adm_[A-Za-z0-9_-]+", value):
            raise ValueError("decision_uid must start with adm_")
        return value

    @field_validator("claim_uid")
    @classmethod
    def validate_semantic_claim_uid(cls, value: str) -> str:
        if not re.fullmatch(r"prometheus\.[a-z0-9_.-]+", value):
            raise ValueError("claim_uid must use semantic prometheus.* identity")
        return value
