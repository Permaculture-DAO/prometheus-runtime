"""Byte-verified context inventory only; no authority promotion or content import.

Reads an existing dated inbox INDEX.md and SHA256SUMS.txt. Embedded instructions,
self-labels and financial narratives are not parsed or acted on. Fresh output only.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def build(root: Path) -> dict:
    root = root.resolve(strict=True)
    index = root / "INDEX.md"
    sums = root / "SHA256SUMS.txt"
    for path in (index, sums):
        if not path.resolve(strict=True).is_relative_to(root):
            raise ValueError("context metadata escapes intake root")
    index_bytes, sums_bytes = index.read_bytes(), sums.read_bytes()
    sources, names = [], set()
    for line in sums_bytes.decode("utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})[ \t]+\*?(.+)", line)
        if not match:
            raise ValueError("malformed source hash entry")
        expected, name = match.groups()
        relative = PurePosixPath(name.replace("\\", "/"))
        if relative.is_absolute() or ":" in name or ".." in relative.parts:
            raise ValueError("unsafe source path")
        portable = relative.as_posix()
        if portable.casefold() in names:
            raise ValueError("duplicate source path")
        names.add(portable.casefold())
        path = (root / portable).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("source escapes intake root or is not a file")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected.lower():
            raise ValueError("source content hash mismatch: " + portable)
        sources.append({"path": portable, "sha256": digest, "status": "context_only",
                        "canonical": False, "authority_layer": 7})
    if not 1 <= len(sources) <= 1000:
        raise ValueError("1..1000 verified context entries required")
    return {"method_version": "context-manifest-v0.1", "intake_id": root.name,
            "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
            "source_sums_sha256": hashlib.sha256(sums_bytes).hexdigest(),
            "sources": sorted(sources, key=lambda row: row["path"]),
            "verification": "bytes_match_declared_hashes_not_source_truth",
            "authority_promoted": False, "production_admitted": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build(args.intake)
    with args.output.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(result, file, sort_keys=True, indent=2, allow_nan=False)
        file.write("\n")
    print(json.dumps({"status": "PASS", "sources": len(result["sources"]),
                      "authority_promoted": False}))
