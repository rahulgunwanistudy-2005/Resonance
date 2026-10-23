"""Environment is read only here; numerical configuration is explicit and validated."""

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    data_dir: Path = Path("data")
    aliked_model: Path | None = None
    lightglue_model: Path | None = None
    vehicle_model: Path | None = None
    instance_type: str | None = None
    ami_id: str | None = None
    admin_token: str | None = Field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        values = {
            key: os.environ[f"RESONANCE_{key.upper()}"]
            for key in cls.model_fields
            if f"RESONANCE_{key.upper()}" in os.environ
        }
        return cls.model_validate(values)


class MeasurementConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    seed: int = 42
    min_snr_db: float = 10.0
    max_ci_width_hz: float = Field(default=0.5, gt=0)
    bootstrap_repeats: int = Field(default=200, ge=20)
    block_seconds: float = Field(default=2.0, gt=0)
    welch_seconds: float = Field(default=4.0, gt=0)
    min_texture_std: float = Field(default=4.0, ge=0)
    min_laplacian_variance: float = Field(default=5.0, ge=0)
    max_clipped_fraction: float = Field(default=0.35, ge=0, le=1)
    max_duration_seconds: float = Field(default=60.0, gt=0)
    max_upload_bytes: int = Field(default=200_000_000, gt=0)
    max_frame_pixels: int = Field(default=3840 * 2160, gt=0)
    max_roi_pixels: int = Field(default=512 * 512, gt=0)
    max_rois: int = Field(default=8, ge=1)
