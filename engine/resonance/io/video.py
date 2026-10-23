"""Local-file reader with explicit acquisition-rate provenance and bounded ROI memory."""

import json
import shutil
import subprocess
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.config import MeasurementConfig
from resonance.errors import EvidenceError
from resonance.models import Capture, Roi, VideoMetadata


def probe_video(capture: Capture, config: MeasurementConfig) -> VideoMetadata:
    path = capture.path.resolve(strict=True)
    if not path.is_file() or path.stat().st_size > config.max_upload_bytes:
        raise EvidenceError("Video is missing or exceeds the upload limit")
    executable = shutil.which("ffprobe")
    if executable is None:
        raise EvidenceError("ffprobe is required to validate video timing; install FFmpeg")
    try:
        completed = subprocess.run(
            [
                executable,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "format=duration:stream=width,height,avg_frame_rate,nb_frames,duration:"
                "frame=best_effort_timestamp_time",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        payload = json.loads(completed.stdout)
        stream = payload["streams"][0]
        duration = float(stream.get("duration") or payload["format"]["duration"])
        playback_fps = float(Fraction(stream["avg_frame_rate"]))
        times = np.asarray(
            [float(frame["best_effort_timestamp_time"]) for frame in payload["frames"]],
            dtype=np.float64,
        )
        width, height = int(stream["width"]), int(stream["height"])
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        ZeroDivisionError,
    ) as exc:
        raise EvidenceError(
            "Video timing could not be decoded; re-export a constant-rate clip"
        ) from exc
    if not np.isfinite(duration) or duration <= 0 or duration > config.max_duration_seconds:
        raise EvidenceError("Video duration exceeds the limit or is invalid; trim the clip")
    if width <= 0 or height <= 0 or width * height > config.max_frame_pixels:
        raise EvidenceError("Frame dimensions exceed the processing limit; downscale the clip")
    if len(times) < 32 or not np.isfinite(times).all():
        raise EvidenceError("Video has too few frames or no reliable frame timestamps")
    intervals = np.diff(times)
    median = float(np.median(intervals))
    if median <= 0 or np.any(intervals <= 0):
        raise EvidenceError("Frame timestamps are not strictly increasing")
    if float(np.max(np.abs(intervals - median)) / median) > 0.05:
        raise EvidenceError("Variable-rate or dropped frames detected; record constant-rate video")
    actual_playback_rate = 1 / median
    if abs(playback_fps - actual_playback_rate) / actual_playback_rate > 0.02:
        raise EvidenceError("Container fps disagrees with frame timestamps; verify capture timing")
    if not capture.acquisition_fps_verified or capture.acquisition_fps is None:
        raise EvidenceError(
            "Frame timestamps establish playback timing, not slow-motion acquisition timing. "
            "Confirm the camera acquisition fps before running a measurement."
        )
    return VideoMetadata(
        width=width,
        height=height,
        frame_count=len(times),
        playback_fps=actual_playback_rate,
        acquisition_fps=capture.acquisition_fps,
        duration_seconds=len(times) / capture.acquisition_fps,
        timestamps_seconds=(np.arange(len(times)) / capture.acquisition_fps).tolist(),
        timing_source="ffprobe PTS plus externally confirmed acquisition fps",
    )


def read_roi_frames(
    path: Path,
    rois: list[Roi],
    metadata: VideoMetadata,
    config: MeasurementConfig,
    frame_transform: Callable[[NDArray[np.uint8]], NDArray[np.uint8]] | None = None,
) -> dict[str, list[NDArray[np.uint8]]]:
    if len(rois) > config.max_rois or len({roi.id for roi in rois}) != len(rois):
        raise EvidenceError("Use a bounded number of ROIs with distinct identifiers")
    for roi in rois:
        if roi.x + roi.width > metadata.width or roi.y + roi.height > metadata.height:
            raise EvidenceError(f"ROI {roi.id} extends outside the video; select it again")
        if roi.width * roi.height > config.max_roi_pixels:
            raise EvidenceError(f"ROI {roi.id} is too large; select a smaller textured area")
    expected_bytes = sum(roi.width * roi.height for roi in rois) * metadata.frame_count
    if expected_bytes > 256 * 1024**2:
        raise EvidenceError("ROI memory budget exceeded; shorten the clip or reduce ROI sizes")
    reader = cv2.VideoCapture(str(path))
    if not reader.isOpened():
        raise EvidenceError("Video codec is unsupported; re-export the clip")
    frames: dict[str, list[NDArray[np.uint8]]] = {roi.id: [] for roi in rois}
    try:
        for _ in range(metadata.frame_count):
            ok, frame = reader.read()
            if not ok:
                raise EvidenceError("Video ended before the timestamped frame count")
            if frame.shape[:2] != (metadata.height, metadata.width):
                raise EvidenceError("Video dimensions change during capture")
            if frame_transform is not None:
                frame = frame_transform(np.asarray(frame, dtype=np.uint8))
            for roi in rois:
                crop = frame[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                frames[roi.id].append(np.asarray(gray, dtype=np.uint8).copy())
    finally:
        reader.release()
    return frames
