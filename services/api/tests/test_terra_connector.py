import copy
import unittest
from app.terra_connector import connector_status, snapshot, reconcile, delta

def envelope(stream="BIGFOOT", day="2026-11-24", value="5", apn="TEST-0001"):
    return {"mode":"TEST","workstream":stream,"source_id":"TEST_ASSESSOR",
        "snapshot_on":day,"scope_id":"TEST-SCOPE-1","coverage":"PARTIAL",
        "fixture":{"adapter_id":"terra_property_mock","synthetic_only":True,
            "live_endpoint":None,"statement":"evaluation, not certification",
            "observations":[{"mode":"TEST","state_fips":"12","county_fips":"055",
                "apn":apn,"source_id":"TEST_ASSESSOR","observed_on":day,
                "kind":"acreage","value":value,"unit":"acre"}]}}

class ConnectorTests(unittest.TestCase):
    def test_provider_hold(self):
        for provider in ("PRYCD","FIRECRAWL","MCP","FEMA","UNKNOWN"):
            self.assertFalse(connector_status(provider)["fixture_allowed"])
            self.assertFalse(connector_status(provider)["network_allowed"])
    def test_real_reject(self):
        x=envelope(); x["mode"]="REAL"
        with self.assertRaises(ValueError): snapshot(x)
    def test_permission_injection(self):
        x=envelope(); x["permission"]="APPROVED"
        with self.assertRaises(ValueError): snapshot(x)
    def test_source_mismatch(self):
        x=envelope(); x["source_id"]="TEST_LISTING"
        with self.assertRaises(ValueError): snapshot(x)
    def test_future_reject(self):
        x=envelope(); x["snapshot_on"]="2026-11-23"
        with self.assertRaises(ValueError): snapshot(x)
    def test_reconciliation(self):
        a,b,c=[envelope(stream=s) for s in ("BIGFOOT","FLOIE","FL-LAND")]
        result=reconcile([a,b,c],"2026-11-24",30)
        self.assertEqual(len(result["evidence"]),1)
        self.assertEqual(len(result["evidence"][0]["workstreams"]),3)
        self.assertEqual(result,reconcile([c,b,a],"2026-11-24",30))
    def test_conflict(self):
        result=reconcile([envelope(),envelope("FLOIE",value="6")],"2026-11-24",30)
        self.assertEqual(len(result["conflicts"]),1)
        self.assertEqual(result["state"],"HOLD")
    def test_stale(self):
        result=reconcile([envelope(day="2026-10-01")],"2026-11-24",30)
        self.assertTrue(result["evidence"][0]["stale_by_declared_policy"])
        self.assertFalse(result["freshness_verified"])
    def test_delta(self):
        a,b=envelope(day="2026-11-23"),envelope(value="6")
        self.assertEqual(delta(a,b)["changes"][0]["status"],"VALUE_SET_CHANGED")
        self.assertEqual(delta(a,b),delta(a,b))
    def test_absence(self):
        a,b=envelope(day="2026-11-23"),envelope(apn="TEST-0002")
        self.assertEqual({x["status"] for x in delta(a,b)["changes"]},{"NEW_OBSERVATION","NOT_OBSERVED"})
    def test_incomparable(self):
        with self.assertRaises(ValueError): delta(envelope(day="2026-11-23"),envelope("FLOIE"))
    def test_order(self):
        with self.assertRaises(ValueError): delta(envelope(),envelope(day="2026-11-23"))
    def test_boundary(self):
        for obj in (snapshot(envelope()),reconcile([envelope()],"2026-11-24",0),
                    delta(envelope(day="2026-11-23"),envelope())):
            self.assertFalse(obj["authoritative"])
            self.assertFalse(obj["real_ingestion_enabled"])
            self.assertEqual(obj["state"],"HOLD")
