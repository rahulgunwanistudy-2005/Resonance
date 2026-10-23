import math

from resonance.errors import EvidenceError
from resonance.models import Calibration


def calibrate_scale(
    first: tuple[float, float], second: tuple[float, float], length_mm: float
) -> Calibration:
    if not all(math.isfinite(x) for point in (first, second) for x in point):
        raise EvidenceError("Calibration points must be finite image coordinates")
    distance = math.dist(first, second)
    if distance <= 1 or not math.isfinite(length_mm) or length_mm <= 0:
        raise EvidenceError("Select distinct points and enter a positive reference length")
    return Calibration(
        mm_per_pixel=length_mm / distance, reference_length_mm=length_mm, points=(first, second)
    )
