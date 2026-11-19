"""Explicit synthetic test issuer adapter. NOT a deployable service.

Only host-owned files with public roots and pre-signed synthetic receipts are
loaded. Private Ed25519 keys are NOT passed to the server and are never saved.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src.trust_boundary import TrustedStore, TrustRoot
from gateway_m92.identity import ClientRegistry
from gateway_m92.ledger import DurableLedger
from gateway_m92.exporter import JsonlExport
from gateway_m92.secure import create_m92_gateway

if os.environ.get('M92_SYNTHETIC_LAB_ONLY') != 'EXPLICIT':
    app = create_m92_gateway()
else:
    directory = Path(os.environ['M92_OWNER_ONLY_DIR'])
    if directory.stat().st_mode & 0o077:
        raise RuntimeError('LAB_DIR_INSECURE')
    data = json.loads((directory/'host_signed_fixture.json').read_text())
    trusted = TrustedStore(
        roots={k:TrustRoot(k,v['role'],base64.b64decode(v['public_key']))
               for k,v in data['roots'].items()},
        expected_manifest_sha256=data['expected_manifest_sha256'],
        expected_policy_sha256=data['expected_policy_sha256'],
        minimum_revocation_epoch=data['minimum_revocation_epoch'],
        records=data['records'],
        raw_evidence={k:base64.b64decode(v) for k,v in data['raw_evidence'].items()},
    )
    token_a = os.environ['M92_LAB_TOKEN_A'].encode('ascii')
    token_b = os.environ['M92_LAB_TOKEN_B'].encode('ascii')
    audit_key = bytes.fromhex(os.environ['M92_LAB_AUDIT_KEY_HEX'])
    clients = ClientRegistry.from_host_secrets({
      'synthetic_client_a': (token_a,frozenset({'omega:review-synthetic'}),
                              datetime.now(timezone.utc)+timedelta(hours=1),False),
      'synthetic_client_b': (token_b,frozenset({'omega:review-synthetic'}),
                              datetime.now(timezone.utc)+timedelta(hours=1),False),
    })
    from tests_m92.conftest import STAMP
    app = create_m92_gateway(staging_enabled=True,clients=clients,
        ledger=DurableLedger(directory/'durable_state',audit_hmac_key=audit_key),
        trust_provider=lambda:trusted,
        emergency_stop_path=directory/'EMERGENCY_STOP',
        audit_export=JsonlExport(directory/'secondary_audit'/'events.jsonl'),
        test_clock=STAMP)
