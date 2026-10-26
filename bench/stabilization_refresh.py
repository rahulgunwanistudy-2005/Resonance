"""Exploratory fixed-scene feature refresh tradeoff; not cloud throughput evidence."""

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    rows = []
    for interval in (1, 10, 30):
        path = Path(f"outputs/refresh-{interval}.json")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "eval.stabilization",
                "--refresh-frames",
                str(interval),
                "--output",
                str(path),
            ],
            check=True,
        )
        rows.append(json.loads(path.read_text()))
    Path("bench/results/stabilization_refresh.json").write_text(
        json.dumps(
            {
                "kind": "measured_local_stabilization_refresh_tradeoff",
                "repeats_per_setting": 1,
                "rows": rows,
                "limitations": [
                    "Exploratory single timing per setting, without a timing confidence interval",
                    "Identical synthetic scene and model files; not real handheld validation",
                    "Timing includes scene generation and full-frame stabilization; not per-ROI inference latency",
                    "Local host only; no cloud or COOL speed claim",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    Path("eval/results/stabilization.json").write_text(
        json.dumps(rows[-1], indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
