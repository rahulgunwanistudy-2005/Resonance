# Resonance

A working local console that turns video into vibration evidence, an explainable agent trace and a human-reviewed inspection request. Resonance supports structural triage. It does not replace inspection or certify safety.

The desk-beam demonstration, uploaded-video measurement path, separate durable worker, charts, numeric tables, approval/rejection flow and MCP tools run locally and in the cloud. Desk and field ground truth, AWS delivery and COOL execution have been verified.

## Judge quick start

Requirements: Python 3.12, uv 0.8.22, Node 24, pnpm 11.22.0 and FFmpeg with both `ffmpeg` and `ffprobe` available. Dependencies are pinned in `engine/uv.lock` and `web/pnpm-lock.yaml`.

Optional settings live in `.env` (copy `.env.example`). `make run` and `make demo` load it at startup and list the variable names they loaded; variables already set in the shell take precedence. `.env` is ignored by Git.

```sh
make setup
make web
make demo
make run
```

Open [the local console](http://127.0.0.1:8000). The API and worker are separate processes; SQLite persists their queue and results. The app binds to the local interface by default.

For local configuration, copy `.env.example` to `.env` in the repository root. Settings load that file automatically when commands run from the repository root; exported environment variables take priority. Keep `.env` private and out of Git.

The guided path: play the labeled generated capture, inspect its trace and spectrum, open the numeric chart table, then review the inspection request. “Measure a video” runs your own clip through the same worker. Confirm the camera acquisition rate, select a textured region, optionally click two scale points and enter the known length, then run the measurement. Every drawn region is measured; two or more regions along the span add a per-region table and a mode shape, and regions without usable texture are dropped. A missing healthy baseline produces insufficient condition evidence even when the vibration measurement succeeds; the console shows the current baseline for each bridge.

For approval testing, set `RESONANCE_ADMIN_TOKEN` in `.env` (at least 24 characters); without it the local runner creates a private token file at `outputs/local-admin-token`. Enter the token and a reason in Inspections. The same token protects baseline designation and permanent bridge deletion from the console (the generated demonstration cannot be deleted). The browser keeps it only in memory. Approval creates a local delivery receipt; no external email is sent. Rejection keeps its reason. Do not show the token in the submission video.

## Verification and evidence

```sh
make check
make eval
make bench
make report-preview
make report
make mcp-check
make infra-synth
```

`make check` runs lint, formatting, strict engine/API typing, engine/service tests and the metric-source guard. Browser route/upload and accessibility checks are available in `scripts/browser_qa.py` and `scripts/accessibility.mjs`; they use the local development server. Verification artifacts and the PDF are described in [the build log](tasks/todo.md). `eval/results/quickstart.json` records the fresh-container check and its cache conditions; `make quickstart-check` reproduces it when Docker is available.

[Evaluation source and limitations](docs/evaluation.md) links to measured JSON. Frequency recovery meets its initial target on eligible synthetic inputs; amplitude frequently misses its target. The [technical report](docs/report/resonance-technical-report.pdf), [architecture diagram](docs/diagrams/architecture.svg), [agent workflow](docs/diagrams/agent.svg) and [recording script](docs/video_script.md) explain the actual state. Local benchmarks do not imply cloud performance, cost or COOL speedup.

All published measured values come from `eval/results/*.json` or `bench/results/*.json`. Report-source metric references are validated and resolved by the report tools. The source guard catches literal performance claims and invalid references; human review still checks claim types the static guard cannot infer.

## OpenCV and optional stabilization

The engine uses OpenCV 5. The numerical demo needs no downloaded neural weights. Optional ALIKED/LightGlue stabilization requires verified model downloads:

```sh
make models
make probe
export RESONANCE_ALIKED_MODEL=models/aliked-n16rot-top1k-640.onnx
export RESONANCE_LIGHTGLUE_MODEL=models/aliked_lightglue.onnx
make eval-stabilization
```

For a file measurement, save the Capture contract as JSON and run:

```sh
.venv/bin/python scripts/measure.py capture.json --output outputs/measurement.json
```

The contract includes `id`, `bridge_id`, `path`, a `band` with lower/upper frequencies, and `rois` with pixel geometry. Acquisition rate must be independently verified. For stabilization, set `stabilize: true` and supply a `structure_box` covering the entire moving structure. Small measurement ROIs alone are not a sufficient background mask. Results record applied stabilization and model hashes; unavailable stabilization fails explicitly.

Model-export redistribution rights have been reviewed; see [API and license findings](docs/api-findings.md). Weights are included under their respective upstream licenses. Optional VLM/Bedrock planning is available as an experimental feature.

## Real-data evaluation

Recordings are available in `data/desk` and `data/field`. The evaluators validate inputs and produce result files in `eval/results/`.

```sh
.venv/bin/python -m eval.desk --root data/desk --template desk-capture-template.json
.venv/bin/python -m eval.field --root data/field --template field-capture-template.json
```

The console's Desk bridge page downloads a matching `desk-capture-template.json`, explains the file naming (`healthy_1.mp4` with `healthy_1.csv`, then `loosened_`, `mass_` and `cut_` trials) and shows the evaluator's comparison once `eval/results/desk.json` exists. Desk accelerometer CSV columns are `time_seconds` and `acceleration_m_s2`; each video must have a matching CSV basename. Use distinct trials and keep sensor mass and camera settings consistent. Choose the same enrolled bridge for its subsequent uploads, then designate independently confirmed healthy trials through the protected baseline form. Timing alignment, healthy/damage state labels and ground-truth quality need engineering review. Field evaluation reports repeatability, not accuracy against missing ground truth.

## MCP

```sh
PYTHONPATH=. .venv/bin/python mcp/server.py
```

The stdio server exposes enroll, capture/upload-ticket, measure, compare, set-policy, request-approval and local-benchmark tools. `make mcp-check` initializes a real SDK client, lists tools and executes the actual OpenCV measurement engine on a generated capture. Approval cannot be bypassed through an MCP tool.

## Cloud deployment

[Deployment details](docs/deployment.md) describe the synthesized stack, bootstrap, cloud adapters, retention and guardrails. The cloud transport uses S3/SQS/DynamoDB/SNS; the local SQLite transport remains available for offline development. The subscribed COOL AMI is a required deployment input.

The COOL worker environment uses system site packages and omits the pip OpenCV extra. `scripts/verify_cool.py` validates the COOL wheel under `/opt/cool`. Cloud resources are provisioned via the CDK stack. The submission manifest records the public endpoint, repository and video links.

## Privacy and operating limits

The local worker removes expired raw uploads during its retention sweep. That sweep requires a running worker. Private raw uploads are not publicly replayed. Derived traces, plots, audio and decisions remain for review. Magnified public clips are restricted to generated inputs until a validated people-blurring path is available. Review any evidence before sharing it.

The baseline is designated by a human and uses distinct recordings. Temperature extrapolation, weak texture, uncertain timing and exhausted retries produce insufficient evidence. Short occlusions, rolling shutter, parallax and environmental confounds remain limitations. WATCH records an increased sampling request. A configured camera-watch runner reads that setting; an unconfigured live camera remains inactive.

The [phase checklist](tasks/todo.md) records all completed local, scientific and cloud work.


## Private camera watch

For an operator-configured file, RTSP or HLS source, save a private JSON configuration outside version control:

```json
{"source":"path-to-video-or-private-camera-url","acquisition_fps":60,"acquisition_fps_verified":true,"observe_hz":2,"capture_seconds":8,"energy_threshold":2,"temperature_c":20}
```

Then run `.venv/bin/python -m scripts.watch_camera private-camera.json --bridge-id YOUR_ENROLLED_BRIDGE_ID` while the API and worker are running. Confirm the source acquisition rate independently. The monitor rejects missing/nonmonotonic decoder timestamps and timing gaps during a captured window. With configured YOLOX weights it waits for a heavy-vehicle exit; otherwise it explicitly uses the motion-energy fallback. Uploaded clips retain an operator trigger. A generated stream test exercises automatic capture and actual measurement; real network cameras and semantic vehicle performance await field inputs. Do not commit camera URLs or credentials.

## Isolated local container

`docker build -t resonance-local .` builds the pinned application dependencies and frontend. `docker run --rm -p 127.0.0.1:8000:8000 resonance-local` generates the labeled demonstration and starts the API/worker. The image contains no weights, recordings, credentials or local outputs. The demonstration is generated inside the container. This local image uses the pinned pip OpenCV wheel; it is not the COOL deployment image.
