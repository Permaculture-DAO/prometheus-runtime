"""Internal arithmetic dry-run only; never an admission or valuation service.

Derived from signed canon controlling expression. No new gate vocabulary,
threshold, Z methodology, legal decision or site-confidence estimator is defined.
"""
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json

FIELDS = ("v_base", "legal_gate", "mrv_gate", "u_max", "g_z", "conf_total")
ZERO_FIELDS = ("v_base", "legal_gate", "mrv_gate", "conf_total")


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def dry_run(inputs: dict) -> dict:
    if set(inputs) != set(FIELDS):
        raise ValueError("exact PRU input fields required; no extra weight or authority fields")
    values = {}
    for name in FIELDS:
        raw = inputs[name]
        if raw is None:
            values[name] = None
            continue
        if not isinstance(raw, str) or not raw or len(raw) > 64:
            raise ValueError("decimal strings or explicit null required")
        try:
            number = Decimal(raw)
        except Exception as exc:
            raise ValueError(f"invalid {name}") from exc
        if not number.is_finite() or number < 0 or abs(number.adjusted()) > 18:
            raise ValueError(f"out-of-domain {name}")
        if name in ("legal_gate", "mrv_gate") and number not in (0, 1):
            raise ValueError(f"binary gate required: {name}")
        if name in ("g_z", "conf_total") and number > 1:
            raise ValueError(f"bounded input required: {name}")
        values[name] = number
    unknown = [name for name in FIELDS if values[name] is None]
    flags = [name for name in ZERO_FIELDS if values[name] == 0]
    shadow = None
    if not unknown:
        # This prototype never admits uplift. The supplied u_max and g_z are
        # retained as inputs, but cannot produce pre-pilot capital uplift.
        with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN, Emax=100, Emin=-100)):
            value = (values["v_base"] * values["legal_gate"] *
                     values["mrv_gate"] * values["conf_total"])
            shadow = format(value, "f")
            if "." in shadow:
                shadow = shadow.rstrip("0").rstrip(".")
            if value == 0:
                shadow = "0"
    return {
        "method_version": "pru-shadow-zero-uplift-v0.1",
        "status": "unknown" if unknown else "synthetic_dry_run",
        "shadow_value": shadow,
        "unknown_inputs": unknown,
        "zero_condition_flags": flags,
        "u_max_effective": "0",
        "capital_value": "0",
        "capital_value_status": "policy_not_admitted_not_a_measurement",
        "authoritative": False,
        "certification": False,
        "creates_rights": False,
    }


def replay(bundle: dict) -> bytes:
    if set(bundle) != {"method_version", "inputs", "input_sha256", "expected"}:
        raise ValueError("invalid frozen bundle")
    if bundle["method_version"] != "pru-shadow-zero-uplift-v0.1":
        raise ValueError("method version mismatch")
    actual_hash = hashlib.sha256(canonical_bytes(bundle["inputs"])).hexdigest()
    if actual_hash != bundle["input_sha256"]:
        raise ValueError("frozen input hash mismatch")
    result = dry_run(bundle["inputs"])
    encoded = canonical_bytes(result)
    if encoded != canonical_bytes(bundle["expected"]):
        raise ValueError("golden output mismatch")
    return encoded
