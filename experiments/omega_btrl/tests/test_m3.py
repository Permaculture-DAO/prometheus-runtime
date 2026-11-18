"""M3 adversarial, interoperability, and explicit-state checker tests."""
from __future__ import annotations
import base64
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from src.m3_guard import evaluate_m3, baseline_issues
from src.trust_boundary import TrustRoot, canonical, evaluate
from src.interop_advisory import make_advice
from conftest import STAMP
from formal.explicit_checker import check

ROOT = Path(__file__).resolve().parents[1]


def test_m3_valid_signed_synthetic_is_review_only(demo):
    result = evaluate_m3(demo.case, demo.store, now=STAMP)
    assert result['decision'] == 'ELIGIBLE_FOR_REVIEW', result
    for f in ('action_authorised','certification','capital_authorised','rights_created'):
        assert result[f] is False


def test_m3_missing_trusted_store_is_hold(demo):
    result=evaluate_m3(demo.case,None,now=STAMP)
    assert result['decision']=='HOLD'
    assert 'HOST_TRUST_STORE_UNAVAILABLE' in result['issues']


def test_m2_previous_promotion_by_key_alias_is_blocked_m3(demo):
    # Two apparent role principals, one Ed25519 public/private key.
    roots=dict(demo.store.roots)
    roots['approver']=TrustRoot('approver','HUMAN_AUTHORITY',roots['reviewer'].public_key)
    records=deepcopy(demo.store.records)
    envelope=records['approval']
    envelope['signature']=base64.b64encode(
        demo.keys['reviewer'].sign(canonical({
            'kind':envelope['kind'], 'issuer':envelope['issuer'], 'claims':envelope['claims']
        }))
    ).decode('ascii')
    demo.change_store(roots=roots,records=records)
    # Regression witness for M2 weakness.
    assert evaluate(demo.case,demo.store,now=STAMP)['decision']=='ELIGIBLE_FOR_REVIEW'
    patched=evaluate_m3(demo.case,demo.store,now=STAMP)
    assert patched['decision']=='HOLD'
    assert 'TRUST_KEY_REUSED_ACROSS_ROLES' in patched['issues']


def test_missing_role_fails_closed(demo):
    roots=dict(demo.store.roots);roots.pop('revoker')
    demo.change_store(roots=roots)
    r=evaluate_m3(demo.case,demo.store,now=STAMP)
    assert r['decision']=='HOLD' and 'TRUST_ROOT_SET_INVALID' in r['issues']


def test_duplicate_role_fails_closed(demo):
    roots=dict(demo.store.roots)
    roots['approver']=TrustRoot('approver','INDEPENDENT_REVIEWER',roots['approver'].public_key)
    demo.change_store(roots=roots)
    r=evaluate_m3(demo.case,demo.store,now=STAMP)
    assert r['decision']=='HOLD' and 'TRUST_ROLE_COVERAGE_INVALID' in r['issues']


def test_issuer_mismatch_fails_closed(demo):
    roots=dict(demo.store.roots)
    roots['reviewer']=TrustRoot('someone_else','INDEPENDENT_REVIEWER',roots['reviewer'].public_key)
    demo.change_store(roots=roots)
    assert 'TRUST_ROOT_IDENTITY_OR_ROLE_INVALID' in baseline_issues(demo.store)


def test_invalid_key_shape_fails_closed(demo):
    roots=dict(demo.store.roots)
    roots['reviewer']=TrustRoot('reviewer','INDEPENDENT_REVIEWER',b'not-an-ed25519-key')
    demo.change_store(roots=roots)
    assert evaluate_m3(demo.case,demo.store,now=STAMP)['decision']=='HOLD'


def test_advice_sidecar_conforms_to_strict_schema(demo):
    result=evaluate_m3(demo.case,demo.store,now=STAMP)
    advice=make_advice(result)
    schema=json.loads((ROOT/'contracts/omega_advice.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(advice)
    assert advice['review_outcome']=='ELIGIBLE_FOR_REVIEW'
    assert 'decision' not in advice
    assert advice['native_admissibility_written'] is False
    assert advice['runtime_mutation_permitted'] is False
    assert all(advice[k] is False for k in ('authoritative','action_authorised','certification','capital_authorised','rights_created'))


def test_advice_sidecar_never_promotes_malicious_input():
    for payload in [None,[],{'decision':'admissible'},
                    {'decision':'ELIGIBLE_FOR_REVIEW','issues':[], 'action_authorised':True,
                     'certification':False,'capital_authorised':False,'rights_created':False}]:
        x=make_advice(payload)
        assert x['review_outcome']=='HOLD'
        assert x['runtime_mutation_permitted'] is False


def test_native_runtime_schema_is_not_the_advice_schema(demo):
    advice=make_advice(evaluate_m3(demo.case,demo.store,now=STAMP))
    runtime_schema=json.loads((ROOT/'snapshots/runtime_admissibility_contract.json').read_text())
    Draft202012Validator.check_schema(runtime_schema)
    with pytest.raises(ValidationError):
        Draft202012Validator(runtime_schema).validate(advice)
    # A raw Ω review status cannot be used as an admissibility decision value.
    assert 'ELIGIBLE_FOR_REVIEW' not in runtime_schema['properties']['decision']['enum']
    assert runtime_schema['properties']['authoritative']=={'type':'boolean','const':False}
    assert runtime_schema['properties']['certification']=={'type':'boolean','const':False}


def test_native_runtime_snapshot_has_exact_github_blob_id():
    import hashlib
    b=(ROOT/'snapshots/runtime_admissibility_contract.json').read_bytes()
    git_blob=b'blob '+str(len(b)).encode()+b'\0'+b
    assert hashlib.sha1(git_blob).hexdigest()=='c81328184b88112ab1786787989093b485e9316a'


def test_native_runtime_rejects_advice_injection(demo):
    advice=make_advice(evaluate_m3(demo.case,demo.store,now=STAMP))
    schema=json.loads((ROOT/'contracts/omega_advice.schema.json').read_text())
    for malicious in [dict(advice,decision='admissible'),
                      dict(advice,authoritative=True),
                      dict(advice,runtime_mutation_permitted=True)]:
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(malicious)


def test_finite_state_exhaustive_good_model():
    r=check(False)
    assert r['status']=='NO_COUNTEREXAMPLE_IN_FINITE_ABSTRACTION'
    assert r['visited_states']>0 and r['explored_edges']>r['visited_states']


def test_finite_state_mutant_exposes_stale_eligibility():
    r=check(True)
    assert r['status']=='COUNTEREXAMPLE_FOUND'
    assert r['problem']=='NO_BYPASS_VIOLATION'
    assert r['trace'][-1]['transition']=='RevokeEvidence'
    assert r['trace'][-1]['state']['reviewEligible'] is True
    assert r['trace'][-1]['state']['evidenceVerified'] is False


def test_m3_output_does_not_modify_original_case(demo):
    before=deepcopy(demo.case)
    _=make_advice(evaluate_m3(demo.case,demo.store,now=STAMP))
    assert demo.case==before


def test_signing_duplicate_public_key_not_equivalent_to_personal_independence(demo):
    # Key uniqueness is a necessary control; no test claims independent natural-person identity.
    assert baseline_issues(demo.store)==[]
    assert evaluate_m3(demo.case,demo.store,now=STAMP)['status']=='SYNTHETIC_ONLY_NON_AUTHORITATIVE'
