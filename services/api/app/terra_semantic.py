"""TERRA RC4: offline semantic mapping, GIS contract and admission diagnostics."""
import re
from datetime import date
from decimal import Decimal, localcontext
from .terra_property_core import digest
from .terra_connector import reconcile, connector_status

VERSION = "0.1.0-rc.4"
REQUIREMENTS = ("dataset_identity", "jurisdiction", "field_scope", "licence",
                "acquisition_permission", "retention_permission", "cost_cap",
                "coverage", "freshness_policy", "provenance", "review_decision")
LAND_GATES = ("rights", "land_use", "environment", "water", "data")

def admission_status(source_id):
    """Current executable policy, not a caller-declared authorization mechanism."""
    policy = connector_status(source_id)
    return {"source_id": source_id, "mode": "TEST", "state": "HOLD",
            "fixture_allowed": policy["fixture_allowed"], "real_enabled": False,
            "network_allowed": False, "incremental_budget_usd": 0,
            "requirements": {key: "UNKNOWN" for key in REQUIREMENTS},
            "competent_review_required": True}

def semantic_mapping(envelopes, as_of, max_age_days):
    """Generate native-schema-shaped synthetic observations, never evidence packages."""
    report = reconcile(envelopes, as_of, max_age_days)
    rows = []
    for item in report["evidence"]:
        obs = item["observation"]
        subject = "test_terra_" + digest(obs["parcel_key"])
        row = {
            "subject_uid": subject,
            "place_context_version": "TEST-PLACE-v1:" + subject,
            "system_boundary_version": "TEST-BOUNDARY-v1:" + subject,
            "method_uid": "terra-property-normalization-test-v1",
            "observed_at": obs["observed_on"] + "T00:00:00Z",
            "source_class": "derived_model",
            "observer_or_instrument_uid": obs["source_id"],
            "management_state_version": "TEST-MANAGEMENT-UNKNOWN",
            "raw_evidence_refs": ["sha256:" + item["evidence_hash"]],
            "uncertainty_note": "Synthetic date-only fixture; midnight is a representation convention, not an observed time. Context is a test placeholder.",
            "zero_weight_for_pru": True,
            "statement": "observation_not_verified_indicator"
        }
        row["observation_uid"] = "obs_terra_" + digest(row)
        rows.append({"observation": row, "property_key": obs["parcel_key"],
                     "property_kind": obs["kind"], "snapshot_hashes": item["snapshot_hashes"],
                     "workstreams": item["workstreams"],
                     "stale_by_declared_policy": item["stale_by_declared_policy"]})
    result = {"version": VERSION, "mode": "TEST", "state": "HOLD",
              "observations": sorted(rows, key=lambda r: r["observation"]["observation_uid"]),
              "reconciliation_hash": report["semantic_hash"], "conflicts": report["conflicts"],
              "claims_registered": False, "evidence_package_created": False,
              "evidence_spine_write": False, "holochain_commit": False,
              "authoritative": False, "production_admitted": False}
    result["semantic_hash"] = digest(result)
    return result

def _decimal(value):
    if type(value) is not str or not re.fullmatch(r"-?[0-9]{1,6}(\.[0-9]{1,6})?", value):
        raise ValueError("bounded ASCII decimal string required")
    d = Decimal(value)
    if abs(d) > 100000:
        raise ValueError("synthetic grid limit")
    return d

def _orientation(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def _on(a,b,c):
    return min(a[0],b[0]) <= c[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= c[1] <= max(a[1],b[1])

def _intersects(a,b,c,d):
    p,q,r,s = _orientation(a,b,c),_orientation(a,b,d),_orientation(c,d,a),_orientation(c,d,b)
    if (p>0>q or q>0>p) and (r>0>s or s>0>r):
        return True
    return ((p==0 and _on(a,b,c)) or (q==0 and _on(a,b,d)) or
            (r==0 and _on(c,d,a)) or (s==0 and _on(c,d,b)))

def validate_geometry(payload):
    """Single synthetic planar ring only; no geographic CRS or real GIS access."""
    required = {"mode","geometry_id","crs","unit","accuracy","source_id","ring"}
    if type(payload) is not dict or set(payload)!=required:
        raise ValueError("exact geometry contract required")
    if (payload["mode"]!="TEST" or payload["crs"]!="TEST_LOCAL_GRID"
        or payload["unit"]!="test_unit" or payload["accuracy"]!="UNKNOWN"
        or payload["source_id"]!="TEST_GEOMETRY"):
        raise ValueError("synthetic grid only")
    if type(payload["geometry_id"]) is not str or not re.fullmatch(r"TEST-[A-Z0-9-]{1,48}",payload["geometry_id"]):
        raise ValueError("synthetic geometry ID required")
    ring=payload["ring"]
    if type(ring) is not list or not 4 <= len(ring) <= 65:
        raise ValueError("bounded closed ring required")
    points=[]
    for xy in ring:
        if type(xy) is not list or len(xy)!=2:
            raise ValueError("two coordinates required")
        points.append(tuple(_decimal(v) for v in xy))
    if points[0]!=points[-1] or len(set(points[:-1]))!=len(points)-1:
        raise ValueError("closed simple ring required")
    n=len(points)-1
    with localcontext() as ctx:
        ctx.prec=50
        for i in range(n):
            if _orientation(points[i-1 if i else n-1],points[i],points[i+1])==0:
                raise ValueError("collinear adjacent edges unsupported")
            for j in range(i+1,n):
                if j==i+1 or (i==0 and j==n-1):
                    continue
                if _intersects(points[i],points[i+1],points[j],points[j+1]):
                    raise ValueError("self-intersecting ring")
        area=abs(sum(points[i][0]*points[i+1][1]-points[i+1][0]*points[i][1] for i in range(n)))/2
        if not area:
            raise ValueError("degenerate polygon")
        area_text=format(area.normalize(),"f")
    return {"version":VERSION,"mode":"TEST","geometry_hash":digest(payload),
            "area_test_units_squared":area_text,"state":"HOLD","geometry_check":"PASS",
            "survey_authority":False,"real_gis_enabled":False,"accuracy_verified":False}

def land_shadow_interface(envelopes, as_of, max_age_days):
    """Gap report only; no fabricated gate catalogs or invocation of candidate engine."""
    mapping=semantic_mapping(envelopes,as_of,max_age_days)
    result={"version":VERSION,"mode":"TEST","state":"HOLD",
            "target_contract":"land-underwriting-shadow/v2",
            "mapping_hash":mapping["semantic_hash"],
            "required_gates":{key:"UNKNOWN" for key in LAND_GATES},
            "engine_invoked":False,"evidence_catalog_created":False,
            "decision_catalog_created":False,"land_value":None,
            "authoritative":False,"capital_admission":False}
    result["semantic_hash"]=digest(result)
    return result

def status_view():
    """Static capability descriptor for future read-only bridge integration."""
    result={"version":VERSION,"mode":"TEST","state":"HOLD",
            "capabilities":{"semantic_mapping":"CANDIDATE","synthetic_geometry":"CANDIDATE",
                            "source_admission":"HOLD","land_shadow":"GAP_REPORT_ONLY"},
            "real_ingestion_enabled":False,"real_gis_enabled":False,
            "evidence_spine_write":False,"holochain_commit":False,
            "production_admitted":False,"authoritative":False,
            "statement":"evaluation, not certification"}
    result["semantic_hash"]=digest(result)
    return result
