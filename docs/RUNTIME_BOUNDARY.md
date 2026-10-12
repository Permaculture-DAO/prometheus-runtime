# Runtime boundary

Current status: `development runtime; production admission gated`.

The runtime may expose local development status endpoints, store non-authoritative evidence candidates, run tests, and prepare evidence packages.

The runtime must not claim certification, validation, investability, market readiness, pilot readiness, or independent assurance; publish `.env.local`; expose Holochain Admin API externally; or use Holochain as a high-frequency telemetry database.

## Stored release boundary

The database stores one release-state record. Startup requires the configured
canonical root and release to match that record. A mismatch fails closed with
`release-state mismatch`, before serving requests; it is not an automatic canon
migration. Review a migration and its backup/restore evidence explicitly, or
choose a distinct database while preserving the original database and provenance.
Changing environment variables alone must not relabel stored evidence. Build-ID
changes do not by themselves change canon; the stored record remains its initial
release receipt rather than being overwritten on restart.
