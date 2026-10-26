"""Magnify measured vertical ROI motion, with the rendering approximation explicit."""

import subprocess
from pathlib import Path

import cv2
import numpy as np
from scipy import signal

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.io.video import probe_video, read_roi_frames
from resonance.models import Capture, ModalEstimate


def magnify(capture: Capture, estimate: ModalEstimate, path: Path, gain: float = 12) -> None:
    if not 1 < gain <= 30 or estimate.selected is None or estimate.spectrum is None:
        raise EvidenceError("Magnification needs a measured trace and bounded gain")
    if capture.stabilize:
        raise EvidenceError(
            "Evidence magnification of stabilized captures needs the stabilized crop cache"
        )
    region = next(roi for roi in capture.rois if roi.id == estimate.selected.roi_id)
    metadata = probe_video(capture, MeasurementConfig())
    count = len(estimate.selected.displacement_px)
    metadata = metadata.model_copy(update={"frame_count": count})
    frames = read_roi_frames(capture.path, [region], metadata, MeasurementConfig())[region.id]
    frequency = estimate.spectrum.peak_hz
    band = [max(0.1, frequency * 0.8), min(estimate.selected.fps * 0.45, frequency * 1.2)]
    filtered = signal.sosfiltfilt(
        signal.butter(2, band, btype="bandpass", fs=estimate.selected.fps, output="sos"),
        np.asarray(estimate.selected.displacement_px),
    )
    intermediate = path.with_suffix(".avi")
    writer = cv2.VideoWriter(
        str(intermediate),
        cv2.VideoWriter.fourcc(*"MJPG"),
        estimate.selected.fps,
        (region.width, region.height),
    )
    if not writer.isOpened():
        raise EvidenceError("Evidence clip encoder did not start")
    try:
        for index, frame in enumerate(frames):
            shift = float(filtered[index]) * (gain - 1)
            transform = np.array([[1, 0, 0], [0, 1, shift]], np.float32)
            image = cv2.warpAffine(
                frame, transform, (region.width, region.height), borderMode=cv2.BORDER_REFLECT_101
            )
            writer.write(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))
    finally:
        writer.release()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(intermediate),
            "-c:v",
            "libvpx-vp9",
            "-crf",
            "25",
            "-b:v",
            "0",
            str(path),
        ],
        check=True,
        timeout=60,
    )
    intermediate.unlink()
