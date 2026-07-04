from pathlib import Path
import hashlib
import json
import sys

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required for contract validation") from exc

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = CONTRACTS / "fixtures"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_event_id(event: dict) -> str:
    material = "\n".join(
        [
            event["source_system"],
            event["source_event_id"],
            event["device_id"],
            event["sensor_id"],
            event["observed_at"],
            event["raw_payload_sha256"],
            event["decoder_id"],
            event["decoder_version"],
        ]
    )
    return "evt_" + hashlib.sha256(material.encode("utf-8")).hexdigest()


checks = [
    ("device.registry.schema.json", "device_registry.synthetic.json"),
    ("decoder.registry.schema.json", "decoder_registry.synthetic.json"),
    ("sensor.event.schema.json", "sensor_event.synthetic.json"),
]

errors = []

for schema_name, fixture_name in checks:
    schema = load_json(CONTRACTS / schema_name)
    fixture = load_json(FIXTURES / fixture_name)
    try:
        jsonschema.validate(instance=fixture, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"{fixture_name}: {exc.message}")

event = load_json(FIXTURES / "sensor_event.synthetic.json")
if event["event_id"] != canonical_event_id(event):
    errors.append("sensor_event.synthetic.json event_id does not match canonical identity policy")
if event["authoritative_for_mrv"] is not False:
    errors.append("synthetic event must not be authoritative_for_mrv")
if event["statement"] != "evaluation, not certification":
    errors.append("synthetic event must retain non-certification statement")
if event["source_system"] == "synthetic" and (
    event["holochain"]["batch_hash"] is not None or event["holochain"]["entry_ref"] is not None
):
    errors.append("synthetic fixture must not include live Holochain commitments")
if event["holochain"]["commit_policy"] == "do_not_commit_raw" and event["holochain"]["entry_ref"]:
    errors.append("do_not_commit_raw events must not include Holochain entry references")

print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
sys.exit(1 if errors else 0)
