"""Synthetic only: no insurance or ecological fact verification."""
from copy import deepcopy
import unittest

from app.pru import canonical_bytes
from app.rei_ravel_ledger_shadow import (
    SCHEMA_VERSION, evaluate_ledger_consistency,
)


def request():
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "synthetic-site",
        "as_of": "2026-10-17T00:00:00Z",
        "currency": "EUR",
        "generation": [
            dict(event_id="flood", risk_id="risk-flood", gross_loss="100.000000",
                 prevented_loss="25.000000", residual_loss="75.000000",
                 evidence_ids=["e1"]),
        ],
        "allocation": [
            dict(event_id="flood", bearer_id="owner", before_transfer="75.000000",
                 after_transfer="55.000000", evidence_ids=["e1"]),
            dict(event_id="flood", bearer_id="insurer", before_transfer="0.000000",
                 after_transfer="20.000000", evidence_ids=["e1"]),
        ],
        "transfers": [
            dict(transfer_id="transfer1", event_id="flood",
                 from_bearer_id="owner", to_bearer_id="insurer",
                 amount="20.000000", evidence_ids=["e1"]),
        ],
    }


class REIRavelLedgerTests(unittest.TestCase):
    def test_declared_conservation_not_certification(self):
        p = request()
        before = deepcopy(p)
        result = evaluate_ledger_consistency(p)
        self.assertEqual(result["status"], "GO_FOR_EXTERNAL_REVIEW")
        self.assertEqual(result["event_summaries"]["flood"]["numeric_consistency"],
                         "DECLARATIONS_RECONCILABLE")
        self.assertFalse(result["loss_reduction_verified"])
        self.assertFalse(result["loss_allocation_verified"])
        self.assertFalse(result["financial_risk_transfer"] == "VERIFIED")
        for key in ("authoritative", "capital_admission", "insurance_binding",
                    "underwriting_approval", "certification"):
            self.assertIs(result[key], False)
        self.assertEqual(before, p)

    def test_claimed_transfer_does_not_eliminate_loss(self):
        p = request()
        p["allocation"][0]["after_transfer"] = "35.000000"
        result = evaluate_ledger_consistency(p)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("event:flood:allocation_conservation_failed", result["blocks"])
        self.assertIn("event:flood:transfer_flow_mismatch:owner", result["blocks"])

    def test_generation_conservation(self):
        for value in ("76", "0", None):
            p = request()
            p["generation"][0]["residual_loss"] = value
            with self.subTest(value=value):
                result = evaluate_ledger_consistency(p)
                self.assertEqual(result["status"], "HOLD")
                self.assertTrue(any(b.startswith("event:flood:") for b in result["blocks"]))

    def test_missing_or_unknown_loss_not_converted_to_zero(self):
        p = request()
        p["allocation"][0]["after_transfer"] = None
        out = evaluate_ledger_consistency(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("event:flood:unknown_allocation", out["blocks"])

    def test_unallocated_bearer_fails(self):
        p = request()
        p["allocation"][0]["bearer_id"] = "UNALLOCATED_RESIDUAL"
        out = evaluate_ledger_consistency(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("allocation:flood:unallocated_bearer", out["blocks"])

    def test_orphan_transfer_fails(self):
        p = request()
        p["transfers"][0]["to_bearer_id"] = "unknown-entity"
        out = evaluate_ledger_consistency(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("transfer:transfer1:orphan_bearer", out["blocks"])

    def test_unknown_transfer_and_fail_closed(self):
        p = request()
        p["transfers"][0]["amount"] = None
        out = evaluate_ledger_consistency(p)
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("transfer:transfer1:unknown_amount", out["blocks"])

    def test_pure_replay_and_order_independent(self):
        p = request()
        a = evaluate_ledger_consistency(p)
        p["allocation"].reverse()
        self.assertEqual(canonical_bytes(a), canonical_bytes(evaluate_ledger_consistency(p)))
        self.assertEqual(a["input_sha256"], evaluate_ledger_consistency(p)["input_sha256"])
        p["generation"][0]["prevented_loss"] = "24"
        self.assertNotEqual(a["input_sha256"], evaluate_ledger_consistency(p)["input_sha256"])

    def test_reject_duplicate_numeric_and_ambiguous_input(self):
        mutations = [
            lambda p: p["generation"][0].update(gross_loss=-1),
            lambda p: p["generation"][0].update(prevented_loss="NaN"),
            lambda p: p["generation"][0].update(prevented_loss="-1.1"),
            lambda p: p["generation"][0].update(prevented_loss="1e-3"),
            lambda p: p["generation"][0].update(prevented_loss="¹"),
            lambda p: p["generation"][0].update(extra="forbidden"),
            lambda p: p["transfers"].append(deepcopy(p["transfers"][0])),
            lambda p: p["allocation"].append(deepcopy(p["allocation"][0])),
            lambda p: p["generation"].append(deepcopy(p["generation"][0])),
            lambda p: p["transfers"][0].update(to_bearer_id="owner"),
            lambda p: p["allocation"][0].update(evidence_ids=[]),
        ]
        for mutate in mutations:
            p = request()
            mutate(p)
            with self.subTest(mutate=str(mutate)):
                with self.assertRaises(ValueError):
                    evaluate_ledger_consistency(p)


if __name__ == "__main__":
    unittest.main()
