"""M9.1 experimental stage-only ingress. NOT a released API or VPS component.

The shadow evaluator remains non-authoritative; the gateway does not import any
native PROMETHEUS API, database connector, Holochain or outbound network client.
All trusted values, emergency stop and auditor are HOST-injected, never JSON.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from experimental_sidecar.app import BODY_LIMIT_BYTES
from src.staging_shadow import HostStageConfig, evaluate_shadow
from src.trust_boundary import TrustedStore, closed_result, safe_json, digest
from src.interop_advisory import make_advice


def _hold(code: str) -> dict:
    return make_advice(closed_result(reasons=[code]))


class AuditUnavailable(Exception):
    pass


def create_secure_lab_gateway(
    *,
    auth_token: bytes | None = None,
    staging_enabled: bool = False,
    trust_provider: Callable[[], TrustedStore] | None = None,
    emergency_stop_path: Path | None = None,
    audit_sink: Callable[[dict], None] | None = None,
    test_clock: datetime | None = None,
) -> FastAPI:
    """Closed by default. A test issuer is never generated in this function.

    Client authorization is only a *laboratory* shared token; a real staging
    service must use independent IAM/mTLS, revocation and audited secret custody.
    """
    token_hash = None
    if type(auth_token) is bytes and len(auth_token) >= 32:
        token_hash = hashlib.sha256(auth_token).digest()
    # Do not silently accept short, empty or non-byte credentials.
    enabled = (
        staging_enabled is True
        and token_hash is not None
        and trust_provider is not None
        and emergency_stop_path is not None
        and audit_sink is not None
    )
    replay_lock = Lock()
    seen_review_cases: set[str] = set()
    replay_capacity = 4096  # Finite in-process LAB-only cache; no distributed guarantee.
    app = FastAPI(title='M9.1 Isolated Assurance Test Gateway',
                  docs_url=None, redoc_url=None, openapi_url=None)

    def emit(event: str, result: str) -> bool:
        if audit_sink is None:
            return False
        try:
            # Fixed vocabulary: no client-controlled data or credentials.
            audit_sink({'time': datetime.now(timezone.utc).isoformat(),
                        'event': event, 'result': result,
                        'nonce': uuid4().hex[:16], 'milestone': 'M9.1'})
            return True
        except Exception:
            return False

    def answer(data: dict, status: int = 200) -> JSONResponse:
        return JSONResponse(content=data, status_code=status,
                            headers={'Cache-Control': 'no-store',
                                     'X-Content-Type-Options': 'nosniff',
                                     'Referrer-Policy': 'no-referrer'})

    @app.get('/internal/health')
    async def health():
        return answer({'status': 'lab', 'authority': 'none',
                       'runtime_write_capability': False,
                       'holochain_write_capability': False})

    @app.post('/internal/advice')
    async def advice(request: Request):
        # Authentication occurs BEFORE request.body() or parsing; duplicate
        # Authorization headers are rejected rather than normalized implicitly.
        auth_headers = request.headers.getlist('authorization')
        valid = False
        if token_hash is not None and len(auth_headers) == 1:
            header = auth_headers[0]
            if header.startswith('Bearer ') and len(header) <= 512:
                token = header[len('Bearer '):].encode('utf-8')
                valid = hmac.compare_digest(hashlib.sha256(token).digest(), token_hash)
        if not valid:
            if not emit('AUTH_REJECTED', 'DENIED'):
                return answer(_hold('AUDIT_UNAVAILABLE'), 503)
            return answer({'detail': 'unauthorized'}, 401)
        if not enabled:
            if not emit('STAGING_CLOSED', 'HOLD'):
                return answer(_hold('AUDIT_UNAVAILABLE'), 503)
            return answer(_hold('STAGING_CLOSED'), 423)
        try:
            # No process-level open/close API exists. Only a privileged local
            # operator can create the stop file; it remains off until removed.
            if emergency_stop_path.exists():
                if not emit('EMERGENCY_STOP', 'HOLD'):
                    return answer(_hold('AUDIT_UNAVAILABLE'), 503)
                return answer(_hold('EMERGENCY_STOP'), 423)
        except Exception:
            return answer(_hold('EMERGENCY_STOP_UNCHECKABLE'), 503)
        content_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
        if content_type != 'application/json':
            if not emit('BAD_CONTENT_TYPE', 'HOLD'):
                return answer(_hold('AUDIT_UNAVAILABLE'), 503)
            return answer(_hold('CONTENT_TYPE_NOT_ALLOWED'), 415)
        parts, size = [], 0
        try:
            async for part in request.stream():
                size += len(part)
                if size > BODY_LIMIT_BYTES:
                    if not emit('BODY_LIMIT', 'HOLD'):
                        return answer(_hold('AUDIT_UNAVAILABLE'), 503)
                    return answer(_hold('PAYLOAD_TOO_LARGE'), 413)
                parts.append(part)
        except Exception:
            return answer(_hold('REQUEST_STREAM_ERROR'), 503)
        try:
            trusted_store = trust_provider()
            if not isinstance(trusted_store, TrustedStore):
                result = _hold('HOST_TRUST_PROVIDER_INVALID')
            else:
                result = evaluate_shadow(b''.join(parts),
                    host=HostStageConfig(enabled=True),
                    trusted_store=trusted_store, now=test_clock)
        except Exception:
            result = _hold('HOST_TRUST_PROVIDER_ERROR')
        outcome = result.get('review_outcome', 'HOLD')
        if outcome not in ('HOLD', 'NO_GO', 'ELIGIBLE_FOR_REVIEW'):
            return answer(_hold('ADVICE_OUTCOME_UNEXPECTED'), 503)
        # Stage-only bounded replay veto. Canonical digest prevents JSON
        # whitespace/key order bypass. This is NOT durable/distributed replay
        # protection and resets on process restart: still HOLD for deployment.
        if outcome == 'ELIGIBLE_FOR_REVIEW':
            try:
                case_digest = digest(safe_json(b''.join(parts)))
            except Exception:
                return answer(_hold('REPLAY_DIGEST_INVALID'), 503)
            with replay_lock:
                if case_digest in seen_review_cases:
                    if not emit('REPLAY_BLOCKED', 'HOLD'):
                        return answer(_hold('AUDIT_UNAVAILABLE'), 503)
                    return answer(_hold('REPLAY_BLOCKED'), 423)
                if len(seen_review_cases) >= replay_capacity:
                    return answer(_hold('REPLAY_CAPACITY_EXHAUSTED'), 503)
                seen_review_cases.add(case_digest)
        # Audit failure has priority over a positive review recommendation.
        if not emit('SHADOW_EVALUATED', outcome):
            return answer(_hold('AUDIT_UNAVAILABLE'), 503)
        return answer(result)

    return app
