"""Keep dependency monitoring and legacy install entry points in sync."""

from pathlib import Path
import re


API = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[^\s]+$")


def lines(name):
    return [
        line.strip()
        for line in (API / name).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def effective_pins(name, seen=()):
    assert name not in seen, "cyclic requirements include"
    pins = []
    for line in lines(name):
        if line.startswith("-r "):
            child = line[3:]
            assert Path(child).name == child, "include must stay in the API directory"
            pins.extend(effective_pins(child, (*seen, name)))
        else:
            assert PIN.fullmatch(line), "dependency must remain exactly pinned"
            pins.append(line)
    assert len(pins) == len(set(pins)), "duplicate dependency pins"
    return pins


def test_production_manifest_is_discoverable_and_exactly_pinned():
    pins = effective_pins("requirements.txt")
    assert {pin.split("==")[0] for pin in pins} == {
        "fastapi", "uvicorn[standard]", "pydantic", "sqlalchemy", "psycopg[binary]",
    }


def test_dev_manifest_includes_discoverable_production_pins():
    assert lines("requirements-dev.txt")[0] == "-r requirements.txt"
    assert set(effective_pins("requirements.txt")) < set(effective_pins("requirements-dev.txt"))


def test_legacy_lock_entry_points_resolve_to_the_same_pins():
    for legacy, canonical in (
        ("requirements.lock", "requirements.txt"),
        ("requirements-dev.lock", "requirements-dev.txt"),
    ):
        assert lines(legacy) == [f"-r {canonical}"]
        assert effective_pins(legacy) == effective_pins(canonical)


def test_container_copies_and_installs_the_canonical_production_manifest():
    dockerfile = (API / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY services/api/requirements.txt ./" in dockerfile
    assert "RUN pip install --requirement requirements.txt" in dockerfile
    assert "requirements-dev" not in dockerfile
