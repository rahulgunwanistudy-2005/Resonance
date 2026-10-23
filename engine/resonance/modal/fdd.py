"""Frequency-domain decomposition of the Hermitian cross-spectral density matrix."""

import numpy as np
from numpy.typing import NDArray
from scipy import signal

from resonance.errors import EvidenceError
from resonance.models import DisplacementSeries, FddSpectrum, FrequencyBand
from resonance.quality.scene import check_sampling


def decompose(
    series: list[DisplacementSeries],
    band: FrequencyBand,
    *,
    window_seconds: float = 4,
) -> FddSpectrum:
    if len(series) < 2:
        raise EvidenceError("Mode shapes require at least two synchronized ROIs")
    fps = series[0].fps
    check_sampling(fps, band)
    length = len(series[0].displacement_px)
    if any(
        item.fps != fps
        or len(item.displacement_px) != length
        or not np.allclose(item.time_seconds, series[0].time_seconds)
        for item in series
    ):
        raise EvidenceError("FDD requires synchronized, equally sampled ROI series")
    count = min(length, max(32, round(window_seconds * fps)))
    if count / fps * band.low_hz < 3:
        raise EvidenceError("Capture is too short for FDD at the lower prior frequency")
    matrix = np.zeros((count // 2 + 1, len(series), len(series)), dtype=np.complex128)
    frequencies: NDArray[np.float64] = np.empty(0, dtype=np.float64)
    for i, first in enumerate(series):
        for j in range(i, len(series)):
            raw_frequencies, cross = signal.csd(
                np.asarray(first.displacement_px),
                np.asarray(series[j].displacement_px),
                fs=fps,
                nperseg=count,
                detrend="constant",
            )
            frequencies = np.asarray(raw_frequencies, dtype=np.float64).reshape(-1)
            matrix[:, i, j] = np.asarray(cross).reshape(-1)
            matrix[:, j, i] = np.conj(matrix[:, i, j])
    vectors, singular_values, _ = np.linalg.svd(matrix, full_matrices=False)
    principal = singular_values[:, 0]
    eligible = np.flatnonzero((frequencies >= band.low_hz) & (frequencies <= band.high_hz))
    if len(eligible) < 3 or float(principal.max()) <= 1e-15:
        raise EvidenceError("No resolvable cross-spectral mode in the prior band")
    index = int(eligible[np.argmax(principal[eligible])])
    if index in (eligible[0], eligible[-1]):
        raise EvidenceError("FDD peak lies at the prior boundary")
    shape = vectors[index, :, 0]
    anchor = int(np.argmax(np.abs(shape)))
    shape *= np.exp(-1j * np.angle(shape[anchor]))
    shape /= np.abs(shape[anchor])
    return FddSpectrum(
        roi_ids=[item.roi_id for item in series],
        frequency_hz=frequencies.tolist(),
        principal_psd=principal.tolist(),
        peak_bin_hz=float(frequencies[index]),
        mode_shape_real=shape.real.tolist(),
        mode_shape_imag=shape.imag.tolist(),
    )
