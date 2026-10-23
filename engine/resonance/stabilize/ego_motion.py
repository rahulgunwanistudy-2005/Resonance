"""ALIKED/LightGlue background anchors with LK tracking between network refreshes."""

from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.errors import EvidenceError
from resonance.models import Roi
from resonance.quality.scene import gray_float


class EgoMotion:
    def __init__(
        self,
        aliked_model: Path,
        lightglue_model: Path,
        rois: Sequence[Roi],
        *,
        refresh_frames: int = 30,
    ) -> None:
        if (
            not aliked_model.is_file()
            or not lightglue_model.is_file()
            or refresh_frames < 1
            or not rois
        ):
            raise EvidenceError(
                "Stabilization needs verified feature models and a positive refresh interval"
            )
        self.detector = cv2.dnn.readNetFromONNX(str(aliked_model), cv2.dnn.ENGINE_NEW)
        self.matcher = cv2.dnn.readNetFromONNX(str(lightglue_model), cv2.dnn.ENGINE_NEW)
        self.rois = rois
        self.refresh_frames = refresh_frames
        self.frame_index = 0
        self.reference_points: NDArray[np.float32] | None = None
        self.reference_normalized: NDArray[np.float32] | None = None
        self.reference_descriptors: NDArray[np.float32] | None = None
        self.anchor_points: NDArray[np.float32] | None = None
        self.previous_points: NDArray[np.float32] | None = None
        self.previous_gray: NDArray[np.uint8] | None = None
        self.image_shape: tuple[int, ...] | None = None

    def _features(
        self,
        frame: NDArray[np.uint8],
    ) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32]]:
        image = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if frame.ndim == 2 else frame
        blob = cv2.dnn.blobFromImage(image, 1 / 255, (640, 640), swapRB=True)
        self.detector.setInput(blob, "image")
        points, descriptors, scores = self.detector.forward(["keypoints", "descriptors", "scores"])
        normalized = np.asarray(points, dtype=np.float32).reshape(-1, 2)
        descriptors_array = np.asarray(descriptors, dtype=np.float32).reshape(-1, 128)
        score_array = np.asarray(scores, dtype=np.float32).reshape(-1)
        height, width = frame.shape[:2]
        pixels = (normalized + 1) * np.array([width, height], dtype=np.float32) / 2
        keep = (
            (pixels[:, 0] >= 0)
            & (pixels[:, 0] < width)
            & (pixels[:, 1] >= 0)
            & (pixels[:, 1] < height)
        )
        for roi in self.rois:
            # Margin protects against deck edges moving into the background mask.
            inside = (
                (pixels[:, 0] >= roi.x - 8)
                & (pixels[:, 0] <= roi.x + roi.width + 8)
                & (pixels[:, 1] >= roi.y - 8)
                & (pixels[:, 1] <= roi.y + roi.height + 8)
            )
            keep &= ~inside
        indices = np.flatnonzero(keep)
        indices = indices[np.argsort(score_array[indices])[-256:]]
        if len(indices) < 8:
            raise EvidenceError(
                "Too few static-background features; widen the view or use a tripod"
            )
        desc = descriptors_array[indices]
        desc /= np.maximum(np.linalg.norm(desc, axis=1, keepdims=True), 1e-12)
        return normalized[indices], np.asarray(pixels[indices], dtype=np.float32), desc

    def _match(
        self,
        frame: NDArray[np.uint8],
    ) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
        normalized, pixels, descriptors = self._features(frame)
        assert self.reference_normalized is not None
        assert self.reference_descriptors is not None
        assert self.reference_points is not None
        inputs = {
            "kpts0": self.reference_normalized[None],
            "kpts1": normalized[None],
            "desc0": self.reference_descriptors[None],
            "desc1": descriptors[None],
        }
        for key, value in inputs.items():
            self.matcher.setInput(value, key)
        pairs_raw, confidence_raw = self.matcher.forward(["matches0", "mscores0"])
        pairs: NDArray[np.int64] = np.asarray(pairs_raw, dtype=np.int64).reshape(-1, 2)
        confidence = np.asarray(confidence_raw, dtype=np.float32).reshape(-1)
        pairs = pairs[confidence >= 0.2]
        valid = (
            (pairs[:, 0] >= 0)
            & (pairs[:, 0] < len(self.reference_points))
            & (pairs[:, 1] >= 0)
            & (pairs[:, 1] < len(pixels))
        )
        pairs = pairs[valid]
        if len(pairs) < 8:
            raise EvidenceError(
                "Background matching failed; use a tripod or choose a clearer scene"
            )
        return self.reference_points[pairs[:, 0]], pixels[pairs[:, 1]]

    def apply(self, frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
        gray = np.asarray(gray_float(frame), dtype=np.uint8)
        if self.previous_gray is None:
            normalized, points, descriptors = self._features(frame)
            self.reference_normalized = normalized
            self.reference_points = points
            self.reference_descriptors = descriptors
            self.anchor_points = points
            self.previous_points = points
            self.previous_gray = gray
            self.image_shape = frame.shape
            self.frame_index = 1
            return frame.copy()
        if frame.shape != self.image_shape:
            raise EvidenceError("Frame dimensions changed during stabilization")
        assert self.previous_points is not None
        assert self.anchor_points is not None
        if self.frame_index % self.refresh_frames == 0:
            anchors, current = self._match(frame)
        else:
            tracked, status, error = cv2.calcOpticalFlowPyrLK(
                self.previous_gray,
                gray,
                self.previous_points.reshape(-1, 1, 2),
                np.empty_like(self.previous_points.reshape(-1, 1, 2)),
                winSize=(21, 21),
                maxLevel=3,
            )
            if tracked is None or status is None or error is None:
                raise EvidenceError("Background optical flow failed; record with a steady camera")
            tracked_array = np.asarray(tracked, dtype=np.float32).reshape(-1, 2)
            keep = (np.asarray(status).reshape(-1) == 1) & (np.asarray(error).reshape(-1) < 20)
            anchors, current = self.anchor_points[keep], tracked_array[keep]
        if len(anchors) < 8:
            raise EvidenceError("Too few stable background tracks to remove camera motion")
        homography, mask = cv2.findHomography(current, anchors, cv2.USAC_MAGSAC, 1.0)
        if homography is None or mask is None:
            raise EvidenceError("Camera transform could not be estimated")
        transform = np.asarray(homography, dtype=np.float64)
        inliers = np.asarray(mask).reshape(-1).astype(bool)
        if (
            int(inliers.sum()) < 8
            or float(inliers.mean()) < 0.5
            or not np.isfinite(transform).all()
            or np.linalg.cond(transform) > 1e6
        ):
            raise EvidenceError("Camera transform is unstable; record from a tripod")
        self.anchor_points = anchors[inliers]
        self.previous_points = current[inliers]
        self.previous_gray = gray
        self.frame_index += 1
        height, width = frame.shape[:2]
        return np.asarray(
            cv2.warpPerspective(
                frame,
                transform,
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT_101,
            ),
            dtype=np.uint8,
        )
