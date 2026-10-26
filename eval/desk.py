"""Evaluate synchronized desk inputs. No inputs means no result file, never placeholder metrics."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from resonance.errors import EvidenceError
from resonance.models import Capture
from resonance.modal.spectrum import estimate_spectrum
from resonance.pipeline import measure
from resonance.config import Settings


def evaluate(root: Path, template: Capture, output: Path) -> None:
    videos = sorted(
        path for path in root.glob("*.mp4") if path.with_suffix(".csv").is_file()
    )
    if not videos:
        raise EvidenceError(
            "No matching desk videos and accelerometer CSVs are available; no result was written"
        )
    rows = []
    for video in videos:
        csv_path = video.with_suffix(".csv")
        with csv_path.open() as stream:
            samples = list(csv.DictReader(stream))
        if len(samples) < 32:
            raise EvidenceError(f"{csv_path.name}: not enough accelerometer samples")
        times = np.array([float(row["time_seconds"]) for row in samples])
        acceleration = np.array([float(row["acceleration_m_s2"]) for row in samples])
        intervals = np.diff(times)
        if (
            not np.isfinite(times).all()
            or np.any(intervals <= 0)
            or np.std(intervals) / np.mean(intervals) > 0.05
        ):
            raise EvidenceError(
                f"{csv_path.name}: invalid or irregular accelerometer timestamps"
            )
        sample_rate = 1 / float(np.mean(intervals))
        truth = estimate_spectrum(acceleration, sample_rate, template.band)
        capture = template.model_copy(update={"id": video.stem, "path": video})
        measured = measure(capture, settings=Settings.from_env())
        rows.append(
            {
                "capture_id": video.stem,
                "state": video.stem.split("_")[0],
                "accelerometer_hz": truth.peak_hz,
                "accelerometer_sample_rate": sample_rate,
                "video_hz": measured.spectrum.peak_hz if measured.spectrum else None,
                "frequency_error_percent": abs(
                    measured.spectrum.peak_hz / truth.peak_hz - 1
                )
                * 100
                if measured.spectrum
                else None,
                "outcome": measured.outcome,
                "reasons": measured.reasons,
                "video_sha256": measured.input_sha256,
                "accelerometer_sha256": hashlib.sha256(
                    csv_path.read_bytes()
                ).hexdigest(),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "kind": "desk_vs_accelerometer",
                "captures": rows,
                "limitations": [
                    "Timing alignment and physical state labels must be independently checked",
                    "A desk rig is not a bridge",
                ],
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/desk"))
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("eval/results/desk.json"))
    args = parser.parse_args()
    evaluate(
        args.root, Capture.model_validate_json(args.template.read_text()), args.output
    )


if __name__ == "__main__":
    main()
