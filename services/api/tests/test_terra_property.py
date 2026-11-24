import copy
import json
from pathlib import Path
import unittest
import jsonschema
from app.terra_property import run_fixture, adapter_descriptor
from app.terra_property_core import digest
from app.evidence_batch import verify_synthetic_evidence_batch, sha256_json

ROOT = Path(__file__).resolve().parents[3]
def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))
def fixture():
    return load("contracts/fixtures/terra_property.synthetic.json")

class TerraNativeTests(unittest.TestCase):
    def test_contract_and_batch(self):
        f = fixture()
        jsonschema.validate(f, load("contracts/terra.property.fixture.schema.json"),
                            format_checker=jsonschema.FormatChecker())
        result = run_fixture(f)
        jsonschema.validate(result["batch"], load("contracts/evidence.batch.schema.json"))
        self.assertEqual(verify_synthetic_evidence_batch(result["batch"]), [])
        self.assertEqual(result["batch"]["event_count"], 2)
        self.assertEqual(result["state"], "HOLD")
    def test_native_reference_replay(self):
        result = run_fixture(fixture())
        events = {e["event_id"]: e for e in result["events"]}
        for ref in result["batch"]["events"]:
            self.assertEqual(ref["event_sha256"], sha256_json(events[ref["event_id"]]))
            self.assertNotIn("observation", ref)
        value = result.pop("semantic_hash")
        self.assertEqual(value, digest(result))
    def test_reordered(self):
        f = fixture()
        a = run_fixture(f)
        f["observations"].reverse()
        self.assertEqual(a, run_fixture(f))
    def test_dedup(self):
        f = fixture()
        a = run_fixture(f)
        f["observations"].append(copy.deepcopy(f["observations"][0]))
        b = run_fixture(f)
        self.assertEqual(a["batch"], b["batch"])
        self.assertEqual(b["report"]["duplicates"], 1)
    def test_conflict_preserved(self):
        f = fixture()
        row = copy.deepcopy(f["observations"][0])
        row["value"] = "6"
        f["observations"].append(row)
        result = run_fixture(f)
        self.assertEqual(len(result["report"]["conflicts"]), 1)
        self.assertEqual(result["batch"]["event_count"], 3)
        self.assertEqual(result["state"], "HOLD")
    def test_batch_namespace(self):
        f = fixture()
        first = run_fixture(f)["batch"]["batch_id"]
        f["observations"][0]["value"] = "6"
        second = run_fixture(f)["batch"]["batch_id"]
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("batch_terra_"))
    def test_tamper(self):
        batch = run_fixture(fixture())["batch"]
        batch["events"][0]["event_sha256"] = "0" * 64
        self.assertTrue(verify_synthetic_evidence_batch(batch))
    def test_fail_closed(self):
        for key, value in [("synthetic_only", False), ("live_endpoint", "https://example.invalid"),
                           ("adapter_id", "unknown"), ("statement", "certified")]:
            f = fixture()
            f[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                run_fixture(f)
        f = fixture()
        f["observations"][0]["mode"] = "REAL"
        with self.assertRaises(ValueError):
            run_fixture(f)
    def test_no_authority(self):
        result = run_fixture(fixture())
        for key in ("evidence_spine_write","holochain_commit","production_admitted",
                    "real_ingestion_enabled","legal_authority","capital_authority"):
            self.assertIs(result[key], False)
        self.assertFalse(adapter_descriptor()["enabled_by_default"])
    def test_source_registry_fail_closed(self):
        registry = load("adapters/terra_source_registry.candidate.json")
        self.assertFalse(registry["real_ingestion_enabled"])
        self.assertEqual(registry["incremental_budget_usd"], 0)
        for source in registry["sources"]:
            self.assertFalse(source["live_enabled"])
            if source["type"] != "fixture":
                self.assertEqual(source["permission"], "UNKNOWN")
