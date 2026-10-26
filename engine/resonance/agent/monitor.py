"""Observe a configured camera, trigger free-decay capture and submit durable jobs."""

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.excitation.detector import Detection, ExcitationTrigger, motion_energy
from resonance.io.stream import StreamFrame
from resonance.models import Bridge, Capture, Contract
from resonance.quality.scene import assess_scene, check_sampling


class Detector(Protocol):
    def detect(self, frame: NDArray[np.uint8]) -> list[Detection]: ...


class MonitorConfig(Contract):
    source: str = Field(min_length=1, repr=False)
    acquisition_fps: float = Field(gt=0, le=240)
    acquisition_fps_verified: bool
    observe_hz: float = Field(default=2, ge=2, le=5)
    capture_seconds: float = Field(default=8, ge=4, le=60)
    energy_threshold: float = Field(default=2, gt=0)
    temperature_c: float | None = Field(default=None, ge=-100, le=100)


def monitor(
    stream: Iterable[StreamFrame],
    *,
    bridge: Bridge,
    config: MonitorConfig,
    output_dir: Path,
    submit: Callable[[Capture], None],
    detector: Detector | None = None,
    sampling_multiplier: Callable[[], float] = lambda: 1,
) -> dict[str, int]:
    if not config.acquisition_fps_verified:
        raise EvidenceError("Confirm the camera acquisition rate before watching a source")
    check_sampling(config.acquisition_fps, bridge.band)
    output_dir.mkdir(parents=True, exist_ok=True)
    trigger = ExcitationTrigger(energy_threshold=config.energy_threshold)
    previous: NDArray[np.uint8] | None = None
    last_observed = -float("inf")
    writer = None
    recording: Capture | None = None
    previous_recorded: float | None = None
    last_source_timestamp: float | None = None
    count = 0
    stats = {"observations": 0, "captures": 0, "refusals": 0}
    try:
        for frame in stream:
            image, timestamp = frame.image, frame.timestamp_seconds
            if not np.isfinite(timestamp) or timestamp < 0:
                raise EvidenceError("Camera decoder did not provide usable frame timestamps")
            if last_source_timestamp is not None and timestamp <= last_source_timestamp:
                raise EvidenceError("Camera timestamps must increase on every decoded frame")
            last_source_timestamp = timestamp
            if writer is not None and recording is not None:
                interval = (
                    timestamp - previous_recorded
                    if previous_recorded is not None
                    else 1 / config.acquisition_fps
                )
                tolerance = max(0.05 / config.acquisition_fps, 0.0011)
                if abs(interval - 1 / config.acquisition_fps) > tolerance:
                    writer.release()
                    writer = None
                    recording.path.unlink(missing_ok=True)
                    recording = None
                    stats["refusals"] += 1
                    trigger = ExcitationTrigger(energy_threshold=config.energy_threshold)
                    previous = None
                    continue
                writer.write(image)
                previous_recorded = timestamp
                count += 1
                if recording.path.stat().st_size > MeasurementConfig().max_upload_bytes:
                    raise EvidenceError("Camera recording exceeded the bounded upload size")
                if count >= round(config.capture_seconds * config.acquisition_fps):
                    writer.release()
                    writer = None
                    submit(recording)
                    stats["captures"] += 1
                    recording = None
                    previous = None
                    last_observed = timestamp
                continue
            interval = 1 / min(5, config.observe_hz * max(1, sampling_multiplier()))
            if timestamp < last_observed:
                raise EvidenceError("Camera timestamps moved backwards")
            if timestamp - last_observed < interval - 1e-6:
                continue
            last_observed = timestamp
            stats["observations"] += 1
            detections = detector.detect(image) if detector else []
            present = (
                any(item.label in {"bus", "train", "truck"} for item in detections)
                if detector
                else None
            )
            usable = []
            for roi in bridge.rois:
                if roi.x + roi.width > image.shape[1] or roi.y + roi.height > image.shape[0]:
                    continue
                crop = image[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
                if assess_scene(crop, MeasurementConfig()).accepted:
                    usable.append(roi)
            energy = motion_energy(previous, image) if previous is not None else 0
            previous = image.copy()
            excited = trigger.observe(heavy_vehicle_present=present, energy=energy)
            if not excited:
                continue
            if not usable:
                stats["refusals"] += 1
                continue
            key = uuid4().hex
            recording = Capture(
                id=key,
                bridge_id=bridge.id,
                path=output_dir / f"{key}.avi",
                band=bridge.band,
                rois=usable,
                calibration=bridge.calibration,
                temperature_c=config.temperature_c,
                acquisition_fps=config.acquisition_fps,
                acquisition_fps_verified=True,
                trigger_source=trigger.source or "motion_energy",
            )
            writer = cv2.VideoWriter(
                str(recording.path),
                cv2.VideoWriter.fourcc(*"MJPG"),
                config.acquisition_fps,
                (image.shape[1], image.shape[0]),
            )
            if not writer.isOpened():
                raise EvidenceError("Camera recording encoder did not start")
            previous_recorded = timestamp
            count = 0
    finally:
        if writer is not None:
            writer.release()
            if recording is not None:
                recording.path.unlink(missing_ok=True)
                stats["refusals"] += 1
    return stats
