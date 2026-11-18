"""M5 shadow-only invariant and transition-conformance checks.

These tests are executable scenarios, NOT a formal refinement proof. The source
TLA+ model has Boolean abstractions and never invokes these Python functions.
"""
from __future__ import annotations
import base64
from copy import deepcopy
from dataclasses import replace
from hashlib import sha1
import json
from pathlib import Path
import sqlite3
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator, ValidationError

from src.staging_shadow import HostStageConfig, evaluate_shadow
from src.trust_boundary import TrustedStore, TrustRoot
from conftest import STAMP

BASE = Path(__file__).resolve().parents[1]
STAGE_ON = HostStageConfig(enabled=True)
_UNSET = object()


def call(demo, *, host=STAGE_ON, raw=_UNSET):
    return evaluate_shadow(json.dumps(demo.case) if raw is _UNSET else raw,
                           host=host, trusted_store=demo.store, now=STAMP)


def assert_advisory(advice, *, expectation=None):
    schema = json.loads((BASE/'contracts/omega_advice.schema.json').read_text())
    Draft202012Validator(schema).validate(advice)
    assert advice['action_authorised'] is False
    assert advice['native_admissibility_written'] is False
    assert advice['runtime_mutation_permitted'] is False
    assert advice['authoritative'] is False
    assert advice['rights_created'] is False
    assert advice['capital_authorised'] is False
    assert advice['certification'] is False
    assert 'decision' not in advice
    assert 'admissible' not in str(advice)
    if expectation is not None:
        assert advice['review_outcome'] == expectation, advice
    native_schema = json.loads((BASE/'snapshots/runtime_admissibility_contract.json').read_text())
    with pytest.raises(ValidationError):
        Draft202012Validator(native_schema).validate(advice)


def test_default_flag_is_closed_and_advice_cannot_write(demo):
    a = evaluate_shadow(json.dumps(demo.case), trusted_store=demo.store, now=STAMP)
    assert_advisory(a, expectation='HOLD')
    assert 'STAGING_CLOSED_OR_SCOPE_INVALID' in a['issues']


def test_positive_test_case_is_only_advisory(demo):
    assert_advisory(call(demo), expectation='ELIGIBLE_FOR_REVIEW')


@pytest.mark.parametrize('cfg', [
    HostStageConfig(enabled=False),
    HostStageConfig(enabled='true'),
    HostStageConfig(enabled=1),
    HostStageConfig(enabled=True, synthetic_only=False),
    HostStageConfig(enabled=True, no_native_writes=False),
    HostStageConfig(enabled=True, no_network=False),
    HostStageConfig(enabled=True, approved_scope='REAL'),
    {'enabled': True, 'synthetic_only': True},
    None,
])
def test_invalid_host_profile_fails_closed(demo,cfg):
    assert_advisory(call(demo,host=cfg),expectation='HOLD')


@pytest.mark.parametrize('bad',[None,22,{},[],b'{"a":1,"a":2}',
                                    '{"status":"SYNTHETIC_TEST", "status":"REAL"}',
                                    b'\xff\xfe', '{"a":NaN}', b'{' + b'x'*65536 + b'}'])
def test_invalid_input_cannot_enable_stage(demo,bad):
    assert_advisory(call(demo,raw=bad),expectation='HOLD')


def test_untrusted_try_to_install_trust_root_as_json(demo):
    x=deepcopy(demo.case)
    x['trusted_store']={'authorised':True}
    assert_advisory(call(demo,raw=json.dumps(x)),expectation='HOLD')


def test_missing_independent_trust_profile_holds(demo):
    r=evaluate_shadow(json.dumps(demo.case),host=STAGE_ON,now=STAMP)
    assert_advisory(r,expectation='HOLD')


@pytest.mark.parametrize('kind',["source","policy","controls","revocations","review","approval"])
def test_missing_signed_transition_record_holds(demo,kind):
    rec=deepcopy(demo.store.records)
    rec.pop(kind)
    demo.change_store(records=rec)
    assert_advisory(call(demo),expectation='HOLD')


