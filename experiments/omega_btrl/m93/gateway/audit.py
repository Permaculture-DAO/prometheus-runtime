"""Host-managed stage audit sink: fixed fields only, never logs bearer tokens or JSON."""
from __future__ import annotations
import json
import os
from pathlib import Path

ALLOWED_EVENTS = frozenset({'AUTH_REJECTED', 'STAGING_CLOSED', 'EMERGENCY_STOP',
                            'BAD_CONTENT_TYPE', 'BODY_LIMIT', 'SHADOW_EVALUATED', 'REPLAY_BLOCKED'})
ALLOWED_RESULTS = frozenset({'DENIED', 'HOLD', 'NO_GO', 'ELIGIBLE_FOR_REVIEW'})


class JsonlAudit:
    def __init__(self, filename: Path):
        self.filename = Path(filename)
        # The parent is an owner-only temp directory created by the test host.
        if self.filename.parent.stat().st_mode & 0o077:
            raise ValueError('Audit parent not owner-only')

    def __call__(self, record: dict):
        assert set(record) == {'time', 'event', 'result', 'nonce', 'milestone'}
        if record['event'] not in ALLOWED_EVENTS or record['result'] not in ALLOWED_RESULTS:
            raise ValueError('unsupported audit category')
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.filename, flags, 0o600)
        try:
            with os.fdopen(fd, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try: os.close(fd)
            except OSError: pass
            raise
