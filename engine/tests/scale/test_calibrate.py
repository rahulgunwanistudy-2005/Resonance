import pytest

from resonance.errors import EvidenceError
from resonance.scale.calibrate import calibrate_scale


def test_two_point_scale() -> None:
    assert calibrate_scale((10, 10), (110, 10), 30).mm_per_pixel == pytest.approx(0.3)


@pytest.mark.parametrize("point,length", [((0, 0), 10), ((100, 0), -1), ((float("nan"), 0), 10)])
def test_invalid_scale_is_refused(point: tuple[float, float], length: float) -> None:
    with pytest.raises(EvidenceError):
        calibrate_scale((0, 0), point, length)
