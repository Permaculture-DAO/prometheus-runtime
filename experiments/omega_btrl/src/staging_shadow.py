"""PROMETHEUS Omega M5 offline, opt-in, advisory-only execution boundary.

API deliberately NOT mounted in FastAPI/Holochain. HostState cannot be inferred
from candidate bytes. This is NOT an independent approval nor a real MRV decision.
No file, network, process, database, token, or Holochain write APIs are used.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .m3_guard import evaluate_m3
from .trust_boundary import TrustedStore, safe_json, closed_result
from .interop_advisory import make_advice


@dataclass(frozen=True)
class HostStageConfig:
    """Trusted host must instantiate. Not accepted as a request JSON field."""
    enabled: bool = False
    synthetic_only: bool = True
    no_native_writes: bool = True
    no_network: bool = True
    approved_scope: str = "TEST_ONLY"


def _hold(code: str, case_id: str | None = None) -> dict:
    return make_advice(closed_result(reasons=[code], case_id=case_id))


def evaluate_shadow(
    untrusted_case_json: bytes | str,
    *,
    host: HostStageConfig = HostStageConfig(),
    trusted_store: TrustedStore | None = None,
    now: datetime | None = None,
) -> dict:
    """Evaluate ONLY signed test case in memory; always emit non-native advice.

    Intended for isolated staging with caller-provided, independently created
    in-memory trust material. Network and filesystem operations are absent.
    """
    if type(host) is not HostStageConfig:
        return _hold("HOST_STAGE_CONFIG_INVALID")
    if (host.enabled is not True or host.synthetic_only is not True
            or host.no_native_writes is not True or host.no_network is not True
            or host.approved_scope != "TEST_ONLY"):
        return _hold("STAGING_CLOSED_OR_SCOPE_INVALID")
    if type(untrusted_case_json) not in (bytes, str):
        return _hold("CASE_TRANSPORT_INVALID")
    try:
        candidate = safe_json(untrusted_case_json)
    except (UnicodeDecodeError, ValueError, TypeError, OverflowError):
        return _hold("CASE_JSON_INVALID_OR_DUPLICATE")
    if candidate.get("status") != "SYNTHETIC_TEST":
        return _hold("SYNTHETIC_SCOPE_REQUIRED")
    if not isinstance(trusted_store, TrustedStore):
        return _hold("TRUSTED_STORE_REQUIRED")
    return make_advice(evaluate_m3(candidate, trusted_store, now=now))
