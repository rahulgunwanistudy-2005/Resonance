import numpy as np
from numpy.typing import NDArray
from scipy import signal

from resonance.errors import EvidenceError
from resonance.models import FrequencyBand, Spectrum
from resonance.quality.scene import check_sampling


def estimate_spectrum(
    values: NDArray[np.float64], fps: float, band: FrequencyBand, *, window_seconds: float = 4.0
) -> Spectrum:
    check_sampling(fps, band)
    if values.ndim != 1 or len(values) < 32 or not np.isfinite(values).all():
        raise EvidenceError("Spectrum requires a finite one-dimensional series with enough samples")
    if float(np.std(values)) <= 1e-10:
        raise EvidenceError("No measurable displacement variation")
    count = min(len(values), max(32, round(window_seconds * fps)))
    if count / fps * band.low_hz < 3:
        raise EvidenceError("Capture is too short to resolve the lower end of the prior band")
    cleaned = np.asarray(signal.detrend(values, type="linear"), dtype=np.float64)
    raw_frequencies, raw_power = signal.welch(cleaned, fs=fps, nperseg=count, detrend=False)
    frequencies = np.asarray(raw_frequencies, dtype=np.float64).reshape(-1)
    power = np.asarray(raw_power, dtype=np.float64).reshape(-1)
    valid = np.flatnonzero((frequencies >= band.low_hz) & (frequencies <= band.high_hz))
    if len(valid) < 3:
        raise EvidenceError("Prior band is narrower than the spectral resolution")
    index = int(valid[np.argmax(power[valid])])
    if index in (valid[0], valid[-1]):
        raise EvidenceError("Peak lies at the prior boundary; revise the prior or capture longer")
    local = np.log(np.maximum(power[index - 1 : index + 2], np.finfo(float).tiny))
    a, b, c = (float(x) for x in local)
    denominator = a - 2 * b + c
    offset = 0.5 * (a - c) / denominator if abs(denominator) > 1e-12 else 0.0
    offset = float(np.clip(offset, -0.5, 0.5))
    resolution = float(frequencies[1] - frequencies[0])
    peak = float(frequencies[index] + offset * resolution)
    noise_indices = valid[np.abs(valid - index) > 2]
    if len(noise_indices) < 2:
        raise EvidenceError("Prior band provides too few bins to estimate spectral noise")
    noise = max(float(np.median(power[noise_indices])), np.finfo(float).tiny)
    snr = 10 * np.log10(float(power[index]) / noise)
    # Fit amplitude at the measured frequency, avoiding Welch-window amplitude bias.
    time = np.arange(len(values)) / fps
    basis = np.column_stack(
        [np.sin(2 * np.pi * peak * time), np.cos(2 * np.pi * peak * time), time, np.ones_like(time)]
    )
    coefficients = np.linalg.lstsq(basis, values, rcond=None)[0]
    amplitude = float(np.hypot(coefficients[0], coefficients[1]) / np.sqrt(2))
    return Spectrum(
        frequency_hz=frequencies.tolist(),
        psd_px2_per_hz=power.tolist(),
        peak_hz=peak,
        snr_db=float(snr),
        amplitude_rms_px=amplitude,
        resolution_hz=resolution,
    )
