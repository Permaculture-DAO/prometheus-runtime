"""RC8 internal synthetic qualification; not an expert/field benchmark."""
import json
import sys
from pathlib import Path
from time import perf_counter
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.terra_connector import reconcile, delta
from app.terra_property_core import digest

AS_OF = "2026-11-24"
BASELINE = "2e216c7887a87902b23f759d4333bcf0e4c62808"

def row(apn, value, county="055", day=AS_OF, unit="acre"):
    return dict(mode="TEST", state_fips="12", county_fips=county, apn=apn,
                source_id="TEST_ASSESSOR", observed_on=day, kind="acreage",
                value=value, unit=unit)

def envelope(stream, rows, day=AS_OF):
    return dict(mode="TEST", workstream=stream, source_id="TEST_ASSESSOR",
                snapshot_on=day, scope_id="TEST-BENCHMARK", coverage="PARTIAL",
                fixture=dict(adapter_id="terra_property_mock", synthetic_only=True,
                             live_endpoint=None, statement="evaluation, not certification",
                             observations=rows))

def corpus():
    # Independently enumerated expected table below, authored in same review session.
    a = row("TEST-A", "5")
    return [
        envelope("BIGFOOT", [a, row("TEST-B", "2"), row("TEST-C", "3", day="2026-10-01")]),
        envelope("FLOIE", [a.copy(), row("TEST-B", "3"), row("TEST-A", "4", county="101")]),
        envelope("FL-LAND", [a.copy(), row("TEST-A", "217800", unit="sqft")])
    ]

# Hand-enumerated fixture oracle: county, APN, day, normalized sqft, provenance, stale.
EXPECTED = [
    ("055", "TEST-A", AS_OF, "217800", ("BIGFOOT", "FL-LAND", "FLOIE"), False),
    ("055", "TEST-A", AS_OF, "217800", ("FL-LAND",), False),
    ("055", "TEST-B", AS_OF, "87120", ("BIGFOOT",), False),
    ("055", "TEST-B", AS_OF, "130680", ("FLOIE",), False),
    ("055", "TEST-C", "2026-10-01", "130680", ("BIGFOOT",), True),
    ("101", "TEST-A", AS_OF, "174240", ("FLOIE",), False)
]
EXPECTED_KEYS = {"US:12:055:TEST-A", "US:12:055:TEST-B", "US:12:055:TEST-C", "US:12:101:TEST-A"}

def observed(result):
    out = []
    for e in result["evidence"]:
        o = e["observation"]
        _, _, co, apn = o["parcel_key"].split(":")
        out.append((co, apn, o["observed_on"], o["normalized_value"],
                    tuple(e["workstreams"]), e["stale_by_declared_policy"]))
    return sorted(out)

def main():
    items = corpus()
    start = perf_counter()
    result = reconcile(items, AS_OF, 30)
    elapsed = perf_counter() - start
    expected = sorted(EXPECTED)
    actual = observed(result)
    # Exact identity and provenance are compared jointly, including equivalent-unit distinct raw evidence.
    checks = {
        "exact_expected_evidence": actual == expected,
        "exact_expected_parcel_keys": set(result["parcel_keys"]) == EXPECTED_KEYS,
        "exact_expected_conflict": [(x["parcel_key"], x["kind"], x["observed_on"])
                                   for x in result["conflicts"]] == [("US:12:055:TEST-B", "acreage", AS_OF)],
        "replay_reversed_envelopes": result == reconcile(list(reversed(items)), AS_OF, 30),
        "replay_same_input": result == reconcile(items, AS_OF, 30),
        "authority_boundary": result["state"] == "HOLD" and result["authoritative"] is False and result["real_ingestion_enabled"] is False
    }
    prev = envelope("BIGFOOT", [row("TEST-A", "5", day="2026-11-23"),
                                 row("TEST-B", "2", day="2026-11-23"),
                                 row("TEST-C", "3", day="2026-11-23")], "2026-11-23")
    curr = envelope("BIGFOOT", [row("TEST-A", "5"), row("TEST-B", "3"), row("TEST-D", "1")])
    changes = delta(prev, curr)
    expected_delta = {"US:12:055:TEST-A":"UNCHANGED_VALUES", "US:12:055:TEST-B":"VALUE_SET_CHANGED",
                      "US:12:055:TEST-C":"NOT_OBSERVED", "US:12:055:TEST-D":"NEW_OBSERVATION"}
    checks["exact_expected_delta"] = {x["parcel_key"]:x["status"] for x in changes["changes"]} == expected_delta
    checks["delta_authority_boundary"] = changes["state"] == "HOLD" and changes["authoritative"] is False
    report = dict(mode="TEST", baseline=BASELINE, fixture_hash=digest(items),
                  oracle_hash=digest(EXPECTED), delta_fixture_hash=digest([prev,curr]),
                  delta_oracle_hash=digest(expected_delta), raw_rows=sum(len(x["fixture"]["observations"]) for x in items),
                  unique_evidence=len(actual), distinct_parcels=len(result["parcel_keys"]),
                  conflicts=len(result["conflicts"]), stale=sum(e[-1] for e in actual),
                  checks=checks, reconciliation_hash=result["semantic_hash"],
                  delta_hash=changes["semantic_hash"],
                  expert_comparison="NOT_RUN", human_review_minutes=None,
                  complexity_comparison="NOT_MEASURED", independent_assurance=False)
    report["deterministic_report_hash"] = digest(report)
    print(json.dumps(dict(report, observed_runtime_seconds=round(elapsed, 6)), sort_keys=True))
    if actual != expected:
        print(json.dumps({"actual":actual,"expected":expected},sort_keys=True),file=sys.stderr)
    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
