from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RavelInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RavelScenarioIn(RavelInput):
    scenario_id: str = Field(min_length=1, max_length=128)
    probability: float = Field(ge=0, le=1)
    gross_loss: float = Field(ge=0)
    mitigated_loss: float = Field(ge=0)
    recovery_value: float | None = Field(default=None, ge=0)
    horizon: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    evidence_refs: list[str] = Field(min_length=1, max_length=1000)


class RavelCapitalLayerIn(RavelInput):
    bearer_id: str = Field(min_length=1, max_length=128)
    economic_group_id: str = Field(min_length=1, max_length=128)
    layer_type: str = Field(min_length=1, max_length=80)
    attachment: float = Field(ge=0)
    limit: float = Field(gt=0)
    priority: int = Field(ge=0)


class RavelProtectionContractIn(RavelInput):
    contract_id: str = Field(min_length=1, max_length=128)
    provider_bearer_id: str = Field(min_length=1, max_length=128)
    receiver_bearer_id: str = Field(min_length=1, max_length=128)
    attachment: float = Field(ge=0)
    limit: float = Field(gt=0)
    effectiveness: float = Field(ge=0, le=1)
    basis_factor: float = Field(ge=0, le=1)
    counterparty_factor: float = Field(ge=0, le=1)
    legal_factor: float = Field(ge=0, le=1)


class RavelShadowRequest(RavelInput):
    baseline_scenarios: list[RavelScenarioIn] = Field(min_length=1, max_length=10000)
    regenerative_scenarios: list[RavelScenarioIn] = Field(min_length=1, max_length=10000)
    alpha_values: list[float] = Field(default_factory=lambda: [0.95, 0.99], min_length=1, max_length=10)
    initial_capital: float | None = Field(default=None, gt=0)
    impairment_threshold: float | None = Field(default=None, ge=0, lt=1)
    allocation_loss: float | None = Field(default=None, ge=0)
    capital_layers: list[RavelCapitalLayerIn] = Field(default_factory=list, max_length=100)
    transfer_contracts: list[RavelProtectionContractIn] = Field(default_factory=list, max_length=100)
    bearer_to_group: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_pairing(self):
        scenarios = self.baseline_scenarios + self.regenerative_scenarios
        if len({s.horizon for s in scenarios}) != 1:
            raise ValueError("baseline and regenerative scenarios require the same declared horizon")
        if any(not ref.strip() for s in scenarios for ref in s.evidence_refs):
            raise ValueError("evidence_refs must contain non-empty identifiers")
        if (self.initial_capital is None) != (self.impairment_threshold is None):
            raise ValueError("initial_capital and impairment_threshold must be supplied together")
        if self.allocation_loss is not None and not self.capital_layers:
            raise ValueError("allocation_loss requires capital_layers")
        if self.transfer_contracts and self.allocation_loss is None:
            raise ValueError("transfer_contracts require allocation_loss and capital_layers")
        for alpha in self.alpha_values:
            if not (0 < alpha < 1):
                raise ValueError("alpha_values must be in (0,1)")
        return self


class RavelShadowResponse(BaseModel):
    authoritative: bool = False
    certification: bool = False
    underwriting_approval: bool = False
    capital_facing: bool = False
    message: str = "evaluation, not certification"
    mode: str = "shadow_underwriting"
    methodology_status: str = "candidate"
    vrrc: float = 0.0
    vrrc_status: str = "not_admitted"
    baseline: dict
    regenerative: dict
    rr_delta: dict
    allocation: dict | None = None
    assumptions: list[str] = Field(default_factory=list)
    scenario_provenance: dict = Field(default_factory=dict)
