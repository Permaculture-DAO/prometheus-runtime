"""PROPOSED synthetic-only PROMETHEUS Omega gate. No integration or release authority.
This program does not prove cryptography, source authenticity or external facts.
"""
from __future__ import annotations
from copy import deepcopy

DIMENSIONS = ('T','DQ','EV','AI','FM','CR','CY','GV','LG','OP','RK','HU','EC')
ALLOWED = {'PASS','CONDITIONAL','HOLD','FAIL','NOT_APPLICABLE','NOT_EVALUATED'}


def evaluate_case(case: dict) -> dict:
    """Return recommendation only; NEVER authorize execution, capital, value or rights."""
    issues = []
    prohibitions = []
    if case.get('status') not in ('PROPOSED','SYNTHETIC_TEST'):
        issues.append('SCOPE_NOT_TEST_ONLY')
    src = case.get('source_reconciliation', {})
    if src.get('active_manifest_hash') in (None,'','UNKNOWN') or src.get('registry_status') != 'VERIFIED':
        issues.append('SOURCE_CHAIN_NOT_VERIFIED')
    if src.get('material_conflict') or src.get('version_mismatch'):
        issues.append('SOURCE_CONFLICT')
    supplied_critical = case.get('critical_dimensions')
    # Candidate-only policy: all declared envelope dimensions are critical.
    # A request payload may not redefine the trusted critical-gate policy.
    critical = set(DIMENSIONS)
    if (not isinstance(supplied_critical, list)
            or len(supplied_critical) != len(DIMENSIONS)
            or set(supplied_critical) != critical):
        issues.append('CRITICAL_SCOPE_MISMATCH')
    dims = case.get('assurance_vector', {})
    for dim in DIMENSIONS:
        entry = dims.get(dim, {})
        state = entry.get('status', 'NOT_EVALUATED') if isinstance(entry, dict) else str(entry)
        if state not in ALLOWED:
            issues.append(f'UNKNOWN_DIMENSION_STATE:{dim}')
            continue
        if dim in critical:
            if state == 'FAIL':
                prohibitions.append(f'CRITICAL_FAIL:{dim}')
            elif state == 'NOT_APPLICABLE':
                if not (isinstance(entry, dict) and entry.get('reason') and entry.get('approved_by')):
                    issues.append(f'UNJUSTIFIED_NA:{dim}')
            elif state != 'PASS':
                issues.append(f'GATE_NOT_PASS:{dim}')
            if state == 'PASS' and not (isinstance(entry, dict) and entry.get('evidence_ids')):
                issues.append(f'PASS_WITHOUT_EVIDENCE:{dim}')
    data = case.get('data_controls', {})
    if data.get('calibrated') is False:
        issues.append('CALIBRATION_INVALID')
    elif data.get('calibrated') is not True:
        issues.append('CALIBRATION_UNKNOWN')
    if data.get('physical_verification') is False:
        issues.append('PHYSICAL_ORIGIN_UNVERIFIED')
    elif data.get('physical_verification') is not True:
        issues.append('PHYSICAL_ORIGIN_UNKNOWN')
    if data.get('dataset_leakage'):
        prohibitions.append('DATASET_LEAKAGE')
    if data.get('relabel_requires_gold') and not data.get('gold_set_verified'):
        issues.append('RELABEL_NO_GOLD_SET')
    if data.get('documentary_claim') and not data.get('documentary_evidence_ids'):
        issues.append('CLAIM_MISSING_DOCUMENTS')
    if case.get('formal_proof', {}).get('claimed_proved') and not case.get('formal_proof', {}).get('independent_tool_receipt'):
        issues.append('UNPROVED_FORMAL_CLAIM')
    crypt = case.get('cryptographic_controls', {})
    if crypt.get('signing_key') in ('REVOKED','COMPROMISED'):
        issues.append('SIGNING_KEY_NOT_VALID')
    elif crypt.get('signing_key') != 'VALID':
        issues.append('SIGNING_KEY_UNVERIFIED')
    if case.get('model_controls', {}).get('validated') is not True:
        issues.append('MODEL_VALIDATION_UNKNOWN')
    if crypt.get('zkp_valid') and data.get('physical_verification') is False:
        issues.append('ZKP_CANNOT_PROVE_PHYSICAL_TRUTH')
    if crypt.get('fhe_correct') and case.get('model_controls',{}).get('validated') is False:
        issues.append('FHE_CANNOT_VALIDATE_MODEL')
    if case.get('agent_controls',{}).get('untrusted_instruction_requested'):
        prohibitions.append('UNTRUSTED_TOOL_INSTRUCTION')
    if case.get('agent_controls',{}).get('requested_privilege_escalation'):
        prohibitions.append('PRIVILEGE_ESCALATION')
    if case.get('claims',{}).get('creates_right_from_pru_rap_trbk'):
        prohibitions.append('PROHIBITED_RIGHTS_SEMANTICS')
    if case.get('compute',{}).get('mode') in ('P','H','Q') and case.get('compute',{}).get('deterministic_verified') is not True:
        issues.append('D_BOUNDARY_NOT_PASSED')
    approval = case.get('human_authorisation', {})
    if not (approval.get('approved') and approval.get('authority_id') and approval.get('scope') and approval.get('reviewer_id')):
        issues.append('HUMAN_AUTHORISATION_MISSING')
    if approval.get('authority_id') and approval.get('authority_id') == case.get('proposer_id'):
        prohibitions.append('SELF_APPROVAL')
    if approval.get('reviewer_id') and approval.get('reviewer_id') == case.get('proposer_id'):
        prohibitions.append('NON_INDEPENDENT_REVIEWER')
    if case.get('release', {}).get('expired') or case.get('release', {}).get('invalidated_by_change'):
        issues.append('ASSURANCE_DECAY')
    if case.get('runtime_action',{}).get('capital_or_physical_or_rights_action'):
        prohibitions.append('HIGH_IMPACT_AUTOMATIC_ACTION')
    if case.get('runtime_action',{}).get('executed'):
        prohibitions.append('UNAUTHORISED_ACTION_ATTEMPT')
    decision = 'NO_GO' if prohibitions else ('HOLD' if issues else 'ELIGIBLE_FOR_REVIEW')
    return {'decision':decision,'issues':sorted(set(issues)),'prohibitions':sorted(set(prohibitions)),
            'action_authorised':False, 'scope':case.get('scope',{}), 'basis':'SYNTHETIC_GATE_CONSISTENCY_ONLY'}


