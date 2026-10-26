from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest

from resonance.agent.monitor import MonitorConfig, monitor
from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.io.stream import StreamFrame, frames
from resonance.models import Bridge, Capture, FrequencyBand, Roi
from resonance.pipeline import measure


def input_stream(*, drop_frame: bool = False) -> Iterator[StreamFrame]:
    rng = np.random.default_rng(42)
    texture = rng.integers(30, 225, (64, 96), dtype=np.uint8)
    texture = np.asarray(cv2.GaussianBlur(texture, (0, 0), 0.6), dtype=np.uint8)
    for index in range(720):
        if drop_frame and index == 250:
            continue
        shift = (
            8 * np.sin(2 * np.pi * 1.3 * index / 60)
            if 60 <= index < 120
            else 0.7 * np.sin(2 * np.pi * 7.1 * index / 60)
        )
        image = cv2.warpAffine(
            texture,
            np.array([[1, 0, 0], [0, 1, shift]], np.float32),
            (96, 64),
            borderMode=cv2.BORDER_REFLECT_101,
        )
        yield StreamFrame(
            np.asarray(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), dtype=np.uint8), index / 60
        )


def test_energy_exit_records_real_measurement_and_dropped_frames_refuse(tmp_path: Path) -> None:
    bridge = Bridge(
        id="beam",
        name="Generated monitor test",
        band=FrequencyBand(low_hz=1, high_hz=15),
        rois=[Roi(id="deck", x=16, y=0, width=64, height=64)],
    )
    config = MonitorConfig(
        source="private-operator-source",
        acquisition_fps=60,
        acquisition_fps_verified=True,
        observe_hz=5,
        capture_seconds=8,
        energy_threshold=500,
    )
    captures: list[Capture] = []
    stats = monitor(
        input_stream(), bridge=bridge, config=config, output_dir=tmp_path, submit=captures.append
    )
    assert stats["captures"] == 1
    assert captures[0].trigger_source == "motion_energy"
    result = measure(captures[0], MeasurementConfig(bootstrap_repeats=20))
    assert result.outcome == "MEASURED", result.reasons
    assert result.spectrum is not None and abs(result.spectrum.peak_hz - 7.1) < 0.05
    assert len(list(frames(str(captures[0].path)))) == 480
    bad: list[Capture] = []
    refused = monitor(
        input_stream(drop_frame=True),
        bridge=bridge,
        config=config,
        output_dir=tmp_path / "bad",
        submit=bad.append,
    )
    assert not bad and refused["refusals"] >= 1
    with pytest.raises(EvidenceError, match="increase"):
        monitor(
            [next(input_stream())] * 2,
            bridge=bridge,
            config=config,
            output_dir=tmp_path / "clock",
            submit=bad.append,
        )
