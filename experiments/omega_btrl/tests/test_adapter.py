import json
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import pytest

from src.trust_boundary import evaluate, safe_json, digest
from src.p0_reference_gate import DIMENSIONS
from conftest import STAMP


def assert_hold(x):
    assert x['decision']=='HOLD',x
    assert x['action_authorised'] is False


def test_synthetic_signed_case_review_only(demo):
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert r['decision']=='ELIGIBLE_FOR_REVIEW',r
    assert r['action_authorised'] is False and r['certification'] is False
    assert r['capital_authorised'] is False and r['rights_created'] is False


def test_default_without_external_trust_fails_closed(demo):
    r=evaluate(demo.case,now=STAMP)
    assert_hold(r); assert 'NO_TRUSTED_ADAPTER' in r['issues']


def test_request_supplied_verified_context_is_rejected(demo):
    demo.case['trusted_context']={'trusted':True, 'policy':'VERIFIED'}
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))

@pytest.mark.parametrize('mutator',[
    lambda c: [c['assurance_vector'].__setitem__(d,{'status':'NOT_APPLICABLE','evidence_ids':['x'], 'reason':'exempt','approved_by':'self'}) for d in DIMENSIONS],
    lambda c: [v.update(evidence_ids=['']) for v in c['assurance_vector'].values()],
    lambda c: [v.update(evidence_ids=[None]) for v in c['assurance_vector'].values()],
    lambda c: c['human_authorisation'].update(approved='no'),
    lambda c: c.pop('proposer_id',None),
    lambda c: c['source_reconciliation'].update(active_manifest_hash='X',registry_status='VERIFIED'),
    lambda c: c['assurance_vector']['CR'].update(status='NOT_APPLICABLE',reason='no need',approved_by='self'),
    lambda c: c.update(assurance_vector=None),
    lambda c: c['source_reconciliation'].update(active_manifest_hash='old_hash'),
], ids=['all_na','blank_ids','null_ids','approval_as_string','no_proposer',
       'self_attested_registry','na_waiver','null_vector','stale_source'])
def test_m1_exploit_probes_all_fails_closed(demo,mutator):
    mutator(demo.case)
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_even_signed_na_waiver_rejected(demo):
    demo.case['assurance_vector']['CR']={'status':'NOT_APPLICABLE','evidence_ids':['EXAMPLE'],
                                        'reason':'exception','approved_by':'policy'}
    demo.reissue()
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_tampered_evidence_bytes(demo):
    evidence_id=demo.case['assurance_vector']['DQ']['evidence_ids'][0]
    raw=deepcopy(demo.store.raw_evidence)
    raw[evidence_id]=b'changed contents'
    demo.change_store(raw=raw)
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert_hold(r); assert 'EVIDENCE_NOT_BOUND_OR_HASH_MISMATCH:DQ' in r['issues']


def test_missing_evidence_receipt(demo):
    records=deepcopy(demo.store.records)
    evidence_id=demo.case['assurance_vector']['CR']['evidence_ids'][0]
    records['evidence'].pop(evidence_id)
    demo.change_store(records=records)
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_bad_evidence_signature(demo):
    records=deepcopy(demo.store.records)
    evidence_id=demo.case['assurance_vector']['EV']['evidence_ids'][0]
    records['evidence'][evidence_id]['claims']['dimension']='CR'  # signature remains same
    demo.change_store(records=records)
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_revoked_evidence(demo):
    evidence_id=demo.case['assurance_vector']['AI']['evidence_ids'][0]
    demo.edit_record('revocations',lambda c:c['revoked_evidence'].append(evidence_id),'revoker')
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert_hold(r); assert 'EVIDENCE_REVOKED:AI' in r['issues']


def test_revoked_attestor_key(demo):
    demo.edit_record('revocations',lambda c:c['revoked_keys'].append('attestor'),'revoker')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_revoked_case(demo):
    h=digest(demo.case)
    demo.edit_record('revocations',lambda c:c['revoked_cases'].append(h),'revoker')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_stale_revocation_snapshot(demo):
    r=evaluate(demo.case,demo.store,now=STAMP+timedelta(minutes=5))
    assert_hold(r);assert 'REVOCATIONS_EXPIRED' in r['issues']


def test_revocation_epoch_rollback(demo):
    demo.edit_record('revocations',lambda c:c.update(epoch=2),'revoker')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_stale_source_receipt(demo):
    demo.edit_record('source',lambda c:c.update(expires_at=(STAMP-timedelta(minutes=1)).isoformat()),'custodian')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_signed_different_policy_does_not_upgrade(demo):
    demo.edit_record('policy',lambda c:c.update(allow_na=['CR']),'policy')
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert_hold(r); assert 'POLICY_NOT_PINNED' in r['issues']


