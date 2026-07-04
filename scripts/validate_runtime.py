from pathlib import Path
import json, re, sys

root = Path(__file__).resolve().parents[1]
errors = []
required = [
    root / "compose.yaml",
    root / ".env.example",
    root / ".gitignore",
    root / "services/api/Dockerfile",
    root / "services/api/app/main.py",
    root / "services/holochain/conductor-config.yaml",
    root / "services/holochain/entrypoint.sh",
    root / "config/canonical_release.json",
]
for p in required:
    if not p.exists():
        errors.append(f"missing {p.relative_to(root)}")
if (root / ".env.local").exists():
    errors.append(".env.local must not be present in the repository candidate")

try:
    import yaml
    compose = yaml.safe_load((root / "compose.yaml").read_text(encoding="utf-8"))
    expected = {"db", "api", "gateway", "holochain-conductor", "holochain-bridge"}
    if set(compose.get("services", {})) != expected:
        errors.append("compose service set mismatch")
    for name, svc in compose.get("services", {}).items():
        if name == "gateway":
            continue
        if svc.get("env_file") != ".env.local":
            errors.append(f"{name} must use local-only .env.local at runtime")
except Exception as e:
    errors.append(f"compose parse failed: {e}")

env = {}
for line in (root / ".env.example").read_text(encoding="utf-8").splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v
for key in ["CANONICAL_ROOT","RUNTIME_BUILD_ID","DOCUMENTARY_PATCH","AUDIT_CONVERGENCE_PATCH","RUNTIME_STAGE","STATUS_QUALIFIER","DATABASE_URL","WRITE_API_KEY","P2_TRBK_ENABLED","HOLOCHAIN_ENABLED","HOLOCHAIN_REQUIRED_VERSION"]:
    if not env.get(key):
        errors.append(f"missing env template key {key}")
for key in ["POSTGRES_PASSWORD", "WRITE_API_KEY"]:
    if env.get(key) != "REPLACE_WITH_STRONG_SECRET":
        errors.append(f"{key} must remain a placeholder in .env.example")
if "REPLACE_WITH_STRONG_SECRET" not in env.get("DATABASE_URL", ""):
    errors.append("DATABASE_URL must use placeholder secret in .env.example")
if env.get("P2_TRBK_ENABLED") != "false":
    errors.append("P2 must default false")
if env.get("HOLOCHAIN_ENABLED") != "false":
    errors.append("Holochain must default false until admitted")
if env.get("HOLOCHAIN_REQUIRED_VERSION") != "0.6.1":
    errors.append("Holochain baseline must be 0.6.1 until hn-introspect supersedes it")

release = json.loads((root / "config/canonical_release.json").read_text(encoding="utf-8"))
if release.get("canonical_root") != "PROMETHEUS-CANON-ROOT-v7.0":
    errors.append("canonical root mismatch")
if release.get("runtime_stage") != "development":
    errors.append("runtime stage must be development")
for key in ["production_admitted", "legal_admitted", "market_admitted"]:
    if release.get(key) is not False:
        errors.append(f"{key} must be false")
if release.get("independent_assurance") != "unsigned":
    errors.append("independent assurance must be unsigned")

conductor = (root / "services/holochain/conductor-config.yaml").read_text(encoding="utf-8")
if ("allowed_origins: " + "'*'") in conductor or ("allowed_origins: " + '"*"') in conductor:
    errors.append("Holochain conductor must not use wildcard allowed_origins")
entrypoint = (root / "services/holochain/entrypoint.sh").read_text(encoding="utf-8")
if "0.6.2" in entrypoint:
    errors.append("entrypoint still references Holochain 0.6.2")

for p in root.rglob("*"):
    if p.is_file() and p.stat().st_size == 0:
        errors.append(f"empty file {p.relative_to(root)}")
    if p.is_file() and p.stat().st_size < 1_000_000:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"POSTGRES_PASSWORD=(?!REPLACE_WITH_STRONG_SECRET)(?=.{20,})[A-Za-z0-9_./+=:-]+", text):
            errors.append(f"non-placeholder postgres password pattern in {p.relative_to(root)}")

print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
sys.exit(1 if errors else 0)
