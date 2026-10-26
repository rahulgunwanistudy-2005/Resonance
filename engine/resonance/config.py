"""Environment is read only here; numerical configuration is explicit and validated."""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def process_environment(overrides: dict[str, str]) -> dict[str, str]:
    return {**os.environ, **overrides}


def load_env_file(path: Path = Path(".env")) -> list[str]:
    """Load KEY=VALUE lines into the process environment; existing variables win."""
    if not path.is_file():
        return []
    loaded = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    data_dir: Path = Path("data")
    aliked_model: Path | None = None
    lightglue_model: Path | None = None
    vehicle_model: Path | None = None
    instance_type: str | None = None
    ami_id: str | None = None
    admin_token: str | None = Field(default=None, repr=False)
    database_path: Path = Path("outputs/resonance.sqlite3")
    artifact_dir: Path = Path("outputs/artifacts")
    upload_dir: Path = Path("outputs/uploads")
    host: str = "127.0.0.1"
    port: int = 8000
    sns_topic_arn: str | None = None
    aws_region: str = "us-east-1"

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
    max_frames: int = Field(default=14_400, ge=32)
    max_frame_pixels: int = Field(default=3840 * 2160, gt=0)
    max_roi_pixels: int = Field(default=512 * 512, gt=0)
    max_rois: int = Field(default=8, ge=1)
    roi_workers: int = Field(default=1, ge=1, le=8)
    analysis_seconds: float | None = Field(default=None, ge=2, le=60)
    extraction_method: Literal["both", "phase_correlation", "riesz"] = "both"
