"""Executable failure scenarios. Unsupported conditions remain explicitly labeled."""

import json
from pathlib import Path

import cv2
import numpy as np

from eval.synthetic import SyntheticConfig, generate, git_revision, source_tree_sha256
from resonance.config import MeasurementConfig
from resonance.models import FrequencyBand
from resonance.pipeline import measure_frames
from resonance.runtime import provenance


def main() -> None:
    config = SyntheticConfig(roi_size=64, duration_seconds=4, amplitude_rms_px=0.5)
    frames, _ = generate(config)
    blank = [np.full_like(frame, 128) for frame in frames]
    occluded = [frame.copy() for frame in frames]
    occluded[60:121] = blank[60:121]
    cases = {
        "low_texture": (blank, 60),
        "aliasing_risk": (frames, 24),
        "night": ([frame * 0.002 for frame in frames], 60),
        "saturation": ([np.full_like(frame, 255) for frame in frames], 60),
        "occlusion": (occluded, 60),
        "blur": ([cv2.GaussianBlur(frame, (0, 0), 8) for frame in frames], 60),
    }
    rows = []
    for name, (sequence, fps) in cases.items():
        result = measure_frames(
            {"deck": sequence},
            fps=fps,
            band=FrequencyBand(low_hz=1, high_hz=15),
            capture_id=name,
            bridge_id="synthetic-failures",
            config=MeasurementConfig(bootstrap_repeats=20),
        )
        rows.append(
            {
                "scenario": name,
                "expected": "INSUFFICIENT_EVIDENCE",
                "outcome": result.outcome,
                "refused_as_expected": result.outcome == "INSUFFICIENT_EVIDENCE",
                "reasons": result.reasons,
            }
        )
    report = {
        "kind": "synthetic_failure_scenarios",
        "git_revision": git_revision(),
        "source_tree_sha256": source_tree_sha256(),
        "provenance": provenance().model_dump(),
        "scenarios": rows,
        "summary": {
            "scenarios": len(rows),
            "correct_refusals": sum(row["refused_as_expected"] for row in rows),
        },
        "pending": [
            "Real night footage",
            "Handheld camera-shake cancellation in P2",
            "Occlusion shorter than scene-quality sampling interval",
        ],
    }
    Path("eval/results/failures.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
