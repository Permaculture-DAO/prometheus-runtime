"""STRICTLY LOCAL temporary trust issuer for HTTPS demonstration, NOT VPS code."""
from __future__ import annotations
import os
import json
from pathlib import Path
from tests.conftest import Factory, STAMP
from gateway.secure import create_secure_lab_gateway
from gateway.audit import JsonlAudit

if os.environ.get('M91_EXPLICIT_ISOLATED_TEST') != 'TRUE':
    raise RuntimeError('M91 explicit local-only opt-in required')
lab=Path(os.environ['M91_TEMP_TEST_DIR'])
if lab.stat().st_mode & 0o077:
    raise RuntimeError('lab directory must be owner-only')
TOKEN=os.environ['M91_LAB_TOKEN'].encode('ascii')
assert len(TOKEN)>=32
_fixture=Factory()
# Synthetic case is shared only via private temp filesystem, not HTTP, not signed
# as an organizational identity. The issuer's private key remains in memory.
fd=os.open(lab/'case.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(_fixture.case,f)
app=create_secure_lab_gateway(
    auth_token=TOKEN,staging_enabled=True,
    trust_provider=lambda:_fixture.store,
    emergency_stop_path=lab/'EMERGENCY_STOP',
    audit_sink=JsonlAudit(lab/'audit.jsonl'), test_clock=STAMP)
