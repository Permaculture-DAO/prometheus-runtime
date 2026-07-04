from __future__ import annotations

import hashlib
import json
from copy import deepcopy


STATEMENT = "evaluation, not certification"
SYNTHETIC_BATCH_ID = "batch_synthetic_20260704_0001"
SYNTHETIC_BATCH_CREATED_AT = "2026-07-04T18:45:00Z"


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(payload: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def event_reference(event: dict) -> dict:
    return {
        "event_id": event["event_id"],
        "source_system": event["source_system"],
        "event_type": event["event_type"],
        "event_sha256": sha256_json(event),
    }


def event_ids_sha256(events: list[dict]) -> str:
    material = "\n".join(sorted(event["event_id"] for event in events))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def batch_hash(batch_without_hash: dict) -> str:
    material = deepcopy(batch_without_hash)
    material["batch_hash"] = ""
    material.setdefault("holochain_reference", {})["reference_hash"] = ""
    return sha256_json(material)


def simulated_holochain_reference_hash(batch_id: str, hash_value: str) -> str:
    return "hcref_" + hashlib.sha256(f"{batch_id}\n{hash_value}".encode("utf-8")).hexdigest()


def build_synthetic_evidence_batch(events: list[dict]) -> dict:
    if not events:
        raise ValueError("synthetic evidence batch requires at least one event")
    for event in events:
        if event.get("authoritative_for_mrv") is not False:
            raise ValueError("S6 batches accept non-authoritative events only")
        if event.get("statement") != STATEMENT:
            raise ValueError("S6 batches require non-certification events")
        if event.get("holochain", {}).get("batch_hash") is not None or event.get("holochain", {}).get("entry_ref") is not None:
            raise ValueError("S6 synthetic batches reject pre-existing Holochain commitments")

    references = sorted((event_reference(event) for event in events), key=lambda item: item["event_id"])
    batch = {
        "batch_id": SYNTHETIC_BATCH_ID,
        "batch_type": "synthetic_evidence_reference",
        "source_stage": "S6 draft",
        "created_at": SYNTHETIC_BATCH_CREATED_AT,
        "event_count": len(references),
        "events": references,
        "event_ids_sha256": event_ids_sha256(events),
        "batch_hash": "",
        "holochain_reference": {
            "mode": "simulated_reference_only",
            "commit_performed": False,
            "entry_ref": None,
            "reference_hash": "",
        },
        "authoritative_for_mrv": False,
        "statement": STATEMENT,
    }
    hash_value = batch_hash(batch)
    batch["batch_hash"] = hash_value
    batch["holochain_reference"]["reference_hash"] = simulated_holochain_reference_hash(batch["batch_id"], hash_value)
    return batch


def verify_synthetic_evidence_batch(batch: dict) -> list[str]:
    errors: list[str] = []
    if "holochain_reference" not in batch:
        errors.append("batch must include holochain_reference")
        return errors
    if batch.get("authoritative_for_mrv") is not False:
        errors.append("batch must remain non-authoritative for MRV")
    if batch.get("statement") != STATEMENT:
        errors.append("batch must retain non-certification statement")
    if batch.get("holochain_reference", {}).get("commit_performed") is not False:
        errors.append("batch must not claim a Holochain commit")
    if batch.get("holochain_reference", {}).get("entry_ref") is not None:
        errors.append("batch must not include a Holochain entry_ref")
    expected_hash = batch_hash(batch)
    if batch.get("batch_hash") != expected_hash:
        errors.append("batch_hash mismatch")
    expected_reference_hash = simulated_holochain_reference_hash(batch.get("batch_id", ""), batch.get("batch_hash", ""))
    if batch.get("holochain_reference", {}).get("reference_hash") != expected_reference_hash:
        errors.append("simulated Holochain reference hash mismatch")
    if batch.get("event_count") != len(batch.get("events", [])):
        errors.append("event_count mismatch")
    return errors
