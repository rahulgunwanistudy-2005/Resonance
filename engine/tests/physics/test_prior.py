import pytest

from resonance.errors import EvidenceError
from resonance.physics.prior import beam_frequency_band


def test_beam_prior_scales_with_inverse_length_squared() -> None:
    short = beam_frequency_band(
        length_m=1, young_pa=200e9, inertia_m4=1e-10, mass_per_m=0.1, support="cantilever"
    )
    long = beam_frequency_band(
        length_m=2, young_pa=200e9, inertia_m4=1e-10, mass_per_m=0.1, support="cantilever"
    )
    assert short.low_hz / long.low_hz == pytest.approx(4)
    assert short.high_hz / long.high_hz == pytest.approx(4)


def test_invalid_beam_parameters_are_refused() -> None:
    with pytest.raises(EvidenceError):
        beam_frequency_band(
            length_m=0, young_pa=200e9, inertia_m4=1e-10, mass_per_m=0.1, support="cantilever"
        )
