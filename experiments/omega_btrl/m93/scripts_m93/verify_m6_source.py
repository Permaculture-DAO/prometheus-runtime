#!/usr/bin/env python3
"""Verify the M6 pinned source mapping. No GitHub push or runtime calls."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
META=Path(__file__).resolve().parents[1]/'docs/M93_REVIEW_CANDIDATE_METADATA.json'
def sha1_blob(raw:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()

meta=json.loads(META.read_text())
assert meta['target_sha']=='0778ba2a1bf91366777d4d7911fa8dafee784f25'
for rel,expected in meta['source_blob_sha1'].items():
    raw=(ROOT/rel).read_bytes()
    assert sha1_blob(raw)==expected,rel+' SOURCE_GIT_BLOB_DRIFT'
    assert hashlib.sha256(raw).hexdigest()==meta['source_file_sha256'][rel],rel+' SOURCE_SHA256_DRIFT'
assert not (ROOT/'m93/omega_btrl_snapshot').exists(),'DUPLICATED_M6_SOURCE'
assert 'gateway_m92' not in (ROOT.parent.parent/'services/api/app/main.py').read_text() if (ROOT.parent.parent/'services/api/app/main.py').exists() else True
print('M93_M6_SOURCE_PROVENANCE_PASS')
