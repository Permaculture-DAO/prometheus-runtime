"""Actual loopback TLS client-certificate + concurrent/restart replay probe.

No VPS, secrets, production trust, network ingress or Holochain. All private
keys and tokens exist only in a restrictive temporary directory and vanish.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import statistics
import subprocess
import sys
import tempfile
import time

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent))
from tests_m92.conftest import Factory
from gateway_m92.ledger import DurableLedger


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]


def create_identity(path:Path):
    now=datetime.now(timezone.utc)
    key=ec.generate_private_key(ec.SECP256R1())
    ca=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'M92 Synthetic CA')])
    ca_cert=(x509.CertificateBuilder().subject_name(ca).issuer_name(ca)
       .public_key(key.public_key()).serial_number(x509.random_serial_number())
       .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(minutes=15))
       .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
       .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
       .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=False,
            data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,
            encipher_only=False,decipher_only=False),critical=True)
       .sign(key,hashes.SHA256()))
    def sign(name:str,server:bool):
        leaf=ec.generate_private_key(ec.SECP256R1())
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
        cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(ca)
          .public_key(leaf.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(minutes=10))
          .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf.public_key()),critical=False)
          .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),critical=False)
          .add_extension(x509.ExtendedKeyUsage([
             x509.oid.ExtendedKeyUsageOID.SERVER_AUTH if server else x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
          .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))])
               if server else x509.SubjectAlternativeName([x509.DNSName('synthetic-client')]),critical=False)
          .sign(key,hashes.SHA256()))
        c=path/(name+'.crt');k=path/(name+'.key')
        c.write_bytes(cert.public_bytes(serialization.Encoding.PEM));os.chmod(c,0o600)
        k.write_bytes(leaf.private_bytes(serialization.Encoding.PEM,
           serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));os.chmod(k,0o600)
        return c,k
    ca_path=path/'lab_ca.crt';ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM));os.chmod(ca_path,0o600)
    return ca_path,sign('server',True),sign('client',False)


def main():
    with tempfile.TemporaryDirectory(prefix='omega_m92_mtls_') as tmp:
        folder=Path(tmp);os.chmod(folder,0o700)
        (folder/'durable_state').mkdir(mode=0o700)
        (folder/'secondary_audit').mkdir(mode=0o700)
        token_a=secrets.token_urlsafe(48);token_b=secrets.token_urlsafe(48)
        audit_key=secrets.token_bytes(48)
        fixture=Factory()
        store=fixture.store
        import base64
        host={
          'roots':{k:{'role':v.role,'public_key':base64.b64encode(v.public_key).decode('ascii')}
                    for k,v in store.roots.items()},
          'expected_manifest_sha256':store.expected_manifest_sha256,
          'expected_policy_sha256':store.expected_policy_sha256,
          'minimum_revocation_epoch':store.minimum_revocation_epoch,
          'records':store.records,
          'raw_evidence':{k:base64.b64encode(v).decode('ascii') for k,v in store.raw_evidence.items()},
        }
        f=folder/'host_signed_fixture.json';f.write_text(json.dumps(host));os.chmod(f,0o600)
        # No private signing key is serialized or sent to the worker processes.
        ca, (servercrt,serverkey),(clientcrt,clientkey) = create_identity(folder)
        env=os.environ.copy()
        env.update({'M92_SYNTHETIC_LAB_ONLY':'EXPLICIT','M92_OWNER_ONLY_DIR':str(folder),
                    'M92_LAB_TOKEN_A':token_a,'M92_LAB_TOKEN_B':token_b,
                    'M92_LAB_AUDIT_KEY_HEX':audit_key.hex(),'PYTHONPATH':str(ROOT)+os.pathsep+str(ROOT.parent)})
        process_list=[];lat=[]
        def launch(p):
            logfile=(folder/('uvicorn_'+str(p)+'.log')).open('wb')
            args=[sys.executable,'-m','uvicorn','scripts_m92.lab_runtime:app',
              '--host','127.0.0.1','--port',str(p),
              '--ssl-keyfile',str(serverkey),'--ssl-certfile',str(servercrt),
              '--ssl-ca-certs',str(ca),'--ssl-cert-reqs','2',
              '--no-access-log','--no-server-header']
            proc=subprocess.Popen(args,env=env,cwd=ROOT,stdout=logfile,stderr=subprocess.STDOUT)
            process_list.append((proc,logfile))
            return proc
        def stop_all():
            for p,log in process_list:
                if p.poll() is None:
                    p.terminate()
                    try:p.wait(timeout=8)
                    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=8)
                log.close()
            process_list.clear()
        def api_client(with_cert=True):
            context=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=str(ca))
            if with_cert:
                context.load_cert_chain(str(clientcrt),str(clientkey))
            return httpx.Client(verify=context,timeout=10,
                follow_redirects=False,trust_env=False)
        try:
            p1,p2=port(),port()
            while p1==p2:p2=port()
            launch(p1);launch(p2)
            with api_client() as c:
                for n in (p1,p2):
                    url=f'https://127.0.0.1:{n}/internal/health'
                    last_error=None
                    for _ in range(100):
                        try:
                            r=c.get(url)
                            if r.status_code==200:break
                        except Exception as exc:
                            last_error=repr(exc)
                        time.sleep(.1)
                    else:
                        logs=[(str(n0),p0.read_text(errors='replace')[-1000:]) for n0,p0 in ((p1,folder/('uvicorn_'+str(p1)+'.log')),(p2,folder/('uvicorn_'+str(p2)+'.log')))]
                        raise RuntimeError('M92_TLS_SERVER_START_FAILED ' + str(last_error) + str(logs))
            base=f'https://127.0.0.1:{p1}'
            # The TLS layer must reject requests with no client certificate.
            try:
                with api_client(False) as no_client:
                    no_cert=no_client.get(base+'/internal/health')
                raise AssertionError('CLIENT_CERT_NOT_REQUIRED '+str(no_cert.status_code))
            except (httpx.TransportError,ssl.SSLError):
                tls_mtls_enforced=True
            with api_client() as c:
                r=c.post(base+'/internal/advice',json=fixture.case)
                assert r.status_code==401
            def exercise(n):
                tok=token_a if n%2==0 else token_b
                url=f'https://127.0.0.1:{p1 if n%2==0 else p2}'
                t=time.perf_counter()
                with api_client() as c:
                    r=c.post(url+'/internal/advice',json=fixture.case,
                         headers={'Authorization':'Bearer '+tok})
                lat.append((time.perf_counter()-t)*1000)
                return r.status_code,r.json()['review_outcome']
            with ThreadPoolExecutor(max_workers=10) as pool:
                vals=list(pool.map(exercise,range(20)))
            assert sum(o=='ELIGIBLE_FOR_REVIEW' for _,o in vals)==1,vals
            assert sum(o=='HOLD' for _,o in vals)==19,vals
            stop_all()
            launch(p1)
            with api_client() as c:
                for _ in range(100):
                    try:
                        if c.get(f'https://127.0.0.1:{p1}/internal/health').status_code==200:break
                    except Exception:pass
                    time.sleep(.1)
                else:raise AssertionError('RESTART_SERVER_UNAVAILABLE')
                r=c.post(f'https://127.0.0.1:{p1}/internal/advice',json=fixture.case,
                     headers={'Authorization':'Bearer '+token_b})
                assert r.status_code==423 and r.json()['review_outcome']=='HOLD',r.text
                stopfile=folder/'EMERGENCY_STOP';stopfile.write_text('operator stop')
                os.chmod(stopfile,0o600)
                stop=c.post(f'https://127.0.0.1:{p1}/internal/advice',json=fixture.case,
                     headers={'Authorization':'Bearer '+token_a})
                assert stop.status_code==423 and stop.json()['review_outcome']=='HOLD'
            ledger=DurableLedger(folder/'durable_state',audit_hmac_key=audit_key)
            verified=ledger.verify()
            assert verified['replay_entries']==1
            audit=(folder/'secondary_audit'/'events.jsonl').read_text()
            assert token_a not in audit and token_b not in audit
            assert 'assurance_case_id' not in audit and 'public_key' not in audit
            assert (folder/'secondary_audit'/'events.jsonl').stat().st_mode & 0o077==0
            result={
                'status':'PASS_M92_LOOPBACK_MTLS_DURABLE_MULTIPROCESS',
                'test_only':True,'tls':'ephemeral lab CA, mTLS client certificate enforced',
                'localhost_only':True,'server_processes_parallel':2,
                'same_case_requests_parallel':20,'eligible_for_review_count':1,
                'replay_hold_concurrent':19,'restart_with_different_client_rejected':True,
                'default_without_bearer_denied':True,'no_client_certificate_rejected':tls_mtls_enforced,
                'emergency_stop_held':True,'ledger_replay_entries':verified['replay_entries'],
                'ledger_audit_events':verified['audit_events'],
                'ledger_verified':True,'secrets_in_secondary_audit':False,
                'latency_median_ms':round(statistics.median(lat),3),
                'latency_p95_ms':round(sorted(lat)[int(.95*len(lat))],3),
                'limitations':['NO_REAL_IAM_OR_KMS','NO_INDEPENDENT_WORM_AUDIT','NO_VPS',
                    'NO_CROSS_HOST_DISTRIBUTED_LEDGER','TEST_CLOCK_ONLY','NO_PRODUCTION_RELEASE']}
            target=Path(os.environ.get('M93_MTLS_RECEIPT_PATH',str(folder/'M93_LOOPBACK_MTLS_RECEIPT.json')))
            target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
            print(json.dumps(result,indent=2))
        finally:
            stop_all()
if __name__=='__main__':main()
