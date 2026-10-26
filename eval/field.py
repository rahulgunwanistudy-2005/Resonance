import argparse
import json
from pathlib import Path

import numpy as np

from resonance.config import Settings
from resonance.errors import EvidenceError
from resonance.models import Capture
from resonance.pipeline import measure


def evaluate(root: Path, template: Capture, output: Path) -> None:
    videos = sorted(root.glob("*.mp4"))
    if len(videos) < 2:
        raise EvidenceError(
            "At least two independent field clips are required; no result was written"
        )
    rows = []
    frequencies = []
    for video in videos:
        result = measure(
            template.model_copy(update={"id": video.stem, "path": video}),
            settings=Settings.from_env(),
        )
        if result.outcome == "MEASURED" and result.spectrum:
            frequencies.append(result.spectrum.peak_hz)
        rows.append(
            {"capture_id": video.stem, "result": result.model_dump(mode="json")}
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "kind": "field_repeatability_without_ground_truth",
                "captures": rows,
                "summary": {
                    "accepted_captures": len(frequencies),
                    "mean_hz": float(np.mean(frequencies)) if frequencies else None,
                    "standard_deviation_hz": float(np.std(frequencies, ddof=1))
                    if len(frequencies) > 1
                    else None,
                },
                "limitations": [
                    "Repeatability is not accuracy",
                    "No structural damage inference without a valid baseline and engineering review",
                ],
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("eval/results/field.json"))
    args = parser.parse_args()
    evaluate(
        args.root, Capture.model_validate_json(args.template.read_text()), args.output
    )


if __name__ == "__main__":
    main()
