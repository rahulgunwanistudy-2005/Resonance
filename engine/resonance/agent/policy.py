from typing import Literal, Self

from pydantic import Field, model_validator

from resonance.models import Contract


class Policy(Contract):
    retries: int = Field(default=3, ge=0, le=3)
    alert_drop_fraction: float = Field(default=0.05, gt=0, lt=1)
    confirmations: int = Field(default=2, ge=1, le=5)
    confirmation_window: int = Field(default=3, ge=1, le=10)
    sampling_multiplier: float = Field(default=2, ge=1, le=10)

    @model_validator(mode="after")
    def confirmations_fit_window(self) -> Self:
        if self.confirmations > self.confirmation_window:
            raise ValueError("Required confirmations cannot exceed the capture window")
        return self


class Plan(Contract):
    roi_ids: list[str] = Field(min_length=1, max_length=8)
    window_seconds: float = Field(default=4, ge=2, le=60)
    method: Literal["both", "phase_correlation", "riesz"] = "both"


class Observation(Contract):
    accepted_rois: list[str]
    rejected_rois: list[str]
    metrics: dict[str, float | str | bool | None]
    reason: str


class Proposal(Contract):
    tool: Literal["switch_roi", "extend_window", "method_b", "defer"]
    reason: str = Field(min_length=1, max_length=400)