def test_self_review_with_new_valid_signatures_still_blocked(demo):
    demo.case['proposer_id']='reviewer'
    demo.reissue()
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert r['decision']=='NO_GO'


def test_approval_scope_mismatch(demo):
    demo.edit_record('approval',lambda c:c.update(scope='CAPITAL'),'approver')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_approval_from_unknown_signer(demo):
    records=deepcopy(demo.store.records)
    records['approval']['issuer']='untrusted'
    demo.change_store(records=records)
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_approval_signed_but_false(demo):
    demo.edit_record('approval',lambda c:c.update(approved=False),'approver')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_control_attestation_false(demo):
    demo.edit_record('controls',lambda c:c.update(physical_verification=False),'attestor')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_malicious_predeclared_action_is_no_go(demo):
    demo.case['runtime_action']['capital_or_physical_or_rights_action']=True
    demo.reissue()
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert r['decision']=='NO_GO' and r['action_authorised'] is False


def test_unsigned_trust_store_is_not_accepted(demo):
    records=deepcopy(demo.store.records)
    records['revocations']=None
    demo.change_store(records=records)
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_strict_types_unknown_fields(demo):
    for altered in [{'human_authorisation':{'approved':'true'}},
                    {'status':'PROPOSED'},
                    {'assurance_vector':[]},
                    {'source_reconciliation':False},
                    {'cryptographic_controls':None},
                    {'unknown_critical_proof':'bypass'}]:
        c=deepcopy(demo.case); c.update(altered)
        assert_hold(evaluate(c,demo.store,now=STAMP))


def test_json_duplicate_keys_rejected():
    with pytest.raises(ValueError,match='DUPLICATE_JSON_KEY'):
        safe_json('{"a":1,"a":2}')


def test_json_nan_rejected():
    with pytest.raises(ValueError,match='INVALID_JSON_NUMBER'):
        safe_json('{"x":NaN}')


def test_json_depth_malformed_fails_closed(demo):
    assert_hold(evaluate({'assurance_vector':None}, demo.store,now=STAMP))


def test_trusted_policy_expiry(demo):
    demo.edit_record('policy',lambda c:c.update(expires_at=(STAMP-timedelta(minutes=1)).isoformat()),'policy')
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))

def test_unreasonably_long_signed_revocation_ttl_is_hold(demo):
    demo.edit_record('revocations',lambda c:c.update(expires_at=(STAMP+timedelta(days=30)).isoformat()),'revoker')
    r=evaluate(demo.case,demo.store,now=STAMP)
    assert_hold(r); assert 'REVOCATION_FRESHNESS_INVALID' in r['issues']


def test_untrusted_malformed_signature_safely_hold(demo):
    records=deepcopy(demo.store.records)
    records['approval']['signature']='@@INVALID_BASE64!'
    demo.change_store(records=records)
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))


def test_request_claimed_admin_record_fails_schema(demo):
    demo.case['human_authorisation']['admin_approval_signed']=True
    assert_hold(evaluate(demo.case,demo.store,now=STAMP))

def test_mutational_fuzz_500_independent_untrusted_changes(demo):
    """No user-controlled one-field mutation may reuse signed case receipts."""
    import random
    rng=random.Random(20261118)
    candidate=demo.case
    values=[None,False,True,[],{},'YES','REVOKED','',9,-1,1.25,'../../secrets',
            [''],['x'],{'status':'NOT_APPLICABLE'},'ELIGIBLE_FOR_REVIEW']
    paths=[
        ('status',),('scope','component_id'),('scope','use_case_id'),
        ('source_reconciliation','active_manifest_hash'),
        ('source_reconciliation','registry_status'),
        ('source_reconciliation','material_conflict'),
        ('data_controls','calibrated'),('data_controls','physical_verification'),
        ('data_controls','dataset_leakage'),('model_controls','validated'),
        ('human_authorisation','approved'),('human_authorisation','authority_id'),
        ('human_authorisation','reviewer_id'),('human_authorisation','scope'),
        ('proposer_id',),('cryptographic_controls','signing_key'),
        ('release','expired'),('compute','deterministic_verified'),
        ('claims','creates_right_from_pru_rap_trbk'),
        ('runtime_action','executed')]
    for _ in range(500):
        c=deepcopy(candidate)
        path=rng.choice(paths)
        val=rng.choice(values)
        parent=c
        for k in path[:-1]: parent=parent[k]
        if parent[path[-1]]==val:
            val='MUTATED_ORIGINAL_VALUE'
        parent[path[-1]]=val
        r=evaluate(c,demo.store,now=STAMP)
        assert r['decision']!='ELIGIBLE_FOR_REVIEW', (path,val,r)
        assert r['action_authorised'] is False
