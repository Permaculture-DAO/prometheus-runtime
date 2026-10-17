"""REI shadow contract tests using synthetic declarations only, not site evidence."""
from copy import deepcopy
import unittest

from app.pru import canonical_bytes
from app.regenerative_economic_intelligence import (
    SCHEMA_VERSION, evaluate_regenerative_economic_intelligence,
)
from test_regenerative_real_estate import specimen as real_estate_specimen


def request():
    return {
        "schema_version": SCHEMA_VERSION,
        "sector": "REAL_ESTATE",
        "project_id": "synthetic-site",
        "as_of": "2026-10-17T00:00:00Z",
        "real_estate": real_estate_specimen(),
        "metrics": [
            {
                "metric_id": "soil-organic-carbon",
                "dimension": "ECOLOGICAL",
                "epistemic_state": "OBSERVATION_CANDIDATE",
                "compute_mode": "D",
                "declared_value": "12.500000",
                "unit": "g/kg",
                "evidence_ids": ["ev"],
                "method_ref": "caller-declared-sampling-method",
                "baseline_evidence_id": "ev",
                "counterfactual_evidence_id": None,
            },
            {
                "metric_id": "community-benefit-hypothesis",
                "dimension": "SOCIAL",
                "epistemic_state": "HYPOTHESIS",
                "compute_mode": "D",
                "declared_value": None,
                "unit": None,
                "evidence_ids": ["ev"],
                "method_ref": "caller-declared-hypothesis",
                "baseline_evidence_id": None,
                "counterfactual_evidence_id": None,
            },
        ],
        "risk_ledger_links": [
            {
                "risk_id": "r1",
                "loss_event_id": "loss-event-1",
                "loss_generation_ref": "loss-generation-ledger-1",
                "risk_allocation_ref": "risk-allocation-ledger-1",
                "ultimate_risk_bearer_id": "community",
                "evidence_id": "ev",
            },
        ],
    }


