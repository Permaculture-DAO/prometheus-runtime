# M9.3 — review-only candidate (noncanonical)

This directory contains a **disabled-by-default synthetic** Ω gateway. It is a review candidate, NOT a deployment, admissibility authority, Canon amendment, Holochain zome, or new source of rights/capital.

## Integration model

- Import existing M6 modules from the parent `experiments/omega_btrl/src` directory. Do not duplicate M6 source.
- M9/M9.1/M9.2 proof modules are placed under this `m93` subtree only.
- All test credentials are ephemeral. Neither this directory nor the Git patch contains a real bearer token, key, mTLS certificate or runtime state DB.
- The package's importable ASGI `gateway_m92.secure:app` is **closed by default**. The mTLS test uses separate lab fixtures and temporary localhost servers.
- `ELIGIBLE_FOR_REVIEW` is recommendation-only. Never translate it into native `admissible`, Holochain persistence, rights, financial approval or certification.

## Review candidate tests

From `experiments/omega_btrl` in a checkout on M6 head:

```bash
python -m pip install -r m93/requirements-lab.txt
PYTHONPATH=.:m93 python -m pytest m93/tests_m92 m93/tests -q -o addopts=''
PYTHONPATH=.:m93 python -m pytest tests -q -o addopts=''
PYTHONPATH=.:m93 python m93/scripts_m92/loopback_mtls_multiworker.py
```

No `env` containing production credentials is needed. The TLS probe generates short-lived certificates and uses loopback only.

## Release HOLDs

- No independent qualified reviewer, source-custodian admission, or maintainer signing on the exact Git SHA.
- No on-VPS staging operator/account, authorized hostname, isolated IAM/KMS or service inventory.
- Ledger is single-POSIX-host SQLite; coherent rollback requires off-host monotonic audit/WORM proof.
- No certificate-to-token channel binding with real principals; no revocation source or rate limiting.
- No VPS/production deployment or Holochain DNA change is authorized.
