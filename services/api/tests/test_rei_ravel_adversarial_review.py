"""Separate adversarial shadow checks. These DO NOT constitute expert actuarial review."""
from copy import deepcopy
import unittest
from app.rei_ravel_ledger_shadow import evaluate_ledger_consistency
from test_rei_ravel_ledger_shadow import request


class ReviewerRegressionTests(unittest.TestCase):
    def test_case_variants_of_unknown_bearer_hold(self):
        for unknown in ("unknown", "Unknown", "unallocated", "Unallocated_Residual"):
            p = request()
            p["allocation"][0]["bearer_id"] = unknown
            p["transfers"][0]["from_bearer_id"] = unknown
            with self.subTest(bearer=unknown):
                result = evaluate_ledger_consistency(p)
                self.assertEqual(result["status"], "HOLD")
                self.assertIn("allocation:flood:unallocated_bearer", result["blocks"])
                self.assertIn("transfer:transfer1:unallocated_bearer", result["blocks"])

    def test_transfer_for_wrong_event_cannot_validate(self):
        p = request()
        p["transfers"][0]["event_id"] = "different-event"
        result = evaluate_ledger_consistency(p)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("transfer:transfer1:unknown_event", result["blocks"])

    def test_undocumented_recipient_is_not_authenticated_by_balanced_numbers(self):
        p = request()
        p["allocation"][1]["bearer_id"] = "fictional-company"
        p["transfers"][0]["to_bearer_id"] = "fictional-company"
        result = evaluate_ledger_consistency(p)
        # Deliberate observed method limit: mathematical GO does NOT prove actual identity.
        self.assertEqual(result["status"], "GO_FOR_EXTERNAL_REVIEW")
        self.assertFalse(result["ultimate_bearers_legally_verified"])
        self.assertEqual(result["financial_risk_transfer"], "NOT_VERIFIED")
        self.assertFalse(result["insurance_binding"])
        self.assertEqual(result["evidence_authenticity"], "NOT_ESTABLISHED")

    def test_one_bad_event_blocks_all_event_labels(self):
        p = request()
        other = deepcopy(p["generation"][0])
        other["event_id"] = "drought"
        other["risk_id"] = "risk-drought"
        p["generation"].append(other)
        a = deepcopy(p["allocation"][0])
        a.update(event_id="drought", before_transfer="75.000000",
                 after_transfer="75.000000")
        p["allocation"].append(a)
        b = deepcopy(p["allocation"][1])
        b.update(event_id="drought", before_transfer="0.000000",
                 after_transfer="0.000000")
        p["allocation"].append(b)
        p["generation"][1]["gross_loss"] = "101"  # inconsistent 101-25 != 75
        result = evaluate_ledger_consistency(p)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["event_summaries"]["flood"]["numeric_consistency"],
                         "INCOMPLETE_OR_CONTRADICTORY")
        self.assertEqual(result["event_summaries"]["drought"]["numeric_consistency"],
                         "INCOMPLETE_OR_CONTRADICTORY")

    def test_ledger_no_outward_authority_even_when_declared_complete(self):
        p = request()
        p["as_of"] = "2000-01-01T00:00:00Z"
        result = evaluate_ledger_consistency(p)
        self.assertEqual(result["status"], "GO_FOR_EXTERNAL_REVIEW")
        self.assertFalse(result["authoritative"])
        self.assertFalse(result["loss_reduction_verified"])
        self.assertFalse(result["loss_allocation_verified"])
        self.assertFalse(result["capital_admission"])


if __name__ == "__main__":
    unittest.main()
