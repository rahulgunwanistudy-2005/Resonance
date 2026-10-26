from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator, field_validator

from resonance.agent.loop import AgentResult
from resonance.models import Bridge, Calibration, Capture, Contract, FrequencyBand, Roi


class BridgeCreate(Contract):
    name: str = Field(min_length=1, max_length=160)
    band: FrequencyBand
    rois: list[Roi] = Field(min_length=1, max_length=8)
    calibration: Calibration | None = None


class BridgeRecord(Contract):
    bridge: Bridge
    created_at: datetime
    sampling_multiplier: float = 1
    synthetic: bool = False


class CaptureCreate(Contract):
    bridge_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    acquisition_fps: float = Field(gt=0, le=1000)
    acquisition_fps_verified: bool
    temperature_c: float | None = Field(default=None, ge=-100, le=100)
    rois: list[Roi] | None = Field(default=None, min_length=1, max_length=8)
    calibration: Calibration | None = None
    stabilize: bool = False
    structure_box: Roi | None = None

    @model_validator(mode="after")
    def stabilization_box(self) -> "CaptureCreate":
        if self.stabilize and self.structure_box is None:
            raise ValueError(
                "Stabilization requires a box covering the entire moving structure"
            )
        return self


class CaptureRecord(Contract):
    capture: Capture
    created_at: datetime
    status: Literal[
        "awaiting_upload", "queued", "processing", "complete", "failed", "expired"
    ]
    error: str | None = None
    result: AgentResult | None = None
    synthetic: bool = False
    artifacts: list[str] = Field(default_factory=list)


class UploadTicket(Contract):
    capture_id: str
    upload_url: str
    upload_token: str
    expires_at: datetime
    max_bytes: int
    transport: Literal["local_stream"] = "local_stream"


class ApprovalRecord(Contract):
    id: str
    bridge_id: str
    capture_id: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    reason: str = ""
    created_at: datetime
    resolved_at: datetime | None = None
    delivery: Literal[
        "not_requested", "pending", "recorded_locally", "sent", "failed"
    ] = "not_requested"


class ApprovalInput(Contract):
    approved: bool
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A review reason is required")
        return value.strip()


class BaselineInput(Contract):
    capture_ids: list[str] = Field(min_length=3, max_length=100)
    confirmed_healthy: bool


class Health(Contract):
    status: str = "ok"
    transport: str = "Local SQLite queue"
    planner: str = "Deterministic policy"
    cloud_deployed: bool = False


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class ErrorResponse(Contract):
    error: str
    request_id: str
