"""Offline-only consistent backup of SQLite ledger + its local anchor.

This backup intentionally omits the secret HMAC key and audit exporter files.
Restore requires host's *original* key and separate audit export reconciliation.
It is NOT an operator-approved production DR procedure.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from .ledger import DurableLedger, LedgerUnavailable, _guard_path


def snapshot_ledger(ledger: DurableLedger, destination: Path) -> dict:
    dest=Path(destination)
    if dest.exists():
        raise LedgerUnavailable('REFUSE_SNAPSHOT_OVERWRITE')
    dest.mkdir(mode=0o700)
    _guard_path(dest,directory=True)
    with ledger._locked():
        src=ledger._open()
        try:
            seq,mac=ledger._verify_locked(src)
            temp=dest/'replay.sqlite3'
            new=sqlite3.connect(temp)
            try:
                src.backup(new)
                new.commit()
            finally:new.close()
            os.chmod(temp,0o600)
            anchor=dest/'audit.anchor'
            anchor.write_bytes(ledger.anchor.read_bytes())
            os.chmod(anchor,0o600)
            # The lockfile is created on recovery, it is not part of history.
            dirfd=os.open(dest,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
            try:os.fsync(dirfd)
            finally:os.close(dirfd)
            report={'status':'SNAPSHOT_LAB_ONLY','audit_seq':seq,
                    'database_sha256':hashlib.sha256(temp.read_bytes()).hexdigest(),
                    'anchor_sha256':hashlib.sha256(anchor.read_bytes()).hexdigest(),
                    'key_included':False,'separate_audit_export_included':False}
            (dest/'MANIFEST.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
            return report
        finally:src.close()
