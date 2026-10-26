import pytest

from resonance.errors import EvidenceError
from resonance.physics.baseline import HealthyCapture, fit_baseline, predict


def test_temperature_correction_and_no_extrapolation() -> None:
    healthy = [
        HealthyCapture(capture_id=str(index), frequency_hz=8 - 0.01 * temp, temperature_c=temp)
        for index, temp in enumerate((10, 15, 20, 25, 30))
    ]
    baseline = fit_baseline("bridge", healthy)
    assert predict(baseline, 20).frequency_hz == pytest.approx(7.8)
    with pytest.raises(EvidenceError, match="outside"):
        predict(baseline, 35)


def test_baseline_requires_unique_designated_captures() -> None:
    item = HealthyCapture(capture_id="same", frequency_hz=8, temperature_c=20)
    with pytest.raises(EvidenceError):
        fit_baseline("bridge", [item] * 3)
