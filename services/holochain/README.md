# Holochain conductor profile

This service is isolated behind the `holochain` Compose profile and is **disabled by default**. It uses the official Holonix 0.6 line, verifies the configured Holochain version at startup, and exposes only the conductor administration interface inside the Compose network. A production/pilot hApp, DNA hash, agent keys and signed admission evidence are intentionally not fabricated by this package.

Start only after the Runtime Admission Matrix and Gate Review permit it:

```bash
docker compose --profile holochain up --build
```
