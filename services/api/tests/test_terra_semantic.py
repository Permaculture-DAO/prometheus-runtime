import copy
import json
import unittest
from pathlib import Path
import jsonschema
from app.terra_semantic import (admission_status, semantic_mapping, validate_geometry,
                                land_shadow_interface, status_view)
from app.terra_property_core import digest

ROOT=Path(__file__).resolve().parents[3]
def load(name):
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))
def envelope():
    row={"mode":"TEST","state_fips":"12","county_fips":"055","apn":"TEST-0001",
         "source_id":"TEST_ASSESSOR","observed_on":"2026-11-24","kind":"acreage","value":"5","unit":"acre"}
    return {"mode":"TEST","workstream":"BIGFOOT","source_id":"TEST_ASSESSOR",
            "snapshot_on":"2026-11-24","scope_id":"TEST-SCOPE-1","coverage":"PARTIAL",
            "fixture":{"adapter_id":"terra_property_mock","synthetic_only":True,
                       "live_endpoint":None,"statement":"evaluation, not certification","observations":[row]}}
def geometry():
    return {"mode":"TEST","geometry_id":"TEST-G1","crs":"TEST_LOCAL_GRID","unit":"test_unit",
            "accuracy":"UNKNOWN","source_id":"TEST_GEOMETRY",
            "ring":[["0","0"],["2","0"],["2","3"],["0","3"],["0","0"]]}

class TerraSemanticTests(unittest.TestCase):
    def test_native_schema(self):
        m=semantic_mapping([envelope()],"2026-11-24",30)
        obs=m["observations"][0]["observation"]
        jsonschema.validate(obs,load("observation.schema.json"),format_checker=jsonschema.FormatChecker())
        self.assertTrue(obs["zero_weight_for_pru"])
        self.assertFalse(m["evidence_package_created"])
    def test_replay_and_provenance(self):
        a=envelope(); b=copy.deepcopy(a); b["workstream"]="FLOIE"
        m=semantic_mapping([a,b],"2026-11-24",30)
        self.assertEqual(m,semantic_mapping([b,a],"2026-11-24",30))
        self.assertEqual(len(m["observations"]),1)
        self.assertEqual(m["observations"][0]["workstreams"],["BIGFOOT","FLOIE"])
        h=m.pop("semantic_hash")
        self.assertEqual(h,digest(m))
    def test_conflict(self):
        a=envelope(); b=copy.deepcopy(a); b["fixture"]["observations"][0]["value"]="6"
        m=semantic_mapping([a,b],"2026-11-24",30)
        self.assertEqual(len(m["conflicts"]),1)
        self.assertEqual(m["state"],"HOLD")
    def test_source_policy(self):
        for s in ("PRYCD","FEMA","TEST_ASSESSOR"):
            a=admission_status(s)
            self.assertFalse(a["real_enabled"])
            self.assertTrue(all(x=="UNKNOWN" for x in a["requirements"].values()))
    def test_geometry_schema_area(self):
        g=geometry()
        jsonschema.validate(g,load("terra.geometry.synthetic.schema.json"))
        r=validate_geometry(g)
        self.assertEqual(r["area_test_units_squared"],"6")
        self.assertFalse(r["survey_authority"])
    def test_geometry_invalid(self):
        for key,value in [("mode","REAL"),("crs","EPSG:4326"),("accuracy","CERTIFIED"),
                          ("ring",[["0","0"],["2","2"],["0","2"],["2","0"],["0","0"]]),
                          ("ring",[["0","0"],["1","0"],["2","0"],["0","0"]]),
                          ("ring",[["0","0"],["1","0"],["1","1"],["0","1"]])]:
            g=geometry(); g[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): validate_geometry(g)
    def test_no_land_authority(self):
        x=land_shadow_interface([envelope()],"2026-11-24",30)
        self.assertEqual(x["state"],"HOLD")
        self.assertFalse(x["engine_invoked"])
        self.assertFalse(x["decision_catalog_created"])
        self.assertIsNone(x["land_value"])
        self.assertEqual(set(x["required_gates"].values()),{"UNKNOWN"})
    def test_static_status(self):
        s=status_view()
        self.assertEqual(s,status_view())
        for key in ("real_ingestion_enabled","real_gis_enabled","evidence_spine_write",
                    "holochain_commit","production_admitted","authoritative"):
            self.assertIs(s[key],False)
