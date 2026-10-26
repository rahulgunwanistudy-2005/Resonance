import numpy as np
import pytest

from resonance.errors import EvidenceError
from resonance.modal.uncertainty import bootstrap_frequency_ci
from resonance.models import FrequencyBand


def test_seeded_residual_bootstrap_has_resolution_floor() -> None:
    rng = np.random.default_rng(3)
    time = np.arange(480) / 60
    values = np.sin(2 * np.pi * 7.1 * time) + rng.normal(0, 0.03, len(time))
    kwargs = {"repeats": 20, "seed": 42}
    first = bootstrap_frequency_ci(values, 60, FrequencyBand(low_hz=1, high_hz=15), **kwargs)
    second = bootstrap_frequency_ci(values, 60, FrequencyBand(low_hz=1, high_hz=15), **kwargs)
    assert first == second
    assert first[0] < 7.1 < first[1]
    assert first[1] - first[0] >= 0.25 - 1e-10


def test_invalid_bootstrap_configuration_is_refused() -> None:
    with pytest.raises(EvidenceError):
        bootstrap_frequency_ci(np.zeros(480), 60, FrequencyBand(low_hz=1, high_hz=15), repeats=1)


def test_longer_analysis_window_changes_bootstrap_resolution() -> None:
    time = np.arange(480) / 60
    values = np.sin(2 * np.pi * 7.1 * time)
    short = bootstrap_frequency_ci(
        values, 60, FrequencyBand(low_hz=1, high_hz=15), repeats=20, window_seconds=4
    )
    long = bootstrap_frequency_ci(
        values, 60, FrequencyBand(low_hz=1, high_hz=15), repeats=20, window_seconds=8
    )
    assert long[1] - long[0] < short[1] - short[0]
