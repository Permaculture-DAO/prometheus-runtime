# PROMETHEUS Development Runtime — Core v7.0.1 / Patch documentale v7.0.2

> **Qualifica obbligatoria:** development runtime; production admission gated.

## Avvio locale immediato

Prerequisito: Docker Desktop o Docker Engine con Docker Compose v2.

Windows PowerShell:

```powershell
cd 09_RUNTIME_DEPLOYMENT
.\scripts\start.ps1
```

Linux/macOS:

```bash
cd 09_RUNTIME_DEPLOYMENT
./scripts/start.sh
```

Aprire `http://localhost:8080`. Il core avvia PostgreSQL, FastAPI e Nginx. L’interfaccia espone esplicitamente:

- `runtime_stage = development`;
- `production_admitted = false`;
- `legal_admitted = false`;
- `market_admitted = false`;
- `independent_assurance = unsigned`;
- `evaluation, not certification`.

Il runtime verifica gli hash dei quattro documenti canonici montati, conserva soltanto **evidence candidates** e non certifica evidenze, PRU, RAP, diritti, pagamenti, capitale o ammissione di produzione.

## Verifica

```bash
python scripts/validate_runtime.py
cd services/api && PYTHONPATH=. pytest -q
```

I report delle prove sono in `validation/`.

## Variabili d’ambiente

- `.env.local`: valori casuali per un avvio esclusivamente locale;
- `.env.example`: template senza segreti;
- tutte le opzioni P1-P4 e Holochain sono `false`;
- `DOCUMENT_INTEGRITY_REQUIRED=true` rende il core fail-closed se i documenti canonici non corrispondono al manifest SHA-256.

Ruotare password e API key prima di ogni ambiente condiviso. Non committare `.env.local`.

## Holochain

Il profilo Holochain è preparato ma disabilitato. Non è inclusa una DNA/hApp ammessa: bundle firmato, hash, test, security review e Gate Review restano condizioni necessarie.

## Arresto

```powershell
.\scripts\stop.ps1
```

oppure:

```bash
./scripts/stop.sh
```


## Patch v7.0.3 Audit Convergence

Il runtime resta di sviluppo. Il percorso critico corrente è G1 Executable Controls seguito da G2 Independent Pilot Readiness. Sono vietate formulazioni che implichino approvazione o readiness da parte di istituzioni nominate. Production, legal e market admission restano false.
