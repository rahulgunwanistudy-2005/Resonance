from collections.abc import Callable, Sequence

import numpy as np
import pytest
from eval.synthetic import SyntheticConfig, generate
from numpy.typing import NDArray

from resonance.errors import EvidenceError
from resonance.modal.spectrum import estimate_spectrum
from resonance.models import DisplacementSeries, FrequencyBand
from resonance.motion.phase_corr import extract_phase_correlation
from resonance.motion.riesz import extract_riesz

Extractor = Callable[[Sequence[NDArray[np.generic]], float, str], DisplacementSeries]


@pytest.mark.parametrize("extractor", [extract_phase_correlation, extract_riesz])
def test_extractors_recover_frequency(extractor: Extractor) -> None:
    config = SyntheticConfig(roi_size=64, duration_seconds=4, amplitude_rms_px=0.5)
    frames, _ = generate(config)
    series = extractor(frames, config.fps, "deck")
    spectrum = estimate_spectrum(
        np.asarray(series.displacement_px), config.fps, FrequencyBand(low_hz=1, high_hz=15)
    )
    assert abs(spectrum.peak_hz - config.frequency_hz) < 0.05
    assert len(series.response) == len(frames)


@pytest.mark.parametrize("extractor", [extract_phase_correlation, extract_riesz])
def test_extractors_reject_empty_and_changing_frames(extractor: Extractor) -> None:
    with pytest.raises(EvidenceError):
        extractor([], 60, "deck")
    rng = np.random.default_rng(42)
    frames = [rng.normal(size=(64, 64)).astype(np.float32) for _ in range(16)]
    frames[-1] = np.zeros((32, 32), np.float32)
    with pytest.raises(EvidenceError, match="shape"):
        extractor(frames, 60, "deck")


def test_riesz_rejects_no_vertical_texture() -> None:
    with pytest.raises(EvidenceError, match="texture"):
        extract_riesz([np.zeros((64, 64), np.float32)] * 16, 60, "deck")


def test_generator_reproduces_pixels_with_fixed_seed() -> None:
    config = SyntheticConfig(roi_size=32, duration_seconds=2)
    frames, truth = generate(config)
    repeated, repeated_truth = generate(config)
    np.testing.assert_array_equal(frames[17], repeated[17])
    np.testing.assert_array_equal(truth, repeated_truth)
