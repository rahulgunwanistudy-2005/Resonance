"""Run with the COOL worker interpreter, not a local pip OpenCV environment."""

import argparse
from pathlib import Path

from resonance.config import Settings
from resonance.runtime import provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = provenance(Settings.from_env(), require_cool=True)
    body = result.model_dump_json(indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body)
    print(body, end="")


if __name__ == "__main__":
    main()
