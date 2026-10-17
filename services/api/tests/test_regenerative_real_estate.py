"""Synthetic regression tests for non-authoritative anti-extraction shadow adapter."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from app.controls import GateRecord, GateState, decision_digest
from app.land_underwriting import GATES, SCHEMA_VERSION as LAND_VERSION
from app.regenerative_real_estate import (
    SCHEMA_VERSION, REQUIRED_CONTROLS, evaluate_regenerative_real_estate,
)
from app.pru import canonical_bytes


def specimen():
    scope = "LAND:synthetic-site:synthetic-dossier"
    gates = [dict(
        gate_uid=uid, scope=scope, state="PASSED",
        spec_ref="synthetic-spec", decision_ref="decision-"+uid,
        issued_at="2026-10-16T00:00:00Z", expires_at="2026-10-18T00:00:00Z",
        evidence=[dict(evidence_id="ev", sha256="a"*64)], prerequisites=[],
    ) for uid in GATES]
    decisions = {}
    for row in gates:
        record = GateRecord(row["gate_uid"], scope, GateState.PASSED, row["spec_ref"],
            row["decision_ref"],
            datetime(2026, 10, 16, tzinfo=timezone.utc),
            datetime(2026, 10, 18, tzinfo=timezone.utc),
            (("ev", "a"*64),), ())
        decisions[row["decision_ref"]] = decision_digest(record)
    land = {
        "schema_version": LAND_VERSION, "site_id": "synthetic-site",
        "dossier_id": "synthetic-dossier", "as_of": "2026-10-17T00:00:00Z",
        "use_case": "NONDEVELOPMENT", "scope": scope, "gates": gates,
        "evidence_hashes": {"ev": "a"*64}, "evidence_states": {"ev": "REVIEWABLE"},
        "decision_hashes": decisions, "revoked_decisions": [], "development": None,
    }
    return {
        "schema_version": SCHEMA_VERSION, "land_underwriting": land,
        "currency": "EUR",
        "safeguards": [dict(control_id=k, state="REVIEWABLE", evidence_id="ev")
                       for k in REQUIRED_CONTROLS],
        "cash_outflows": [
            dict(event_id="x1", amount="30.00", currency="EUR",
                 recipient_scope="LOCAL", evidence_id="ev"),
            dict(event_id="x2", amount="20.00", currency="EUR",
                 recipient_scope="NONLOCAL", evidence_id="ev"),
        ],
        "risk_links": [dict(risk_id="r1", ultimate_bearer_id="community",
                            evidence_id="ev")],
    }


class RegenerativeRealEstateTests(unittest.TestCase):
    def check(self, p):
        return evaluate_regenerative_real_estate(p)

    def test_valid_declarations_still_no_authority(self):
        p = specimen()
        original = deepcopy(p)
        r = self.check(p)
        self.assertEqual(r["status"], "GO_FOR_EXTERNAL_REVIEW")
        self.assertEqual(r["mode"], "SHADOW")
        self.assertEqual(r["cash_outflow_local_share"]["ratio"], "0.600000")
        self.assertEqual(r["cash_outflow_local_share"]["status"],
                         "CALLER_DECLARED_UNVERIFIED")
        self.assertEqual(r["cash_outflow_local_share"]["basis"],
                         "declared_project_cash_outflows_only")
        self.assertEqual(r["regenerative_outcome"], "NOT_VERIFIED")
        for k in ("capital_admission", "authoritative", "financial_certification",
                  "legal_rights_created"):
            self.assertIs(r[k], False)
        for k in ("land_value", "ecological_uplift", "trbk_entitlement"):
            self.assertIsNone(r[k])
        self.assertEqual(p, original)

    def test_permutation_and_decimal_context_replay(self):
        p = specimen()
        a = self.check(p)
        p["cash_outflows"].reverse()
        p["safeguards"].reverse()
        p["land_underwriting"]["gates"].reverse()
        self.assertEqual(canonical_bytes(a), canonical_bytes(self.check(p)))
        self.assertEqual(a["input_sha256"], self.check(p)["input_sha256"])
        p["cash_outflows"][0]["amount"] = "25.00"
        self.assertNotEqual(a["input_sha256"], self.check(p)["input_sha256"])

    def test_absent_safeguard_must_hold(self):
        p = specimen()
        p["safeguards"].pop()
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("safeguard:exit_and_default:missing", r["blocks"])

    def test_unknown_and_adverse_must_hold(self):
        for state in ("UNKNOWN", "ADVERSE", "NOT_APPLICABLE"):
            p = specimen()
            p["safeguards"][0]["state"] = state
            with self.subTest(state=state):
                r = self.check(p)
                self.assertEqual(r["status"], "HOLD")
                self.assertIn(f"safeguard:land_access:{state.lower()}", r["blocks"])

    def test_rejects_unlinked_evidence(self):
        p = specimen()
        p["safeguards"][0]["evidence_id"] = "fabricated"
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("safeguard:land_access:unusable_evidence", r["blocks"])

    def test_bad_land_gate_not_promoted_by_territorial_claims(self):
        p = specimen()
        p["land_underwriting"]["decision_hashes"] = {}
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertEqual(r["land_preflight"]["status"], "HOLD")
        self.assertIn("land_preflight:hold", r["blocks"])
        self.assertIsNone(r["cash_outflow_local_share"]["ratio"])

    def test_unknown_cash_location_never_zero_filled(self):
        p = specimen()
        p["cash_outflows"][0]["recipient_scope"] = "UNKNOWN"
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertIsNone(r["cash_outflow_local_share"]["ratio"])
        self.assertIn("cash_outflow:x1:recipient_unknown", r["blocks"])

    def test_zero_denominator_never_fake_zero(self):
        p = specimen()
        for row in p["cash_outflows"]:
            row["amount"] = "0"
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertIsNone(r["cash_outflow_local_share"]["ratio"])
        self.assertIn("cash_outflows:zero_denominator", r["blocks"])

    def test_risk_bearer_required(self):
        p = specimen()
        p["risk_links"] = []
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("risk_links:missing", r["blocks"])

    def test_duplicate_or_invalid_events_fail_input(self):
        cases = [
            lambda p: p["cash_outflows"].append(deepcopy(p["cash_outflows"][0])),
            lambda p: p["safeguards"].append(deepcopy(p["safeguards"][0])),
            lambda p: p["risk_links"].append(deepcopy(p["risk_links"][0])),
            lambda p: p["cash_outflows"][0].update(amount="NaN"),
            lambda p: p["cash_outflows"][0].update(amount="-1"),
            lambda p: p["cash_outflows"][0].update(amount=1),
            lambda p: p["cash_outflows"][0].update(currency="USD"),
            lambda p: p["cash_outflows"][0].update(amount="¹0"),
            lambda p: p["cash_outflows"][0].update(extra="forbidden"),
        ]
        for mutate in cases:
            with self.subTest(case=str(mutate)):
                p = specimen()
                mutate(p)
                with self.assertRaises(ValueError):
                    self.check(p)

    def test_unusable_flow_evidence_never_calculates_share(self):
        p = specimen()
        p["cash_outflows"][0]["evidence_id"] = "not-bound"
        r = self.check(p)
        self.assertEqual(r["status"], "HOLD")
        self.assertIsNone(r["cash_outflow_local_share"]["ratio"])

    def test_is_pure_and_has_no_external_clock_claim(self):
        p = specimen()
        p["land_underwriting"]["as_of"] = "2000-01-02T00:00:00Z"
        for row in p["land_underwriting"]["gates"]:
            row["issued_at"] = "2000-01-01T00:00:00Z"
            row["expires_at"] = "2001-01-01T00:00:00Z"
            g = GateRecord(row["gate_uid"], row["scope"], GateState.PASSED,
                           row["spec_ref"], row["decision_ref"],
                           datetime(2000, 1, 1, tzinfo=timezone.utc),
                           datetime(2001, 1, 1, tzinfo=timezone.utc),
                           (("ev", "a"*64),), ())
            p["land_underwriting"]["decision_hashes"][row["decision_ref"]] = decision_digest(g)
        r = self.check(p)
        self.assertEqual(r["as_of"], "2000-01-02T00:00:00Z")
        self.assertNotIn("freshness_verified", r)
        self.assertFalse(r["authoritative"])


if __name__ == "__main__":
    unittest.main()
