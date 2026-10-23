import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.models import Contract, FrequencyBand


class SceneQuality(Contract):
    texture_std: float = Field(ge=0)
    laplacian_variance: float = Field(ge=0)
    clipped_fraction: float = Field(ge=0, le=1)
    accepted: bool
    reasons: list[str]


def gray_float(frame: NDArray[np.generic]) -> NDArray[np.float32]:
    if frame.size == 0 or frame.ndim not in (2, 3):
        raise EvidenceError("Frame is empty or has an unsupported shape")
    if frame.ndim == 3 and frame.shape[2] not in (3, 4):
        raise EvidenceError("Color frames need three or four channels")
    if not np.isfinite(frame).all():
        raise EvidenceError("Frame contains non-finite pixels")
    image = np.asarray(frame, dtype=np.float32)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return np.asarray(gray, dtype=np.float32)


def assess_scene(frame: NDArray[np.generic], config: MeasurementConfig) -> SceneQuality:
    gray = gray_float(frame)
    texture = float(np.std(gray))
    laplacian = float(np.var(np.asarray(cv2.Laplacian(gray, cv2.CV_32F), dtype=np.float32)))
    clipped = float(np.mean((gray <= 2) | (gray >= 253)))
    reasons: list[str] = []
    if texture < config.min_texture_std:
        reasons.append(
            "Low texture: select a textured ROI or add a reference pattern on the desk rig"
        )
    if laplacian < config.min_laplacian_variance:
        reasons.append("Blur: lock focus and shorten exposure, then record again")
    if clipped > config.max_clipped_fraction:
        reasons.append("Clipped exposure: reduce glare or adjust lighting, then record again")
    return SceneQuality(
        texture_std=texture,
        laplacian_variance=laplacian,
        clipped_fraction=clipped,
        accepted=not reasons,
        reasons=reasons,
    )


def check_sampling(fps: float, band: FrequencyBand) -> None:
    required = 2.5 * band.high_hz
    if not np.isfinite(fps) or fps < required:
        raise EvidenceError(
            f"Video is {fps:g} fps; the selected band needs at least {required:g} fps. "
            "Record at a higher verified acquisition rate or revise the physics prior."
        )
