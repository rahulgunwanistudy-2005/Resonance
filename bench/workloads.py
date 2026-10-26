from collections.abc import Callable

import cv2
import numpy as np

from eval.synthetic import SyntheticConfig, generate
from resonance.config import MeasurementConfig
from resonance.models import FrequencyBand
from resonance.pipeline import measure_frames


def operations() -> dict[str, Callable[[], object]]:
    rng = np.random.default_rng(42)
    image = rng.integers(0, 255, size=(512, 512, 3), dtype=np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    kernel = np.outer(
        np.array([1, 4, 6, 4, 1], np.float32) / 16,
        np.array([1, 4, 6, 4, 1], np.float32) / 16,
    )
    points = rng.uniform(0, 512, size=(100, 2)).astype(np.float32)
    moved = points + np.array([1, 2], np.float32)
    window = cv2.createHanningWindow((512, 512), cv2.CV_32F)
    return {
        "cvtColor": lambda: cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
        "resize": lambda: cv2.resize(image, (256, 256)),
        "GaussianBlur": lambda: cv2.GaussianBlur(gray, (0, 0), 1.2),
        "pyrDown": lambda: cv2.pyrDown(gray),
        "filter2D": lambda: cv2.filter2D(gray, -1, kernel),
        "phaseCorrelate": lambda: cv2.phaseCorrelate(
            gray.copy(), gray.copy(), window.copy()
        ),
        "findHomography": lambda: cv2.findHomography(points, moved, cv2.USAC_MAGSAC, 1),
    }


def pipeline_workload() -> tuple[Callable[[], object], str, int]:
    import hashlib

    frames, _ = generate(
        SyntheticConfig(roi_size=64, duration_seconds=8, amplitude_rms_px=0.5)
    )
    digest = hashlib.sha256(np.stack(frames).tobytes()).hexdigest()

    def execute() -> object:
        result = measure_frames(
            {"deck": frames},
            fps=60,
            band=FrequencyBand(low_hz=1, high_hz=15),
            capture_id="benchmark",
            bridge_id="synthetic",
            config=MeasurementConfig(),
        )
        if result.outcome != "MEASURED":
            raise RuntimeError("Benchmark workload refused its input")
        return result

    return execute, digest, len(frames)
