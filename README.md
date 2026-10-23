# Resonance

Video-based vibration measurement for structural triage. Resonance does not replace inspection and does not certify structural safety.

## Current build

Local OpenCV runtime and model compatibility probes are implemented. Synthetic measurement development is in progress. No public endpoint, real bridge result, desk-rig validation, AWS deployment or COOL benchmark is claimed.

The phase plan and human prerequisites are tracked in [tasks/todo.md](tasks/todo.md). Executed API findings and their limits are in [docs/api-findings.md](docs/api-findings.md).

## Reproduce the local runtime

Install Python, uv and FFmpeg, then run from the repository root:

```sh
UV_PROJECT_ENVIRONMENT=../.venv uv sync --project engine --extra local --frozen
.venv/bin/python -c 'import resonance; import cv2; print(cv2.__version__)'
.venv/bin/python scripts/download_models.py
.venv/bin/python scripts/probe_opencv.py
```

Model downloads are optional for the numerical synthetic evaluation. Check [model license notes](docs/api-findings.md#model-selection-and-licensing) before redistribution.

The engine's OpenCV dependency is a local extra. A future COOL worker must instead use its AMI-provided OpenCV from `/opt/cool` in a virtual environment created with `--system-site-packages`, and must pass `scripts/verify_cool.py`. This local wheel intentionally fails that check.

## Evidence rules

Evaluation and benchmark JSON under `eval/results/` and `bench/results/` is the source of published project measurements. Synthetic inputs are labeled explicitly. Unavailable recordings and cloud runs remain pending. Measured values must not be copied into UI or report source as constants.
