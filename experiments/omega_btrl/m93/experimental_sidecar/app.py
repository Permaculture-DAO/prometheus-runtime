"""M9 staging-sidecar candidate: HTTP transport, never a runtime write bridge.

Default app is closed even if reached over HTTP. The only way to create an
explicitly enabled staging instance is *in code* with a host-owned trust-provider;
request JSON never selects keys/policies/reviewers or sets staging enablement.

Do not mount into the PROMETHEUS runtime FastAPI app. No data persistence,
Holochain or network client is used by the evaluator. HTTP transport is expected
to bind on loopback during lab tests; any production placement is NOT approved.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from fastapi import FastAPI, Request

from src.staging_shadow import HostStageConfig, evaluate_shadow
from src.trust_boundary import TrustedStore, closed_result
from src.interop_advisory import make_advice

BODY_LIMIT_BYTES = 32768
ALLOWED_CT = frozenset({"application/json"})


def _hold(reason: str) -> dict:
    return make_advice(closed_result(reasons=[reason]))


def create_shadow_app(*,
                      stage_enabled: bool = False,
                      trusted_provider: Callable[[], TrustedStore] | None = None,
                      test_clock: datetime | None = None) -> FastAPI:
    """Build an in-memory advice-only app. Never infers trust from request JSON.

    This laboratory transport does NOT implement authentication or TLS. External
    exposure is FORBIDDEN; use in-process tests or isolated loopback only.
    """
    api = FastAPI(title="Omega M9 Shadow Advisory TEST-ONLY", docs_url=None,
                  redoc_url=None, openapi_url=None)

    @api.get("/internal/health")
    async def health():
        return {"status": "lab_only", "staging_enabled": stage_enabled is True,
                "authority": "none", "runtime_write_capability": False,
                "holochain_write_capability": False,
                "canonical_admission": False}

    @api.post("/internal/advice")
    async def advice(request: Request):
        # Reject large bodies before parsing; avoid request.body() unbounded buffering.
        size = 0
        chunks = []
        async for part in request.stream():
            size += len(part)
            if size > BODY_LIMIT_BYTES:
                return _hold("PAYLOAD_TOO_LARGE")
            chunks.append(part)
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() not in ALLOWED_CT:
            return _hold("CONTENT_TYPE_NOT_ALLOWED")
        if stage_enabled is not True or trusted_provider is None:
            return _hold("HOST_STAGE_CLOSED_OR_TRUST_MISSING")
        try:
            # Only host application code may supply this object. The payload is
            # separately parsed by evaluate_shadow, which rejects impersonation.
            roots = trusted_provider()
            if not isinstance(roots, TrustedStore):
                return _hold("HOST_TRUST_PROVIDER_INVALID")
        except Exception:
            return _hold("HOST_TRUST_PROVIDER_ERROR")
        result = evaluate_shadow(b"".join(chunks),
                                 host=HostStageConfig(enabled=True),
                                 trusted_store=roots,
                                 now=test_clock)
        # No native write API is reachable here. make_advice hardens all flags.
        return result

    return api


# The ASGI app used by uvicorn is always CLOSED. No trusted_provider is included.
app = create_shadow_app()
