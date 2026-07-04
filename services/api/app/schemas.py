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
