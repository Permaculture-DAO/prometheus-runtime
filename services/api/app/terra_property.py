"""RC2 native runtime property adapter: offline synthetic reference packaging only."""
from .terra_property_core import evaluate, digest
from .normalization import STATEMENT
from .evidence_batch import (build_synthetic_evidence_batch, batch_hash,
                             simulated_holochain_reference_hash,
                             verify_synthetic_evidence_batch, sha256_json)

VERSION = "0.1.0-rc.2"
ADAPTER_ID = "terra_property_mock"
ENVELOPE_FIELDS = {"adapter_id", "synthetic_only", "live_endpoint", "statement", "observations"}

def adapter_descriptor():
    return {"adapter_id": ADAPTER_ID, "source_system": "terra_property_mock",
            "enabled_by_default": False, "fixture_only": True, "endpoint_url": None,
            "live_ingestion_admitted": False, "statement": STATEMENT}

def run_fixture(fixture):
    if not isinstance(fixture, dict) or set(fixture) != ENVELOPE_FIELDS:
        raise ValueError("invalid property fixture envelope")
    if (fixture["adapter_id"] != ADAPTER_ID or fixture["synthetic_only"] is not True
            or fixture["live_endpoint"] is not None or fixture["statement"] != STATEMENT):
        raise ValueError("offline synthetic property adapter only")
    report = evaluate(fixture["observations"])
    events = []
    for observation in report["observations"]:
        event = {
            "event_type": "property_observation_synthetic",
            "source_system": ADAPTER_ID, "mode": "TEST",
            "method_version": VERSION, "observation": observation,
            "authoritative_for_mrv": False, "statement": STATEMENT,
            "holochain": {"batch_hash": None, "entry_ref": None}
        }
        event["event_id"] = "evt_" + sha256_json(event)
        events.append(event)
    events.sort(key=lambda x: x["event_id"])
    # Use the existing S6 builder and hash protocol, but namespace the batch
    # away from the fixed historical sensor fixture identifier.
    batch = build_synthetic_evidence_batch(events)
    batch["batch_id"] = "batch_terra_" + digest([e["event_id"] for e in events])
    # Fixed synthetic packaging epoch, not a claim of actual retrieval time.
    batch["created_at"] = "2026-11-24T00:00:00Z"
    batch["batch_hash"] = batch_hash(batch)
    batch["holochain_reference"]["reference_hash"] = simulated_holochain_reference_hash(
        batch["batch_id"], batch["batch_hash"])
    errors = verify_synthetic_evidence_batch(batch)
    if errors:
        raise ValueError("native S6 verifier rejected batch: " + "; ".join(errors))
    output = {"version": VERSION, "mode": "TEST", "state": "HOLD",
              "adapter": adapter_descriptor(), "report": report, "events": events,
              "batch": batch, "evidence_spine_write": False, "holochain_commit": False,
              "production_admitted": False, "real_ingestion_enabled": False,
              "legal_authority": False, "capital_authority": False}
    output["semantic_hash"] = digest(output)
    return output
