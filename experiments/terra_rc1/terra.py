"""TERRA RC1: offline TEST-only candidate; no production integration or external I/O."""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext

VERSION = "0.1.0-rc.1"
MAX_BYTES = 1_000_000
MAX_ROWS = 1000
FIELDS = {"mode", "state_fips", "county_fips", "apn", "source_id", "observed_on", "kind", "value", "unit"}
UNITS = {"acreage": {"acre", "sqft"}, "asking_price": {"USD"}, "recorded_sale_price": {"USD"}}
SOURCES = {"TEST_ASSESSOR", "TEST_LISTING", "TEST_RECORDER"}
SCOPE = {"12": {"055", "101"}, "13": {"001"}}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def unique_pairs(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate JSON key")
        obj[k] = v
    return obj

def normalize(row):
    if not isinstance(row, dict) or set(row) != FIELDS:
        raise ValueError("invalid fields")
    if any(not isinstance(v, str) for v in row.values()):
        raise ValueError("all input fields must be strings")
    if row["mode"] != "TEST" or row["source_id"] not in SOURCES:
        raise ValueError("TEST sources only")
    st, co, apn = (row[k] for k in ("state_fips", "county_fips", "apn"))
    if st not in SCOPE or co not in SCOPE[st]:
        raise ValueError("outside synthetic jurisdiction allowlist")
    # RC1 fixture IDs MUST begin TEST-; no real APNs or heuristics.
    if not re.fullmatch(r"TEST-[A-Z0-9-]{1,48}", apn):
        raise ValueError("synthetic APN required")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["observed_on"]):
        raise ValueError("invalid observation date")
    date.fromisoformat(row["observed_on"])
    kind, unit, raw = (row[k] for k in ("kind", "unit", "value"))
    if kind not in UNITS or unit not in UNITS[kind]:
        raise ValueError("invalid kind/unit")
    allowed = {"TEST_ASSESSOR": {"acreage"}, "TEST_LISTING": {"asking_price"}, "TEST_RECORDER": {"recorded_sale_price"}}
    if kind not in allowed[row["source_id"]]:
        raise ValueError("source outside field scope")
    if not re.fullmatch(r"[0-9]{1,12}(\.[0-9]{1,6})?", raw):
        raise ValueError("invalid numeric string")
    with localcontext() as ctx:
        ctx.prec = 50
        value = Decimal(raw)
        if kind == "acreage" and value <= 0:
            raise ValueError("acreage must be positive")
        # Normalize acreage to exact square feet, avoid approximate division.
        if unit == "acre":
            value *= Decimal("43560")
        if kind != "acreage" and value.quantize(Decimal(".01")) != value:
            raise ValueError("USD value exceeds cent precision")
        val = format(value.normalize(), "f") if value else "0"
    return {
        "mode": "TEST", "parcel_key": "US:" + st + ":" + co + ":" + apn,
        "source_id": row["source_id"], "observed_on": row["observed_on"],
        "kind": kind, "normalized_value": val,
        "normalized_unit": "sqft" if kind == "acreage" else "USD",
        "raw": row, "evidence_hash": digest(row), "evidence_state": "SYNTHETIC_ONLY"
    }

def evaluate(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError("expected bounded non-empty JSON array")
    observations = {}
    for row in rows:
        item = normalize(row)
        observations[item["evidence_hash"]] = item
    items = [observations[k] for k in sorted(observations)]
    groups = {}
    for x in items:
        # Only same-day incompatible observations within same parcel/kind conflict.
        key = (x["parcel_key"], x["kind"], x["observed_on"])
        groups.setdefault(key, []).append(x)
    conflicts = []
    for key, obs in sorted(groups.items()):
        if len({x["normalized_value"] for x in obs}) > 1:
            conflicts.append({"parcel_key": key[0], "kind": key[1], "observed_on": key[2],
                              "evidence_hashes": sorted(x["evidence_hash"] for x in obs),
                              "state": "REVIEW_REQUIRED"})
    result = {
        "version": VERSION, "mode": "TEST", "state": "HOLD",
        "production_admitted": False, "legal_authority": False,
        "capital_authority": False, "real_ingestion_enabled": False,
        "local_checks": {"synthetic_contract": "PASS", "conflict_review": "UNKNOWN" if conflicts else "PASS",
                         "real_identity": "UNKNOWN", "data_rights": "UNKNOWN", "title": "UNKNOWN",
                         "legal": "UNKNOWN", "environment": "UNKNOWN"},
        "input_count": len(rows), "duplicates": len(rows) - len(items),
        "parcel_keys": sorted({x["parcel_key"] for x in items}),
        "observations": items, "conflicts": conflicts,
        "boundary": "Synthetic evaluation only; not title, valuation, MRV or investment approval."
    }
    result["semantic_hash"] = digest(result)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", help="Local synthetic JSON fixture")
    args = parser.parse_args()
    try:
        with open(args.fixture, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("fixture too large")
        rows = json.loads(raw, object_pairs_hook=unique_pairs)
        print(canonical(evaluate(rows)).decode("ascii"))
    except (OSError, ValueError, TypeError, InvalidOperation, RecursionError) as exc:
        print("REJECTED: " + str(exc), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
