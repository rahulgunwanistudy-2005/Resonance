import numpy as np
from pydantic import Field
from scipy.stats import t

from resonance.errors import EvidenceError
from resonance.models import Baseline, Contract


class HealthyCapture(Contract):
    capture_id: str
    frequency_hz: float = Field(gt=0)
    temperature_c: float


class Prediction(Contract):
    frequency_hz: float
    lower_hz: float
    upper_hz: float


def fit_baseline(bridge_id: str, healthy: list[HealthyCapture]) -> Baseline:
    if len(healthy) < 3 or len({item.capture_id for item in healthy}) != len(healthy):
        raise EvidenceError("A baseline needs distinct, explicitly designated healthy captures")
    temperatures = np.array([item.temperature_c for item in healthy])
    frequencies = np.array([item.frequency_hz for item in healthy])
    reference = float(temperatures.mean())
    spread = float(np.ptp(temperatures))
    if spread > 0 and spread < 2:
        raise EvidenceError("Temperature range is too narrow to fit temperature correction")
    design = (
        np.column_stack([np.ones(len(healthy)), temperatures - reference])
        if spread
        else np.ones((len(healthy), 1))
    )
    coefficients = np.linalg.lstsq(design, frequencies, rcond=None)[0]
    f0 = float(coefficients[0])
    if f0 <= 0:
        raise EvidenceError("Baseline regression is not physically plausible")
    residual = frequencies - design @ coefficients
    sigma = float(np.sqrt(np.sum(residual**2) / (len(healthy) - design.shape[1])))
    return Baseline(
        bridge_id=bridge_id,
        f0_hz=f0,
        temperature_reference_c=reference,
        alpha_per_c=float(coefficients[1] / f0) if spread else 0,
        residual_std_hz=sigma,
        capture_ids=[item.capture_id for item in healthy],
        temperature_min_c=float(temperatures.min()),
        temperature_max_c=float(temperatures.max()),
        regression_inverse=np.linalg.inv(design.T @ design).tolist(),
    )


def predict(baseline: Baseline, temperature_c: float) -> Prediction:
    if not baseline.temperature_min_c <= temperature_c <= baseline.temperature_max_c:
        raise EvidenceError("Temperature is outside the healthy baseline's observed range")
    if not baseline.regression_inverse:
        raise EvidenceError("Baseline lacks regression provenance; refit from healthy captures")
    count = len(baseline.regression_inverse)
    vector = np.array([1, temperature_c - baseline.temperature_reference_c][:count])
    leverage = float(vector @ np.asarray(baseline.regression_inverse) @ vector)
    center = baseline.f0_hz * (
        1 + baseline.alpha_per_c * (temperature_c - baseline.temperature_reference_c)
    )
    margin = (
        float(t.ppf(0.975, len(baseline.capture_ids) - count))
        * baseline.residual_std_hz
        * np.sqrt(1 + leverage)
    )
    return Prediction(frequency_hz=center, lower_hz=center - margin, upper_hz=center + margin)
