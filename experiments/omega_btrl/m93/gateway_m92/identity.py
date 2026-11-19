"""M9.2 host-provisioned LAB client identities; NOT IAM or enterprise mTLS.

Client identity is a host-side record, never derived from request body, JSON or
untrusted X-Client-* headers. A real issuer / revocation feed is still required.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from typing import Mapping


@dataclass(frozen=True)
class ClientRecord:
    actor: str
    token_sha256: bytes
    scopes: frozenset[str]
    expires_at: datetime
    revoked: bool = False

    def __post_init__(self) -> None:
        if not self.actor.isascii() or not (1 <= len(self.actor) <= 64) or not all(
                x.isalnum() or x in '_-' for x in self.actor):
            raise ValueError('INVALID_HOST_ACTOR')
        if type(self.token_sha256) is not bytes or len(self.token_sha256) != 32:
            raise ValueError('INVALID_TOKEN_DIGEST')
        if self.expires_at.tzinfo is None:
            raise ValueError('EXPLICIT_EXPIRY_REQUIRED')


class ClientRegistry:
    def __init__(self, records: tuple[ClientRecord, ...]):
        if len(records) < 1 or len(records) > 128:
            raise ValueError('CLIENT_REGISTRY_EMPTY_OR_TOO_LARGE')
        if len({r.actor for r in records}) != len(records):
            raise ValueError('DUPLICATE_HOST_ACTOR')
        if len({r.token_sha256 for r in records}) != len(records):
            raise ValueError('SHARED_TOKEN_FOR_DISTINCT_ACTORS')
        self._records = records

    def authenticate(self, authorization_values: list[str], now: datetime | None = None) -> str | None:
        if len(authorization_values) != 1:
            return None
        h = authorization_values[0]
        if not h.startswith('Bearer ') or len(h) > 512:
            return None
        token = h[7:]
        if len(token) < 32 or not token.isascii():
            return None
        raw_digest = sha256(token.encode('ascii')).digest()
        now = now or datetime.now(timezone.utc)
        chosen = None
        for r in self._records:
            matched = hmac.compare_digest(raw_digest, r.token_sha256)
            if matched and not r.revoked and now < r.expires_at and 'omega:review-synthetic' in r.scopes:
                chosen = r.actor
        return chosen

    @staticmethod
    def from_host_secrets(config: Mapping[str, tuple[bytes, frozenset[str], datetime, bool]]) -> 'ClientRegistry':
        # Caller supplies host-owned secret inputs; never read config from HTTP.
        records = []
        for actor, (secret, scopes, expiry, revoked) in config.items():
            if type(secret) is not bytes or len(secret) < 32:
                raise ValueError('HOST_SECRET_INVALID')
            records.append(ClientRecord(actor, sha256(secret).digest(), scopes, expiry, revoked))
        return ClientRegistry(tuple(records))
