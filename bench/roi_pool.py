"""Measure startup/IPC-inclusive serial and spawned ROI work on identical inputs."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import t

from eval.synthetic import SyntheticConfig, generate, source_tree_sha256
from resonance.config import MeasurementConfig
from resonance.models import FrequencyBand
from resonance.pipeline import measure_frames


def run(workers: int, repeats: int) -> dict[str, object]:
    frames, _ = generate(
        SyntheticConfig(roi_size=128, duration_seconds=8, amplitude_rms_px=0.5)
    )
    timings = []
    peaks = []
    for index in range(repeats + 1):
        start = time.perf_counter()
        result = measure_frames(
            {f"deck-{roi}": frames for roi in range(4)},
            fps=60,
            band=FrequencyBand(low_hz=1, high_hz=15),
            capture_id="pool-benchmark",
            bridge_id="synthetic",
            config=MeasurementConfig(roi_workers=workers),
        )
        elapsed = time.perf_counter() - start
        if result.spectrum is None or result.outcome != "MEASURED":
            raise RuntimeError("Pool experiment did not produce a valid measurement")
        if index:
            timings.append(elapsed)
            peaks.append(result.spectrum.peak_hz)
    return {
        "workers": workers,
        "repeats_seconds": timings,
        "mean_seconds": float(np.mean(timings)),
        "ci95_seconds": float(
            t.ppf(0.975, repeats - 1) * np.std(timings, ddof=1) / np.sqrt(repeats)
        )
        if repeats > 1
        else None,
        "peaks_hz": peaks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-workers", type=int, choices=[1, 2])
    args = parser.parse_args()
    if args.profile_workers:
        run(args.profile_workers, 5)
        return
    result = {
        "kind": "measured_local_roi_pool_comparison",
        "source_tree_sha256": source_tree_sha256(),
        "warmup_runs": 1,
        "roi_count": 4,
        "rows": [run(workers, 5) for workers in (1, 2)],
        "includes": "Process spawn, frame serialization, extraction, spectra, FDD and bootstrap. No persistent pool or cloud inference.",
    }
    path = Path("bench/results/roi_pool.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print("Measured serial and bounded-process results saved")


if __name__ == "__main__":
    main()
