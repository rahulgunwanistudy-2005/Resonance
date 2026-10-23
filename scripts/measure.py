"""Local file-to-result entry point; capture JSON is validated at the boundary."""

import argparse
from pathlib import Path

from resonance.config import Settings
from resonance.models import Capture
from resonance.pipeline import measure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "capture",
        type=Path,
        help="Validated Capture JSON, including acquisition timing",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    capture = Capture.model_validate_json(args.capture.read_text())
    result = measure(capture, settings=Settings.from_env())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2) + "\n")
    print(result.outcome)
    for reason in result.reasons:
        print(reason)
    if result.outcome != "MEASURED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