def test_tla_revoke_evidence_invalidates_review(demo):
    # Corresponds to abstract RevokeEvidence, without claiming equivalence.
    e=next(iter(demo.store.raw_evidence))
    rec=deepcopy(demo.store.records)
    c=deepcopy(rec['revocations']['claims'])
    c['revoked_evidence'].append(e)
    rec['revocations']=demo.envelope('revocations','revoker',c)
    demo.change_store(records=rec)
    assert_advisory(call(demo),expectation='HOLD')


def test_tla_expire_revocations_invalidates_review(demo):
    # An outdated revocation list MUST not sustain a review decision.
    rec=deepcopy(demo.store.records)
    c=deepcopy(rec['revocations']['claims'])
    c['expires_at']='2026-11-18T11:59:00+00:00'
    rec['revocations']=demo.envelope('revocations','revoker',c)
    demo.change_store(records=rec)
    assert_advisory(call(demo),expectation='HOLD')


def test_tla_supersede_source_invalidates_review(demo):
    x=deepcopy(demo.case)
    x['source_reconciliation']['active_manifest_hash']='a'*64
    assert_advisory(call(demo,raw=json.dumps(x)),expectation='HOLD')


def test_tla_supersede_policy_invalidates_review(demo):
    demo.change_store(expected_policy_sha256='a'*64)
    assert_advisory(call(demo),expectation='HOLD')


def test_tla_withdraw_review_invalidates_review(demo):
    r=deepcopy(demo.store.records)
    r.pop('review')
    demo.change_store(records=r)
    assert_advisory(call(demo),expectation='HOLD')


def test_tla_withdraw_human_approval_invalidates_review(demo):
    r=deepcopy(demo.store.records)
    r.pop('approval')
    demo.change_store(records=r)
    assert_advisory(call(demo),expectation='HOLD')


def test_tla_no_conflict_invariant(demo):
    x=deepcopy(demo.case)
    x['source_reconciliation']['material_conflict']=True
    a=call(demo,raw=json.dumps(x))
    assert_advisory(a,expectation='HOLD')
    assert 'SOURCE_CONFLICT' in a['issues']


def test_same_ed25519_key_role_alias_detected(demo):
    roots=dict(demo.store.roots)
    roots['approver']=TrustRoot('approver','HUMAN_AUTHORITY',roots['reviewer'].public_key)
    demo.change_store(roots=roots)
    assert_advisory(call(demo),expectation='HOLD')


def test_opaque_claim_cannot_create_runtime_admission(demo):
    a=call(demo)
    for mutation in ({**a,'decision':'admissible'},
                     {**a,'native_admissibility_written':True},
                     {**a,'authoritative':True}):
        schema=json.loads((BASE/'contracts/omega_advice.schema.json').read_text())
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(mutation)


def test_no_side_effects_under_mocked_interfaces(demo,monkeypatch,tmp_path):
    db=tmp_path/'test.sqlite3'
    conn=sqlite3.connect(db)
    conn.execute('create table native_admission (val text)')
    conn.commit();conn.close()
    original=db.read_bytes()
    def deny(*a,**kw):
        raise AssertionError('Forbidden external effect')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)
    monkeypatch.setattr(sqlite3,'connect',deny)
    monkeypatch.setattr(subprocess,'Popen',deny)
    monkeypatch.setattr(Path,'write_text',deny)
    monkeypatch.setattr(Path,'write_bytes',deny)
    result=call(demo)
    assert_advisory(result,expectation='ELIGIBLE_FOR_REVIEW')
    assert db.read_bytes()==original


def test_native_schema_git_blob_matches_pinned_repo():
    raw=(BASE/'snapshots/runtime_admissibility_contract.json').read_bytes()
    gitblob=sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
    assert gitblob=='c81328184b88112ab1786787989093b485e9316a'
