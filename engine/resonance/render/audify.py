"""Replay measured displacement faster; loop the short waveform for audibility."""

from math import ceil, gcd
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from resonance.errors import EvidenceError
from resonance.models import DisplacementSeries


def audify(
    series: DisplacementSeries, peak_hz: float, path: Path, *, reference_hz: float | None = None
) -> None:
    reference = peak_hz if reference_hz is None else reference_hz
    if not np.isfinite([peak_hz, reference]).all() or min(peak_hz, reference) <= 0:
        raise EvidenceError("Audification requires a positive measured frequency")
    displacement = np.asarray(series.displacement_px, dtype=np.float64)
    displacement -= np.mean(displacement)
    maximum = float(np.max(np.abs(displacement)))
    if maximum <= 1e-12:
        raise EvidenceError("No motion is available to audify")
    playback_rate = round(series.fps * 330 / reference)
    if playback_rate < 1:
        raise EvidenceError("Audification playback rate is invalid")
    sample_rate = 22050
    divisor = gcd(sample_rate, playback_rate)
    compressed = resample_poly(
        displacement / maximum, sample_rate // divisor, playback_rate // divisor
    )
    fade = min(round(sample_rate * 0.002), len(compressed) // 4)
    if fade:
        compressed[:fade] *= np.linspace(0, 1, fade)
        compressed[-fade:] *= np.linspace(1, 0, fade)
    audio = np.tile(compressed, ceil(3 * sample_rate / len(compressed)))[: 3 * sample_rate]
    wavfile.write(
        path, sample_rate, (np.clip(audio, -1, 1) * 0.8 * 32767).astype(np.int16).reshape(-1)
    )
