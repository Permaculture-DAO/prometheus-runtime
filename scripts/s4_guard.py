from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "adapters" / "adapter_manifest.json"

errors: list[str] = []

if not MANIFEST.exists():
    errors.append("missing adapters/adapter_manifest.json")
else:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("live_ingestion_admitted") is not False:
        errors.append("adapter manifest must keep live_ingestion_admitted=false")
    if manifest.get("statement") != "evaluation, not certification":
        errors.append("adapter manifest must retain non-certification statement")
    for adapter in manifest.get("adapters", []):
        adapter_id = adapter.get("adapter_id", "<missing>")
        if adapter.get("enabled_by_default") is not False:
            errors.append(f"{adapter_id} must be disabled by default")
        if adapter.get("endpoint_url") is not None:
            errors.append(f"{adapter_id} must not declare a live endpoint")
        fixture = adapter.get("fixture")
        if not fixture:
            errors.append(f"{adapter_id} missing fixture reference")
            continue
        fixture_path = ROOT / fixture
        if not fixture_path.exists():
            errors.append(f"{adapter_id} fixture missing: {fixture}")
            continue
        fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if fixture_payload.get("synthetic_only") is not True:
            errors.append(f"{fixture} must declare synthetic_only=true")
        if fixture_payload.get("live_endpoint") is not None:
            errors.append(f"{fixture} must not declare live_endpoint")
        if fixture_payload.get("statement") != "evaluation, not certification":
            errors.append(f"{fixture} must retain non-certification statement")

env_example = ROOT / ".env.example"
if env_example.exists():
    text = env_example.read_text(encoding="utf-8")
    required_false_flags = [
        "S4_INGESTION_ENABLED=false",
        "S4_LIVE_INGESTION_ADMITTED=false",
        "S4_TTN_MOCK_ENABLED=false",
        "S4_MANUAL_MOCK_ENABLED=false",
        "S4_LAB_MOCK_ENABLED=false",
    ]
    for flag in required_false_flags:
        if flag not in text:
            errors.append(f".env.example missing closed default: {flag}")

live_secret_patterns = {
    "ttn_api_key": re.compile(r"\bNNSXS\.[A-Za-z0-9._-]+"),
    "private_key_material": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "mqtt_url": re.compile(r"\bmqtts?://", re.IGNORECASE),
}

for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT).as_posix()
    if ".git/" in rel or not path.is_file() or path.stat().st_size > 2_000_000:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for rule, pattern in live_secret_patterns.items():
        if pattern.search(text):
            errors.append(f"{rule} detected in {rel}")

print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
sys.exit(1 if errors else 0)
