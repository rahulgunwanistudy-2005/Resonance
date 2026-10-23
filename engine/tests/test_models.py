import pytest
from pydantic import ValidationError

from resonance.models import DisplacementSeries, FrequencyBand, Roi


def test_prior_rejects_reversed_or_nonfinite_band() -> None:
    with pytest.raises(ValidationError):
        FrequencyBand(low_hz=12, high_hz=1)
    with pytest.raises(ValidationError):
        FrequencyBand(low_hz=1, high_hz=float("nan"))


def test_roi_rejects_invalid_geometry() -> None:
    with pytest.raises(ValidationError):
        Roi(id="deck", x=-1, y=0, width=64, height=64)


def test_series_rejects_misaligned_arrays() -> None:
    with pytest.raises(ValidationError):
        DisplacementSeries(
            roi_id="deck",
            method="riesz",
            fps=60,
            time_seconds=list(range(16)),
            displacement_px=[0.0] * 16,
            response=[],
        )
