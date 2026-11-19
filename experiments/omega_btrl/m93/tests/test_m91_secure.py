"""M9.1 local-only ingress, auditing and kill switch regression suite."""
from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from gateway.secure import create_secure_lab_gateway, BODY_LIMIT_BYTES
from tests.conftest import Factory, STAMP, OMEGA

TOKEN = b'm91-synthetic-lab-token-longer-than-thirty-two-bytes'
SCHEMA = json.loads((OMEGA/'contracts/omega_advice.schema.json').read_text())


def make_app(tmp_path, demo=None, *, enabled=True, token=TOKEN, audit=None, trust=None):
    demo = demo or Factory()
    events = [] if audit is None else audit
    app = create_secure_lab_gateway(
        auth_token=token, staging_enabled=enabled,
        trust_provider=(lambda: demo.store) if trust is None else trust,
        emergency_stop_path=tmp_path/'STOP', audit_sink=events.append,
        test_clock=STAMP)
    return app, demo, events


def check_advice(obj, outcome):
    assert Draft202012Validator(SCHEMA).is_valid(obj), obj
    assert obj['review_outcome'] == outcome
    assert obj['authoritative'] is False
    assert obj['native_admissibility_written'] is False
    assert obj['holochain_commit_performed'] is False if 'holochain_commit_performed' in obj else True
    assert obj['action_authorised'] is False


def post(client, value, token=TOKEN):
    return client.post('/internal/advice', json=value,
        headers={'Authorization': 'Bearer '+token.decode('ascii')})


def test_fail_closed_default_token_missing(tmp_path):
    app = create_secure_lab_gateway()
    with TestClient(app) as c:
        assert c.get('/internal/health').status_code == 200
        assert c.get('/internal/health').json()['authority'] == 'none'
        assert c.post('/internal/advice', json={}).status_code in (401,503)
        assert c.get('/openapi.json').status_code == 404


def test_authenticated_lab_positive_advice_is_non_authoritative(tmp_path):
    app, demo, audit = make_app(tmp_path)
    with TestClient(app) as c:
        resp = post(c, demo.case)
        assert resp.status_code == 200
        check_advice(resp.json(), 'ELIGIBLE_FOR_REVIEW')
        assert resp.headers['cache-control'] == 'no-store'
        assert c.post('/v1/evidence/candidates',json={}).status_code == 404
        assert c.post('/holochain',json={}).status_code == 404
    assert audit[-1]['event'] == 'SHADOW_EVALUATED'
    assert audit[-1]['result'] == 'ELIGIBLE_FOR_REVIEW'


def test_no_bearer_invalid_bearer_and_token_guess(tmp_path):
    app,demo,events=make_app(tmp_path)
    with TestClient(app) as c:
        for headers in ({}, {'Authorization':'Bearer fake'}, {'Authorization':'Basic '+TOKEN.decode()},
                        {'Authorization':'Bearer '+TOKEN.decode()+'x'}):
            res = c.post('/internal/advice', json=demo.case, headers=headers)
            assert res.status_code == 401
    assert len(events)==4 and all(e['event']=='AUTH_REJECTED' for e in events)


def test_duplicate_authorization_header_denied(tmp_path):
    app,demo,_=make_app(tmp_path)
    with TestClient(app) as c:
        res=c.post('/internal/advice',json=demo.case,headers=[
            ('authorization','Bearer '+TOKEN.decode()),
            ('authorization','Bearer '+TOKEN.decode())])
        assert res.status_code == 401


def test_stage_disabled_even_when_token_valid(tmp_path):
    app,demo,_=make_app(tmp_path,enabled=False)
    with TestClient(app) as c:
        res=post(c,demo.case)
        assert res.status_code==423
        check_advice(res.json(),'HOLD')


def test_emergency_stop_revokes_without_restarting_process(tmp_path):
    app,demo,events=make_app(tmp_path)
    stop=tmp_path/'STOP'
    with TestClient(app) as c:
        check_advice(post(c,demo.case).json(),'ELIGIBLE_FOR_REVIEW')
        stop.write_text('STOP - OPERATOR ONLY')
        for _ in range(3):
            res=post(c,demo.case)
            assert res.status_code==423
            check_advice(res.json(),'HOLD')
    assert [e['event'] for e in events].count('EMERGENCY_STOP') == 3


def test_forged_trust_root_host_override_and_content_type(tmp_path):
    app,demo,_=make_app(tmp_path)
    tampered=deepcopy(demo.case)
    tampered['trusted_store']={'fake':'yes'}
    tampered['host']={'enabled':True}
    with TestClient(app) as c:
        check_advice(post(c,tampered).json(),'HOLD')
        bad=c.post('/internal/advice', content=json.dumps(demo.case),headers={
            'content-type':'text/plain','Authorization':'Bearer '+TOKEN.decode()})
        assert bad.status_code==415
        check_advice(bad.json(),'HOLD')


