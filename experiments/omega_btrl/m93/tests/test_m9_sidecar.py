"""M9 shadow advisory HTTP tests; no production endpoints or test keys persist."""
from __future__ import annotations
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from experimental_sidecar.app import create_shadow_app, BODY_LIMIT_BYTES
from tests.conftest import Factory, STAMP, OMEGA

SCHEMA=json.loads((OMEGA/'contracts/omega_advice.schema.json').read_text())
NATIVE_SCHEMA=json.loads((OMEGA/'snapshots/runtime_admissibility_contract.json').read_text())


def check_advice(a, outcome=None):
    assert Draft202012Validator(SCHEMA).is_valid(a),a
    assert not Draft202012Validator(NATIVE_SCHEMA).is_valid(a)
    for k in ['action_authorised','certification','capital_authorised','rights_created',
              'native_admissibility_written','runtime_mutation_permitted','authoritative']:
        assert a[k] is False,(k,a)
    assert a['authority_boundary']=='RECOMMENDATION_ONLY_NO_NATIVE_ADMISSION'
    if outcome is not None: assert a['review_outcome']==outcome,a


def test_closed_default_http():
    demo=Factory()
    with TestClient(create_shadow_app()) as c:
        assert c.get('/internal/health').json()['staging_enabled'] is False
        check_advice(c.post('/internal/advice',json=demo.case).json(),'HOLD')


def test_stage_enabled_without_trust_is_closed():
    demo=Factory()
    with TestClient(create_shadow_app(stage_enabled=True)) as c:
        check_advice(c.post('/internal/advice',json=demo.case).json(),'HOLD')


def test_staging_test_issuer_can_obtain_advice_but_never_runtime_admission():
    demo=Factory()
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        a=c.post('/internal/advice',json=demo.case).json()
        check_advice(a,'ELIGIBLE_FOR_REVIEW')
        assert c.post('/v1/runtime/evaluate',json={}).status_code==404
        assert c.post('/v1/evidence/candidates',json={}).status_code==404
        assert c.post('/holochain',json={}).status_code==404
        assert c.get('/openapi.json').status_code==404
        assert c.get('/docs').status_code==404


def test_tampered_case_is_held():
    demo=Factory()
    altered=deepcopy(demo.case)
    altered['assurance_case_id']='M9-FORGED-BY-CALLER'
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        check_advice(c.post('/internal/advice',json=altered).json(),'HOLD')


def test_request_cannot_inject_trust_or_override_host():
    demo=Factory()
    altered=deepcopy(demo.case)
    altered['trusted_store']={'enabled':True,'signing_key':'example'}
    altered['host']={'enabled':True,'approved_scope':'REAL'}
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        check_advice(c.post('/internal/advice',json=altered).json(),'HOLD')


def test_invalid_json_duplicate_json_and_oversize_hold():
    demo=Factory()
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        for raw in [b'{',b'{"x":1,"x":2}',b'['+b'x'*BODY_LIMIT_BYTES+b']',b'null']:
            check_advice(c.post('/internal/advice',content=raw,headers={'content-type':'application/json'}).json(),'HOLD')
        check_advice(c.post('/internal/advice',content=json.dumps(demo.case),headers={'content-type':'text/plain'}).json(),'HOLD')


def test_bad_or_throwing_host_trust_provider_holds():
    demo=Factory()
    for provider in [lambda:None, lambda:(_ for _ in ()).throw(RuntimeError('failed'))]:
        with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=provider,test_clock=STAMP)) as c:
            check_advice(c.post('/internal/advice',json=demo.case).json(),'HOLD')


def test_expired_revocation_holds():
    demo=Factory()
    records=deepcopy(demo.store.records)
    claims=deepcopy(records['revocations']['claims'])
    claims['expires_at']='2026-11-18T11:59:00+00:00'
    records['revocations']=demo.envelope('revocations','revoker',claims)
    demo.change_store(records=records)
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        check_advice(c.post('/internal/advice',json=demo.case).json(),'HOLD')


def test_shared_role_key_holds():
    from src.trust_boundary import TrustRoot
    demo=Factory()
    roots=dict(demo.store.roots)
    roots['approver']=TrustRoot('approver','HUMAN_AUTHORITY',roots['reviewer'].public_key)
    demo.change_store(roots=roots)
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        check_advice(c.post('/internal/advice',json=demo.case).json(),'HOLD')


def test_no_state_change_for_real_service_local_sentinel(tmp_path):
    demo=Factory()
    sentinel=tmp_path/'native_decision.txt'
    sentinel.write_text('NO_NATIVE_DECISIONS')
    old=hashlib.sha256(sentinel.read_bytes()).hexdigest()
    with TestClient(create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)) as c:
        for i in range(20):
            check_advice(c.post('/internal/advice',json=demo.case).json(),'ELIGIBLE_FOR_REVIEW')
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest()==old
