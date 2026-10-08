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
    ("rtc_os.dossier.schema.json", "rtc_os.synthetic.json"),
    ("device.registry.schema.json", "device_registry.synthetic.json"),
    ("decoder.registry.schema.json", "decoder_registry.synthetic.json"),
    ("sensor.event.schema.json", "sensor_event.synthetic.json"),
    ("claim.schema.json", "claim_uid.synthetic.json"),
    ("observation.schema.json", "observation.synthetic.json"),
    ("relationship.assertion.schema.json", "relationship_context.synthetic.json"),
    ("disturbance.schema.json", "disturbance.synthetic.json"),
    ("evidence.package.schema.json", "evidence_package.synthetic.json"),
]

errors = []
format_checker = jsonschema.FormatChecker()

for schema_name, fixture_name in checks:
    schema = load_json(CONTRACTS / schema_name)
    fixture = load_json(FIXTURES / fixture_name)
    try:
        jsonschema.validate(instance=fixture, schema=schema, format_checker=format_checker)
    except jsonschema.ValidationError as exc:
        errors.append(f"{fixture_name}: {exc.message}")

# Existing sensor-event identity and authority boundaries.
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

# P0.3 semantic firewalls.
claim = load_json(FIXTURES / "claim_uid.synthetic.json")
if claim["claim_uid"].startswith("C-"):
    errors.append("claim_uid must be semantic and immutable; bare legacy C-numbers are forbidden as global IDs")

relationship = load_json(FIXTURES / "relationship_context.synthetic.json")
if relationship["zero_weight_for_pru"] is not True:
    errors.append("relationship assertions must default to zero PRU weight")

observation_schema = load_json(CONTRACTS / "observation.schema.json")
invalid_observation = {
    "observation_uid": "obs_invalid_missing_context",
    "subject_uid": "ohe_sicily_genesis",
    "method_uid": "method-x",
    "observed_at": "2026-09-29T10:00:00Z",
    "source_class": "sensor",
    "observer_or_instrument_uid": "sensor-x",
    "management_state_version": "ms-v0.1",
    "raw_evidence_refs": ["sha256:x"],
    "statement": "observation_not_verified_indicator"
}
try:
    jsonschema.validate(instance=invalid_observation, schema=observation_schema, format_checker=format_checker)
    errors.append("fail-closed test failed: observation without place/system-boundary context was accepted")
except jsonschema.ValidationError:
    pass

relationship_schema = load_json(CONTRACTS / "relationship.assertion.schema.json")
invalid_relationship = dict(relationship)
invalid_relationship["zero_weight_for_pru"] = False
try:
    jsonschema.validate(instance=invalid_relationship, schema=relationship_schema, format_checker=format_checker)
    errors.append("fail-closed test failed: relationship assertion with PRU weight was accepted")
except jsonschema.ValidationError:
    pass


# P2.2 schema integrity: review/admissibility contracts must themselves be valid JSON Schema.
for schema_name in ["review.attestation.schema.json", "admissibility.decision.schema.json"]:
    try:
        jsonschema.Draft202012Validator.check_schema(load_json(CONTRACTS / schema_name))
    except Exception as exc:
        errors.append(f"{schema_name}: invalid JSON Schema: {exc}")

print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
sys.exit(1 if errors else 0)
