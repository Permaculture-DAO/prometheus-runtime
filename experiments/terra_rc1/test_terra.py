import copy
import json
import unittest
from terra import evaluate, normalize, digest, unique_pairs

def fixture(**changes):
    data = dict(mode="TEST",state_fips="12",county_fips="055",apn="TEST-0001",
                source_id="TEST_ASSESSOR",observed_on="2026-11-24",kind="acreage",
                value="5",unit="acre")
    data.update(changes)
    return data

class TerraTests(unittest.TestCase):
    def test_exact_area(self):
        self.assertEqual(normalize(fixture())["normalized_value"],"217800")
    def test_replay_order(self):
        rows=[fixture(),fixture(value="6")]
        self.assertEqual(evaluate(rows),evaluate(list(reversed(rows))))
    def test_replay_hash(self):
        result=evaluate([fixture()])
        sha=result.pop("semantic_hash")
        self.assertEqual(sha,digest(result))
    def test_duplicates(self):
        self.assertEqual(evaluate([fixture(),fixture()])["duplicates"],1)
    def test_conflict(self):
        self.assertEqual(len(evaluate([fixture(),fixture(value="6")])["conflicts"]),1)
    def test_equivalent_units(self):
        self.assertFalse(evaluate([fixture(),fixture(value="217800",unit="sqft")])["conflicts"])
    def test_zero_preserved(self):
        self.assertTrue(normalize(fixture())["parcel_key"].endswith("TEST-0001"))
    def test_county_distinct(self):
        self.assertEqual(len(evaluate([fixture(),fixture(county_fips="101")])["parcel_keys"]),2)
    def test_date_distinct(self):
        self.assertFalse(evaluate([fixture(),fixture(value="6",observed_on="2026-11-23")])["conflicts"])
    def test_price_kinds_distinct(self):
        a=fixture(source_id="TEST_LISTING",kind="asking_price",unit="USD",value="900")
        b=fixture(source_id="TEST_RECORDER",kind="recorded_sale_price",unit="USD",value="800")
        self.assertFalse(evaluate([a,b])["conflicts"])
    def test_reject(self):
        for delta in [dict(mode="REAL"),dict(apn="0001"),dict(county_fips="999"),
                      dict(value="-1"),dict(value="0"),dict(value="NaN"),dict(value=5),
                      dict(unit="ha"),dict(observed_on="2026-02-30"),dict(source_id="UNKNOWN"),
                      dict(source_id="TEST_LISTING"),dict(owner="not allowed"),
                      dict(kind="unknown"),dict(value="1e5")]:
            with self.subTest(delta=delta):
                with self.assertRaises(ValueError): normalize(fixture(**delta))
    def test_missing_field(self):
        row=fixture(); del row["source_id"]
        with self.assertRaises(ValueError): normalize(row)
    def test_duplicate_json(self):
        with self.assertRaises(ValueError): json.loads('{"a":1,"a":2}',object_pairs_hook=unique_pairs)
    def test_gate_hold(self):
        result=evaluate([fixture()])
        self.assertEqual(result["state"],"HOLD")
        for key in ("production_admitted","legal_authority","capital_authority","real_ingestion_enabled"):
            self.assertIs(result[key],False)
    def test_empty(self):
        with self.assertRaises(ValueError): evaluate([])
if __name__=="__main__":
    unittest.main()
