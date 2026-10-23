from pathlib import Path

import cv2
import numpy as np
import pytest
from eval.synthetic import SyntheticConfig, generate

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.io.video import probe_video
from resonance.models import Capture, FrequencyBand, Roi
from resonance.pipeline import measure


@pytest.fixture
def capture(tmp_path: Path) -> Capture:
    path = tmp_path / "fixture.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"MJPG"), 60, (96, 96))
    assert writer.isOpened()
    frames, _ = generate(SyntheticConfig(roi_size=96, duration_seconds=4, amplitude_rms_px=0.5))
    try:
        for frame in frames:
            writer.write(cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_GRAY2BGR))
    finally:
        writer.release()
    return Capture(
        id="fixture",
        bridge_id="desk",
        path=path,
        band=FrequencyBand(low_hz=1, high_hz=15),
        rois=[Roi(id="deck", x=0, y=0, width=96, height=96)],
        acquisition_fps=60,
        acquisition_fps_verified=True,
    )


def test_file_to_measurement_end_to_end(capture: Capture) -> None:
    result = measure(capture, MeasurementConfig(bootstrap_repeats=20))
    assert result.outcome == "MEASURED", result.reasons
    assert result.spectrum is not None
    assert abs(result.spectrum.peak_hz - 7.1) < 0.05
    assert result.input_sha256 is not None


def test_playback_fps_cannot_silently_be_treated_as_acquisition_fps(capture: Capture) -> None:
    capture.acquisition_fps_verified = False
    with pytest.raises(EvidenceError, match="acquisition"):
        probe_video(capture, MeasurementConfig())


def test_oversized_upload_and_invalid_roi_are_refused(capture: Capture) -> None:
    result = measure(capture, MeasurementConfig(max_upload_bytes=1))
    assert result.outcome == "INSUFFICIENT_EVIDENCE"
    capture.rois[0].x = 10000
    result = measure(capture)
    assert result.outcome == "INSUFFICIENT_EVIDENCE"
    assert any("outside" in reason for reason in result.reasons)


def test_missing_file_is_an_evidence_failure(tmp_path: Path) -> None:
    capture = Capture(
        id="missing",
        bridge_id="desk",
        path=tmp_path / "missing.mp4",
        band=FrequencyBand(low_hz=1, high_hz=15),
        rois=[Roi(id="deck", x=0, y=0, width=64, height=64)],
    )
    assert measure(capture).outcome == "INSUFFICIENT_EVIDENCE"


def test_requested_stabilization_never_silently_falls_back(capture: Capture) -> None:
    capture.stabilize = True
    capture.structure_box = Roi(id="entire-structure", x=0, y=0, width=96, height=96)
    result = measure(capture)
    assert result.outcome == "INSUFFICIENT_EVIDENCE"
    assert not result.stabilization_applied
    assert any("models are missing" in reason for reason in result.reasons)
