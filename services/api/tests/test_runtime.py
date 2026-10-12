from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import Settings


@pytest.mark.parametrize("field", ["canonical_root", "canonical_release"])
def test_release_transition_requires_explicit_migration(tmp_path: Path, field):
    database = tmp_path / "release.db"
    settings = Settings(database_url=f"sqlite:///{database}",
                        evidence_storage_path=tmp_path / "evidence",
                        document_integrity_manifest_path=tmp_path / "absent.json",
                        document_integrity_required=False)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/ready").status_code == 200
    with sqlite3.connect(database) as db:
        before = list(db.iterdump())
    changed = replace(settings, **{field: "TEST-successor-not-ratified"})
    with pytest.raises(RuntimeError, match="release-state mismatch.*reviewed migration"):
        with TestClient(create_app(changed)):
            pytest.fail("mismatched release must not serve requests")
    with sqlite3.connect(database) as db:
        assert list(db.iterdump()) == before
    # A rejected transition must leave the original release usable and idempotent.
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/ready").json()["canonical_root"] == settings.canonical_root
    with sqlite3.connect(database) as db:
        assert list(db.iterdump()) == before

def test_health_and_invariant(client):
    assert client.get('/health/live').status_code == 200
    ready=client.get('/health/ready').json()
    assert ready['statement'] == 'evaluation, not certification'
    assert ready['runtime_stage'] == 'development'
    assert ready['production_admitted'] is False
    status=client.get('/v1/status').json()
    assert status['status_qualifier'] == 'development runtime; production admission gated'
    assert status['audit_convergence_patch'] == 'PROMETHEUS-AUDIT-CONVERGENCE-v7.0.3-20260704'
    assert status['legal_admitted'] is False
    assert status['market_admitted'] is False
    assert status['independent_assurance'] == 'unsigned'


def test_rejected_release_does_not_expand_older_database_schema(tmp_path: Path):
    database = tmp_path / "older.db"
    settings = Settings(database_url=f"sqlite:///{database}",
                        evidence_storage_path=tmp_path / "evidence",
                        document_integrity_manifest_path=tmp_path / "absent.json",
                        document_integrity_required=False)
    with TestClient(create_app(settings)):
        pass
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE audit_log")
        db.commit()
        before = list(db.iterdump())
    changed = replace(settings, canonical_root="TEST-rejected-successor")
    with pytest.raises(RuntimeError, match="release-state mismatch"):
        with TestClient(create_app(changed)):
            pytest.fail("mismatched older schema must not be upgraded")
    with sqlite3.connect(database) as db:
        assert list(db.iterdump()) == before
        assert db.execute("SELECT name FROM sqlite_master WHERE name='audit_log'").fetchone() is None

def test_write_requires_key(client):
    payload={"site_id":"site-1","evidence_type":"soil","source_uri":"file://sample.csv","sha256":"a"*64,"method_id":"soil-v1","captured_at":datetime.now(timezone.utc).isoformat(),"metadata":{}}
    assert client.post('/v1/evidence/candidates',json=payload).status_code == 401
    r=client.post('/v1/evidence/candidates',json=payload,headers={'X-API-Key':'test-key'})
    assert r.status_code == 201
    body=r.json(); assert body['status']=='candidate'; assert body['authoritative'] is False

def test_evaluation_never_certifies(client):
    r=client.post('/v1/runtime/evaluate',json={"claim_id":"C-005","evidence_candidate_ids":[]})
    assert r.status_code == 200
    body=r.json(); assert body['authoritative'] is False; assert body['certification'] is False
