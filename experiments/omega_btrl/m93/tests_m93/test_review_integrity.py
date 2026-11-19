from pathlib import Path
import importlib.util, hashlib,json
ROOT=Path(__file__).resolve().parents[2]
M93=ROOT/'m93'
META=json.loads((M93/'docs/M93_REVIEW_CANDIDATE_METADATA.json').read_text())

def git_blob(raw):
 return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def test_m6_sources_match_both_digests():
 for path,sha in META['source_blob_sha1'].items():
  raw=(ROOT/path).read_bytes()
  assert git_blob(raw)==sha
  assert hashlib.sha256(raw).hexdigest()==META['source_file_sha256'][path]

def test_disallow_duplicate_omega_source():
 assert not (M93/'omega_btrl_snapshot').exists()

def test_runtime_native_not_imported_into_new_gateway():
 raw=(M93/'gateway_m92/secure.py').read_text()
 assert 'from app.main' not in raw
 assert 'import holochain' not in raw
 assert "app = create_m92_gateway()" in raw

def test_declared_policy_boundaries():
 assert META['classification']=='NONCANONICAL_SYNTHETIC_ADVISORY_LAB_ONLY'
 for key in ['github_write_authorized','merged','signed','independent_review','holochain_change','vps_deployment','production_deployed','native_admission_allowed']:
  assert META[key] is False

def test_no_test_private_key_or_ledger_committed():
 for glob in ['*.pem','*.key','*.sqlite','*.sqlite3','*.db','*.p12','*.pfx','*.crt']:
  assert not list(M93.rglob(glob)),glob
