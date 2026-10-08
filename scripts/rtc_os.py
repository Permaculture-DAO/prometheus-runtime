#!/usr/bin/env python3
"""Compile/replay a synthetic RTC-OS dossier locally; never send or persist it."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from app.rtc_os import compile_dossier, replay_dossier
from app.pru import canonical_bytes

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input", type=Path)
parser.add_argument("--replay", action="store_true")
args = parser.parse_args()
try:
    if args.input.stat().st_size > 2_000_000:
        raise ValueError("input exceeds 2 MB")
    with args.input.open("rb") as stream:
        raw = stream.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("input exceeds 2 MB")
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate JSON key")
            result[k] = v
        return result
    payload = json.loads(raw, object_pairs_hook=pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    registry = json.loads((ROOT / "config/semantic_claims_vnext.json").read_text())
    known = frozenset(c["claim_uid"] for c in registry["claims"])
    result = replay_dossier(payload, known_claim_uids=known) if args.replay else canonical_bytes(compile_dossier(payload, known_claim_uids=known))
    print(result.decode())
except (ValueError, OSError, KeyError, TypeError) as exc:
    print(json.dumps({"status":"INVALID","error":str(exc),"capital_authorised":False}))
    sys.exit(1)
