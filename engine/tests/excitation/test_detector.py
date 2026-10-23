from pathlib import Path

import numpy as np
import pytest

from resonance.errors import EvidenceError
from resonance.excitation.detector import ExcitationTrigger, VehicleDetector, motion_energy


def test_heavy_vehicle_exit_is_debounced() -> None:
    trigger = ExcitationTrigger(absent_samples=3)
    assert not trigger.observe(heavy_vehicle_present=True, energy=10)
    assert not trigger.observe(heavy_vehicle_present=False, energy=0)
    assert not trigger.observe(heavy_vehicle_present=False, energy=0)
    assert trigger.observe(heavy_vehicle_present=False, energy=0)
    assert trigger.source == "heavy_vehicle_exit"
    assert not trigger.observe(heavy_vehicle_present=False, energy=0)


def test_motion_fallback_is_explicit_and_debounced() -> None:
    trigger = ExcitationTrigger(absent_samples=2)
    assert not trigger.observe(heavy_vehicle_present=None, energy=4)
    assert not trigger.observe(heavy_vehicle_present=None, energy=0)
    assert trigger.observe(heavy_vehicle_present=None, energy=0)
    assert trigger.source == "motion_energy"


def test_detector_loss_cannot_be_mistaken_for_vehicle_exit() -> None:
    trigger = ExcitationTrigger(absent_samples=1)
    assert not trigger.observe(heavy_vehicle_present=True, energy=4)
    assert not trigger.observe(heavy_vehicle_present=None, energy=0)
    assert not trigger.observe(heavy_vehicle_present=None, energy=4)
    assert trigger.observe(heavy_vehicle_present=None, energy=0)
    assert trigger.source == "motion_energy"


def test_energy_is_wide_typed_and_shape_checked() -> None:
    first = np.zeros((16, 16), dtype=np.uint8)
    second = np.full((16, 16), 255, dtype=np.uint8)
    assert motion_energy(first, second) == pytest.approx(255**2)
    with pytest.raises(EvidenceError):
        motion_energy(first, second[:8])


def test_missing_model_is_refused(tmp_path: Path) -> None:
    with pytest.raises(EvidenceError):
        VehicleDetector(tmp_path / "missing.onnx")


def test_detector_blank_frame_when_model_available() -> None:
    model = Path("models/object_detection_yolox_2022nov.onnx")
    if not model.is_file():
        pytest.skip("Optional detector model is not downloaded in numerical CI")
    detector = VehicleDetector(model)
    assert not detector.detect(np.zeros((256, 384, 3), dtype=np.uint8))
