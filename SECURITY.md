# Security policy

- `.env.local` must never be committed, archived, published, or reused from a shared package. Copy `.env.example` locally and generate fresh secrets.
- P2, P3, P4 and Holochain are disabled by default.
- The runtime may record candidates and prepare review packages; it cannot certify evidence, admit PRU/RAP value, create rights or approve governance.
- Report exposed keys, integrity-schema drift, unauthorised claims, duplicate evidence, privacy incidents and supply-chain compromise as release-blocking events.
