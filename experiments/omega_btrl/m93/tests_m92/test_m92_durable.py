"""M9.2 transient laboratory validation. No external services, no real key material."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import stat

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from gateway_m92.identity import ClientRegistry
from gateway_m92.ledger import DurableLedger, LedgerIntegrityError, LedgerUnavailable
from gateway_m92.exporter import JsonlExport
from gateway_m92.secure import create_m92_gateway
from tests_m92.conftest import Factory, STAMP, ROOT, SNAP
from experimental_sidecar.app import BODY_LIMIT_BYTES

ALPHA=b'alpha-ephemeral-m92-demo-token-35bytes-more'
BETA=b'beta-ephemeral-m92-demo-token-35bytes-more!'
NOW=datetime.now(timezone.utc)
SCHEMA=json.loads((SNAP/'contracts/omega_advice.schema.json').read_text())


def setup_host(tmp_path:Path, *, test_store=None, enabled=True, exporter=None, registry=None, key=None):
    tmp_path.chmod(0o700)
    lab=tmp_path/'state'
    lab.mkdir(mode=0o700,exist_ok=True)
    sink_dir=tmp_path/'export'
    sink_dir.mkdir(mode=0o700,exist_ok=True)
    hmac_key=key or b'M92_SYNTHETIC_AUDIT_KEY_32_BYTES_TEST_ONLY!!!'
    ledger=DurableLedger(lab,audit_hmac_key=hmac_key)
    registry=registry or ClientRegistry.from_host_secrets({
        'actor_a':(ALPHA,frozenset({'omega:review-synthetic'}),NOW+timedelta(days=1),False),
        'actor_b':(BETA,frozenset({'omega:review-synthetic'}),NOW+timedelta(days=1),False),
    })
    demo=test_store or Factory()
    audit_export = exporter if exporter is not None else JsonlExport(sink_dir/'events.jsonl')
    app=create_m92_gateway(staging_enabled=enabled,clients=registry,ledger=ledger,
        trust_provider=lambda:demo.store,emergency_stop_path=tmp_path/'STOP',
        audit_export=audit_export,test_clock=STAMP)
    return app,demo,ledger,sink_dir/'events.jsonl',hmac_key


def post(c,case,token=ALPHA):
    return c.post('/internal/advice',json=case,
                  headers={'authorization':'Bearer '+token.decode('ascii')})


def check_adv(result, expected):
    assert Draft202012Validator(SCHEMA).is_valid(result)
    assert result['review_outcome']==expected
    for key in ('authoritative','native_admissibility_written','action_authorised',
                'certification','capital_authorised','rights_created','runtime_mutation_permitted'):
        assert result[key] is False


def worker_direct(state_dir, secret, case_digest):
    from gateway_m92.ledger import DurableLedger
    l=DurableLedger(Path(state_dir),audit_hmac_key=secret)
    return l.record('SHADOW_EVALUATED','ELIGIBLE_FOR_REVIEW','worker',case_digest)[0]


def test_default_fails_closed_and_exposes_no_native_endpoints():
    with TestClient(create_m92_gateway()) as c:
        assert c.get('/internal/health').status_code==200
        assert c.post('/internal/advice',json={}).status_code==503
        for path in ('/v1/admissibility','/holochain','/v1/evidence/candidates','/openapi.json'):
            assert c.post(path,json={}).status_code==404


def test_first_advice_positive_but_non_authoritative(tmp_path):
    app,demo,ledger,export,_=setup_host(tmp_path)
    with TestClient(app) as c:
        r=post(c,demo.case)
        assert r.status_code==200,r.text
        check_adv(r.json(),'ELIGIBLE_FOR_REVIEW')
        assert r.headers['cache-control']=='no-store'
    state=ledger.verify()
    assert state['replay_entries']==1 and state['audit_events']==1
    txt=export.read_text()
    assert ALPHA.decode() not in txt
    assert demo.case['assurance_case_id'] not in txt
    assert 'public_key' not in txt and 'signatures' not in txt
    assert (export.stat().st_mode & 0o777)==0o600


def test_duplicate_case_blocked_for_second_distinct_client(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    with TestClient(app) as c:
        check_adv(post(c,demo.case).json(),'ELIGIBLE_FOR_REVIEW')
        r=post(c,demo.case,token=BETA)
        assert r.status_code==423
        check_adv(r.json(),'HOLD')
    assert ledger.verify()['replay_entries']==1


def test_restart_reuses_ledger_and_replay_stays_blocked(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    with TestClient(app) as c:
        check_adv(post(c,demo.case).json(),'ELIGIBLE_FOR_REVIEW')
    ledger2=DurableLedger(tmp_path/'state',audit_hmac_key=key)
    app2=create_m92_gateway(staging_enabled=True,clients=ClientRegistry.from_host_secrets({
        'actor_b':(BETA,frozenset({'omega:review-synthetic'}),NOW+timedelta(days=1),False)}),
        ledger=ledger2, trust_provider=lambda:demo.store,emergency_stop_path=tmp_path/'STOP',
        audit_export=JsonlExport(tmp_path/'export'/'events.jsonl'),test_clock=STAMP)
    with TestClient(app2) as c:
        r=post(c,demo.case,token=BETA)
        assert r.status_code==423
        check_adv(r.json(),'HOLD')
    assert ledger2.verify()['replay_entries']==1


def test_same_case_reordered_json_and_whitespace_still_blocked(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
        raw=json.dumps(demo.case,indent=4,sort_keys=True).encode()
        r=c.post('/internal/advice',content=raw,headers={
            'authorization':'Bearer '+BETA.decode(),'content-type':'application/json'})
        assert r.status_code==423 and r.json()['review_outcome']=='HOLD'
    assert ledger.verify()['replay_entries']==1


def test_high_concurrency_shared_ledger_separate_app_instances(tmp_path):
    app,demo,ledger,path,key=setup_host(tmp_path)
    r=ClientRegistry.from_host_secrets({'a':(ALPHA,frozenset({'omega:review-synthetic'}),NOW+timedelta(days=1),False)})
    def parallel(_):
        instance=DurableLedger(tmp_path/'state',audit_hmac_key=key)
        api=create_m92_gateway(staging_enabled=True,clients=r,ledger=instance,
              trust_provider=lambda:demo.store,emergency_stop_path=tmp_path/'STOP',
              audit_export=JsonlExport(path),test_clock=STAMP)
        with TestClient(api) as c:
            resp=post(c,demo.case)
            return resp.status_code,resp.json()['review_outcome']
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(parallel,range(18)))
    assert sum(v=='ELIGIBLE_FOR_REVIEW' for _,v in results)==1,results
    assert sum(v=='HOLD' for _,v in results)==17,results
    assert ledger.verify()['replay_entries']==1


def test_multiprocess_atomic_positive_reservation(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    case_digest='a'*64
    with ProcessPoolExecutor(max_workers=5,mp_context=multiprocessing.get_context('spawn')) as executor:
        values=list(executor.map(worker_direct,[str(tmp_path/'state')]*9,
                                 [key]*9,[case_digest]*9))
    assert values.count(True)==1 and values.count(False)==8,values
    assert ledger.verify()['replay_entries']==1


def test_failed_secondary_export_consumes_positive_and_returns_hold(tmp_path):
    def broken(_):raise OSError('secondary export unavailable')
    app,demo,ledger,_,_=setup_host(tmp_path,exporter=broken)
    with TestClient(app) as c:
        r=post(c,demo.case)
        assert r.status_code==503
        check_adv(r.json(),'HOLD')
    assert ledger.verify()['replay_entries']==1  # no positive escaped over HTTP
    app2,_,_,_,_=setup_host(tmp_path,test_store=demo)
    with TestClient(app2) as c:
        assert post(c,demo.case).status_code==423
    assert ledger.verify()['replay_entries']==1


def test_anchor_tamper_detected_on_subsequent_request_and_restart(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    with TestClient(app) as c:
        check_adv(post(c,demo.case).json(),'ELIGIBLE_FOR_REVIEW')
        anchor=tmp_path/'state'/'audit.anchor'
        obj=json.loads(anchor.read_text());obj['mac']='f'*64
        anchor.write_text(json.dumps(obj))
        assert post(c,demo.case).status_code==503
    with pytest.raises(LedgerIntegrityError):
        DurableLedger(tmp_path/'state',audit_hmac_key=key)


def test_db_event_tamper_detected_and_closed(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
        con=sqlite3.connect(ledger.db)
        con.execute("UPDATE audit_events SET outcome='HOLD' WHERE seq=1")
        con.commit();con.close()
        resp=post(c,demo.case)
        assert resp.status_code==503
        check_adv(resp.json(),'HOLD')
    with pytest.raises(LedgerIntegrityError): ledger.verify()


def test_invalid_key_or_missing_anchor_blocks_existing_database(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
    with pytest.raises(LedgerIntegrityError):
        DurableLedger(tmp_path/'state',audit_hmac_key=b'wrong-not-the-previous-hmac-key-32bytes')
    (tmp_path/'state'/'audit.anchor').unlink()
    with pytest.raises(LedgerIntegrityError):
        DurableLedger(tmp_path/'state',audit_hmac_key=key)


def test_insecure_state_directory_or_symlink_refused(tmp_path):
    tmp_path.chmod(0o700)
    insecure=tmp_path/'bad'
    insecure.mkdir(mode=0o700)
    insecure.chmod(0o755)
    with pytest.raises(LedgerUnavailable):DurableLedger(insecure,audit_hmac_key=b'x'*32)
    valid=tmp_path/'good'
    valid.mkdir(mode=0o700)
    outside=tmp_path/'outside.sqlite'
    outside.write_text('test')
    (valid/'replay.sqlite3').symlink_to(outside)
    with pytest.raises(LedgerUnavailable):DurableLedger(valid,audit_hmac_key=b'y'*32)


def test_invalid_or_revoked_client_prevents_trust_provider_invocation(tmp_path):
    calls=[0]
    f=Factory()
    records=ClientRegistry.from_host_secrets({
        'revoked':(ALPHA,frozenset({'omega:review-synthetic'}),NOW+timedelta(days=1),True),
        'no_scope':(BETA,frozenset({'omega:admin'}),NOW+timedelta(days=1),False)})
    app,_,ledger,_,_=setup_host(tmp_path,registry=records,test_store=f)
    app=create_m92_gateway(staging_enabled=True,clients=records,ledger=ledger,
        trust_provider=lambda:calls.__setitem__(0,calls[0]+1),emergency_stop_path=tmp_path/'STOP',
        audit_export=JsonlExport(tmp_path/'export'/'events.jsonl'),test_clock=STAMP)
    with TestClient(app) as c:
        for token in (ALPHA,BETA,b'nonexistent-synthetic-token-123456789012345'):
            assert post(c,f.case,token=token).status_code==401
    assert calls[0]==0


def test_duplicate_auth_and_content_type_rejected(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    with TestClient(app) as c:
        hdr=[('authorization','Bearer '+ALPHA.decode()),('authorization','Bearer '+ALPHA.decode())]
        assert c.post('/internal/advice',json=demo.case,headers=hdr).status_code==401
        assert c.post('/internal/advice',json=demo.case,headers={
             'authorization':'Bearer '+ALPHA.decode(), 'content-type':'text/plain'}).status_code==415
        assert ledger.verify()['replay_entries']==0


def test_emergency_stop_file_or_symlink_blocks_without_restart(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
        stop=tmp_path/'STOP'
        stop.write_text('STOP',encoding='ascii')
        r=post(c,demo.case)
        assert r.status_code==423
        stop.unlink()
        stop.symlink_to(tmp_path/'absent')
        assert post(c,demo.case).status_code==423
    assert ledger.verify()['replay_entries']==1


def test_invalid_signed_case_and_untrusted_host_claim_not_promoted(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    case=deepcopy(demo.case);case['trusted_store']={'root':'injected'}
    case['assurance_case_id']='M92_FORGED_ID'
    with TestClient(app) as c:
        r=post(c,case)
        assert r.status_code==200
        check_adv(r.json(),'HOLD')
    assert ledger.verify()['replay_entries']==0


def test_audit_never_contains_secret_or_raw_case(tmp_path):
    app,demo,ledger,export,_=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
        assert c.post('/internal/advice',json=demo.case,headers={'authorization':'Bearer invalid'}).status_code==401
    text=export.read_text()
    assert ALPHA.decode() not in text and BETA.decode() not in text
    assert 'assurance_case_id' not in text and demo.case['assurance_case_id'] not in text
    assert 'public_key' not in text and 'signatures' not in text
    assert len(text.strip().splitlines())==2
    assert ledger.verify()['audit_events']==2


def test_oversized_and_duplicate_json_keys_hold_without_replay(tmp_path):
    app,demo,ledger,_,_=setup_host(tmp_path)
    with TestClient(app) as c:
        hdr={'content-type':'application/json','authorization':'Bearer '+ALPHA.decode()}
        res=c.post('/internal/advice',headers=hdr,content=b'x'*(BODY_LIMIT_BYTES+1))
        assert res.status_code==413
        res=c.post('/internal/advice',headers=hdr,content=b'{"status":1,"status":2}')
        assert res.status_code==422
    assert ledger.verify()['replay_entries']==0


def test_snapshot_restore_recovers_replay_and_anchor(tmp_path):
    from gateway_m92.backup import snapshot_ledger
    app,demo,ledger,_,key=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
    prior=ledger.verify()
    backup_dir=tmp_path/'consistent_snapshot'
    data=snapshot_ledger(ledger,backup_dir)
    assert data['key_included'] is False
    assert (backup_dir/'replay.sqlite3').stat().st_mode & 0o077 == 0
    restored=DurableLedger(backup_dir,audit_hmac_key=key)
    assert restored.verify()==prior
    from src.trust_boundary import digest
    already_seen, replay_receipt=restored.record('SHADOW_EVALUATED',
        'ELIGIBLE_FOR_REVIEW', 'synthetic_actor', digest(demo.case))
    assert already_seen is False
    assert replay_receipt['event']=='REPLAY_BLOCKED'
    again, event=restored.record('SHADOW_EVALUATED','ELIGIBLE_FOR_REVIEW',
                   'synthetic_actor', 'a'*64)
    assert again is True
    # Snapshot includes the original case digest. The source remains unchanged.
    assert restored.verify()['replay_entries']==2
    assert ledger.verify()['replay_entries']==1


def test_crash_between_transaction_and_anchor_update_fails_closed(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    original=ledger._write_anchor
    def crash_after_db_commit(*args):
        raise OSError('injected crash after SQLite COMMIT before anchor write')
    ledger._write_anchor=crash_after_db_commit
    with TestClient(app) as c:
        r=post(c,demo.case)
        assert r.status_code==503
        check_adv(r.json(),'HOLD')
    ledger._write_anchor=original
    with pytest.raises(LedgerIntegrityError):
        ledger.verify()
    with pytest.raises(LedgerIntegrityError):
        DurableLedger(tmp_path/'state',audit_hmac_key=key)


def test_expired_identity_denied(tmp_path):
    expired=ClientRegistry.from_host_secrets({'expired':(
        ALPHA,frozenset({'omega:review-synthetic'}),NOW-timedelta(seconds=10),False)})
    app,demo,ledger,_,_=setup_host(tmp_path,registry=expired)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==401
    assert ledger.verify()['replay_entries']==0


def test_replay_row_deletion_cannot_regain_eligibility(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
        conn=sqlite3.connect(ledger.db)
        conn.execute('DELETE FROM replay_cases')
        conn.commit();conn.close()
        # Audit chain remained HMAC-valid, but bijection must fail before INSERT.
        r=post(c,demo.case)
        assert r.status_code==503
        check_adv(r.json(),'HOLD')
    with pytest.raises(LedgerIntegrityError,match='BIJECTION'):
        DurableLedger(tmp_path/'state',audit_hmac_key=key)


def test_forged_replay_row_cannot_spoof_audit_receipt(tmp_path):
    app,demo,ledger,_,key=setup_host(tmp_path)
    with TestClient(app) as c:
        assert post(c,demo.case).status_code==200
    conn=sqlite3.connect(ledger.db)
    conn.execute('INSERT INTO replay_cases(digest, first_utc, actor) VALUES(?,?,?)',
                 ('b'*64,'2026-11-18T00:00:00Z','forged'))
    conn.commit();conn.close()
    with pytest.raises(LedgerIntegrityError,match='BIJECTION'):
        ledger.verify()