def test_oversized_or_invalid_json_holds(tmp_path):
    app,demo,_=make_app(tmp_path)
    with TestClient(app) as c:
        bad=c.post('/internal/advice',content=b'x'*(BODY_LIMIT_BYTES+1),headers={
            'Content-Type':'application/json','Authorization':'Bearer '+TOKEN.decode()})
        assert bad.status_code==413 and bad.json()['review_outcome']=='HOLD'
        bad=c.post('/internal/advice',content=b'{',headers={
            'Content-Type':'application/json','Authorization':'Bearer '+TOKEN.decode()})
        assert bad.json()['review_outcome']=='HOLD'


def test_audit_sink_failure_refuses_positive_advice(tmp_path):
    app,demo,_=make_app(tmp_path)
    def broken(_): raise OSError('audit offline')
    app=create_secure_lab_gateway(auth_token=TOKEN,staging_enabled=True,
        trust_provider=lambda:demo.store,emergency_stop_path=tmp_path/'STOP',
        audit_sink=broken,test_clock=STAMP)
    with TestClient(app) as c:
        r=post(c,demo.case)
        assert r.status_code==503
        check_advice(r.json(),'HOLD')


def test_missing_trust_provider_never_reopens_stage(tmp_path):
    app,demo,_=make_app(tmp_path,trust=lambda:None)
    with TestClient(app) as c:
        check_advice(post(c,demo.case).json(),'HOLD')


def test_no_auth_secret_leaks_in_audit_events(tmp_path):
    app,demo,events=make_app(tmp_path)
    with TestClient(app) as c:
        post(c,demo.case)
        c.post('/internal/advice', json=demo.case,headers={'Authorization':'Bearer wrong'})
    log=json.dumps(events)
    assert TOKEN.decode() not in log
    assert 'signatures' not in log and 'public_key' not in log
    assert 'assurance_case_id' not in log
    assert 'm91-synthetic' not in log


def test_short_secret_disables_even_host_claim_enabled(tmp_path):
    app,demo,_=make_app(tmp_path,token=b'short')
    with TestClient(app) as c:
        assert c.post('/internal/advice',json=demo.case,headers={'Authorization':'Bearer short'}).status_code==401


def test_gateway_has_no_native_write_routes(tmp_path):
    app,demo,_=make_app(tmp_path)
    with TestClient(app) as c:
        for method,path in [('POST','/v1/runtime/evaluate'),('POST','/holochain'),
                            ('POST','/v1/reviews'),('POST','/v1/admissibility'),
                            ('GET','/internal/settings')]:
            assert c.request(method,path,json={}).status_code==404


def test_mass_auth_probes_never_reach_trust_provider(tmp_path):
    counter=[0]
    def provider():
        counter[0]+=1
        return Factory().store
    app,demo,_=make_app(tmp_path,trust=provider)
    with TestClient(app) as c:
        for k in range(50):
            assert c.post('/internal/advice',json=demo.case,headers={
                'Authorization':'Bearer invalid-'+str(k)}).status_code==401
    assert counter[0]==0


def test_same_case_replay_with_different_json_whitespace_is_held(tmp_path):
    app,demo,events=make_app(tmp_path)
    with TestClient(app) as c:
        first=post(c,demo.case)
        check_advice(first.json(),'ELIGIBLE_FOR_REVIEW')
        raw=json.dumps(demo.case,indent=2).encode()
        res=c.post('/internal/advice',content=raw,headers={
            'Content-Type':'application/json','Authorization':'Bearer '+TOKEN.decode()})
        assert res.status_code==423
        check_advice(res.json(),'HOLD')
    assert any(x['event']=='REPLAY_BLOCKED' for x in events)


def test_replay_cache_reset_after_process_restart_is_known_gap(tmp_path):
    # Deliberately records a remaining design limitation: per-process state is
    # not a durable anti-replay authority. This is NOT a gate PASS for replicas.
    demo=Factory()
    app1,_,_=make_app(tmp_path,demo=demo)
    with TestClient(app1) as c:
        check_advice(post(c,demo.case).json(),'ELIGIBLE_FOR_REVIEW')
        assert post(c,demo.case).json()['review_outcome']=='HOLD'
    app2,_,_=make_app(tmp_path,demo=demo)
    with TestClient(app2) as c:
        check_advice(post(c,demo.case).json(),'ELIGIBLE_FOR_REVIEW')


def test_original_lab_http_has_no_transport_auth_and_is_not_releasable(tmp_path):
    # Audit of old M9 lab-only surface, not an exploit against a live service.
    from experimental_sidecar.app import create_shadow_app
    demo=Factory()
    original=create_shadow_app(stage_enabled=True,trusted_provider=lambda:demo.store,test_clock=STAMP)
    with TestClient(original) as c:
        r=c.post('/internal/advice',json=demo.case)
        assert r.status_code==200
        check_advice(r.json(),'ELIGIBLE_FOR_REVIEW')


def test_concurrent_identical_case_has_at_most_one_review_eligible(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    app,demo,_=make_app(tmp_path)
    def request_one(_):
        with TestClient(app) as c:
            res=post(c,demo.case)
            return res.status_code,res.json()['review_outcome']
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(request_one,range(16)))
    assert sum(v=='ELIGIBLE_FOR_REVIEW' for _,v in results)==1,results
    assert sum(v=='HOLD' for _,v in results)==15,results
    assert all(code in (200,423) for code,_ in results)
