from pathlib import Path
import json
import sys

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required for S5 guard") from exc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.normalization import canonical_event_id, normalize_fixture  # noqa: E402

CONTRACT = json.loads((ROOT / "contracts" / "sensor.event.schema.json").read_text(encoding="utf-8"))

ADAPTER_FIXTURES = {
    "ttn_mock": ROOT / "adapters" / "ttn" / "synthetic_uplink.json",
    "manual_mock": ROOT / "adapters" / "manual" / "synthetic_observation.json",
    "lab_mock": ROOT / "adapters" / "lab" / "synthetic_result.json",
}

errors: list[str] = []

for adapter_id, fixture_path in ADAPTER_FIXTURES.items():
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    try:
        generated = normalize_fixture(adapter_id, fixture)
    except ValueError as exc:
        errors.append(f"{adapter_id}: {exc}")
        continue
    artifact_path = ROOT / "adapters" / "normalized" / f"{adapter_id}.normalized.synthetic.json"
    if not artifact_path.exists():
        errors.append(f"{adapter_id}: normalized artifact missing")
        continue
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact != generated:
        errors.append(f"{adapter_id}: normalized artifact is stale")
    try:
        jsonschema.validate(instance=artifact, schema=CONTRACT)
    except jsonschema.ValidationError as exc:
        errors.append(f"{adapter_id}: contract validation failed: {exc.message}")
    if artifact["event_id"] != canonical_event_id(artifact):
        errors.append(f"{adapter_id}: canonical event_id mismatch")
    if artifact["qa"]["quality_status"] != "synthetic":
        errors.append(f"{adapter_id}: quality_status must remain synthetic")
    if artifact["authoritative_for_mrv"] is not False:
        errors.append(f"{adapter_id}: authoritative_for_mrv must remain false")
    if artifact["statement"] != "evaluation, not certification":
        errors.append(f"{adapter_id}: non-certification statement missing")
    if artifact["holochain"]["batch_hash"] is not None or artifact["holochain"]["entry_ref"] is not None:
        errors.append(f"{adapter_id}: normalized synthetic event must not include Holochain commitments")

print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
sys.exit(1 if errors else 0)
