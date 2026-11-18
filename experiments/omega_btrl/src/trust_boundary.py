"""PROMETHEUS Ω M2 — synthetic-only read-only assurance adapter.

A trusted host constructs TrustedStore from protected, pinned roots and fetches
signed records independently of the untrusted candidate. These sample interfaces
are NOT production trust infrastructure or verification of ecological truth.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import base64
import binascii
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator

from .p0_reference_gate import DIMENSIONS, evaluate_case

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$", re.ASCII)
HASH = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def closed_result(decision='HOLD', reasons=(), prohibitions=(), case_id=None) -> dict:
    return {'decision': decision,
            'issues': sorted(set(reasons)), 'prohibitions': sorted(set(prohibitions)),
            'action_authorised': False, 'certification': False,
            'capital_authorised': False, 'rights_created': False,
            'status': 'SYNTHETIC_ONLY_NON_AUTHORITATIVE',
            'case_id': case_id}


def _nested(*fields, required=True, extra=False) -> dict:
    return {'type': 'object', 'required': list(fields) if required else [],
            'additionalProperties': extra}


# Strict case input contract: flags are CLAIMS, not attestations. The adapter
# does not accept receipts, certificates or trusted_context from this JSON.
_nonblank = {'type': 'string', 'pattern': r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'}
_boolean = {'type': 'boolean'}
_evidence_ids = {'type': 'array', 'minItems': 1, 'maxItems': 20,
                 'uniqueItems': True, 'items': _nonblank}
_dimension = {'type': 'object', 'required': ['status', 'evidence_ids'],
              'additionalProperties': False,
              'properties': {'status': {'enum': ['PASS', 'CONDITIONAL', 'HOLD', 'FAIL',
                                                'NOT_APPLICABLE', 'NOT_EVALUATED']},
                             'evidence_ids': _evidence_ids,
                             'reason': {'type': 'string', 'maxLength': 200},
                             'approved_by': _nonblank}}
CASE_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'type': 'object', 'additionalProperties': False,
    'required': ['assurance_case_id','status','scope','source_reconciliation',
                 'critical_dimensions','assurance_vector','data_controls',
                 'formal_proof','cryptographic_controls','agent_controls',
                 'model_controls','claims','compute','human_authorisation',
                 'proposer_id','release','runtime_action'],
    'properties': {
        'assurance_case_id': _nonblank,
        'status': {'const': 'SYNTHETIC_TEST'},
        'scope': {'type':'object','additionalProperties':False,
                  'required':['component_id','use_case_id','jurisdictions'],
                  'properties':{'component_id':_nonblank,'use_case_id': {'const':'TEST_ONLY'},
                                'jurisdictions':{'type':'array','maxItems':8,'items':_nonblank}}},
        'source_reconciliation': {'type':'object','additionalProperties':False,
            'required':['active_manifest_hash','registry_status','material_conflict','version_mismatch'],
            'properties':{'active_manifest_hash': {'type':'string','minLength':1,'maxLength':128},
                          'registry_status': {'type':'string','maxLength':30},
                          'material_conflict':_boolean,'version_mismatch':_boolean}},
        'critical_dimensions': {'type':'array','minItems':len(DIMENSIONS),'maxItems':len(DIMENSIONS),
                                'uniqueItems': True, 'items':{'enum':list(DIMENSIONS)}},
        'assurance_vector': {'type':'object','required':list(DIMENSIONS),
                             'additionalProperties':False,'properties':{d:_dimension for d in DIMENSIONS}},
        'data_controls': {'type':'object','additionalProperties':False,
            'required':['calibrated','physical_verification','dataset_leakage','relabel_requires_gold'],
            'properties':{'calibrated':_boolean,'physical_verification':_boolean,
                          'dataset_leakage':_boolean,'relabel_requires_gold':_boolean,
                          'gold_set_verified':_boolean,'documentary_claim':_boolean,
                          'documentary_evidence_ids':{'type':'array','items':_nonblank,'maxItems':20}}},
        'formal_proof': {'type':'object','additionalProperties':False,
                         'required':['claimed_proved'],
                         'properties':{'claimed_proved':_boolean,
                                       'independent_tool_receipt':_nonblank}},
        'cryptographic_controls': {'type':'object','additionalProperties':False,
                                   'required':['signing_key','zkp_valid','fhe_correct'],
                                   'properties':{'signing_key':{'enum':['VALID','REVOKED','COMPROMISED','UNKNOWN']},
                                                 'zkp_valid':_boolean,'fhe_correct':_boolean}},
        'agent_controls': {'type':'object','additionalProperties':False,
                           'required':['untrusted_instruction_requested','requested_privilege_escalation'],
                           'properties':{'untrusted_instruction_requested':_boolean,
                                         'requested_privilege_escalation':_boolean}},
        'model_controls': {'type':'object','additionalProperties':False,
                           'required':['validated'],'properties':{'validated':_boolean}},
        'claims': {'type':'object','additionalProperties':False,
                   'required':['creates_right_from_pru_rap_trbk'],
                   'properties':{'creates_right_from_pru_rap_trbk':_boolean}},
        'compute': {'type':'object','additionalProperties':False,
                    'required':['mode','deterministic_verified'],
                    'properties':{'mode':{'enum':['D','P','H','Q']},
                                  'deterministic_verified':_boolean}},
        'human_authorisation': {'type':'object','additionalProperties':False,
                  'required':['approved','authority_id','reviewer_id','scope'],
                  'properties':{'approved':_boolean,'authority_id':_nonblank,
                                'reviewer_id':_nonblank,'scope':{'const':'TEST_ONLY'}}},
        'proposer_id':_nonblank,
        'release': {'type':'object','additionalProperties':False,
                    'required':['expired','invalidated_by_change'],
                    'properties':{'expired':_boolean,'invalidated_by_change':_boolean}},
        'runtime_action': {'type':'object','additionalProperties':False,
                    'required':['capital_or_physical_or_rights_action','executed'],
                    'properties':{'capital_or_physical_or_rights_action':_boolean,
                                  'executed':_boolean}}
    }
}
Draft202012Validator.check_schema(CASE_SCHEMA)
_validator = Draft202012Validator(CASE_SCHEMA)


def safe_json(text: str | bytes) -> dict:
    """Reject duplicate keys and invalid JSON constants at the API boundary."""
    if len(text) > 65536:
        raise ValueError('PAYLOAD_TOO_LARGE')
    def pairs(items):
        record = {}
        for k, v in items:
            if k in record:
                raise ValueError('DUPLICATE_JSON_KEY')
            record[k] = v
        return record
    def bad_constant(_):
        raise ValueError('INVALID_JSON_NUMBER')
    parsed = json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)
    if not isinstance(parsed, dict):
        raise ValueError('CASE_NOT_OBJECT')
    return parsed


def utc_time(t: str) -> datetime:
    dt = datetime.fromisoformat(t.replace('Z','+00:00'))
    if dt.utcoffset() is None:
        raise ValueError('NAIVE_TIME_NOT_ALLOWED')
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class TrustRoot:
    principal_id: str
    role: str
    public_key: bytes


@dataclass(frozen=True)
class TrustedStore:
    """Passed by trusted host, never decoded from the user request.

    `expected_*` and keys must come from independent, access-controlled config.
    `records` and raw_evidence must be independently fetched, not request fields.
    """
    roots: dict[str, TrustRoot]
    expected_manifest_sha256: str
    expected_policy_sha256: str
    minimum_revocation_epoch: int
    records: dict[str, Any]
    raw_evidence: dict[str, bytes]


def check_signed(envelope: Any, kind: str, role: str,
                 store: TrustedStore, now: datetime, revoked_keys: set[str]) -> tuple[dict|None, str|None]:
    try:
        if not isinstance(envelope, dict) or set(envelope) != {'kind','issuer','claims','signature'}:
            return None, f'{kind.upper()}_ENVELOPE_INVALID'
        if envelope['kind'] != kind or not isinstance(envelope['issuer'], str) or not isinstance(envelope['claims'], dict):
            return None, f'{kind.upper()}_ENVELOPE_INVALID'
        kid=envelope['issuer']
        if kid in revoked_keys:
            return None, f'{kind.upper()}_ISSUER_REVOKED'
        root = store.roots.get(kid)
        if not root or root.role != role or root.principal_id != kid:
            return None, f'{kind.upper()}_ROLE_UNTRUSTED'
        signature = base64.b64decode(envelope['signature'], validate=True)
        Ed25519PublicKey.from_public_bytes(root.public_key).verify(
            signature, canonical({'kind':kind, 'issuer':kid, 'claims':envelope['claims']}))
        c = envelope['claims']
        if not isinstance(c.get('expires_at'), str) or utc_time(c['expires_at']) <= now:
            return None, f'{kind.upper()}_EXPIRED'
        if c.get('not_before') and utc_time(c['not_before']) > now:
            return None, f'{kind.upper()}_NOT_YET_VALID'
        return c, None
    except (InvalidSignature, TypeError, ValueError, KeyError, OverflowError, binascii.Error):
        return None, f'{kind.upper()}_SIGNATURE_OR_CLAIMS_INVALID'


def _verified_context(candidate: dict, store: TrustedStore, now: datetime) -> list[str]:
    """Report errors only. This never returns any authority or capability token."""
    errors: list[str] = []
    def fail(code):
        errors.append(code)
    if not isinstance(store, TrustedStore):
        return ['NO_TRUSTED_ADAPTER']
    if not HASH.fullmatch(store.expected_manifest_sha256) or not HASH.fullmatch(store.expected_policy_sha256):
        return ['UNPINNED_TRUST_BASELINE']
    if not isinstance(store.minimum_revocation_epoch, int) or isinstance(store.minimum_revocation_epoch, bool):
        return ['REVOCATION_FLOOR_UNKNOWN']
    records = store.records
    if not isinstance(records, dict):
        return ['SIGNED_RECORD_STORE_UNAVAILABLE']
    # Revocation list must itself be independently signed by a pinned authority.
    # Its expiry controls freshness. On missing/stale: fail-closed.
    rev, err = check_signed(records.get('revocations'), 'revocations', 'REVOCATION_AUTHORITY',
                            store, now, set())
    if err:
        return [err]
    if (type(rev.get('epoch')) is not int or rev['epoch'] < store.minimum_revocation_epoch
            or not all(isinstance(rev.get(k), list) and all(isinstance(v, str) for v in rev[k])
                       for k in ('revoked_keys','revoked_evidence','revoked_cases','revoked_manifests'))):
        return ['REVOCATION_STATE_INVALID_OR_ROLLED_BACK']
    # Signed freshness is not a substitute for an online revocation service.
    # These bounds reduce replay windows for the synthetic snapshot protocol.
    try:
        issued_at = utc_time(rev['issued_at'])
        expires_at = utc_time(rev['expires_at'])
        if (issued_at > now + timedelta(seconds=30)
                or now - issued_at > timedelta(minutes=5)
                or expires_at - issued_at > timedelta(minutes=5)):
            return ['REVOCATION_FRESHNESS_INVALID']
    except (KeyError, ValueError, TypeError, OverflowError):
        return ['REVOCATION_FRESHNESS_INVALID']
    revoked_keys = set(rev['revoked_keys'])
    revoked_evidence = set(rev['revoked_evidence'])
    revoked_cases = set(rev['revoked_cases'])
    revoked_manifests = set(rev['revoked_manifests'])
    case_digest = digest(candidate)
    if case_digest in revoked_cases or store.expected_manifest_sha256 in revoked_manifests:
        fail('CASE_OR_MANIFEST_REVOKED')
    source, err = check_signed(records.get('source'), 'source', 'SOURCE_CUSTODIAN', store, now, revoked_keys)
    if err: fail(err)
    else:
        if source.get('manifest_sha256') != store.expected_manifest_sha256 or source.get('status') != 'ACTIVE':
            fail('SOURCE_NOT_PINNED_OR_ACTIVE')
    policy, err = check_signed(records.get('policy'), 'policy', 'POLICY_AUTHORITY', store, now, revoked_keys)
    if err: fail(err)
    else:
        # A digest over all policy claims prevents a validly signed but different
        # policy being substituted without out-of-band policy governance.
        if digest(policy) != store.expected_policy_sha256:
            fail('POLICY_NOT_PINNED')
        if (policy.get('critical_dimensions') != list(DIMENSIONS) or policy.get('allow_na') != []
                or policy.get('use_case_id') != 'TEST_ONLY'
                or policy.get('manifest_sha256') != store.expected_manifest_sha256):
            fail('POLICY_SCOPE_INVALID')
    if candidate['source_reconciliation']['active_manifest_hash'] != store.expected_manifest_sha256:
        fail('CANDIDATE_SOURCE_MISMATCH')
    if set(candidate['critical_dimensions']) != set(DIMENSIONS):
        fail('CANDIDATE_CRITICAL_VECTOR_INVALID')
    if candidate['scope']['use_case_id'] != 'TEST_ONLY':
        fail('CASE_SCOPE_INVALID')
    control, err = check_signed(records.get('controls'), 'controls', 'EVIDENCE_ATTESTOR', store, now, revoked_keys)
    if err: fail(err)
    else:
        if control.get('case_digest') != case_digest:
            fail('CONTROLS_NOT_BOUND_TO_CASE')
        for field in ['calibrated','physical_verification','model_validated',
                      'signing_key_valid','deterministic_verified']:
            if control.get(field) is not True:
                fail(f'CONTROL_NOT_ATTESTED:{field}')
    evidence = records.get('evidence')
    if not isinstance(evidence, dict):
        fail('EVIDENCE_REGISTRY_UNAVAILABLE')
    else:
        for d in DIMENSIONS:
            entry = candidate['assurance_vector'][d]
            if entry['status'] != 'PASS':
                fail(f'CRITICAL_NOT_PASS:{d}')
                continue
            for evidence_id in entry['evidence_ids']:
                if evidence_id in revoked_evidence:
                    fail(f'EVIDENCE_REVOKED:{d}')
                    continue
                receipt, err = check_signed(evidence.get(evidence_id), 'evidence', 'EVIDENCE_ATTESTOR', store, now, revoked_keys)
                if err:
                    fail(f'EVIDENCE_INVALID:{d}:{err}')
                    continue
                raw = store.raw_evidence.get(evidence_id)
                if (receipt.get('case_digest') != case_digest or receipt.get('dimension') != d
                    or receipt.get('evidence_id') != evidence_id or not isinstance(raw, bytes)
                    or receipt.get('content_sha256') != sha256(raw).hexdigest()
                    or receipt.get('manifest_sha256') != store.expected_manifest_sha256):
                    fail(f'EVIDENCE_NOT_BOUND_OR_HASH_MISMATCH:{d}')
    proposer_id = candidate['proposer_id']
    reviewer, err = check_signed(records.get('review'), 'review', 'INDEPENDENT_REVIEWER', store, now, revoked_keys)
    if err: fail(err)
    else:
        if (reviewer.get('case_digest') != case_digest
                or reviewer.get('principal_id') != records['review']['issuer']
                or reviewer.get('principal_id') != candidate['human_authorisation']['reviewer_id']
                or reviewer.get('principal_id') == proposer_id
                or reviewer.get('decision') != 'REVIEWED_FOR_SYNTHETIC_TEST'):
            fail('REVIEW_NOT_INDEPENDENT_OR_BOUND')
    approval, err = check_signed(records.get('approval'), 'approval', 'HUMAN_AUTHORITY', store, now, revoked_keys)
    if err: fail(err)
    else:
        if (approval.get('case_digest') != case_digest
                or approval.get('principal_id') != records['approval']['issuer']
                or approval.get('principal_id') != candidate['human_authorisation']['authority_id']
                or approval.get('principal_id') in (proposer_id, candidate['human_authorisation']['reviewer_id'])
                or approval.get('approved') is not True
                or approval.get('scope') != 'TEST_ONLY'):
            fail('APPROVAL_NOT_INDEPENDENT_OR_BOUND')
    return errors


def evaluate(candidate: Any, store: TrustedStore | None = None, *, now: datetime | None = None) -> dict:
    """Return review-only recommendation. No keys/authorization are read from case."""
    case_id = candidate.get('assurance_case_id') if isinstance(candidate,dict) else None
    try:
        if not isinstance(candidate, dict):
            return closed_result(reasons=['INVALID_CASE_OBJECT'])
        if len(canonical(candidate)) > 65536:
            return closed_result(reasons=['PAYLOAD_TOO_LARGE'],case_id=case_id)
        errors = sorted(_validator.iter_errors(candidate), key=lambda e: tuple(str(x) for x in e.path))
        if errors:
            return closed_result(reasons=['SCHEMA_INVALID', *[f"{'.'.join(map(str,e.path)) or '$'}:{e.validator}" for e in errors[:16]]], case_id=case_id)
        # Both the legacy candidate's semantic checks and independent signed
        # evidence checks must pass; either may keep the result in HOLD.
        base = evaluate_case(candidate)
        concerns = list(base['issues'])
        prohibitions = list(base['prohibitions'])
        if isinstance(now, datetime):
            if now.utcoffset() is None:
                return closed_result(reasons=['CLOCK_NOT_UTC_AWARE'],case_id=case_id)
            current=now.astimezone(timezone.utc)
        elif now is None:
            current=datetime.now(timezone.utc)
        else:
            return closed_result(reasons=['CLOCK_INVALID'],case_id=case_id)
        concerns.extend(_verified_context(candidate,store,current) if store else ['NO_TRUSTED_ADAPTER'])
        decision = 'NO_GO' if prohibitions else 'HOLD' if concerns else 'ELIGIBLE_FOR_REVIEW'
        return closed_result(decision, concerns, prohibitions, case_id)
    except Exception:
        return closed_result(reasons=['MALFORMED_INPUT_SAFE_HOLD'],case_id=case_id)
