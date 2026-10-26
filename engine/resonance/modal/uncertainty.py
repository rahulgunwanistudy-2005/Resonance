import numpy as np
from numpy.typing import NDArray

from resonance.errors import EvidenceError
from resonance.modal.spectrum import estimate_spectrum
from resonance.models import FrequencyBand


def bootstrap_frequency_ci(
    values: NDArray[np.float64],
    fps: float,
    band: FrequencyBand,
    *,
    repeats: int = 200,
    block_seconds: float = 2.0,
    seed: int = 42,
    window_seconds: float = 4.0,
) -> tuple[float, float]:
    """Moving-block residual bootstrap conditional on a fitted single stationary mode.

    Keeps the fitted carrier coherent across block seams. This interval describes residual
    uncertainty under the single-mode model, not environmental or calibration uncertainty.
    """
    if repeats < 20 or block_seconds <= 0 or fps <= 0:
        raise EvidenceError("Bootstrap needs positive timing and at least twenty repeats")
    window_seconds = min(window_seconds, len(values) / fps)
    estimate = estimate_spectrum(values, fps, band, window_seconds=window_seconds)
    time = np.arange(len(values)) / fps
    basis = np.column_stack(
        [
            np.sin(2 * np.pi * estimate.peak_hz * time),
            np.cos(2 * np.pi * estimate.peak_hz * time),
            time,
            np.ones_like(time),
        ]
    )
    fitted = basis @ np.linalg.lstsq(basis, values, rcond=None)[0]
    residual = values - fitted
    residual -= np.mean(residual)
    block = min(len(values) // 4, max(2, round(block_seconds * fps)))
    rng = np.random.default_rng(seed)
    peaks: list[float] = []
    for _ in range(repeats):
        starts = rng.integers(0, len(values) - block + 1, size=int(np.ceil(len(values) / block)))
        resampled = np.concatenate([residual[start : start + block] for start in starts])[
            : len(values)
        ]
        result = estimate_spectrum(fitted + resampled, fps, band, window_seconds=window_seconds)
        peaks.append(result.peak_hz)
    lower, upper = (float(x) for x in np.quantile(peaks, [0.025, 0.975]))
    # Include the estimator's bin-scale systematic floor; interpolation is not new resolution.
    half_bin = estimate.resolution_hz / 2
    return min(lower, estimate.peak_hz - half_bin), max(upper, estimate.peak_hz + half_bin)
