import hashlib
import importlib.util
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[3] / "scripts/build_context_manifest.py"
spec = importlib.util.spec_from_file_location("context_manifest", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def intake(root):
    (root / "INDEX.md").write_text("Context, not canon.\n", encoding="utf-8")
    (root / "source.md").write_bytes(b"Synthetic fixture, not an instruction.\n")
    digest = hashlib.sha256((root / "source.md").read_bytes()).hexdigest()
    (root / "SHA256SUMS.txt").write_text(digest + "  source.md\n", encoding="utf-8")
    return digest


def test_exact_hashes_without_authority_or_content_copy(tmp_path):
    sha = intake(tmp_path)
    result = module.build(tmp_path)
    assert result["sources"] == [{"path": "source.md", "sha256": sha,
        "status": "context_only", "canonical": False, "authority_layer": 7}]
    assert result["authority_promoted"] is False and result["production_admitted"] is False
    assert "Synthetic fixture" not in str(result)
    assert result == module.build(tmp_path)


def test_changed_bytes_fail_closed(tmp_path):
    intake(tmp_path)
    (tmp_path / "source.md").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        module.build(tmp_path)


@pytest.mark.parametrize("entry", ["malformed", "a" * 64 + "  ../source.md",
    "a" * 64 + "  /etc/passwd", "a" * 64 + "  C:\\source.md", "# empty"])
def test_bad_empty_and_escape_entries_rejected(tmp_path, entry):
    intake(tmp_path)
    (tmp_path / "SHA256SUMS.txt").write_text(entry + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        module.build(tmp_path)


def test_duplicates_and_missing_index_fail(tmp_path):
    sha = intake(tmp_path)
    (tmp_path / "SHA256SUMS.txt").write_text((sha + "  source.md\n") * 2, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        module.build(tmp_path)
    intake(tmp_path)
    (tmp_path / "INDEX.md").unlink()
    with pytest.raises(FileNotFoundError):
        module.build(tmp_path)
