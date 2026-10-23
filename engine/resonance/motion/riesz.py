"""Multiscale Riesz quadrature; local phase gradients resolve small vertical translations."""

from collections.abc import Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.errors import EvidenceError
from resonance.models import DisplacementSeries
from resonance.quality.scene import gray_float


def _quadrature(image: NDArray[np.float32]) -> NDArray[np.complex128]:
    kernel = np.array([1, 4, 6, 4, 1], dtype=np.float32) / 16
    smooth = cv2.filter2D(image, -1, np.outer(kernel, kernel))
    band = image - smooth
    fy = np.fft.fftfreq(image.shape[0])[:, None]
    fx = np.fft.fftfreq(image.shape[1])[None, :]
    radius = np.hypot(fy, fx)
    multiplier = -1j * fy / np.maximum(radius, np.finfo(float).eps)
    riesz_y = np.fft.ifft2(np.fft.fft2(band) * multiplier).real
    return np.asarray(band + 1j * riesz_y, dtype=np.complex128)


def extract_riesz(
    frames: Sequence[NDArray[np.generic]], fps: float, roi_id: str, *, levels: int = 2
) -> DisplacementSeries:
    if len(frames) < 16 or fps <= 0 or levels < 1:
        raise EvidenceError("Riesz needs sixteen frames, a positive rate and at least one level")
    reference_image = gray_float(frames[0])
    if min(reference_image.shape) < 16 * 2 ** (levels - 1):
        raise EvidenceError("ROI is too small for the requested Riesz pyramid")
    references: list[NDArray[np.complex128]] = []
    gradients: list[NDArray[np.float64]] = []
    weights: list[NDArray[np.float64]] = []
    image = reference_image
    for _ in range(levels):
        ref = _quadrature(image)
        power = np.abs(ref) ** 2
        gradient = np.imag(np.conj(ref) * np.gradient(ref, axis=0)) / np.maximum(power, 1e-9)
        weight = power.copy()
        weight[:4] = weight[-4:] = 0
        weight[:, :4] = weight[:, -4:] = 0
        weight[(power < np.percentile(power, 30)) | (np.abs(gradient) > np.pi)] = 0
        references.append(ref)
        gradients.append(gradient)
        weights.append(weight)
        image = np.asarray(cv2.pyrDown(image), dtype=np.float32)
    displacement: list[float] = []
    responses: list[float] = []
    for frame in frames:
        image = gray_float(frame)
        if image.shape != reference_image.shape:
            raise EvidenceError("ROI shape changes during capture")
        estimates: list[float] = []
        for level, (ref, gradient, weight) in enumerate(
            zip(references, gradients, weights, strict=True)
        ):
            current = _quadrature(image)
            delta = np.angle(current * np.conj(ref))
            denominator = float(np.sum(weight * gradient**2))
            if denominator <= 1e-9:
                raise EvidenceError("Riesz phase has insufficient vertical texture")
            shift = -float(np.sum(weight * delta * gradient)) / denominator
            estimates.append(shift * 2**level)
            image = np.asarray(cv2.pyrDown(image), dtype=np.float32)
        displacement.append(float(np.median(estimates)))
        responses.append(float(1 / (1 + np.std(estimates))))
    return DisplacementSeries(
        roi_id=roi_id,
        method="riesz",
        fps=fps,
        time_seconds=(np.arange(len(frames)) / fps).tolist(),
        displacement_px=displacement,
        response=responses,
    )
