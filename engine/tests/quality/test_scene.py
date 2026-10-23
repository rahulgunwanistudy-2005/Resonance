import numpy as np
import pytest

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.models import FrequencyBand
from resonance.quality.scene import assess_scene, check_sampling, gray_float


def test_low_texture_and_exposure_are_reported() -> None:
    quality = assess_scene(np.zeros((64, 64), dtype=np.uint8), MeasurementConfig())
    assert not quality.accepted
    assert len(quality.reasons) == 3


def test_textured_scene_passes() -> None:
    image = np.random.default_rng(42).integers(30, 220, size=(64, 64), dtype=np.uint8)
    assert assess_scene(image, MeasurementConfig()).accepted


def test_invalid_channel_shape_is_an_evidence_error() -> None:
    with pytest.raises(EvidenceError, match="channels"):
        gray_float(np.zeros((32, 32, 2), np.uint8))


@pytest.mark.parametrize("fps", [0, -1, float("nan"), 24])
def test_invalid_sample_rate_is_refused(fps: float) -> None:
    with pytest.raises(EvidenceError):
        check_sampling(fps, FrequencyBand(low_hz=1, high_hz=15))
