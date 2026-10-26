"""Bounded OpenCV stream reader retaining decoder presentation timestamps."""

from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urlsplit

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.errors import EvidenceError


@dataclass(frozen=True)
class StreamFrame:
    image: NDArray[np.uint8]
    timestamp_seconds: float


def frames(source: str, *, max_pixels: int = 3840 * 2160) -> Iterator[StreamFrame]:
    scheme = urlsplit(source).scheme
    if scheme and scheme not in {"rtsp", "rtsps", "http", "https"}:
        raise EvidenceError("Camera source must be a video file, RTSP or HLS URL")
    capture = cv2.VideoCapture(
        source,
        cv2.CAP_FFMPEG,
        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000],
    )
    if not capture.isOpened():
        raise EvidenceError("Camera source could not be opened; check its private configuration")
    try:
        while True:
            ok, image = capture.read()
            if not ok:
                return
            if image.shape[0] * image.shape[1] > max_pixels:
                raise EvidenceError("Camera frame exceeds the configured pixel bound")
            yield StreamFrame(
                np.asarray(image, dtype=np.uint8), float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000
            )
    finally:
        capture.release()
