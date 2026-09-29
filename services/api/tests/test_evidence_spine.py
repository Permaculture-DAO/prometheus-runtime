from datetime import datetime, timezone


def package_payload():
    return {
        "package_uid": "ep_test_001",
        "subject_uid": "ohe_sicily_genesis",
        "claim_uids": ["prometheus.runtime.evaluation_not_certification"],
        "place_context_version": "pc-v0.1",
        "system_boundary_version": "sb-v0.1",
        "observation_refs": ["obs_test_001"],
        "method_refs": ["method-test-v0.1"],
        "raw_data_hashes": ["a" * 64],
        "transformed_data_hashes": [],
        "missing_data_statement": "none in synthetic test",
        "adverse_event_statement": "none in synthetic test",
    }


def review_payload():
    return {
        "review_uid": "rev_test_001",
        "reviewer_uid": "reviewer-test-001",
        "scope": "synthetic package structure",
        "coi_status": "independent",
        "subject_refs": ["ep_test_001"],
        "decision": "pass",
        "limitations": "synthetic test only",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "independent_for_scope": True,
    }


def test_p2_2_spine_package_review_and_blocked_admissibility(client):
    headers = {"X-API-Key": "test-key"}

    package = client.post("/v1/evidence/packages", json=package_payload(), headers=headers)
    assert package.status_code == 201
    assert package.json()["authoritative_for_mrv"] is False
    assert package.json()["holochain_commit_status"] == "not_committed"
    assert package.json()["holochain_entry_ref"] is None
    assert len(package.json()["package_hash"]) == 64
    assert len(package.json()["claims_registry_hash"]) == 64

    review = client.post("/v1/reviews", json=review_payload(), headers=headers)
    assert review.status_code == 201
    assert review.json()["authoritative"] is False

    decision = client.post(
        "/v1/admissibility/decisions",
        json={
            "decision_uid": "adm_test_001",
            "subject_uid": "ohe_sicily_genesis",
            "claim_uid": "prometheus.runtime.evaluation_not_certification",
            "evidence_package_refs": ["ep_test_001"],
            "review_attestation_refs": ["rev_test_001"],
            "legal_gate": False,
            "legal_review_ref": None,
            "confidence": 0.90,
            "confidence_threshold": 0.85,
            "require_independent_review": True,
        },
        headers=headers,
    )
    assert decision.status_code == 201
    body = decision.json()
    assert body["decision"] == "blocked"
    assert body["mrv_gate"] is True
    assert body["legal_gate"] is False
    assert body["authoritative"] is False
    assert body["certification"] is False
    assert body["authority_boundary"] == "admissibility_only_no_value"

    status = client.get("/v1/evidence/spine/status")
    assert status.status_code == 200
    s = status.json()
    assert s["stage"] == "P2.2-candidate"
    assert s["counts"]["evidence_packages"] == 1
    assert s["counts"]["review_attestations"] == 1
    assert s["counts"]["admissibility_decisions"] == 1
    assert s["certification"] is False


def test_conflicted_reviewer_cannot_pass(client):
    headers = {"X-API-Key": "test-key"}
    payload = review_payload()
    payload["review_uid"] = "rev_test_conflict"
    payload["coi_status"] = "conflicted"
    payload["independent_for_scope"] = False
    response = client.post("/v1/reviews", json=payload, headers=headers)
    assert response.status_code == 422


def test_legacy_claim_id_rejected_at_package_boundary(client):
    headers = {"X-API-Key": "test-key"}
    payload = package_payload()
    payload["package_uid"] = "ep_test_legacy"
    payload["claim_uids"] = ["C-013"]
    response = client.post("/v1/evidence/packages", json=payload, headers=headers)
    assert response.status_code == 422