class REITests(unittest.TestCase):
    def evaluate(self, p):
        return evaluate_regenerative_economic_intelligence(p)

    def test_preflight_only_no_certification_or_value(self):
        p = request()
        snapshot = deepcopy(p)
        out = self.evaluate(p)
        self.assertEqual(out["status"], "GO_FOR_EXTERNAL_REVIEW")
        self.assertEqual(out["mode"], "SHADOW")
        self.assertEqual(out["components"]["real_estate"]["status"], "GO_FOR_EXTERNAL_REVIEW")
        self.assertEqual(out["cash_outflow_local_share"]["ratio"], "0.600000")
        self.assertEqual(out["declared_metric_counts"]["ECOLOGICAL"], 1)
        self.assertEqual(out["declared_metric_counts"]["SOCIAL"], 1)
        self.assertEqual(out["source_status"], "PROPOSED_NOT_ADOPTED")
        for key in ("causal_attribution_verified", "ecological_outcome_verified",
                    "financial_value_verified", "risk_reduction_verified",
                    "underwriting_approval", "capital_admission",
                    "legal_rights_created", "certification", "authoritative"):
            self.assertIs(out[key], False)
        for key in ("trbk_entitlement", "valuation", "composite_regeneration_score"):
            self.assertIsNone(out[key])
        self.assertEqual(p, snapshot)

    def test_order_independent_hash_and_byte_replay(self):
        p = request()
        a = self.evaluate(p)
        p["metrics"].reverse()
        p["real_estate"]["safeguards"].reverse()
        p["real_estate"]["cash_outflows"].reverse()
        p["risk_ledger_links"].reverse()
        self.assertEqual(a["input_sha256"], self.evaluate(p)["input_sha256"])
        self.assertEqual(canonical_bytes(a), canonical_bytes(self.evaluate(p)))
        p["metrics"][0]["method_ref"] = "other-method"
        self.assertNotEqual(a["input_sha256"], self.evaluate(p)["input_sha256"])

    def test_no_sector_jump_when_adapters_missing(self):
        for sector in ("AGRICULTURE", "ENERGY", "INFRASTRUCTURE"):
            p = request()
            p["sector"] = sector
            p["real_estate"] = None
            with self.subTest(sector=sector):
                out = self.evaluate(p)
                self.assertEqual(out["status"], "HOLD")
                self.assertIn("domain_adapter:not_implemented", out["blocks"])
                self.assertIsNone(out["cash_outflow_local_share"]["ratio"])
        p = request()
        p["sector"] = "ENERGY"
        with self.assertRaises(ValueError):
            self.evaluate(p)

    def test_upstream_hold_suppresses_share(self):
        p = request()
        p["real_estate"]["land_underwriting"]["decision_hashes"] = {}
        out = self.evaluate(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("real_estate:hold", out["blocks"])
        self.assertIsNone(out["cash_outflow_local_share"]["ratio"])

    def test_project_scope_and_time_binding(self):
        for field, value, reason in (
            ("project_id", "different-site", "identity:project_site_mismatch"),
            ("as_of", "2026-10-16T00:00:00Z", "time:as_of_mismatch"),
        ):
            p = request()
            p[field] = value
            with self.subTest(field=field):
                out = self.evaluate(p)
                self.assertEqual(out["status"], "HOLD")
                self.assertIn(reason, out["blocks"])

    def test_causal_and_valuation_never_self_promote(self):
        for status in ("CAUSAL_CANDIDATE", "VALUATION_CANDIDATE"):
            p = request()
            p["metrics"][0]["epistemic_state"] = status
            p["metrics"][0]["counterfactual_evidence_id"] = "ev"
            with self.subTest(status=status):
                out = self.evaluate(p)
                self.assertEqual(out["status"], "HOLD")
                self.assertIn("metric:soil-organic-carbon:independent_method_review_required",
                              out["blocks"])
                self.assertIsNone(out["cash_outflow_local_share"]["ratio"])

    def test_probabilistic_heuristic_quantum_require_d_verification(self):
        for mode in ("P", "H", "Q"):
            p = request()
            p["metrics"][0]["compute_mode"] = mode
            with self.subTest(mode=mode):
                out = self.evaluate(p)
                self.assertEqual(out["status"], "HOLD")
                self.assertIn("metric:soil-organic-carbon:deterministic_verification_missing",
                              out["blocks"])
                self.assertFalse(out["capital_admission"])

    def test_orphan_and_empty_evidence_fail_closed(self):
        for ids in ([], ["not-bound"]):
            p = request()
            p["metrics"][0]["evidence_ids"] = ids
            with self.subTest(ids=ids):
                out = self.evaluate(p)
                self.assertEqual(out["status"], "HOLD")
                self.assertIn("metric:soil-organic-carbon:unusable_evidence", out["blocks"])

    def test_unmeasured_observation_never_imputes_zero(self):
        p = request()
        p["metrics"][0]["declared_value"] = None
        p["metrics"][0]["unit"] = None
        out = self.evaluate(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("metric:soil-organic-carbon:unknown_measurement", out["blocks"])

    def test_two_ledgers_complete_but_not_audited(self):
        p = request()
        out = self.evaluate(p)
        self.assertEqual(out["two_ledger_linkage"], "DECLARED_NOT_AUDITED")
        p["risk_ledger_links"][0]["ultimate_risk_bearer_id"] = "insurer"
        out = self.evaluate(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("risk:r1:ultimate_bearer_mismatch", out["blocks"])
        p = request()
        p["risk_ledger_links"] = []
        out = self.evaluate(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("risk:lower_adapter_set_mismatch", out["blocks"])
        self.assertIn("risk:two_ledger_links_missing", out["blocks"])

    def test_non_admissible_shapes_rejected(self):
        scenarios = [
            lambda p: p["metrics"][0].update(declared_value=float("nan")),
            lambda p: p["metrics"][0].update(declared_value="1e12"),
            lambda p: p["metrics"][0].update(declared_value="²"),
            lambda p: p["metrics"][0].update(declared_value="00.1"),
            lambda p: p["metrics"][0].update(unit=None),
            lambda p: p["metrics"][0].update(compute_mode="SUPERQUANTUM"),
            lambda p: p["metrics"][0].update(extra="no"),
            lambda p: p["metrics"].append(deepcopy(p["metrics"][0])),
            lambda p: p["risk_ledger_links"].append(deepcopy(p["risk_ledger_links"][0])),
            lambda p: p["risk_ledger_links"][0].update(loss_event_id=42),
        ]
        for mutate in scenarios:
            p = request()
            mutate(p)
            with self.subTest(mutation=str(mutate)):
                with self.assertRaises(ValueError):
                    self.evaluate(p)

    def test_missing_claims_never_looks_complete(self):
        p = request()
        p["metrics"] = []
        out = self.evaluate(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("metrics:missing", out["blocks"])

    def test_metric_baseline_missing_evidence_does_not_self_validate(self):
        p = request()
        p["metrics"][0]["baseline_evidence_id"] = "orphan"
        out = self.evaluate(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("metric:soil-organic-carbon:unusable_evidence", out["blocks"])


if __name__ == "__main__":
    unittest.main()
