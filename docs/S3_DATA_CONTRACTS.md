# S3 — Data contracts

Status: `DRAFT`

S3 defines the minimum contracts required before any TTN, lab, manual, or external-world data can enter the runtime.

The current repository state admits synthetic fixtures only.

## Contracts

- `contracts/device.registry.schema.json`
- `contracts/decoder.registry.schema.json`
- `contracts/sensor.event.schema.json`
- `contracts/event_identity.md`

## Boundary

The contracts preserve the v7.0.4 roadmap boundary:

```text
sensor → raw landing → decoder/version → QA/QC → storage → evidence batch → Holochain provenance
```

Holochain stores provenance and batch references. It is not the raw telemetry database.

## No-go until later gates

Do not connect live TTN applications, lab results, irrigation automation, or production Holochain commitments until S4/S6/S8 checks exist and pass.

