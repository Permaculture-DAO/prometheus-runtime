"""M9.2 LAB ONLY: durable process-shared replay veto + transactional audit.

SQLite WAL under a local POSIX owner-only directory. A separate local anchor
records (last-sequence, HMAC head); it is NOT an independent WORM attestation.
Failures are FAIL CLOSED. Never expose or deploy this lab-only store to a VPS.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import stat
from typing import Callable, Iterator
from uuid import uuid4

ZERO = '0' * 64
EVENTS = frozenset({
    'AUTH_REJECTED', 'STAGING_CLOSED', 'EMERGENCY_STOP', 'BAD_CONTENT_TYPE',
    'BODY_LIMIT', 'SHADOW_EVALUATED', 'REPLAY_BLOCKED', 'TRUST_ERROR',
    'JSON_INVALID', 'REQUEST_STREAM_ERROR', 'AUDIT_RECONCILIATION',
})
RESULTS = frozenset({'DENIED', 'HOLD', 'NO_GO', 'ELIGIBLE_FOR_REVIEW'})


class LedgerUnavailable(RuntimeError):
    """Closed condition for missing or suspect durable state."""


class LedgerIntegrityError(LedgerUnavailable):
    """HMAC/anchor mismatch or unauthorized change."""


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _guard_path(path: Path, *, directory: bool = False) -> None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    if directory:
        valid = stat.S_ISDIR(st.st_mode) and (st.st_mode & 0o077) == 0
    else:
        valid = (stat.S_ISREG(st.st_mode) and st.st_nlink == 1
                 and (st.st_mode & 0o077) == 0)
    if st.st_uid != os.getuid() or not valid:
        raise LedgerUnavailable('INSECURE_LEDGER_PATH')


def _create_exclusive(path: Path) -> None:
    try:
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        os.close(fd)
    except FileExistsError:
        pass
    _guard_path(path)


class DurableLedger:
    """A fail-closed, local synthetic ledger shared by multiple worker processes.

    Do not infer identity from the case. The audit HMAC key must be host-owned,
    persistent through restarts, and inaccessible to HTTP requesters. This
    implementation is POSIX-only; NFS/multi-host SQLite is NOT supported.
    """
    def __init__(self, state_dir: Path, *, audit_hmac_key: bytes):
        if type(audit_hmac_key) is not bytes or len(audit_hmac_key) < 32:
            raise LedgerUnavailable('AUDIT_KEY_REQUIRED')
        self.state_dir = Path(state_dir)
        self.db = self.state_dir / 'replay.sqlite3'
        self.anchor = self.state_dir / 'audit.anchor'
        self.lockfile = self.state_dir / 'ledger.lock'
        self._key = audit_hmac_key
        self._initialize()

    @contextmanager
    def _locked(self) -> Iterator[None]:
        _guard_path(self.state_dir, directory=True)
        _create_exclusive(self.lockfile)
        flags = os.O_RDWR
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.lockfile, flags)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            _guard_path(self.lockfile)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _open(self) -> sqlite3.Connection:
        _guard_path(self.db)
        if not self.db.exists():
            raise LedgerUnavailable('LEDGER_DB_MISSING')
        conn = sqlite3.connect(str(self.db), timeout=20, isolation_level=None)
        try:
            conn.execute('PRAGMA busy_timeout=20000')
            conn.execute('PRAGMA synchronous=FULL')
            conn.execute('PRAGMA journal_mode=WAL')
            _guard_path(self.db)
            return conn
        except Exception:
            conn.close()
            raise

    def _read_anchor(self) -> tuple[int, str]:
        _guard_path(self.anchor)
        try:
            item = json.loads(self.anchor.read_text(encoding='ascii'))
            seq, mac = item['seq'], item['mac']
            if type(seq) is not int or seq < 0 or not isinstance(mac, str) or len(mac) != 64:
                raise ValueError('invalid anchor')
            return seq, mac
        except Exception as exc:
            raise LedgerIntegrityError('AUDIT_ANCHOR_MISSING_OR_INVALID') from exc

    def _write_anchor(self, seq: int, mac: str) -> None:
        # Exactly one cooperating process holds the POSIX lock. Atomic rename
        # never permits serving a positive if the anchor write fails.
        target = self.state_dir / ('anchor.' + uuid4().hex + '.new')
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(_canonical({'seq': seq, 'mac': mac}) + b'\n')
                f.flush()
                os.fsync(f.fileno())
            os.replace(target, self.anchor)
            dirfd = os.open(self.state_dir, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try:os.fsync(dirfd)
            finally:os.close(dirfd)
            _guard_path(self.anchor)
        finally:
            try: target.unlink(missing_ok=True)
            except OSError: pass

    def _mac(self, record: dict, previous: str) -> str:
        return hmac.new(self._key, previous.encode('ascii') + b':' + _canonical(record), hashlib.sha256).hexdigest()

    def _verify_locked(self, conn: sqlite3.Connection) -> tuple[int, str]:
        seq, previous = 0, ZERO
        rows = conn.execute('SELECT seq, time_utc, event, outcome, actor, case_digest, nonce, prev_mac, mac FROM audit_events ORDER BY seq')
        for row in rows:
            current, stamp, event, outcome, actor, case_digest, nonce, prev_mac, mac = row
            if current != seq + 1 or prev_mac != previous:
                raise LedgerIntegrityError('AUDIT_SEQUENCE_INVALID')
            record = dict(seq=current, time_utc=stamp, event=event, outcome=outcome,
                          actor=actor, case_digest=case_digest, nonce=nonce)
            if not hmac.compare_digest(self._mac(record, previous), mac):
                raise LedgerIntegrityError('AUDIT_MAC_MISMATCH')
            seq, previous = current, mac
        expected = self._read_anchor()
        if (seq, previous) != expected:
            raise LedgerIntegrityError('AUDIT_ANCHOR_MISMATCH')
        # An attacker without the HMAC key could otherwise delete a replay
        # receipt while preserving the signed audit chain, then obtain a
        # second positive on the next request. Verify complete 1-to-1 mapping.
        positive_digests = [x[0] for x in conn.execute(
            "SELECT case_digest FROM audit_events WHERE outcome='ELIGIBLE_FOR_REVIEW'")]
        stored_digests = [x[0] for x in conn.execute('SELECT digest FROM replay_cases')]
        if (len(positive_digests) != len(set(positive_digests))
                or set(positive_digests) != set(stored_digests)):
            raise LedgerIntegrityError('AUDIT_REPLAY_BIJECTION_VIOLATION')
        return seq, previous

    def _initialize(self) -> None:
        _guard_path(self.state_dir, directory=True)
        if not self.state_dir.exists():
            self.state_dir.mkdir(mode=0o700, parents=False)
        _guard_path(self.state_dir, directory=True)
        with self._locked():
            _create_exclusive(self.db)
            conn = self._open()
            try:
                conn.executescript('''
                CREATE TABLE IF NOT EXISTS replay_cases (
                    digest TEXT PRIMARY KEY CHECK(length(digest)=64),
                    first_utc TEXT NOT NULL, actor TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    time_utc TEXT NOT NULL, event TEXT NOT NULL,
                    outcome TEXT NOT NULL, actor TEXT NOT NULL,
                    case_digest TEXT, nonce TEXT NOT NULL,
                    prev_mac TEXT NOT NULL, mac TEXT NOT NULL);
                ''')
                if not self.anchor.exists():
                    count = conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
                    if count != 0:
                        raise LedgerIntegrityError('MISSING_ANCHOR_WITH_HISTORY')
                    self._write_anchor(0, ZERO)
                self._verify_locked(conn)
            finally:conn.close()

    def _run(self, *, event: str, outcome: str, actor: str,
             case_digest: str | None = None) -> tuple[bool, dict]:
        if event not in EVENTS or outcome not in RESULTS:
            raise LedgerUnavailable('AUDIT_VOCABULARY_VIOLATION')
        if not isinstance(actor, str) or not actor or len(actor) > 96:
            raise LedgerUnavailable('INVALID_ACTOR_LABEL')
        if case_digest is not None and (type(case_digest) is not str or len(case_digest) != 64
                                        or any(c not in '0123456789abcdef' for c in case_digest)):
            raise LedgerUnavailable('INVALID_CASE_DIGEST')
        with self._locked():
            conn = self._open()
            try:
                seq, previous = self._verify_locked(conn)
                conn.execute('BEGIN IMMEDIATE')
                accepted = False
                actual_event, actual_outcome = event, outcome
                timestamp = datetime.now(timezone.utc).isoformat()
                if outcome == 'ELIGIBLE_FOR_REVIEW':
                    if case_digest is None:
                        raise LedgerUnavailable('MISSING_REPLAY_KEY')
                    cursor = conn.execute('INSERT OR IGNORE INTO replay_cases(digest, first_utc, actor) VALUES(?,?,?)',
                                          (case_digest, timestamp, actor))
                    accepted = cursor.rowcount == 1
                    if not accepted:
                        actual_event, actual_outcome = 'REPLAY_BLOCKED', 'HOLD'
                record = dict(seq=seq + 1, time_utc=timestamp, event=actual_event,
                              outcome=actual_outcome, actor=actor, case_digest=case_digest,
                              nonce=uuid4().hex)
                mac = self._mac(record, previous)
                conn.execute('INSERT INTO audit_events(seq, time_utc,event,outcome,actor,case_digest,nonce,prev_mac,mac) VALUES(?,?,?,?,?,?,?,?,?)',
                             (record['seq'], timestamp, actual_event, actual_outcome, actor, case_digest,
                              record['nonce'], previous, mac))
                conn.commit()
                self._write_anchor(seq + 1, mac)
                # Return sanitized event; never include digest in external export.
                exported = {k:record[k] for k in ('seq', 'time_utc', 'event', 'outcome', 'actor', 'nonce')}
                exported['audit_mac'] = mac
                return accepted, exported
            except Exception as exc:
                try:conn.rollback()
                except Exception:pass
                if isinstance(exc, LedgerUnavailable):raise
                raise LedgerUnavailable('REPLAY_AUDIT_WRITE_FAILED') from exc
            finally:conn.close()

    def record(self, event: str, outcome: str, actor: str = 'unattributed',
               case_digest: str | None = None) -> tuple[bool, dict]:
        return self._run(event=event, outcome=outcome, actor=actor, case_digest=case_digest)

    def verify(self) -> dict:
        with self._locked():
            conn = self._open()
            try:
                seq, mac = self._verify_locked(conn)
                replay_count = conn.execute('SELECT COUNT(*) FROM replay_cases').fetchone()[0]
                eligible_count = conn.execute("SELECT COUNT(*) FROM audit_events WHERE outcome='ELIGIBLE_FOR_REVIEW'").fetchone()[0]
                if eligible_count != replay_count:
                    raise LedgerIntegrityError('REPLAY_TO_AUDIT_MISMATCH')
                return {'verified': True, 'audit_events': seq, 'replay_entries': replay_count,
                        'anchor_mac': mac}
            finally:conn.close()
