from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.evidence_batch import build_synthetic_evidence_batch  # noqa: E402

NORMALIZED = ROOT / "adapters" / "normalized"
OUT = ROOT / "evidence" / "batches"
TARGET = OUT / "synthetic_batch_0001.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    events = [load_json(path) for path in sorted(NORMALIZED.glob("*.normalized.synthetic.json"))]
    batch = build_synthetic_evidence_batch(events)
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(batch, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
