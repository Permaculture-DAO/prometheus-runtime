from pathlib import Path
import json
import sys

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required for S6 guard") from exc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.evidence_batch import build_synthetic_evidence_batch, verify_synthetic_evidence_batch  # noqa: E402

BATCH_PATH = ROOT / "evidence" / "batches" / "synthetic_batch_0001.json"
SCHEMA_PATH = ROOT / "contracts" / "evidence.batch.schema.json"
NORMALIZED = ROOT / "adapters" / "normalized"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


errors: list[str] = []

if not BATCH_PATH.exists():
    errors.append("missing evidence/batches/synthetic_batch_0001.json")
else:
    batch = load_json(BATCH_PATH)
    schema = load_json(SCHEMA_PATH)
    try:
        jsonschema.validate(instance=batch, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"batch schema validation failed: {exc.message}")

    generated = build_synthetic_evidence_batch(
        [load_json(path) for path in sorted(NORMALIZED.glob("*.normalized.synthetic.json"))]
    )
    if batch != generated:
        errors.append("synthetic evidence batch artifact is stale")
    errors.extend(verify_synthetic_evidence_batch(batch))

    for event in batch.get("events", []):
        if "raw_payload" in event or "normalized" in event:
            errors.append(f"{event.get('event_id', '<missing>')}: batch must contain references, not event bodies")

print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
sys.exit(1 if errors else 0)
