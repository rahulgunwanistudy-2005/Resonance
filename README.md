# Resonance

Video-based vibration measurement for structural triage. Resonance does not replace inspection and does not certify structural safety.

## Current build

Local OpenCV runtime/model probes and the numerical measurement slice are implemented: bounded file decoding, acquisition-timing checks, scene quality, phase correlation and Riesz extraction, spectra, uncertainty, beam priors and scale conversion. Synthetic frequency recovery meets the initial target; amplitude frequently misses its target. See [measured evaluation evidence and limitations](docs/evaluation.md).

Optional ALIKED/LightGlue background stabilization is implemented and tested with synthetic camera shake. Multiple ROIs produce method selections and a cross-spectral mode shape. YOLOX inference and a debounced excitation trigger are implemented; semantic vehicle validation on a real clip is pending.

No public endpoint, real bridge result, desk-rig validation, AWS deployment, agent approval flow or COOL benchmark is claimed.

The phase plan and human prerequisites are tracked in [tasks/todo.md](tasks/todo.md). Executed API findings and their limits are in [docs/api-findings.md](docs/api-findings.md).

## Reproduce the local runtime

Install Python, uv and FFmpeg, then run from the repository root:

```sh
UV_PROJECT_ENVIRONMENT=../.venv uv sync --project engine --extra local --frozen
.venv/bin/python -c 'import resonance; import cv2; print(cv2.__version__)'
.venv/bin/python scripts/download_models.py
.venv/bin/python scripts/probe_opencv.py
```

Run the numerical quality gates and regenerate evidence:

```sh
make check
make eval
```

Measure a local clip by saving a Capture contract as JSON and running:

```sh
.venv/bin/python scripts/measure.py capture.json --output outputs/measurement.json
```

The contract needs `id`, `bridge_id`, `path`, `band` (`low_hz`, `high_hz`), and `rois` (`id`, `x`, `y`, `width`, `height`). Supply `acquisition_fps` from confirmed camera acquisition settings and `acquisition_fps_verified: true` only when that timing is known. `calibration` is optional. Missing or weak evidence produces `INSUFFICIENT_EVIDENCE` and a corrective reason, with exit code `2` in the local CLI.

For camera-shake cancellation, set `stabilize: true`, supply `structure_box` covering the entire moving structure, and configure model paths from `.env.example` in your shell. Small measurement ROIs alone are not a sufficient background mask. Stabilization failure produces insufficient evidence rather than falling back silently. Results record whether stabilization ran and hash its models.

```sh
export RESONANCE_ALIKED_MODEL=models/aliked-n16rot-top1k-640.onnx
export RESONANCE_LIGHTGLUE_MODEL=models/aliked_lightglue.onnx
```

After optional model downloads, reproduce the shake experiment with `make eval-stabilization`.

Model downloads are optional for the numerical synthetic evaluation. Check [model license notes](docs/api-findings.md#model-selection-and-licensing) before redistribution.

The engine's OpenCV dependency is a local extra. A future COOL worker must instead use its AMI-provided OpenCV from `/opt/cool` in a virtual environment created with `--system-site-packages`, and must pass `scripts/verify_cool.py`. This local wheel intentionally fails that check.

## Evidence rules

Evaluation and benchmark JSON under `eval/results/` and `bench/results/` is the source of published project measurements. Synthetic inputs are labeled explicitly. Unavailable recordings and cloud runs remain pending. Measured values must not be copied into UI or report source as constants.
