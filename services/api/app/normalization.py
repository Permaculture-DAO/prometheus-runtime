from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime


STATEMENT = "evaluation, not certification"
METHOD_VERSION = "method-v0.1.0-draft"
DECODER_VERSION = "v0.1.0-draft"


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(payload: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def canonical_event_id(event: dict) -> str:
    material = "\n".join(
        [
            event["source_system"],
            event["source_event_id"],
            event["device_id"],
            event["sensor_id"],
            event["observed_at"],
            event["raw_payload_sha256"],
            event["decoder_id"],
            event["decoder_version"],
        ]
    )
    return "evt_" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def base_event(
    *,
    event_type: str,
    source_system: str,
    source_event_id: str,
    device_id: str,
    sensor_id: str,
    observed_at: str,
    received_at: str,
    decoder_id: str,
    raw_payload: dict,
    normalized: dict,
    raw_uri: str,
    normalized_uri: str,
) -> dict:
    event = {
        "event_id": "",
        "event_type": event_type,
        "source_system": source_system,
        "source_event_id": source_event_id,
        "device_id": device_id,
        "sensor_id": sensor_id,
        "observed_at": observed_at,
        "received_at": received_at,
        "decoder_id": decoder_id,
        "decoder_version": DECODER_VERSION,
        "method_version": METHOD_VERSION,
        "raw_payload_sha256": sha256_json(raw_payload),
        "normalized": normalized,
        "qa": {
            "quality_status": "synthetic",
            "duplicate_status": "not_checked",
            "gap_status": "not_applicable",
            "out_of_order": False,
        },
        "storage": {
            "raw_uri": raw_uri,
            "normalized_uri": normalized_uri,
            "retention_policy": "development_ephemeral",
        },
        "holochain": {
            "commit_policy": "commit_batch_reference_only",
            "batch_hash": None,
            "entry_ref": None,
        },
        "authoritative_for_mrv": False,
        "statement": STATEMENT,
    }
    event["event_id"] = canonical_event_id(event)
    return event


def normalize_ttn_mock(fixture: dict) -> dict:
    payload_shape = deepcopy(fixture["payload_shape"])
    return base_event(
        event_type="sensor_observation",
        source_system="ttn",
        source_event_id=fixture["source_event_id"],
        device_id=fixture["device_id"],
        sensor_id="sen_synthetic_soil_moisture_001",
        observed_at=fixture["observed_at"],
        received_at=fixture["received_at"],
        decoder_id="dec_synthetic_soil_vwc",
        raw_payload=payload_shape,
        normalized={
            "measurement_type": "soil_moisture",
            "value": payload_shape["decoded_payload"]["soil_moisture_percent_vwc"],
            "unit": "percent_vwc",
        },
        raw_uri="memory://synthetic/ttn/uplink-0001/raw",
        normalized_uri="memory://synthetic/ttn/uplink-0001/normalized",
    )


def normalize_manual_mock(fixture: dict) -> dict:
    return base_event(
        event_type="manual_observation",
        source_system="manual",
        source_event_id=fixture["source_event_id"],
        device_id="dev_synthetic_manual_001",
        sensor_id="sen_synthetic_manual_soil_moisture_001",
        observed_at=fixture["observed_at"],
        received_at=fixture["observed_at"],
        decoder_id="dec_synthetic_manual_observation",
        raw_payload={"observer_ref": fixture["observer_ref"], "observation": fixture["observation"]},
        normalized=fixture["observation"],
        raw_uri="memory://synthetic/manual/observation-0001/raw",
        normalized_uri="memory://synthetic/manual/observation-0001/normalized",
    )


def normalize_lab_mock(fixture: dict) -> dict:
    return base_event(
        event_type="lab_result",
        source_system="lab",
        source_event_id=fixture["source_event_id"],
        device_id="dev_synthetic_lab_001",
        sensor_id="sen_synthetic_lab_som_001",
        observed_at=fixture["observed_at"],
        received_at=fixture["observed_at"],
        decoder_id="dec_synthetic_lab_result",
        raw_payload={"sample_id": fixture["sample_id"], "result": fixture["result"]},
        normalized=fixture["result"],
        raw_uri="memory://synthetic/lab/result-0001/raw",
        normalized_uri="memory://synthetic/lab/result-0001/normalized",
    )


NORMALIZERS = {
    "ttn_mock": normalize_ttn_mock,
    "manual_mock": normalize_manual_mock,
    "lab_mock": normalize_lab_mock,
}


def normalize_fixture(adapter_id: str, fixture: dict) -> dict:
    try:
        normalizer = NORMALIZERS[adapter_id]
    except KeyError as exc:
        raise ValueError(f"unknown adapter: {adapter_id}") from exc
    if fixture.get("synthetic_only") is not True:
        raise ValueError("S5 normalization accepts synthetic fixtures only")
    if fixture.get("live_endpoint") is not None:
        raise ValueError("S5 normalization rejects live endpoints")
    if fixture.get("statement") != STATEMENT:
        raise ValueError("S5 normalization requires non-certification statement")
    return normalizer(fixture)
