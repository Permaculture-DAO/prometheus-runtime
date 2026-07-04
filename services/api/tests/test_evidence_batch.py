import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.evidence_batch import build_synthetic_evidence_batch, verify_synthetic_evidence_batch
from app.main import create_app
from app.settings import Settings


def synthetic_event(event_id: str, source_system: str = "ttn") -> dict:
    return {
        "event_id": event_id,
        "event_type": "sensor_observation",
        "source_system": source_system,
        "source_event_id": f"{source_system}-synthetic-0001",
        "device_id": f"dev_synthetic_{source_system}_001",
        "sensor_id": f"sen_synthetic_{source_system}_001",
        "observed_at": "2026-07-04T17:00:00Z",
        "received_at": "2026-07-04T17:00:02Z",
        "decoder_id": f"dec_synthetic_{source_system}",
        "decoder_version": "v0.1.0-draft",
        "method_version": "method-v0.1.0-draft",
        "raw_payload_sha256": "a" * 64,
        "normalized": {"measurement_type": "soil_moisture", "value": 21.5, "unit": "percent_vwc"},
        "qa": {
            "quality_status": "synthetic",
            "duplicate_status": "not_checked",
            "gap_status": "not_applicable",
            "out_of_order": False,
        },
        "storage": {
            "raw_uri": "memory://synthetic/raw",
            "normalized_uri": "memory://synthetic/normalized",
            "retention_policy": "development_ephemeral",
        },
        "holochain": {"commit_policy": "commit_batch_reference_only", "batch_hash": None, "entry_ref": None},
        "authoritative_for_mrv": False,
        "statement": "evaluation, not certification",
    }


def test_s6_builds_non_authoritative_reference_batch():
    batch = build_synthetic_evidence_batch(
        [
            synthetic_event("evt_" + "b" * 64, "manual"),
            synthetic_event("evt_" + "a" * 64, "ttn"),
        ]
    )
    assert batch["source_stage"] == "S6 draft"
    assert batch["event_count"] == 2
    assert batch["authoritative_for_mrv"] is False
    assert batch["statement"] == "evaluation, not certification"
    assert batch["holochain_reference"]["commit_performed"] is False
    assert batch["holochain_reference"]["entry_ref"] is None
    assert batch["holochain_reference"]["reference_hash"].startswith("hcref_")
    assert [event["event_id"] for event in batch["events"]] == sorted(event["event_id"] for event in batch["events"])
    assert verify_synthetic_evidence_batch(batch) == []


def test_s6_rejects_authoritative_events():
    event = synthetic_event("evt_" + "c" * 64)
    event["authoritative_for_mrv"] = True
    try:
        build_synthetic_evidence_batch([event])
    except ValueError as exc:
        assert "non-authoritative events only" in str(exc)
    else:
        raise AssertionError("authoritative event was not rejected")


def test_s6_synthetic_batch_endpoint_is_read_only(tmp_path: Path):
    batch = build_synthetic_evidence_batch([synthetic_event("evt_" + "d" * 64)])
    batch_path = tmp_path / "synthetic_batch_0001.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    settings = Settings(
        database_url=f"sqlite:///{tmp_path/'test.db'}",
        write_api_key="test-key",
        document_root=tmp_path,
        evidence_storage_path=tmp_path / "evidence",
        claims_register_path=Path("/app/config/claims_register.json"),
        gate_status_path=Path("/app/config/gate_status.json"),
        canonical_release_path=Path("/app/config/canonical_release.json"),
        synthetic_evidence_batch_path=batch_path,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/v1/evidence/batches/synthetic")
    assert response.status_code == 200
    body = response.json()
    assert body["batch_hash"] == batch["batch_hash"]
    assert body["authoritative_for_mrv"] is False
    assert body["holochain_reference"]["commit_performed"] is False
