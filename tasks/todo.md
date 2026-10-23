# Resonance build plan

Goal: a reproducible OpenCV 5 measurement service with measured evidence, an explainable agent, human-gated alerts, and an accessible public console. Resonance supports triage; it does not replace inspection.

## Schedule and assumptions

- Started Friday, 2026-10-23 (IST). Budgets below are estimates, not measurements.
- The supplied deadline has inconsistent weekdays: 2026-10-26 is Monday and 2026-10-27 is Tuesday. Verify the official Devpost deadline before relying on either date. Preserve the user's intended Monday 08:00 IST submission target provisionally as 2026-10-26 08:00 IST.
- Work follows the supplied plan without further confirmation, as explicitly authorized by the build prompt. The supplied engineering-workflow skill is loaded from `/private/tmp/resonance-skills/engineering-workflow/SKILL.md`; frontend-design is available locally.

## Engineering phases

- [x] Gate 1: plan recorded before implementation; risks and acceptance criteria explicit.
- [ ] Gate 2: scaffold §3.1; define Pydantic contracts and typed module boundaries.
- [x] P0 / Friday night / budget 2h: install requested OpenCV pin in isolated uv environment; inspect ALIKED, DISK, LightGlue, ANNIndex and DNN ENGINE_NEW; verify model requirements/licensing; inspect official VLM sample; load vehicle detector if compatible. Gate: `docs/api-findings.md` with executed snippets and honest blockers.
- [x] P1 / Friday night–Saturday / 6h: video I/O, quality, phase correlation, Riesz, spectra, bootstrap, physics prior, synthetic generation. Gate: actual `eval/results/synthetic.json`, mirrored tests, strict typing and lint.
- [ ] P2 / Saturday / 5h: background stabilization, scale calibration, excitation detection. Gate: measured shake benefit and sample vehicle trigger.
- [ ] P3 / Saturday after recordings arrive by 14:00 IST / 4h: desk vs accelerometer evaluation, damage-state comparison, healthy/damaged magnification and audification, true-fps checks. Gate: `eval/results/desk.json` from supplied recordings.
- [ ] P4 / Saturday / 5h: deterministic agent, baseline, optional guarded Bedrock planner; evaluate ADAPT, RETRY, WATCH and approval, including insufficient evidence. Gate: replay trace and `eval/results/agent.json` across at least 20 captures.
- [ ] P5 / Saturday–Sunday / 5h: FastAPI, upload limits, request IDs, SQS worker, S3/Dynamo storage, WebSocket updates and MCP stdio. Gate: complete upload-to-results path plus protected approval.
- [ ] P6 / Sunday / 8h: write, critique and revise `docs/design-plan.md` before UI; build React/Vite/TypeScript/uPlot console; show only implemented capabilities. Gate: build/typecheck, keyboard, reduced motion, chart tables, 1440/390 screenshots and measured accessibility check.
- [ ] P7 / Sunday / 5h: CDK storage/compute/edge/observability, COOL Graviton worker without pip OpenCV, budget alarm, scheduled stop, teardown. Gate: public endpoint and real COOL provenance. Human subscription/AMI may block.
- [ ] P8 / Sunday / 3h: COOL Graviton vs pip Graviton vs pip x86 microbench and pipeline, warmup and repeated runs with intervals, prices and provenance. Gate: actual `bench/results/*.json` and `make bench`.
- [ ] P9 / Sunday / 4h: judge quick start, report/PDF, architecture and agent diagrams, video script/shot list, limitations. Gate: clean-container quick start verified.
- [ ] P10 / Sunday before submission / 2h: self-review, security/upload/privacy audit, metric checker, desktop/mobile judge walkthrough. Freeze new features at Sunday 22:00 IST (date subject to deadline verification).
- [ ] At every phase: run checks, update this file with commands/output/deferred work, and commit a meaningful green checkpoint.

## Human tasks (Rahul)

### Friday 2026-10-23 evening IST
- [ ] Confirm Devpost registration/proposal and the actual competition deadline at https://opencv26.devpost.com/ . Contact organizers yourself if necessary.
- [ ] Prepare AWS region (prefer us-east-1 if service availability permits), budget alarm at $20, credentials and optional Bedrock model access.
- [ ] Subscribe to a COOL Marketplace listing shipping OpenCV 5.x; provide AMI ID, region and instance access. If COOL is OpenCV 4.x, stop COOL deployment and select a suitable listing.
- [ ] Build desk rig; keep accelerometer/phone mass fixed across states and make irreversible cuts last.

### Saturday 2026-10-24 by 14:00 IST
- [ ] Supply `data/desk/{state}_{trial}.mp4` with matching accelerometer CSV, five trials per S0 healthy, S1 added mass, S2 notch, S3 deeper notch/loosened clamp; include timestamps, sample rate, camera settings and scale reference.
- [ ] Supply three handheld healthy clips for shake evaluation.
- [ ] Record field clips safely from ground-mounted tripod: vehicle passes, two viewpoints, handheld examples, recording time and span length if known. Field results are repeatability, not accuracy against ground truth.

