# Event identity policy

Status: `S3 draft`

`event_id` is deterministic and content-addressed:

```text
evt_ + sha256(
  source_system + "\n" +
  source_event_id + "\n" +
  device_id + "\n" +
  sensor_id + "\n" +
  observed_at + "\n" +
  raw_payload_sha256 + "\n" +
  decoder_id + "\n" +
  decoder_version
)
```

Rules:

- the raw payload hash is computed before decoding;
- decoder identity and version are part of the event identity;
- replayed events must retain the same `event_id`;
- changed decoder versions must produce reviewable downstream changes;
- Holochain receives batch references/provenance commitments, not high-frequency raw telemetry.