def synthetic_positive_fixture():
    """Manufactured fixture: PASS states simulate hypothetical supporting evidence, not reality."""
    return {
      'assurance_case_id':'PRM-OMEGA-FIXTURE-POSITIVE', 'status':'SYNTHETIC_TEST',
      'scope':{'component_id':'EXAMPLE_LOCAL_KERNEL','use_case_id':'TEST_ONLY','jurisdictions':['EU','US']},
      'source_reconciliation':{'active_manifest_hash':'SYNTHETIC_SHA256_PLACEHOLDER','registry_status':'VERIFIED','material_conflict':False,'version_mismatch':False},
      'critical_dimensions':list(DIMENSIONS),
      'assurance_vector':{d:{'status':'PASS','evidence_ids':[f'SYNTHETIC_EVIDENCE_{d}']} for d in DIMENSIONS},
      'data_controls':{'calibrated':True,'physical_verification':True,'dataset_leakage':False,'relabel_requires_gold':False},
      'formal_proof':{'claimed_proved':False},
      'cryptographic_controls':{'signing_key':'VALID','zkp_valid':False,'fhe_correct':False},
      'agent_controls':{'untrusted_instruction_requested':False,'requested_privilege_escalation':False},
      'model_controls':{'validated':True},'claims':{'creates_right_from_pru_rap_trbk':False},
      'compute':{'mode':'D','deterministic_verified':True},
      'human_authorisation':{'approved':True,'authority_id':'SYNTHETIC_HUMAN_2','reviewer_id':'SYNTHETIC_HUMAN_3','scope':'TEST_ONLY'},
      'proposer_id':'SYNTHETIC_HUMAN_1','release':{'expired':False,'invalidated_by_change':False},
      'runtime_action':{'capital_or_physical_or_rights_action':False,'executed':False},
    }
