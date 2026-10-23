import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from resonance.errors import EvidenceError
from resonance.modal.spectrum import estimate_spectrum
from resonance.models import FrequencyBand


@given(st.floats(min_value=2, max_value=12, allow_nan=False, allow_infinity=False))
@settings(max_examples=12, deadline=None)
def test_known_frequency_is_recovered(frequency: float) -> None:
    time = np.arange(480) / 60
    values = 0.4 * np.sin(2 * np.pi * frequency * time) + time * 0.003
    result = estimate_spectrum(values, 60, FrequencyBand(low_hz=1, high_hz=15))
    assert abs(result.peak_hz - frequency) < 0.01
    assert abs(result.amplitude_rms_px - 0.4 / np.sqrt(2)) < 0.01


def test_no_motion_and_nonfinite_inputs_are_refused() -> None:
    for values in (np.zeros(480), np.full(480, np.nan), np.zeros((4, 120))):
        with pytest.raises(EvidenceError):
            estimate_spectrum(values, 60, FrequencyBand(low_hz=1, high_hz=15))


def test_aliasing_and_boundary_peaks_are_refused() -> None:
    time = np.arange(480) / 60
    with pytest.raises(EvidenceError, match="fps"):
        estimate_spectrum(np.sin(time), 24, FrequencyBand(low_hz=1, high_hz=15))
    with pytest.raises(EvidenceError, match="boundary"):
        estimate_spectrum(np.sin(2 * np.pi * time), 60, FrequencyBand(low_hz=1, high_hz=15))
