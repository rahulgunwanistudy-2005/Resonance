import numpy as np
import pytest

from resonance.errors import EvidenceError
from resonance.modal.fdd import decompose
from resonance.models import DisplacementSeries, FrequencyBand


def test_fdd_recovers_relative_mode_shape() -> None:
    time = np.arange(480) / 60
    mode = np.sin(2 * np.pi * 7 * time)
    series = [
        DisplacementSeries(
            roi_id=f"roi-{index}",
            method="riesz",
            fps=60,
            time_seconds=time.tolist(),
            displacement_px=(gain * mode).tolist(),
            response=[1.0] * len(time),
        )
        for index, gain in enumerate((1, -0.5, 0.25))
    ]
    result = decompose(series, FrequencyBand(low_hz=1, high_hz=15))
    assert result.peak_bin_hz == pytest.approx(7)
    np.testing.assert_allclose(result.mode_shape_real, [1, -0.5, 0.25], atol=1e-6)
    np.testing.assert_allclose(result.mode_shape_imag, 0, atol=1e-6)


def test_fdd_rejects_missing_rois() -> None:
    with pytest.raises(EvidenceError, match="two"):
        decompose([], FrequencyBand(low_hz=1, high_hz=15))
