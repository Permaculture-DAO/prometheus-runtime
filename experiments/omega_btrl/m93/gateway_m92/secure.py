"""M9.2 lab-only secure sidecar, host-provisioned identity & durable replay.

This is NOT a production API. No runtime DB, Holochain, token, rights or capital
writes. No trusted data is accepted from the request JSON. No IAM/KMS/mTLS.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import stat
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from experimental_sidecar.app import BODY_LIMIT_BYTES
from src.staging_shadow import HostStageConfig, evaluate_shadow
from src.trust_boundary import TrustedStore, closed_result, safe_json, digest
from src.interop_advisory import make_advice
from .identity import ClientRegistry
from .ledger import DurableLedger, LedgerUnavailable, _guard_path


def _hold(code: str) -> dict:
    return make_advice(closed_result(reasons=[code]))


def create_m92_gateway(*,
    staging_enabled: bool = False,
    clients: ClientRegistry | None = None,
    ledger: DurableLedger | None = None,
    trust_provider: Callable[[], TrustedStore] | None = None,
    emergency_stop_path: Path | None = None,
    audit_export: Callable[[dict], None] | None = None,
    test_clock: datetime | None = None,
) -> FastAPI:
    """Closed by default; all capabilities are explicitly injected by the host.

    Replayed positive cases are rejected after restart and across workers sharing
    local POSIX SQLite. For a multi-host VPS, transactional DB and IAM must be
    replaced with enterprise-controlled services, subject to separate approval.
    """
    enabled = (staging_enabled is True and isinstance(clients, ClientRegistry)
               and isinstance(ledger, DurableLedger) and trust_provider is not None
               and emergency_stop_path is not None and audit_export is not None)
    app = FastAPI(title='M9.2 Isolated Durable Shadow Laboratory',
                  docs_url=None, redoc_url=None, openapi_url=None)

    def respond(data: dict, status: int = 200) -> JSONResponse:
        return JSONResponse(content=data, status_code=status,
            headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                     'Referrer-Policy': 'no-referrer', 'X-Robots-Tag': 'noindex'})

    def log(event: str, outcome: str, actor: str='unattributed',
            case_digest: str | None = None) -> tuple[bool, bool]:
        """(operation ok, fresh eligible) where failure always suppresses advice.

        Ledger commits BEFORE secondary export. If export fails, the positive
        receipt remains consumed and the HTTP response is HOLD (fail closed).
        """
        if not isinstance(ledger, DurableLedger) or audit_export is None:
            return False, False
        try:
            fresh, sanitized = ledger.record(event, outcome, actor, case_digest)
            audit_export(sanitized)
            return True, fresh
        except Exception:
            return False, False

    def stopped() -> bool:
        if emergency_stop_path is None:
            return True
        try:
            stop = Path(emergency_stop_path)
            _guard_path(stop.parent, directory=True)
            if not stop.parent.exists():
                return True
            try:
                entry = os.lstat(stop)
            except FileNotFoundError:
                return False
            return True  # Any path entry (including symlink) means STOP.
        except Exception:
            return True

    @app.get('/internal/health')
    async def health():
        # Health reveals no IAM status, trust data or signed policy material.
        return respond({'status':'local_lab','authority':'none',
                        'holochain_write_capability':False,
                        'runtime_write_capability':False,'production_admitted':False})

    @app.post('/internal/advice')
    async def advise(request: Request):
        auth_headers = request.headers.getlist('authorization')
        actor = clients.authenticate(auth_headers) if isinstance(clients, ClientRegistry) else None
        if actor is None:
            if not log('AUTH_REJECTED','DENIED')[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond({'detail':'unauthorized'},401)
        if not enabled:
            if not log('STAGING_CLOSED','HOLD',actor)[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond(_hold('STAGING_CLOSED'),423)
        if stopped():
            if not log('EMERGENCY_STOP','HOLD',actor)[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond(_hold('EMERGENCY_STOP'),423)
        content_types=request.headers.getlist('content-type')
        if len(content_types)!=1 or content_types[0].split(';',1)[0].strip().lower()!='application/json':
            if not log('BAD_CONTENT_TYPE','HOLD',actor)[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond(_hold('CONTENT_TYPE_NOT_ALLOWED'),415)
        body_parts=[]; size=0
        try:
            async for chunk in request.stream():
                size += len(chunk)
                if size > BODY_LIMIT_BYTES:
                    if not log('BODY_LIMIT','HOLD',actor)[0]:
                        return respond(_hold('AUDIT_UNAVAILABLE'),503)
                    return respond(_hold('PAYLOAD_TOO_LARGE'),413)
                body_parts.append(chunk)
        except Exception:
            if not log('REQUEST_STREAM_ERROR','HOLD',actor)[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond(_hold('REQUEST_STREAM_ERROR'),503)
        raw=b''.join(body_parts)
        try:
            candidate=safe_json(raw)
            # Digest is calculated from canonical JSON before evaluating a
            # positive. A request cannot choose the replay key directly.
            canonical_case_hash=digest(candidate)
        except Exception:
            if not log('JSON_INVALID','HOLD',actor)[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond(_hold('CASE_JSON_INVALID_OR_DUPLICATE'),422)
        try:
            trusted=trust_provider()
            if not isinstance(trusted, TrustedStore):
                advice=_hold('HOST_TRUST_PROVIDER_INVALID')
            else:
                advice=evaluate_shadow(raw,host=HostStageConfig(enabled=True),
                                       trusted_store=trusted,now=test_clock)
        except Exception:
            advice=_hold('HOST_TRUST_PROVIDER_ERROR')
        outcome=advice.get('review_outcome','HOLD')
        if outcome not in ('ELIGIBLE_FOR_REVIEW','HOLD','NO_GO'):
            advice=_hold('UNEXPECTED_OUTPUT')
            outcome='HOLD'
        if stopped():
            if not log('EMERGENCY_STOP','HOLD',actor)[0]:
                return respond(_hold('AUDIT_UNAVAILABLE'),503)
            return respond(_hold('EMERGENCY_STOP'),423)
        # The only path returning a positive result must atomically consume
        # replay receipt AND audit commit, then pass a second audit export.
        ok, fresh = log('SHADOW_EVALUATED',outcome,actor,
                        case_digest=canonical_case_hash if outcome=='ELIGIBLE_FOR_REVIEW' else None)
        if not ok:
            return respond(_hold('AUDIT_OR_REPLAY_LEDGER_UNAVAILABLE'),503)
        if outcome=='ELIGIBLE_FOR_REVIEW' and not fresh:
            return respond(_hold('REPLAY_BLOCKED'),423)
        return respond(advice)

    return app

# Always-closed importable entrypoint; no credentials, identity or trust installed.
app = create_m92_gateway()
