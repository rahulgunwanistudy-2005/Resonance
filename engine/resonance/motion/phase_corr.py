from collections.abc import Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.errors import EvidenceError
from resonance.models import DisplacementSeries
from resonance.quality.scene import gray_float


def extract_phase_correlation(
    frames: Sequence[NDArray[np.generic]], fps: float, roi_id: str
) -> DisplacementSeries:
    if len(frames) < 16 or fps <= 0:
        raise EvidenceError("Use at least sixteen frames at a positive acquisition rate")
    reference = gray_float(frames[0])
    height, width = reference.shape
    window = cv2.createHanningWindow((width, height), cv2.CV_32F)
    displacement = [0.0]
    response = [1.0]
    for frame in frames[1:]:
        current = gray_float(frame)
        if current.shape != reference.shape:
            raise EvidenceError("ROI shape changes during capture")
        # OpenCV applies the window in place, so protect the persistent reference.
        shift, confidence = cv2.phaseCorrelate(reference.copy(), current.copy(), window.copy())
        displacement.append(float(shift[1]))
        response.append(float(confidence))
    return DisplacementSeries(
        roi_id=roi_id,
        method="phase_correlation",
        fps=fps,
        time_seconds=(np.arange(len(frames)) / fps).tolist(),
        displacement_px=displacement,
        response=response,
    )
