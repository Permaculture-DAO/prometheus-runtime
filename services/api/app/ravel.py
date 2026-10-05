from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence


class RavelModelError(ValueError):
    """Raised when a RAVEL shadow-underwriting input violates v0.1 invariants."""


@dataclass(frozen=True)
class ScenarioLoss:
    scenario_id: str
    probability: float
    gross_loss: float
    mitigated_loss: float
    recovery_value: float | None = None


@dataclass(frozen=True)
class CapitalLayer:
    bearer_id: str
    economic_group_id: str
    layer_type: str
    attachment: float
    limit: float
    priority: int


@dataclass(frozen=True)
class ProtectionContract:
    contract_id: str
    provider_bearer_id: str
    receiver_bearer_id: str
    attachment: float
    limit: float
    effectiveness: float
    basis_factor: float
    counterparty_factor: float
    legal_factor: float


def _finite_nonnegative(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise RavelModelError(f"{name} must be finite and >= 0")


def normalise_scenarios(scenarios: Sequence[ScenarioLoss]) -> list[ScenarioLoss]:
    if not scenarios:
        raise RavelModelError("at least one scenario is required")
    total = 0.0
    seen: set[str] = set()
    for s in scenarios:
        if not s.scenario_id or s.scenario_id in seen:
            raise RavelModelError("scenario_id must be non-empty and unique")
        seen.add(s.scenario_id)
        if not isfinite(s.probability) or s.probability < 0:
            raise RavelModelError("scenario probability must be finite and >= 0")
        _finite_nonnegative("gross_loss", s.gross_loss)
        _finite_nonnegative("mitigated_loss", s.mitigated_loss)
        if s.mitigated_loss > s.gross_loss + 1e-9:
            raise RavelModelError("mitigated_loss cannot exceed gross_loss in v0.1")
        if s.recovery_value is not None:
            _finite_nonnegative("recovery_value", s.recovery_value)
        total += s.probability
    if not isfinite(total) or total <= 0:
        raise RavelModelError("scenario probabilities must sum to > 0")
    return [
        ScenarioLoss(
            scenario_id=s.scenario_id,
            probability=s.probability / total,
            gross_loss=s.gross_loss,
            mitigated_loss=s.mitigated_loss,
            recovery_value=s.recovery_value,
        )
        for s in scenarios
    ]


def expected_loss(scenarios: Sequence[ScenarioLoss], field: str = "mitigated_loss") -> float:
    ss = normalise_scenarios(scenarios)
    return sum(s.probability * float(getattr(s, field)) for s in ss)


def weighted_var(scenarios: Sequence[ScenarioLoss], alpha: float, field: str = "mitigated_loss") -> float:
    if not (0 < alpha < 1):
        raise RavelModelError("alpha must be in (0,1)")
    ss = normalise_scenarios(scenarios)
    ordered = sorted((float(getattr(s, field)), s.probability) for s in ss)
    cumulative = 0.0
    for loss, probability in ordered:
        cumulative += probability
        if cumulative + 1e-15 >= alpha:
            return loss
    return ordered[-1][0]


def expected_shortfall(scenarios: Sequence[ScenarioLoss], alpha: float, field: str = "mitigated_loss") -> float:
    """Probability-weighted mean of the worst (1-alpha) mass, with partial atoms."""
    if not (0 < alpha < 1):
        raise RavelModelError("alpha must be in (0,1)")
    ss = normalise_scenarios(scenarios)
    tail_mass = 1.0 - alpha
    remaining = tail_mass
    tail_loss = 0.0
    for s in sorted(ss, key=lambda x: float(getattr(x, field)), reverse=True):
        if remaining <= 1e-15:
            break
        take = min(remaining, s.probability)
        tail_loss += take * float(getattr(s, field))
        remaining -= take
    if tail_mass <= 0:
        raise RavelModelError("invalid tail mass")
    return tail_loss / tail_mass


def ppci(
    scenarios: Sequence[ScenarioLoss],
    *,
    initial_capital: float,
    impairment_threshold: float,
) -> float:
    """Probability of permanent capital impairment using declared recovery values."""
    _finite_nonnegative("initial_capital", initial_capital)
    if initial_capital <= 0:
        raise RavelModelError("initial_capital must be > 0")
    if not (0 <= impairment_threshold < 1):
        raise RavelModelError("impairment_threshold must be in [0,1)")
    ss = normalise_scenarios(scenarios)
    if any(s.recovery_value is None for s in ss):
        raise RavelModelError("PPCI requires recovery_value for every scenario")
    floor = (1.0 - impairment_threshold) * initial_capital
    return sum(s.probability for s in ss if float(s.recovery_value) < floor)


def rr_delta(*, baseline_metric: float, regenerative_metric: float) -> float:
    _finite_nonnegative("baseline_metric", baseline_metric)
    _finite_nonnegative("regenerative_metric", regenerative_metric)
    if baseline_metric <= 0:
        raise RavelModelError("RRDelta is undefined when baseline metric <= 0")
    return 1.0 - regenerative_metric / baseline_metric


def validate_layers(layers: Sequence[CapitalLayer]) -> list[CapitalLayer]:
    if not layers:
        raise RavelModelError("at least one capital layer is required")
    ordered = sorted(layers, key=lambda x: (x.attachment, x.priority, x.bearer_id))
    previous_end = 0.0
    groups: dict[str, str] = {}
    for layer in ordered:
        if not layer.bearer_id or not layer.economic_group_id or not layer.layer_type:
            raise RavelModelError("capital layer identifiers must be non-empty")
        if layer.bearer_id == "UNALLOCATED_RESIDUAL":
            raise RavelModelError("UNALLOCATED_RESIDUAL is a reserved bearer id")
        if layer.bearer_id in groups and groups[layer.bearer_id] != layer.economic_group_id:
            raise RavelModelError("a bearer cannot belong to conflicting economic groups")
        groups[layer.bearer_id] = layer.economic_group_id
        _finite_nonnegative("attachment", layer.attachment)
        _finite_nonnegative("limit", layer.limit)
        if layer.limit <= 0:
            raise RavelModelError("capital layer limit must be > 0")
        if layer.attachment + 1e-9 < previous_end:
            raise RavelModelError("capital layers overlap; v0.1 requires non-overlapping attachments")
        previous_end = max(previous_end, layer.attachment + layer.limit)
        if not isfinite(previous_end):
            raise RavelModelError("capital layer end must be finite")
    return ordered


def allocate_waterfall(loss: float, layers: Sequence[CapitalLayer]) -> dict:
    """Allocate one mitigated system loss through absolute attachment/limit layers."""
    _finite_nonnegative("loss", loss)
    ordered = validate_layers(layers)
    by_bearer: dict[str, float] = {}
    for layer in ordered:
        allocated = min(layer.limit, max(0.0, loss - layer.attachment))
        if allocated > 0:
            by_bearer[layer.bearer_id] = by_bearer.get(layer.bearer_id, 0.0) + allocated
    allocated_total = sum(by_bearer.values())
    residual = max(0.0, loss - allocated_total)
    if residual <= 1e-9 * max(1.0, loss):
        residual = 0.0
    if residual > 0:
        by_bearer["UNALLOCATED_RESIDUAL"] = residual
    return {
        "loss": loss,
        "by_bearer": by_bearer,
        "allocated_total": allocated_total,
        "residual": residual,
        "conservation_error": abs(sum(by_bearer.values()) - loss),
    }


def _factor(name: str, value: float) -> None:
    if not isfinite(value) or not (0 <= value <= 1):
        raise RavelModelError(f"{name} must be in [0,1]")


def apply_transfers(
    bearer_losses: Mapping[str, float],
    contracts: Sequence[ProtectionContract],
) -> dict:
    losses = {k: float(v) for k, v in bearer_losses.items()}
    for bearer, loss in losses.items():
        if not bearer:
            raise RavelModelError("bearer id must be non-empty")
        _finite_nonnegative(f"loss[{bearer}]", loss)
    transfers: list[dict] = []
    seen: set[str] = set()
    before_total = sum(losses.values())
    if any(c.provider_bearer_id == c.receiver_bearer_id for c in contracts):
        raise RavelModelError("self-transfer cannot reduce receiver loss")
    providers = {c.provider_bearer_id for c in contracts}
    receivers = {c.receiver_bearer_id for c in contracts}
    if providers & receivers:
        raise RavelModelError("chained protection requires an explicit admitted ordering model")
    for c in contracts:
        if not c.contract_id or not c.provider_bearer_id or not c.receiver_bearer_id:
            raise RavelModelError("protection contract identifiers must be non-empty")
        if c.contract_id in seen:
            raise RavelModelError("protection contract identifiers must be unique")
        seen.add(c.contract_id)
        if "UNALLOCATED_RESIDUAL" in (c.provider_bearer_id, c.receiver_bearer_id):
            raise RavelModelError("UNALLOCATED_RESIDUAL is a reserved bearer id")
        _finite_nonnegative("attachment", c.attachment)
        _finite_nonnegative("limit", c.limit)
        if c.limit <= 0:
            raise RavelModelError("protection contract limit must be > 0")
        for name, value in (
            ("effectiveness", c.effectiveness),
            ("basis_factor", c.basis_factor),
            ("counterparty_factor", c.counterparty_factor),
            ("legal_factor", c.legal_factor),
        ):
            _factor(name, value)
        receiver_loss = losses.get(c.receiver_bearer_id, 0.0)
        nominal = min(c.limit, max(0.0, receiver_loss - c.attachment))
        combined = c.effectiveness * c.basis_factor * c.counterparty_factor * c.legal_factor
        effective = min(receiver_loss, nominal * combined)
        losses[c.receiver_bearer_id] = receiver_loss - effective
        losses[c.provider_bearer_id] = losses.get(c.provider_bearer_id, 0.0) + effective
        transfers.append({
            "contract_id": c.contract_id,
            "receiver_bearer_id": c.receiver_bearer_id,
            "provider_bearer_id": c.provider_bearer_id,
            "receiver_loss_before": receiver_loss,
            "receiver_loss_after": losses[c.receiver_bearer_id],
            "nominal_payout": nominal,
            "effective_payout": effective,
            "combined_effectiveness": combined,
            "rte_loss_share": 0.0 if receiver_loss <= 0 else effective / receiver_loss,
        })
    after_total = sum(losses.values())
    return {
        "by_bearer": losses,
        "transfers": transfers,
        "conservation_error": abs(after_total - before_total),
    }


def risk_transfer_effectiveness(*, before_metric: float, after_metric: float) -> float:
    _finite_nonnegative("before_metric", before_metric)
    _finite_nonnegative("after_metric", after_metric)
    if before_metric <= 0:
        raise RavelModelError("RTE is undefined when before_metric <= 0")
    value = 1.0 - after_metric / before_metric
    return max(0.0, min(1.0, value))


def aggregate_by_economic_group(
    bearer_losses: Mapping[str, float],
    bearer_to_group: Mapping[str, str],
) -> dict[str, float]:
    groups: dict[str, float] = {}
    for bearer, loss in bearer_losses.items():
        _finite_nonnegative(f"loss[{bearer}]", float(loss))
        group = bearer_to_group.get(bearer, bearer)
        groups[group] = groups.get(group, 0.0) + float(loss)
    return groups


def reconcile_economic_groups(layers: Sequence[CapitalLayer], declared: Mapping[str, str]) -> dict[str, str]:
    """Do not silently override the capital stack's common-control declarations."""
    groups = {layer.bearer_id: layer.economic_group_id for layer in validate_layers(layers)}
    for bearer, group in declared.items():
        if not bearer or not group:
            raise RavelModelError("economic group identifiers must be non-empty")
        if bearer in groups and groups[bearer] != group:
            raise RavelModelError("economic group mapping conflicts with capital layer")
        groups[bearer] = group
    return groups


def urbc(group_losses: Mapping[str, float]) -> float:
    total = sum(float(v) for v in group_losses.values())
    if total <= 0:
        return 0.0
    shares = [float(v) / total for v in group_losses.values() if float(v) > 0]
    return sum(q * q for q in shares)


def shadow_state(
    scenarios: Sequence[ScenarioLoss],
    *,
    alpha_values: Iterable[float] = (0.95, 0.99),
    initial_capital: float | None = None,
    impairment_threshold: float | None = None,
) -> dict:
    ss = normalise_scenarios(scenarios)
    out = {
        "expected_loss": expected_loss(ss),
        "var": {},
        "expected_shortfall": {},
        "vrrc": 0.0,
        "vrrc_status": "not_admitted",
        "authority_boundary": "evaluation_not_certification",
    }
    for alpha in alpha_values:
        key = f"{alpha:.4f}"
        out["var"][key] = weighted_var(ss, alpha)
        out["expected_shortfall"][key] = expected_shortfall(ss, alpha)
    if initial_capital is not None or impairment_threshold is not None:
        if initial_capital is None or impairment_threshold is None:
            raise RavelModelError("PPCI requires both initial_capital and impairment_threshold")
        out["ppci"] = ppci(ss, initial_capital=initial_capital, impairment_threshold=impairment_threshold)
    else:
        out["ppci"] = None
    return out
