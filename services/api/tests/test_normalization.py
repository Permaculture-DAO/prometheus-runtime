from app.normalization import canonical_event_id, normalize_fixture


def test_s5_normalization_accepts_synthetic_ttn_fixture():
    fixture = {
        "fixture_type": "synthetic_ttn_uplink",
        "synthetic_only": True,
        "live_endpoint": None,
        "source_event_id": "ttn-synthetic-uplink-0001",
        "device_id": "dev_synthetic_soil_001",
        "observed_at": "2026-07-04T17:00:00Z",
        "received_at": "2026-07-04T17:00:02Z",
        "payload_shape": {
            "frm_payload": "U1lOVEhFVElDX1BBWUxPQUQ=",
            "f_port": 1,
            "decoded_payload": {"soil_moisture_percent_vwc": 21.5},
        },
        "statement": "evaluation, not certification",
    }
    event = normalize_fixture("ttn_mock", fixture)
    assert event["event_type"] == "sensor_observation"
    assert event["source_system"] == "ttn"
    assert event["qa"]["quality_status"] == "synthetic"
    assert event["authoritative_for_mrv"] is False
    assert event["statement"] == "evaluation, not certification"
    assert event["event_id"] == canonical_event_id(event)


def test_s5_normalization_rejects_live_fixture():
    fixture = {
        "synthetic_only": False,
        "live_endpoint": "https://example.invalid/live",
        "statement": "evaluation, not certification",
    }
    try:
        normalize_fixture("ttn_mock", fixture)
    except ValueError as exc:
        assert "synthetic fixtures only" in str(exc)
    else:
        raise AssertionError("live fixture was not rejected")
