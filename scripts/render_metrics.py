"""Resolve report-source metric references from actual evaluation/benchmark JSON."""

import argparse
from pathlib import Path

from scripts.check_no_hardcoded_metrics import TOKEN, check_text, resolve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text()
    failures = check_text(source)
    if failures:
        raise SystemExit("\n".join(failures))
    body = TOKEN.sub(lambda match: str(resolve(match[0])), source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body)
    print(f"Rendered measured values to {args.output}")


if __name__ == "__main__":
    main()
