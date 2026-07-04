import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import Settings

@pytest.fixture
def client(tmp_path: Path):
    settings=Settings(database_url=f"sqlite:///{tmp_path/'test.db'}", write_api_key="test-key", document_root=tmp_path, evidence_storage_path=tmp_path/'evidence', claims_register_path=Path('/app/config/claims_register.json'), gate_status_path=Path('/app/config/gate_status.json'), canonical_release_path=Path('/app/config/canonical_release.json'))
    app=create_app(settings)
    with TestClient(app) as c:
        yield c
