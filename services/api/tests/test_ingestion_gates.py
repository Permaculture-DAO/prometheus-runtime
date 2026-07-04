def test_s4_adapters_are_discoverable_but_closed(client):
    response = client.get("/v1/ingestion/adapters")
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "S4 draft"
    assert body["live_ingestion_admitted"] is False
    assert body["ingestion_enabled"] is False
    assert body["production_admitted"] is False
    assert {adapter["adapter_id"] for adapter in body["adapters"]} == {"ttn_mock", "manual_mock", "lab_mock"}
    assert all(adapter["enabled"] is False for adapter in body["adapters"])
    assert all(adapter["fixture_only"] is True for adapter in body["adapters"])


def test_s4_intake_requires_key_and_stays_locked(client):
    payload = {"synthetic_only": True}

    unauthorized = client.post("/v1/ingestion/intake/ttn_mock", json=payload)
    assert unauthorized.status_code == 401

    locked = client.post("/v1/ingestion/intake/ttn_mock", json=payload, headers={"X-API-Key": "test-key"})
    assert locked.status_code == 423
    detail = locked.json()["detail"]
    assert detail["status"] == "locked"
    assert detail["adapter_id"] == "ttn_mock"
    assert detail["statement"] == "evaluation, not certification"


def test_s4_unknown_adapter_is_not_admitted(client):
    response = client.post(
        "/v1/ingestion/intake/live_unknown",
        json={"synthetic_only": True},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 404
