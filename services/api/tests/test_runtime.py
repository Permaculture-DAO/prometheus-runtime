from datetime import datetime, timezone

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
