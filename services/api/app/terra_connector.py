"""RC3 offline connector contract and snapshot reconciliation. No network or writes."""
from datetime import date
import re
from .terra_property_core import digest, MAX_ROWS
from .terra_property import run_fixture

VERSION = "0.1.0-rc.3"
STREAMS = {"BIGFOOT", "FLOIE", "FL-LAND"}
TEST_SOURCES = {"TEST_ASSESSOR", "TEST_LISTING", "TEST_RECORDER"}
FIELDS = {"mode", "workstream", "source_id", "snapshot_on", "scope_id",
          "coverage", "fixture"}
COVERAGE = {"PARTIAL", "COMPLETE_TEST"}

def _day(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("ASCII calendar date required")
    return date.fromisoformat(value)

def connector_status(source_id):
    # No caller-supplied permissions can promote this policy.
    if type(source_id) is not str or not re.fullmatch(r"[A-Z0-9_]{1,64}", source_id):
        raise ValueError("invalid source ID")
    return {"source_id": source_id, "fixture_allowed": source_id in TEST_SOURCES,
            "live_enabled": False, "network_allowed": False,
            "incremental_budget_usd": 0, "state": "TEST_ONLY" if source_id in TEST_SOURCES else "HOLD"}

def snapshot(envelope):
    if type(envelope) is not dict or set(envelope) != FIELDS:
        raise ValueError("exact connector envelope required")
    if envelope["mode"] != "TEST" or envelope["workstream"] not in STREAMS:
        raise ValueError("TEST workstreams only")
    if not connector_status(envelope["source_id"])["fixture_allowed"]:
        raise ValueError("source not admitted for fixture use")
    day = _day(envelope["snapshot_on"])
    if type(envelope["scope_id"]) is not str or not re.fullmatch(r"TEST-[A-Z0-9-]{1,48}", envelope["scope_id"]):
        raise ValueError("synthetic scope required")
    if envelope["coverage"] not in COVERAGE:
        raise ValueError("explicit synthetic coverage required")
    report = run_fixture(envelope["fixture"])
    observations = report["report"]["observations"]
    for obs in observations:
        if obs["source_id"] != envelope["source_id"]:
            raise ValueError("source mismatch")
        if _day(obs["observed_on"]) > day:
            raise ValueError("future observation relative to snapshot")
    result = {k: envelope[k] for k in FIELDS if k != "fixture"}
    result.update(version=VERSION, observations=observations, batch=report["batch"],
                  conflicts=report["report"]["conflicts"], state="HOLD",
                  real_ingestion_enabled=False, authoritative=False)
    result["snapshot_hash"] = digest(result)
    return result

def reconcile(envelopes, as_of, max_age_days):
    """Compare evidence, not property status. All times caller declared."""
    day = _day(as_of)
    if type(max_age_days) is not int or not 0 <= max_age_days <= 3660:
        raise ValueError("bounded freshness policy required")
    if type(envelopes) is not list or not 1 <= len(envelopes) <= 30:
        raise ValueError("bounded snapshot list required")
    snapshots = [snapshot(x) for x in envelopes]
    if any(_day(x["snapshot_on"]) > day for x in snapshots):
        raise ValueError("future snapshot")
    if sum(len(x["observations"]) for x in snapshots) > MAX_ROWS:
        raise ValueError("combined observation limit exceeded")
    by_hash = {}
    for snap in snapshots:
        for obs in snap["observations"]:
            h = obs["evidence_hash"]
            entry = by_hash.setdefault(h, {"observation": obs, "workstreams": set(), "snapshot_hashes": set()})
            entry["workstreams"].add(snap["workstream"])
            entry["snapshot_hashes"].add(snap["snapshot_hash"])
    evidence = []
    for h, entry in sorted(by_hash.items()):
        obs = entry["observation"]
        evidence.append({"evidence_hash": h, "observation": obs,
            "workstreams": sorted(entry["workstreams"]), "snapshot_hashes": sorted(entry["snapshot_hashes"]),
            "stale_by_declared_policy": (day - _day(obs["observed_on"])).days > max_age_days})
    groups = {}
    for entry in evidence:
        obs = entry["observation"]
        key = (obs["parcel_key"], obs["kind"], obs["observed_on"])
        groups.setdefault(key, []).append(entry)
    conflicts = [{"parcel_key": k[0], "kind": k[1], "observed_on": k[2],
                  "evidence_hashes": sorted(e["evidence_hash"] for e in rows)}
                 for k, rows in sorted(groups.items())
                 if len({e["observation"]["normalized_value"] for e in rows}) > 1]
    output = {"version": VERSION, "mode": "TEST", "state": "HOLD", "as_of": as_of,
              "max_age_days": max_age_days, "freshness_verified": False,
              "evidence": evidence, "conflicts": conflicts,
              "parcel_keys": sorted({e["observation"]["parcel_key"] for e in evidence}),
              "real_ingestion_enabled": False, "authoritative": False}
    output["semantic_hash"] = digest(output)
    return output

def delta(previous, current):
    """No absence implies a sale, deletion, title change, or real-world removal."""
    a, b = snapshot(previous), snapshot(current)
    for k in ("source_id", "workstream", "scope_id"):
        if a[k] != b[k]:
            raise ValueError("incomparable snapshot scope")
    if _day(b["snapshot_on"]) <= _day(a["snapshot_on"]):
        raise ValueError("strict chronological order required")
    def index(snap):
        groups = {}
        for obs in snap["observations"]:
            k = (obs["parcel_key"], obs["kind"])
            groups.setdefault(k, set()).add((obs["normalized_value"], obs["normalized_unit"]))
        return groups
    left, right = index(a), index(b)
    rows = []
    for key in sorted(left.keys() | right.keys()):
        x, y = left.get(key), right.get(key)
        status = ("NEW_OBSERVATION" if x is None else
                  "NOT_OBSERVED" if y is None else
                  "UNCHANGED_VALUES" if x == y else "VALUE_SET_CHANGED")
        rows.append({"parcel_key": key[0], "kind": key[1], "status": status,
                     "previous_values": sorted(x) if x is not None else [],
                     "current_values": sorted(y) if y is not None else [],
                     "requires_review": status != "UNCHANGED_VALUES" or
                         (x is not None and len(x) > 1) or (y is not None and len(y) > 1)})
    result = {"version": VERSION, "mode": "TEST", "state": "HOLD",
              "previous_hash": a["snapshot_hash"], "current_hash": b["snapshot_hash"],
              "previous_coverage": a["coverage"], "current_coverage": b["coverage"],
              "changes": rows, "real_ingestion_enabled": False, "authoritative": False}
    result["semantic_hash"] = digest(result)
    return result
