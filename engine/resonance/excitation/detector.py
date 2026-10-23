"""Vehicle excitation via OpenCV Zoo YOLOX, with an explicitly labeled energy fallback."""

from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from resonance.errors import EvidenceError
from resonance.models import Contract
from resonance.quality.scene import gray_float


class Detection(Contract):
    label: Literal["person", "bus", "train", "truck"]
    confidence: float = Field(ge=0, le=1)
    box_xywh: tuple[float, float, float, float]


class VehicleDetector:
    def __init__(self, model: Path, *, confidence: float = 0.4) -> None:
        if not model.is_file() or not 0 < confidence < 1:
            raise EvidenceError(
                "Vehicle detection needs verified model weights and a valid threshold"
            )
        self.net = cv2.dnn.readNetFromONNX(str(model), cv2.dnn.ENGINE_NEW)
        self.confidence = confidence
        grids = []
        strides = []
        for stride in (8, 16, 32):
            size = 640 // stride
            x, y = np.meshgrid(np.arange(size), np.arange(size))
            grids.append(np.stack((x, y), axis=-1).reshape(-1, 2))
            strides.append(np.full((size * size, 1), stride))
        self.grid = np.concatenate(grids).astype(np.float32)
        self.strides = np.concatenate(strides).astype(np.float32)

    def detect(self, frame: NDArray[np.uint8]) -> list[Detection]:
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0:
            raise EvidenceError("Vehicle detection requires a non-empty BGR image")
        height, width = frame.shape[:2]
        scale = min(640 / width, 640 / height)
        resized = cv2.resize(frame, (max(1, round(width * scale)), max(1, round(height * scale))))
        image = np.full((640, 640, 3), 114, dtype=np.uint8)
        image[: resized.shape[0], : resized.shape[1]] = resized
        self.net.setInput(cv2.dnn.blobFromImage(image))
        raw = np.asarray(self.net.forward(), dtype=np.float32).reshape(-1, 85)
        return self.decode(raw, scale=scale, width=width, height=height)

    def decode(
        self,
        raw: NDArray[np.float32],
        *,
        scale: float,
        width: int,
        height: int,
    ) -> list[Detection]:
        if raw.shape != (len(self.grid), 85) or not np.isfinite(raw).all() or scale <= 0:
            raise EvidenceError("Vehicle model produced invalid detections")
        scores = raw[:, 4, None] * raw[:, 5:]
        classes = np.argmax(scores, axis=1)
        confidence = np.max(scores, axis=1)
        relevant = (confidence >= self.confidence) & np.isin(classes, [0, 5, 6, 7])
        indices = np.flatnonzero(relevant)
        if len(indices) == 0:
            return []
        centers = (raw[indices, :2] + self.grid[indices]) * self.strides[indices] / scale
        dimensions = np.exp(np.clip(raw[indices, 2:4], -20, 20)) * self.strides[indices] / scale
        top_left = centers - dimensions / 2
        lower = np.maximum(top_left, 0)
        upper = np.minimum(top_left + dimensions, [width, height])
        boxes = np.column_stack([lower, np.maximum(upper - lower, 0)])
        kept = cv2.dnn.NMSBoxesBatched(
            boxes.tolist(),
            confidence[indices].tolist(),
            classes[indices].tolist(),
            self.confidence,
            0.5,
        )
        names: dict[int, Literal["person", "bus", "train", "truck"]] = {
            0: "person",
            5: "bus",
            6: "train",
            7: "truck",
        }
        detections = []
        for selected in np.asarray(kept).reshape(-1):
            box = boxes[int(selected)]
            if box[2] <= 0 or box[3] <= 0:
                continue
            index = int(indices[int(selected)])
            detections.append(
                Detection(
                    label=names[int(classes[index])],
                    confidence=float(np.clip(confidence[index], 0, 1)),
                    box_xywh=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                )
            )
        return detections


class ExcitationTrigger:
    def __init__(self, *, energy_threshold: float = 2, absent_samples: int = 3) -> None:
        if energy_threshold <= 0 or absent_samples < 1:
            raise EvidenceError("Excitation thresholds must be positive")
        self.energy_threshold = energy_threshold
        self.absent_samples = absent_samples
        self.active = False
        self.quiet_samples = 0
        self.source: Literal["heavy_vehicle_exit", "motion_energy"] | None = None

    def observe(self, *, heavy_vehicle_present: bool | None, energy: float) -> bool:
        if not np.isfinite(energy) or energy < 0:
            raise EvidenceError("Motion energy must be finite and non-negative")
        using_vehicle = heavy_vehicle_present is not None
        source: Literal["heavy_vehicle_exit", "motion_energy"] = (
            "heavy_vehicle_exit" if using_vehicle else "motion_energy"
        )
        if self.source is not None and self.source != source:
            self.active = False
            self.quiet_samples = 0
        present = heavy_vehicle_present if using_vehicle else energy >= self.energy_threshold
        if present:
            self.active = True
            self.quiet_samples = 0
            self.source = source
            return False
        if not self.active:
            return False
        self.quiet_samples += 1
        if self.quiet_samples < self.absent_samples:
            return False
        self.active = False
        self.quiet_samples = 0
        return True


def motion_energy(previous: NDArray[np.generic], current: NDArray[np.generic]) -> float:
    first, second = gray_float(previous), gray_float(current)
    if first.shape != second.shape:
        raise EvidenceError("Motion-energy frames must have matching shapes")
    return float(np.mean((second - first) ** 2))
