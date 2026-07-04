from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.normalization import normalize_fixture  # noqa: E402

ADAPTER_FIXTURES = {
    "ttn_mock": ROOT / "adapters" / "ttn" / "synthetic_uplink.json",
    "manual_mock": ROOT / "adapters" / "manual" / "synthetic_observation.json",
    "lab_mock": ROOT / "adapters" / "lab" / "synthetic_result.json",
}

OUT = ROOT / "adapters" / "normalized"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for adapter_id, fixture_path in ADAPTER_FIXTURES.items():
        event = normalize_fixture(adapter_id, load_json(fixture_path))
        target = OUT / f"{adapter_id}.normalized.synthetic.json"
        target.write_text(json.dumps(event, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
