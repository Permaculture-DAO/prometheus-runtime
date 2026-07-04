# S0 — Freeze & rotate record

Status: `IN PROGRESS`

Applied locally:

- Packaged `.env.local` removed.
- `.env.example` retained as a template only.
- Holochain required version aligned to the machine-observed baseline: `0.6.1`.
- Holochain conductor wildcard origin removed.
- Runtime remains development-only and non-authoritative.

Treat all values from the original packaged `.env.local` as disclosed. Generate fresh secrets before any shared or remote operational use.
