"""Secondary sanitized local export only; not an independent WORM archive."""
from __future__ import annotations
import json
import os
from pathlib import Path
from .ledger import _guard_path, LedgerUnavailable

class JsonlExport:
    def __init__(self, filename: Path):
        self.filename = Path(filename)
        _guard_path(self.filename.parent, directory=True)
        if not self.filename.parent.exists():
            raise LedgerUnavailable('EXPORT_DIRECTORY_MISSING')

    def __call__(self, event: dict) -> None:
        if set(event) != {'seq', 'time_utc', 'event', 'outcome', 'actor', 'nonce', 'audit_mac'}:
            raise LedgerUnavailable('EXPORT_EVENT_SCHEMA_MISMATCH')
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, 'O_NOFOLLOW'): flags |= os.O_NOFOLLOW
        fd = os.open(self.filename, flags, 0o600)
        try:
            with os.fdopen(fd, 'a', encoding='utf-8') as out:
                out.write(json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n')
                out.flush()
                os.fsync(out.fileno())
        finally:
            _guard_path(self.filename)
