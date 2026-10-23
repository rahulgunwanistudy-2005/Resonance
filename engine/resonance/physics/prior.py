import math
from typing import Literal

from resonance.errors import EvidenceError
from resonance.models import FrequencyBand


def beam_frequency_band(
    *,
    length_m: float,
    young_pa: float,
    inertia_m4: float,
    mass_per_m: float,
    support: Literal["cantilever", "simply_supported"],
    relative_uncertainty: float = 0.5,
) -> FrequencyBand:
    """Euler–Bernoulli bending prior; inputs are assumptions, not enrollment facts."""
    values = (length_m, young_pa, inertia_m4, mass_per_m, relative_uncertainty)
    if not all(math.isfinite(v) and v > 0 for v in values) or relative_uncertainty >= 1:
        raise EvidenceError("Beam parameters must be positive and uncertainty must be below one")
    if support not in ("cantilever", "simply_supported"):
        raise EvidenceError("Unknown support condition; provide an explicit measured prior")
    beta = 1.8751040687 if support == "cantilever" else math.pi
    first = beta**2 / (2 * math.pi * length_m**2) * math.sqrt(young_pa * inertia_m4 / mass_per_m)
    return FrequencyBand(
        low_hz=first * (1 - relative_uncertainty), high_hz=first * (1 + relative_uncertainty)
    )
