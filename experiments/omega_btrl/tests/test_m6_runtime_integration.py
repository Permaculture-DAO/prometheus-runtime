"""M6: cross-repo fixture integrity and fail-closed advisory boundary.

Some tests use an exact pinned GitHub fixture snapshot; only when run inside
prometheus-runtime checkout do they exercise real, unmodified runtime code.
"""
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError
import pytest
from src.staging_shadow import evaluate_shadow, HostStageConfig
from conftest import STAMP

EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = EXPERIMENT.parents[1]
S6 = EXPERIMENT / 'snapshots' / 's6_synthetic_evidence_batch.json'
PINNED_S6_GIT_BLOB = 'f85a1fd553f3fe69cdb7e764f4cae9db405cc492'


def git_blob_sha(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def test_s6_fixture_is_exact_pinned_git_blob():
    raw=S6.read_bytes()
    assert git_blob_sha(raw)==PINNED_S6_GIT_BLOB
    batch=json.loads(raw)
    assert batch['authoritative_for_mrv'] is False
    assert batch['holochain_reference']['commit_performed'] is False
    assert batch['holochain_reference']['entry_ref'] is None
    assert batch['event_count']==len(batch['events'])==3
    assert batch['statement']=='evaluation, not certification'


def test_s6_is_never_eligible_for_omega_advisory(demo):
    result=evaluate_shadow(S6.read_bytes(),host=HostStageConfig(enabled=True),trusted_store=demo.store,now=STAMP)
    assert result['review_outcome']=='HOLD'
    assert result['action_authorised'] is False
    assert result['native_admissibility_written'] is False
    assert result['rights_created'] is False
    assert result['capital_authorised'] is False
    assert result['authoritative'] is False
    schema=json.loads((EXPERIMENT/'snapshots/runtime_admissibility_contract.json').read_text())
    with pytest.raises(ValidationError):Draft202012Validator(schema).validate(result)


def test_native_runtime_s6_equivalence_when_in_checkout():
    original=REPO/'evidence/batches/synthetic_batch_0001.json'
    verifier=REPO/'services/api/app/evidence_batch.py'
    if not original.is_file() or not verifier.is_file():
        pytest.skip('run in actual prometheus-runtime checkout for native integration')
    assert original.read_bytes()==S6.read_bytes(), 'pinned S6 bytes drifted; HOLD'
    spec=importlib.util.spec_from_file_location('omega_test_native_evidence_batch',verifier)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.verify_synthetic_evidence_batch(json.loads(original.read_text()))==[]
    assert module.verify_synthetic_evidence_batch(json.loads(S6.read_text()))==[]


def test_no_omega_imports_in_existing_api_entrypoint_when_in_checkout():
    main=REPO/'services/api/app/main.py'
    if not main.is_file(): pytest.skip('run in actual runtime checkout')
    # M6 MUST NOT be integrated into public FastAPI routing.
    assert 'omega_btrl' not in main.read_text(encoding='utf-8')
    assert 'evaluate_shadow' not in main.read_text(encoding='utf-8')
