# S2 remote publication checklist

- [ ] `.env.local` absent from git and archives.
- [ ] Original packaged credentials rotated.
- [ ] `.env.example` contains placeholders only.
- [ ] Secret scan passes.
- [ ] `scripts/s0_guard.py` passes.
- [ ] `scripts/validate_runtime.py` passes.
- [ ] Python tests pass.
- [ ] Holochain conductor has no wildcard `allowed_origins`.
- [ ] Admin API is not exposed externally.
- [ ] Holochain remains disabled by default.
- [ ] Docker/Compose validation is run on a machine with Docker available.
- [ ] Branch protection and required checks are enabled.