### Sunday 2026-10-25 IST
- [ ] Record the final video (up to five minutes) from generated script, including team segment.
- [ ] Review live endpoint on phone.
- [ ] Submit all deliverables by the verified deadline; provisional internal target Monday 2026-10-26 08:00 IST.

## Mandatory submission package
- [ ] Technical report and PDF: problem, users, architecture, OpenCV/AWS, evaluation, limitations, responsible use.
- [ ] Judge-accessible repository, pinned dependencies, reproducible build/deploy/test instructions.
- [ ] Rendered architecture diagram showing OpenCV, AWS, COOL and agent boundaries.
- [ ] Public endpoint where judges can run a real measurement.
- [ ] Video and shot list, recorded by Rahul.
- [ ] Evaluation artifacts including failures; no invented field or desk results.
- [ ] COOL version/config/input/baseline/benchmark evidence proving the claimed workload ran on COOL.
- [ ] Agent workflow, evidence-driven action trace and measured success/failure/human-control evaluation.

## Risks and failure modes
- OpenCV pin or Python APIs may not exist for this platform; no silent downgrade to OpenCV 4 or alternate inference runtime.
- Model weights/exports may require license acceptance or unsupported operators; unavailable capabilities stay disabled.
- Aliasing, variable/slow-motion frame timing, texture loss, saturation, occlusion, camera shake and bootstrap bias can invalidate measurements. Reject weak evidence explicitly.
- Pixel-to-mm needs a valid scale in the motion plane; no calibration means no millimetre claim.
- Temperature/baseline mismatch, environmental confounds and unverified beam parameters must not imply damage or safety certification.
- Missing recordings, accelerometer synchronization, AWS subscription/access or correct COOL AMI block their respective gates.
- Malformed/oversized uploads, traversal, codec failure, auth bypass, concurrent approvals and notification replay need explicit handling.
- Numeric claims in UI/docs must resolve to generated eval/bench JSON. Targets, configuration, dates and sourced context must be distinguished from measured results.
- No public publication or paid-resource creation until configuration is concrete and authorization is established. No messages to organizers or third parties are authorized.

## Done criteria
- [ ] Happy path works end to end; malformed/empty/weak/oversized inputs produce useful typed errors.
- [ ] Core inference uses OpenCV 5; COOL execution provenance attached on actual COOL runs.
- [ ] Tests, mypy strict, ruff, frontend typecheck/build and required phase gates pass.
- [ ] Diff self-reviewed for security, naming, edge cases, logging, determinism and unused code.
- [ ] No unbuilt feature or synthetic result is presented as real bridge evidence.
- [ ] Human approval required before any inspection notification; rejection reason retained.
- [ ] README/report state limitations and actual deployment state.

## Review and verification log

- Initial repository: empty checkout, no commits; no existing implementation or lessons.
- Skill archive inspected and loaded; no global skill installation performed.
- P0 verified: pinned wheel installed; explicit ENGINE_NEW forward passes for YOLOX, ALIKED and LightGlue passed (`.venv/bin/python scripts/probe_opencv.py`). Results: `eval/results/api_reality.json`.
- P0 quality gate: `.venv/bin/python -m pytest -c engine/pyproject.toml engine/tests/test_models.py engine/tests/test_runtime.py` → 5 passed. Strict mypy on the engine at this checkpoint → no issues. Ruff on checkpoint modules/scripts → all checks passed; `git diff --check` clean.
- Deferred: native feature wrapper inference, real detector sample, VLM runtime, and feature-export redistribution permission. P0 has no numerical-core blocker; continue P1.
- Gate 2 scaffold directories, core contracts and typed integration protocols are present. Later-phase implementations are intentionally absent; full module inventory is pending.
- P1 built: file decoding with bounded ROI memory, presentation/acquisition timing separation, scene quality and aliasing guard, phase correlation and Riesz, Welch spectrum and fitted amplitude, conditional residual block bootstrap, beam prior, two-point scale, pure numerical pipeline and local CLI.
- P1 verified: `make check` → ruff and format passed, strict mypy clean (engine including tests and API scaffold), 38 tests passed, metric source guard passed. Encoded video end-to-end test exercises the real ffprobe/decode/measurement path. `make eval` → 48 synthetic method/input experiments, 36 eligible; frequency target 36/36, amplitude target 6/36. Failure evaluation → 6/6 correct refusals. These are synthetic results, not desk/field evidence.
- P1 self-review: checked malformed/non-finite input, shape/timing mismatch, ROI bounds, upload/memory limits, module layering, configuration access, lack of alternate inference engines and honest result labeling. Runtime provenance and source/input hashes recorded.
- P1 deferred: amplitude bias correction and real-data interval coverage, multiprocessing/profile comparison, FDD mode shapes, stabilization and all service/cloud/UI phases. No claim that amplitude targets are met.
