"""Synthetic declarations only; no fixture is authenticated source evidence."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import localcontext, ROUND_UP
import hashlib
import unittest

from app.controls import GateRecord, GateState, decision_digest
from app.land_underwriting import AMOUNTS, GATES, SCHEMA_VERSION, evaluate_land_underwriting
from app.pru import canonical_bytes


def bind(p):
    p['decision_hashes'] = {}
    for r in p['gates']:
        g = GateRecord(r['gate_uid'], r['scope'], GateState(r['state']), r['spec_ref'],
            r['decision_ref'], *[None if r[k] is None else datetime.strptime(r[k], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                                for k in ('issued_at', 'expires_at')],
            tuple((e['evidence_id'], e['sha256']) for e in r['evidence']), tuple(r['prerequisites']))
        if g.decision_ref:
            p['decision_hashes'][g.decision_ref] = decision_digest(g)
    return p


def request():
    return bind(dict(schema_version=SCHEMA_VERSION, site_id='synthetic-site', dossier_id='synthetic-dossier',
        as_of='2026-10-17T00:00:00Z', use_case='DEVELOPMENT', scope='LAND:synthetic-site:synthetic-dossier',
        gates=[dict(gate_uid=g, scope='LAND:synthetic-site:synthetic-dossier', state='PASSED', spec_ref='synthetic-spec',
            decision_ref='decision-'+g, issued_at='2026-10-16T00:00:00Z', expires_at='2026-10-18T00:00:00Z',
            evidence=[dict(evidence_id='e1', sha256='a'*64)], prerequisites=[]) for g in GATES],
        evidence_hashes={'e1': 'a'*64}, evidence_states={'e1': 'REVIEWABLE'}, revoked_decisions=[],
        development=dict(currency='EUR', evidence_ids=['e1'], gross_development_value='100.10',
                         development_cost='60.20', finance_cost='10.30', developer_profit='40.40')))


class LandTests(unittest.TestCase):
    def evaluate(self, p):
        return evaluate_land_underwriting(p)

    def test_input_completeness_without_valuation_or_authority(self):
        p = request()
        before = deepcopy(p)
        r = self.evaluate(p)
        self.assertEqual(r['status'], 'GO_FOR_EXTERNAL_REVIEW')
        self.assertIsNone(r['development_input_diagnostic']['value'])
        self.assertIsNone(r['land_value'])
        self.assertEqual(r['valuation_status'], 'valuation_not_admitted')
        self.assertEqual(r['development_input_diagnostic']['warnings'], [])
        self.assertEqual(r['development_input_diagnostic']['status'], 'INPUTS_COMPLETE')
        self.assertEqual(r['references_status'], 'caller_declared_not_authenticated')
        self.assertEqual(r['legal_professional_review'], 'HOLD')
        for key in ('authoritative', 'capital_admission', 'underwriting_approval', 'certification', 'creates_rights'):
            self.assertIs(r[key], False)
            self.assertIs(r['controls'][key], False)
        self.assertTrue(r['independent_reviewer_authority_required'])
        self.assertTrue(r['source_verification_required'])
        r['development_input_diagnostic']['inputs']['currency'] = 'XXX'
        self.assertEqual(p, before)

    def test_replay_order_context_and_frozen_hash(self):
        p = request()
        encoded = canonical_bytes(self.evaluate(p))
        expected_hash = hashlib.sha256(canonical_bytes(dict(p, gates=sorted(p['gates'], key=lambda g: g['gate_uid'])))).hexdigest()
        self.assertEqual(self.evaluate(p)['input_sha256'], expected_hash)
        self.assertEqual(expected_hash, 'dde439ca534d718d798ac8e4d8cce9c17b00bd3fb86b3471e922025e655ded13')
        p['gates'].reverse()
        p = dict(reversed(list(p.items())))
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.rounding = ROUND_UP
            ctx.Emax = 1
            self.assertEqual(canonical_bytes(self.evaluate(p)), encoded)
        self.assertEqual(canonical_bytes(self.evaluate(p)), encoded)
        p['development']['finance_cost'] = '11'
        self.assertNotEqual(canonical_bytes(self.evaluate(p)), encoded)

    def test_controls_blockers(self):
        cases = [
            ('missing_decision', lambda p: p['gates'][0].update(decision_ref=None)),
            ('decision_snapshot_mismatch', lambda p: p.update(decision_hashes={})),
            ('decision_snapshot_mismatch', lambda p: p['gates'][0].update(spec_ref='mutated')),
            ('scope_mismatch', lambda p: p['gates'][0].update(scope='other')),
            ('missing_specification', lambda p: p['gates'][0].update(spec_ref=None)),
            ('expired_decision', lambda p: p['gates'][0].update(expires_at=p['as_of'])),
            ('future_decision', lambda p: p['gates'][0].update(issued_at='2026-10-17T01:00:00Z')),
            ('evidence_hash_mismatch', lambda p: p['evidence_hashes'].update(e1='b'*64)),
            ('evidence_state_unusable', lambda p: p['evidence_states'].update(e1='REJECTED')),
            ('evidence_below_policy_state', lambda p: p['evidence_states'].update(e1='RAW')),
            ('revoked_decision', lambda p: p['revoked_decisions'].append('decision-rights')),
        ]
        for reason, mutate in cases:
            with self.subTest(reason=reason):
                p = request()
                mutate(p)
                r = self.evaluate(p)
                self.assertEqual(r['status'], 'HOLD')
                self.assertIn('rights:'+reason, r['blocks'])
                self.assertIsNone(r['development_input_diagnostic']['value'])

    def test_failed_rejection_requires_intact_declaration(self):
        p = request()
        p['gates'][0]['state'] = 'FAILED'
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')
        bind(p)
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')
        p['revoked_decisions'] = ['decision-rights']
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')

    def test_failed_never_overrides_other_gate_failures(self):
        mutations = [
            lambda p: p['gates'].pop(),
            lambda p: p['gates'][1].update(state='UNSPECIFIED'),
            lambda p: p['gates'][1].update(scope='other'),
            lambda p: p['gates'][1].update(expires_at=p['as_of']),
            lambda p: p['gates'][1].update(decision_ref=None),
            lambda p: p['gates'][1]['evidence'][0].update(sha256='b'*64),
        ]
        for mutate in mutations:
            p = request()
            p['gates'][0]['state'] = 'FAILED'
            mutate(p)
            bind(p)
            with self.subTest(mutation=mutate):
                self.assertEqual(self.evaluate(p)['status'], 'HOLD')
        p = request()
        for row in p['gates']:
            row['state'] = 'UNSPECIFIED'
        p['gates'][0]['state'] = 'FAILED'
        bind(p)
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')
        p['decision_hashes'].pop('decision-water')
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')

    def test_site_and_dossier_replay_and_scope_binding(self):
        for key in ('site_id', 'dossier_id'):
            for update_scope in (False, True):
                p = request()
                p[key] = 'other'
                if update_scope:
                    p['scope'] = f"LAND:{p['site_id']}:{p['dossier_id']}"
                with self.subTest(key=key, update_scope=update_scope):
                    r = self.evaluate(p)
                    self.assertEqual(r['status'], 'HOLD')
                    self.assertIn('rights:scope_mismatch', r['blocks'])
        p = request()
        p['site_id'] = 'a:b'
        with self.assertRaises(ValueError):
            self.evaluate(p)
        p = request()
        p['dossier_id'] = 'a:b'
        with self.assertRaises(ValueError):
            self.evaluate(p)
        p = request()
        p['scope'] = 'arbitrary'
        for row in p['gates']:
            row['scope'] = p['scope']
        bind(p)
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')

    def test_declared_time_and_validity_policy(self):
        p = request()
        p['as_of'] = '2000-01-02T00:00:00Z'
        for row in p['gates']:
            row.update(issued_at='2000-01-01T00:00:00Z', expires_at='2001-01-01T00:00:00Z')
        bind(p)
        r = self.evaluate(p)
        self.assertEqual(r['status'], 'GO_FOR_EXTERNAL_REVIEW')
        self.assertEqual(r['time_basis']['status'], 'caller_declared')
        self.assertFalse(r['time_basis']['freshness_verified'])
        self.assertEqual(r['time_basis']['as_of'], p['as_of'])
        self.assertEqual(r['time_basis']['max_decision_validity_days'], 366)
        self.assertEqual(r['time_basis']['gate_intervals']['rights'],
                         dict(issued_at='2000-01-01T00:00:00Z', expires_at='2001-01-01T00:00:00Z'))
        for expiry in ('2001-01-01T00:00:01Z', '9999-12-31T00:00:00Z'):
            p['gates'][0]['expires_at'] = expiry
            bind(p)
            r = self.evaluate(p)
            self.assertEqual(r['status'], 'HOLD')
            self.assertIn('rights:validity_interval_exceeds_policy', r['blocks'])

    def test_orphan_development_evidence(self):
        p = request()
        p['evidence_hashes']['orphan'] = 'b'*64
        p['evidence_states']['orphan'] = 'ADMISSIBLE'
        p['development']['evidence_ids'] = ['orphan']
        r = self.evaluate(p)
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('development:orphan_evidence', r['blocks'])
        self.assertEqual(r['development_input_diagnostic']['status'], 'UNKNOWN')

    def test_reject_control_and_non_nfc_text_without_coalescing(self):
        for text in ('a\nb', 'a\x00b', 'a\x7fb', 'a\u0085b', 'a\u200bb', 'cafe\u0301', 'a\ud800b', 'a\u2028b'):
            mutations = [
                lambda p: p.update(site_id=text),
                lambda p: p.update(dossier_id=text),
                lambda p: p.update(scope=text),
                lambda p: p['gates'][0].update(spec_ref=text),
                lambda p: p['gates'][0].update(decision_ref=text),
                lambda p: p['gates'][0].update(gate_uid=text),
                lambda p: p['gates'][0].update(scope=text),
                lambda p: p['gates'][0].update(prerequisites=[text]),
                lambda p: p['gates'][0]['evidence'][0].update(evidence_id=text),
                lambda p: p['evidence_hashes'].update({text: 'a'*64}),
                lambda p: p['evidence_states'].update({text: 'REVIEWABLE'}),
                lambda p: p['decision_hashes'].update({text: 'a'*64}),
                lambda p: p.update(revoked_decisions=[text]),
                lambda p: p['development'].update(evidence_ids=[text]),
            ]
            for mutate in mutations:
                p = request()
                mutate(p)
                with self.subTest(text=repr(text), mutation=mutate), self.assertRaises(ValueError):
                    self.evaluate(p)
        p = request()
        p['gates'][0]['spec_ref'] = 'caf\u00e9'
        bind(p)
        self.assertEqual(self.evaluate(p)['status'], 'GO_FOR_EXTERNAL_REVIEW')

    def test_missing_unknown_and_dependency_failure(self):
        for state in ('UNSPECIFIED', 'SPECIFIED', 'READY_FOR_TEST', 'SUSPENDED', 'EXPIRED'):
            p = request()
            p['gates'][0]['state'] = state
            bind(p)
            self.assertEqual(self.evaluate(p)['status'], 'HOLD')
        p = request()
        p['gates'].pop(0)
        self.assertIn('rights:missing_required_gate', self.evaluate(p)['blocks'])
        p['gates'] = []
        self.assertEqual(self.evaluate(p)['status'], 'HOLD')
        p = request()
        p['gates'][1]['prerequisites'] = ['rights']
        p['gates'][0]['state'] = 'UNSPECIFIED'
        bind(p)
        r = self.evaluate(p)
        self.assertEqual(r['controls']['gates']['land_use']['blocked_by'], ['rights'])

    def test_unknown_zero_and_nondevelopment(self):
        for amount in AMOUNTS:
            p = request()
            p['development'][amount] = None
            self.assertEqual(self.evaluate(p)['status'], 'HOLD')
            self.assertIsNone(self.evaluate(p)['development_input_diagnostic']['value'])
        p = request()
        for amount in AMOUNTS:
            p['development'][amount] = '0'
        self.assertIsNone(self.evaluate(p)['development_input_diagnostic']['value'])
        p.update(use_case='NONDEVELOPMENT', development=None)
        self.assertEqual(self.evaluate(p)['development_input_diagnostic']['status'], 'NOT_APPLICABLE')
        p['gates'] = []
        self.assertEqual(self.evaluate(p)['development_input_diagnostic']['status'], 'NOT_APPLICABLE')

    def test_invalid_schema_bounds_graphs_authority(self):
        mutations = [
            lambda p: p.update(authoritative=True),
            lambda p: p['gates'][0].update(reviewer_authenticated=True),
            lambda p: p['development'].update(v_base='1'),
            lambda p: p.update(site_id='x'*129),
            lambda p: p.update(as_of='２０２６-10-17T00:00:00Z'),
            lambda p: p.update(as_of='2026-02-30T00:00:00Z'),
            lambda p: p['gates'][0].update(issued_at='2026-１０-16T00:00:00Z'),
            lambda p: p['gates'][0].update(state='PASS'),
            lambda p: p['gates'].append(deepcopy(p['gates'][0])),
            lambda p: p['gates'][0].update(prerequisites=['rights']),
            lambda p: p['gates'][0].update(prerequisites=['absent']),
            lambda p: p['gates'][0].update(evidence=p['gates'][0]['evidence']*2),
            lambda p: p['gates'][0].update(prerequisites=['data', 'data']),
            lambda p: p.update(gates=p['gates']*21),
            lambda p: p.update(evidence_hashes={str(i): 'a'*64 for i in range(101)}),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                p = request()
                mutate(p)
                with self.assertRaises(ValueError):
                    self.evaluate(p)
        p = request()
        p['gates'][0]['prerequisites'] = ['land_use']
        p['gates'][1]['prerequisites'] = ['rights']
        with self.assertRaises(ValueError):
            self.evaluate(p)

    def test_money_domain(self):
        for value in (0, True, 1.1, 'NaN', 'Infinity', '-1', '1e3', ' 1', '01', '0.0000001', '1000000000000000000', '１'):
            p = request()
            p['development'][AMOUNTS[0]] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.evaluate(p)

    def test_byte_limit_and_unordered_reference_replay(self):
        p = request()
        # Individually legal strings/rows, but a catalog of long Unicode IDs exceeds byte budget.
        ids = ['😀'*120+str(i) for i in range(100)]
        p['evidence_hashes'] = {i: 'a'*64 for i in ids}
        p['evidence_states'] = {i: 'REVIEWABLE' for i in ids}
        p['decision_hashes'] = {i: 'a'*64 for i in ids}
        with self.assertRaises(ValueError):
            self.evaluate(p)
        p = request()
        p['evidence_hashes']['e2'] = 'b'*64
        p['evidence_states']['e2'] = 'REVIEWABLE'
        for r in p['gates']:
            r['evidence'].append(dict(evidence_id='e2', sha256='b'*64))
        p['gates'][1]['prerequisites'] = ['rights', 'water']
        p['development']['evidence_ids'].append('e2')
        bind(p)
        before = canonical_bytes(self.evaluate(p))
        for r in p['gates']:
            r['evidence'].reverse()
            r['prerequisites'].reverse()
        p['development']['evidence_ids'].reverse()
        self.assertEqual(canonical_bytes(self.evaluate(p)), before)


if __name__ == '__main__':
    unittest.main()
