from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
wildcard_origin_pattern = "allowed_origins:" + r"\s*['\"]\*['\"]"

DENY_REGEXES = {
    "holochain_wildcard_origin": re.compile(wildcard_origin_pattern),
    "old_holochain_required_version": re.compile(r"HOLOCHAIN_REQUIRED_VERSION=0\.6\.2|HOLOCHAIN_REQUIRED_VERSION:-0\.6\.2"),
    "non_placeholder_postgres_password": re.compile(r"POSTGRES_PASSWORD=(?!REPLACE_WITH_STRONG_SECRET)(?=.{20,})[A-Za-z0-9_./+=:-]+"),
    "private_key_material": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

findings = []
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT).as_posix()
    if path.is_file() and path.name == ".env.local":
        findings.append({"rule": "packaged_env_file", "path": rel})
        continue
    if not path.is_file() or path.stat().st_size > 2_000_000:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for rule, pattern in DENY_REGEXES.items():
        if pattern.search(text):
            findings.append({"rule": rule, "path": rel})
    if rel == ".env.example":
        for key in ["POSTGRES_PASSWORD", "WRITE_API_KEY"]:
            if f"{key}=REPLACE_WITH_STRONG_SECRET" not in text:
                findings.append({"rule": "env_example_secret_placeholder_missing", "path": rel, "key": key})

print(json.dumps({"status": "FAIL" if findings else "PASS", "findings": findings}, indent=2))
sys.exit(1 if findings else 0)
