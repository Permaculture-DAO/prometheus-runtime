# TERRA RC4 — semantic and territorial integration candidate

TEST only; HOLD_REAL / HOLD_PRODUCTION. No network, database writes, real GIS, Holochain commit, actual source admission or HTTP routes.

- WP06: semantic_mapping reuses RC3 reconciliation and produces objects compatible with the native observation schema. Subject, place and system boundary are explicitly TEST-derived placeholders, not registered contexts. The date-only source is rendered at midnight by convention, not a verified timestamp. References and workstream provenance preserved in sidecar. Zero PRU weight. No EvidencePackage, no claim UID creation, no admissibility state.
- WP01/WP04: admission_status enumerates missing dataset identity, jurisdiction, scope, licence, acquisition/retention permission, cost cap, coverage, freshness, provenance and competent decision. All UNKNOWN, all real access disabled. This is a diagnostic, not a permission registry or authorization API.
- WP07: exact Decimal area, bounded closed simple planar ring, reject self-intersection and degenerate/collinear adjacent edges. TEST_LOCAL_GRID only, synthetic units only, no EPSG, real GIS or area/accuracy claim. Hash binds input representation, not canonical polygon identity. No holes or multipolygons.
- WP08: land_shadow_interface is a gap report targeting land-underwriting-shadow/v2. All five gate states UNKNOWN; no gate decision, evidence catalog, engine invocation or value. Existing branch is not merged or copied.
- WP09: status_view returns a deterministic static read-only descriptor, not a registered route or Console integration.
- Tests: native observation schema, zero weight, replay, conflicts, admission firewall, geometry schema/area and negative cases, shadow and status boundaries. Existing API suite discovers test_terra_semantic.py.
- Open: authenticate/approve source-specific permissions and costs; reconcile actual archives; establish competent claim/context mapping; real GIS review; reviewed shadow integration; Bridge/Console integration; release admission. No changes to core gates or live infrastructure.
