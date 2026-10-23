from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from resonance.errors import EvidenceError
from resonance.models import Capture, FrequencyBand, Roi
from resonance.stabilize.ego_motion import EgoMotion


def test_stabilization_requires_models_and_structure_box(tmp_path: Path) -> None:
    with pytest.raises(EvidenceError, match="models"):
        EgoMotion(tmp_path / "missing.onnx", tmp_path / "missing2.onnx", [])
    with pytest.raises(ValidationError, match="entire moving structure"):
        Capture(
            id="handheld",
            bridge_id="desk",
            path=tmp_path / "video.mp4",
            band=FrequencyBand(low_hz=1, high_hz=15),
            stabilize=True,
            rois=[Roi(id="deck", x=20, y=20, width=64, height=64)],
        )


def test_features_exclude_entire_structure_when_models_available() -> None:
    aliked = Path("models/aliked-n16rot-top1k-640.onnx")
    lightglue = Path("models/aliked_lightglue.onnx")
    if not aliked.is_file() or not lightglue.is_file():
        pytest.skip("Optional learned models are not part of the numerical CI installation")
    structure = Roi(id="structure", x=96, y=80, width=192, height=96)
    stabilizer = EgoMotion(aliked, lightglue, [structure])
    image = np.random.default_rng(42).integers(0, 255, size=(256, 384), dtype=np.uint8)
    stabilizer.apply(image)
    assert stabilizer.reference_points is not None
    points = stabilizer.reference_points
    inside = (
        (points[:, 0] >= 88) & (points[:, 0] <= 296) & (points[:, 1] >= 72) & (points[:, 1] <= 184)
    )
    assert not inside.any()
    translated = cv2.warpAffine(image, np.array([[1, 0, 0], [0, 1, 2]], np.float32), (384, 256))
    corrected = stabilizer.apply(np.asarray(translated, dtype=np.uint8))
    assert corrected.shape == image.shape
