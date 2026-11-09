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
    root / "config/ravel_profile.json",
    root / "services/api/app/ravel.py",
    root / "services/api/app/ravel_schemas.py",
    root / "config/semantic_claims_vnext.json",
    root / "config/claims_registry_projection_v0_1.json",
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
if release.get("canon_authority", "").split()[0] != "PROMETHEUS-CANON-ROOT-v1.1":
    errors.append("canon authority must map to v1.1 Genesis line")
if release.get("runtime_stage") != "development":
    errors.append("runtime stage must be development")
for key in ["production_admitted", "legal_admitted", "market_admitted"]:
    if release.get(key) is not False:
        errors.append(f"{key} must be false")
if release.get("independent_assurance") != "unsigned":
    errors.append("independent assurance must be unsigned")


ravel = json.loads((root / "config/ravel_profile.json").read_text(encoding="utf-8"))
if ravel.get("mode") != "shadow_underwriting":
    errors.append("RAVEL mode must remain shadow_underwriting")
if ravel.get("vrrc") != 0.0 or ravel.get("vrrc_status") != "not_admitted":
    errors.append("RAVEL VRRC must remain zero/not_admitted in candidate runtime")
for key in ["authoritative", "certification", "underwriting_approval", "capital_facing"]:
    if ravel.get(key) is not False:
        errors.append(f"RAVEL {key} must remain false")
semantic_registry = json.loads((root / "config/semantic_claims_vnext.json").read_text(encoding="utf-8"))
semantic_uids = [item.get("claim_uid") for item in semantic_registry.get("claims", [])]
if not semantic_uids:
    errors.append("semantic claim registry must contain claims")
if any(not uid or not uid.startswith("prometheus.") for uid in semantic_uids):
    errors.append("semantic claim registry contains invalid claim_uid")
if len(semantic_uids) != len(set(semantic_uids)):
    errors.append("semantic claim registry contains duplicate claim_uid")
deprecated = semantic_registry.get("deprecated_claims", [])
if any(item.get("claim_uid") in semantic_uids for item in deprecated):
    errors.append("deprecated claim_uid must not appear among active claims")
active_aliases = {alias for item in semantic_registry.get("claims", []) for alias in item.get("legacy_aliases", [])}
if any(alias in active_aliases for item in deprecated for alias in item.get("legacy_aliases", [])):
    errors.append("alias of a deprecated claim is attached to an active claim_uid")

claims_projection = json.loads((root / "config/claims_registry_projection_v0_1.json").read_text(encoding="utf-8"))
if claims_projection.get("projection_status") != "consumer_projection":
    errors.append("claims registry projection status mismatch")
if claims_projection.get("authoritative") is not False or claims_projection.get("projection_only") is not True:
    errors.append("claims registry projection must remain non-authoritative and projection-only")
src = claims_projection.get("source_registry", {})
if src.get("snapshot_sha256") != "7b2f9b4aec2df0c1ca2262ba27725652b4c119daea754165b623e677e756edb4":
    errors.append("claims registry projection snapshot hash mismatch")
if src.get("merge_commit") != "0151e3f869a819b0833a046f30a92036fe0e3b4d":
    errors.append("claims registry projection merge commit mismatch")
if claims_projection.get("authority_boundary", {}).get("current_canonical_release") != "v1.1.2-genesis":
    errors.append("claims registry projection must preserve current signed canon v1.1.2-genesis")
admitted_projection = claims_projection.get("admitted_mapping_only", [])
if len(admitted_projection) != 8:
    errors.append("claims registry projection must contain exactly 8 admitted mapping-only records")
projection_ids = {item.get("source_claim_id") for item in admitted_projection}
if projection_ids != {"C-001","C-003","C-004","C-006","C-007","C-010","C-011","C-012"}:
    errors.append("claims registry projection admitted source-claim set mismatch")
projection_uids = [item.get("claim_uid") for item in admitted_projection]
if any(not uid or not uid.startswith("prometheus.") for uid in projection_uids) or len(projection_uids) != len(set(projection_uids)):
    errors.append("claims registry projection claim_uid set invalid")
hold_ids = {item.get("source_claim_id") for item in claims_projection.get("holds", [])}
if hold_ids != {"C-002","C-005","C-008","C-009"}:
    errors.append("claims registry projection HOLD set mismatch")
runtime_effect = claims_projection.get("runtime_effect", {})
if any(runtime_effect.get(key) is not False for key in ["enables_behavior","changes_gates","changes_trbk_pathways","changes_pru_value","changes_legal_admission","changes_market_admission"]):
    errors.append("claims registry projection must not enable runtime or admission effects")
if claims_projection.get("semantic_candidate_separation", {}).get("status") != "separate_candidate_not_overridden":
    errors.append("semantic candidate registry must remain separate from signed mapping projection")

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
