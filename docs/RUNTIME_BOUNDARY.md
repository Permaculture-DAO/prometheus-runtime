# Runtime boundary

Current status: `development runtime; production admission gated`.

The runtime may expose local development status endpoints, store non-authoritative evidence candidates, run tests, and prepare evidence packages.

The runtime must not claim certification, validation, investability, market readiness, pilot readiness, or independent assurance; publish `.env.local`; expose Holochain Admin API externally; or use Holochain as a high-frequency telemetry database.
