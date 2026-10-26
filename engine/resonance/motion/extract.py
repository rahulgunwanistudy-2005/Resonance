"""Independent per-region work, suitable for a bounded spawned process pool."""

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.modal.spectrum import estimate_spectrum
from resonance.models import DisplacementSeries, FrequencyBand, Spectrum
from resonance.motion.phase_corr import extract_phase_correlation
from resonance.motion.riesz import extract_riesz


@dataclass(frozen=True)
class RoiWork:
    roi_id: str
    frames: Sequence[NDArray[np.generic]]
    fps: float
    band: FrequencyBand
    config: MeasurementConfig


def initialize_worker() -> None:
    cv2.setNumThreads(1)
    cv2.setRNGSeed(42)


def extract(work: RoiWork) -> tuple[list[tuple[DisplacementSeries, Spectrum]], list[str]]:
    candidates: list[tuple[DisplacementSeries, Spectrum]] = []
    reasons = []
    for name, extractor in (
        ("phase_correlation", extract_phase_correlation),
        ("riesz", extract_riesz),
    ):
        if work.config.extraction_method not in ("both", name):
            continue
        try:
            series = extractor(work.frames, work.fps, work.roi_id)
            spectrum = estimate_spectrum(
                np.asarray(series.displacement_px),
                work.fps,
                work.band,
                window_seconds=work.config.welch_seconds,
            )
            candidates.append((series, spectrum))
        except EvidenceError as exc:
            reasons.append(f"{work.roi_id}/{name}: {exc}")
    return candidates, reasons
