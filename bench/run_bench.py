import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
from scipy.stats import t

from bench.workloads import operations, pipeline_workload
from eval.synthetic import git_revision, source_tree_sha256
from resonance.config import Settings
from resonance.runtime import provenance


def run(label: str = "local") -> dict[str, object]:
    cv2.setRNGSeed(42)
    workloads = []
    execute, digest, frames = pipeline_workload()
    for name, operation in {**operations(), "measurement_pipeline": execute}.items():
        for _ in range(3):
            operation()
        repeats = []
        samples = []
        cpu = []
        iterations = 1 if name == "measurement_pipeline" else 30
        for _ in range(5):
            started = time.perf_counter()
            cpu_start = time.process_time()
            for _ in range(iterations):
                tick = time.perf_counter()
                operation()
                samples.append((time.perf_counter() - tick) * 1000)
            elapsed = time.perf_counter() - started
            repeats.append(elapsed / iterations * 1000)
            cpu.append((time.process_time() - cpu_start) / elapsed * 100)
        mean = float(np.mean(repeats))
        half = float(t.ppf(0.975, 4) * np.std(repeats, ddof=1) / np.sqrt(5))
        workloads.append(
            {
                "name": name,
                "mean_ms": mean,
                "ci95_ms": half,
                "repeats_ms": repeats,
                "p50_ms": float(np.quantile(samples, 0.5)),
                "p95_ms": float(np.quantile(samples, 0.95)),
                "process_cpu_percent": float(np.mean(cpu)),
                "iterations_per_repeat": iterations,
                "processing_fps": frames / (mean / 1000)
                if name == "measurement_pipeline"
                else None,
                "real_time_factor": frames / (mean / 1000) / 60
                if name == "measurement_pipeline"
                else None,
            }
        )
    result = {
        "kind": "measured_local_benchmark"
        if label == "local"
        else "measured_runtime_benchmark",
        "label": label,
        "git_revision": git_revision(),
        "source_tree_sha256": source_tree_sha256(),
        "provenance": provenance(Settings.from_env()).model_dump(),
        "seed": 42,
        "warmup_runs": 3,
        "pipeline_input_sha256": digest,
        "workloads": workloads,
        "usd_per_camera_hour": None,
        "price_source": None,
        "cloud_capacity": None,
        "limitations": [
            "Local runs do not establish cloud speed or cost",
            "Pipeline timing is whole-job latency, not individual frame latency",
            "Process CPU percent can exceed one logical core; it is not system utilization",
        ],
    }
    path = Path("bench/results") / f"{label}.json"
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--label",
        choices=["local", "cool-graviton", "pip-graviton", "pip-x86"],
        default="local",
    )
    args = parser.parse_args()
    if args.label == "cool-graviton":
        provenance(Settings.from_env(), require_cool=True)
    run(args.label)
    print(f"Measured results saved to bench/results/{args.label}.json")


if __name__ == "__main__":
    main()
