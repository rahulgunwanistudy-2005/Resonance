"""Validated contracts shared by the engine, service and evidence writers."""

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Roi(Contract):
    id: str = Field(min_length=1, max_length=80)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=16)
    height: int = Field(ge=16)


class FrequencyBand(Contract):
    low_hz: float = Field(gt=0)
    high_hz: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.high_hz <= self.low_hz:
            raise ValueError("Upper frequency must exceed lower frequency")
        return self


class Calibration(Contract):
    mm_per_pixel: float = Field(gt=0)
    reference_length_mm: float = Field(gt=0)
    points: tuple[tuple[float, float], tuple[float, float]]


class Bridge(Contract):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    span_type: Literal["cantilever", "simply_supported", "unknown"] = "unknown"
    span_length_m: float | None = Field(default=None, gt=0)
    band: FrequencyBand
    rois: list[Roi] = Field(min_length=1, max_length=8)
    calibration: Calibration | None = None


class Capture(Contract):
    id: str
    bridge_id: str
    path: Path
    band: FrequencyBand
    rois: list[Roi] = Field(min_length=1, max_length=8)
    calibration: Calibration | None = None
    temperature_c: float | None = None
    acquisition_fps: float | None = Field(default=None, gt=0)
    acquisition_fps_verified: bool = False


class VideoMetadata(Contract):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_count: int = Field(gt=0)
    playback_fps: float = Field(gt=0)
    acquisition_fps: float = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    timestamps_seconds: list[float]
    timing_source: str


class DisplacementSeries(Contract):
    roi_id: str
    method: Literal["phase_correlation", "riesz"]
    fps: float = Field(gt=0)
    time_seconds: list[float] = Field(min_length=16)
    displacement_px: list[float] = Field(min_length=16)
    displacement_mm: list[float] | None = None
    response: list[float]

    @model_validator(mode="after")
    def aligned(self) -> Self:
        n = len(self.time_seconds)
        if len(self.displacement_px) != n or len(self.response) != n:
            raise ValueError("Displacement, response and time arrays must align")
        if self.displacement_mm is not None and len(self.displacement_mm) != n:
            raise ValueError("Calibrated displacement must align with time")
        if any(b <= a for a, b in zip(self.time_seconds, self.time_seconds[1:], strict=False)):
            raise ValueError("Frame times must increase strictly")
        return self


class Spectrum(Contract):
    frequency_hz: list[float]
    psd_px2_per_hz: list[float]
    peak_hz: float = Field(gt=0)
    snr_db: float
    amplitude_rms_px: float = Field(ge=0)
    resolution_hz: float = Field(gt=0)


class RuntimeProvenance(Contract):
    cv2_version: str
    cv2_path: str
    build_info_sha: str
    machine: str
    instance_type: str | None = None
    ami_id: str | None = None
    cool_verified: bool = False


class ModalEstimate(Contract):
    capture_id: str
    bridge_id: str
    outcome: Literal["MEASURED", "INSUFFICIENT_EVIDENCE"]
    reasons: list[str]
    selected: DisplacementSeries | None = None
    spectrum: Spectrum | None = None
    ci_hz: tuple[float, float] | None = None
    candidates: list[Spectrum] = Field(default_factory=list)
    provenance: RuntimeProvenance
    input_sha256: str | None = None
    config_sha256: str


class Baseline(Contract):
    bridge_id: str
    f0_hz: float = Field(gt=0)
    temperature_reference_c: float
    alpha_per_c: float
    residual_std_hz: float = Field(ge=0)
    capture_ids: list[str] = Field(min_length=3)


class DecisionStatus(StrEnum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ALERT = "ALERT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Decision(Contract):
    bridge_id: str
    capture_id: str
    status: DecisionStatus
    reason: str
    action: str
    approval_id: str | None = None


class TraceEvent(Contract):
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    bridge_id: str
    state: str
    inputs_ref: str
    evidence: dict[str, float | str | bool | None]
    proposal: str | None = None
    decision: str
    action: str
    outcome: str


class BenchResult(Contract):
    workload: str
    provenance: RuntimeProvenance
    repeats_seconds: list[float] = Field(min_length=5)
    input_sha256: str
    configuration: dict[str, str | int | float | bool]
