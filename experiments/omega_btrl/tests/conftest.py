"""Generate all TEST KEYS in memory per pytest invocation; never production keys."""
import base64
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from src.p0_reference_gate import synthetic_positive_fixture, DIMENSIONS
from src.trust_boundary import TrustedStore, TrustRoot, canonical, digest

STAMP = datetime(2026,11,18,12,0,0,tzinfo=timezone.utc)

ROLES = {'custodian':'SOURCE_CUSTODIAN','policy':'POLICY_AUTHORITY',
         'attestor':'EVIDENCE_ATTESTOR','reviewer':'INDEPENDENT_REVIEWER',
         'approver':'HUMAN_AUTHORITY','revoker':'REVOCATION_AUTHORITY'}


class Factory:
    def __init__(self):
        self.keys = {k: Ed25519PrivateKey.generate() for k in ROLES}
        self.roots = {k:TrustRoot(k,v, self.keys[k].public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)) for k,v in ROLES.items()}
        self.manifest = sha256(b'IN_MEMORY_DEMO_MANIFEST_NOT_REAL').hexdigest()
        self.case = deepcopy(synthetic_positive_fixture())
        self.case['source_reconciliation']['active_manifest_hash'] = self.manifest
        self.case['human_authorisation']['authority_id'] = 'approver'
        self.case['human_authorisation']['reviewer_id'] = 'reviewer'
        self.case['proposer_id']='proposer_untrusted'
        self.store = None
        self.reissue()

    def envelope(self,kind,issuer,claims):
        body = {'kind':kind,'issuer':issuer,'claims':claims}
        sig = self.keys[issuer].sign(canonical(body))
        return {**body,'signature':base64.b64encode(sig).decode('ascii')}

    def deadline(self,minutes=15):
        return (STAMP+timedelta(minutes=minutes)).isoformat()

    def reissue(self):
        c=self.case
        h=digest(c)
        expiry=self.deadline()
        source={'manifest_sha256':self.manifest,'status':'ACTIVE','expires_at':expiry}
        policy={'critical_dimensions':list(DIMENSIONS),'allow_na':[],
                'use_case_id':'TEST_ONLY','manifest_sha256':self.manifest,
                'expires_at':expiry}
        control={'case_digest':h,'calibrated':True,'physical_verification':True,
                 'model_validated':True,'signing_key_valid':True,
                 'deterministic_verified':True,'expires_at':expiry}
        raw={}
        receipts={}
        for d in DIMENSIONS:
            for evidence_id in c['assurance_vector'][d].get('evidence_ids',[]):
                if not isinstance(evidence_id,str) or not evidence_id:
                    continue
                raw[evidence_id]=f'SYNTHETIC_TEST_OBJECT:{d}:{evidence_id}'.encode('ascii')
                receipts[evidence_id]=self.envelope('evidence','attestor',{
                    'case_digest':h, 'dimension':d, 'evidence_id':evidence_id,
                    'content_sha256':sha256(raw[evidence_id]).hexdigest(),
                    'manifest_sha256':self.manifest,'expires_at':expiry})
        records={
            'source':self.envelope('source','custodian',source),
            'policy':self.envelope('policy','policy',policy),
            'controls':self.envelope('controls','attestor',control),
            'review':self.envelope('review','reviewer',{'case_digest':h, 'principal_id':'reviewer',
                'decision':'REVIEWED_FOR_SYNTHETIC_TEST','expires_at':expiry}),
            'approval':self.envelope('approval','approver',{'case_digest':h,'principal_id':'approver',
                'approved':True,'scope':'TEST_ONLY','expires_at':expiry}),
            'revocations':self.envelope('revocations','revoker',{'epoch':3,'revoked_keys':[],
                'revoked_evidence':[],'revoked_cases':[],'revoked_manifests':[],
                'issued_at':STAMP.isoformat(),'expires_at':self.deadline(4)}),
            'evidence':receipts,
        }
        self.store=TrustedStore(roots=self.roots, expected_manifest_sha256=self.manifest,
             expected_policy_sha256=digest(policy),minimum_revocation_epoch=3,
             records=records,raw_evidence=raw)
        return self

    def change_store(self, *, records=None, raw=None, **kwargs):
        s=self.store
        self.store=TrustedStore(
            roots=kwargs.get('roots',s.roots),
            expected_manifest_sha256=kwargs.get('expected_manifest_sha256',s.expected_manifest_sha256),
            expected_policy_sha256=kwargs.get('expected_policy_sha256',s.expected_policy_sha256),
            minimum_revocation_epoch=kwargs.get('minimum_revocation_epoch',s.minimum_revocation_epoch),
            records=records if records is not None else s.records,
            raw_evidence=raw if raw is not None else s.raw_evidence)
        return self

    def edit_record(self,key,mod,signer):
        records=deepcopy(self.store.records)
        claims=deepcopy(records[key]['claims']); mod(claims)
        records[key]=self.envelope(key,signer,claims)
        return self.change_store(records=records)

@pytest.fixture
def demo():
    return Factory()
