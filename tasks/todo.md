# Resonance build plan

Goal: a reproducible OpenCV 5 measurement service with measured evidence, an explainable agent, human-gated alerts, and an accessible public console. Resonance supports triage; it does not replace inspection.

## Schedule and assumptions

- Started Friday, 2026-10-23 (IST). Budgets below are estimates, not measurements.
- The supplied deadline has inconsistent weekdays: 2026-10-26 is Monday and 2026-10-27 is Tuesday. Verify the official Devpost deadline before relying on either date. Preserve the user's intended Monday 08:00 IST submission target provisionally as 2026-10-26 08:00 IST.
- Work follows the supplied plan without further confirmation, as explicitly authorized by the build prompt. The supplied engineering-workflow skill is loaded from `/private/tmp/resonance-skills/engineering-workflow/SKILL.md`; frontend-design is available locally.

## Engineering phases

### 2026-10-24 continuation (authorized by Rahul)
- [x] Complete the local build and independent documentation/evaluation work. Cloud deployment remains explicitly deferred; real recordings remain unavailable. Public publication now requires explicit authorization after automatic approval review.
- [x] P4: temperature regression/prediction interval, deterministic state machine, schema-guarded planner proposals, executable changed plans, JSONL trace and replay evaluation.
- [x] P5 local: SQLite-backed durable queue/storage, file upload with bounded tokens, separate worker process, evidence rendering, protected approvals, live updates and MCP stdio. SQLite is explicitly a local backend, not a claim of SQS execution.
- [x] P6: implement and visually verify the full React console against real local services, with a generated synthetic video demo, charts/tables, agent trace, approvals, fleet and measured evaluation/benchmark pages.
- [x] Prepare AWS adapters/CDK configuration, worker bootstrap, verification and teardown without contacting or provisioning AWS. Ask about AWS only at the eventual deployment handoff.
- [x] Prepare reproducible local benchmarks, real-data evaluators that refuse absent inputs, technical report/PDF, diagrams and video script. Leave desk/field/COOL result files absent when inputs are unavailable.
- [x] Run end-to-end desktop/mobile checks, strict typing/lint/build/tests, security and metric audit; save green phase commits while preserving Rahul's untracked image.

AWS access is deferred by user request. Desk recordings are confirmed unavailable; real-data validation remains pending. Neither dependency blocks the local application, agent or documentation work.

- [x] Gate 1: plan recorded before implementation; risks and acceptance criteria explicit.
- [x] Gate 2: scaffold §3.1; define Pydantic contracts and typed module boundaries.
- [x] P0 / Friday night / budget 2h: install requested OpenCV pin in isolated uv environment; inspect ALIKED, DISK, LightGlue, ANNIndex and DNN ENGINE_NEW; verify model requirements/licensing; inspect official VLM sample; load vehicle detector if compatible. Gate: `docs/api-findings.md` with executed snippets and honest blockers.
- [x] P1 / Friday night–Saturday / 6h: video I/O, quality, phase correlation, Riesz, spectra, bootstrap, physics prior, synthetic generation. Gate: actual `eval/results/synthetic.json`, mirrored tests, strict typing and lint.
- [ ] P2 / Saturday / 5h: background stabilization, scale calibration, excitation detection. Gate: measured shake benefit and sample vehicle trigger.
  - [x] ALIKED + LightGlue with explicit ENGINE_NEW, entire-structure exclusion, MAGSAC and LK between refreshes.
  - [x] Integrate optional stabilization into file measurement; missing models/refused transforms never silently fall back.
  - [x] Record synthetic camera-shake comparison and runtime/model provenance.
  - [x] Per-ROI method selection and multi-ROI FDD mode shape; two-point scale conversion.
  - [x] YOLOX preprocessing/inference/decoding and debounced vehicle-exit or explicit motion-energy fallback.
  - [x] Bounded spawned ROI pool, serial/pool numerical equivalence, actual local before/after timings and profile fallback.
  - [x] Fixed-scene feature-refresh timing/error comparison saved in `bench/results/stabilization_refresh.json`, with the exploratory repeat count and limitations recorded.
  - [ ] Real vehicle clip and handheld validation. py-spy requires operating-system root on this Mac; actual cProfile fallback is retained.
- [ ] P3 / Saturday after recordings arrive by 14:00 IST / 4h: desk vs accelerometer evaluation, damage-state comparison, healthy/damaged magnification and audification, true-fps checks. Gate: `eval/results/desk.json` from supplied recordings.
- [x] P4 / Saturday / 5h: deterministic agent, baseline, optional guarded Bedrock planner; evaluate ADAPT, RETRY, WATCH and approval, including insufficient evidence. Gate: replay trace and `eval/results/agent.json` across at least 20 captures.
- [ ] P5 / Saturday–Sunday / 5h: FastAPI, upload limits, request IDs, SQS worker, S3/Dynamo storage, WebSocket updates and MCP stdio. Gate: complete upload-to-results path plus protected approval.
- [x] P6 / Sunday / 8h: write, critique and revise `docs/design-plan.md` before UI; build React/Vite/TypeScript/uPlot console; show only implemented capabilities. Gate: build/typecheck, keyboard, reduced motion, chart tables, 1440/390 screenshots and measured accessibility check.
- [ ] P7 / Sunday / 5h: CDK storage/compute/edge/observability, COOL Graviton worker without pip OpenCV, budget alarm, scheduled stop, teardown. Gate: public endpoint and real COOL provenance. Human subscription/AMI may block.
- [ ] P8 / Sunday / 3h: COOL Graviton vs pip Graviton vs pip x86 microbench and pipeline, warmup and repeated runs with intervals, prices and provenance. Gate: actual `bench/results/*.json` and `make bench`.
- [x] P9 local / Sunday / 4h: judge quick start, report/PDF, architecture and agent diagrams, video script/shot list, limitations. Gate: clean-container quick start verified.
- [x] P10 local / final local verification: self-review, security/upload/privacy audit, metric checker, desktop/mobile judge walkthrough. Freeze new features at Sunday 22:00 IST (date subject to deadline verification).
- [x] At every completed local phase: run checks, update this file with commands/output/deferred work, and commit a meaningful green checkpoint.

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
- [x] Technical report and PDF: problem, users, architecture, OpenCV/AWS, evaluation, limitations, responsible use.
- [x] Pinned dependencies and reproducible local build/deploy/test instructions.
- [ ] Publish the reviewed committed source and evidence to the configured public repository; automatic approval review requires Rahul's explicit authorization of destination and payload.
- [x] Rendered architecture diagram showing OpenCV, AWS, COOL and agent boundaries.
- [ ] Public endpoint where judges can run a real measurement.
- [ ] Video and shot list, recorded by Rahul.
- [x] Evaluation artifacts including failures; no invented field or desk results.
- [ ] COOL version/config/input/baseline/benchmark evidence proving the claimed workload ran on COOL.
- [x] Agent workflow, evidence-driven action trace and measured success/failure/human-control evaluation.

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
- [x] Happy path works end to end; malformed/empty/weak/oversized inputs produce useful typed errors.
- [x] Core inference uses OpenCV 5; COOL execution provenance attached on actual COOL runs.
- [x] Tests, mypy strict, ruff, frontend typecheck/build and required phase gates pass.
- [x] Diff self-reviewed for security, naming, edge cases, logging, determinism and unused code.
- [x] No unbuilt feature or synthetic result is presented as real bridge evidence.
- [x] Human approval required before any inspection notification; rejection reason retained.
- [x] README/report state limitations and actual deployment state.

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
- P2 progress: synthetic shake cancellation shows benefit in `eval/results/stabilization.json`; learned models actually execute through ENGINE_NEW. The real-clip detector gate remains open, so P2 is not marked complete. Multi-ROI selection/FDD and scale are now implemented. Optional model tests run locally; CI skips those tests if model assets are absent.
- Human inputs requested during implementation: desk video/accelerometer folder and confirmed acquisition fps; AWS profile/region and subscribed COOL AMI. No secret keys requested. No real-data or cloud results have been invented.

- P2 checkpoint verification: `make check` → 50 local tests passed, strict mypy clean, ruff/format and metric source guard passed. `make eval-stabilization` → benefit observed; actual before/after errors are in generated JSON, with matching source/model hashes. `make report-preview` generated `outputs/evaluation.md` from JSON references. Real vehicle/handheld gates remain pending.
- Local CLI smoke: generated an encoded synthetic fixture and ran `scripts/measure.py` → MEASURED, with runtime/input provenance and no COOL claim.

## 2026-10-24 local continuation verification

- AWS remains deferred by explicit user request; desk recordings are confirmed unavailable. Continued independent work instead of stopping at those gates.
- P4: real OpenCV synthetic replay completed all 24 expected outcomes, including ROI adaptation, actual changed-window retries, WATCH escalation, refusals and four human-approval requests. Baseline regression includes temperature range and prediction leverage; no-baseline results cannot be NORMAL. Invalid planner proposals are discarded.
- Fixed a replay-exposed bootstrap bug: uncertainty now follows the changed spectral window. Fixed a browser-exposed timestamp bug: container clock quantization is tolerated without accepting actual dropped frames.
- Local API/worker: actual bounded upload-to-durable-job-to-results path exercised in browser; token auth/replay, exclusive job leases, approval/rejection/idempotence and retention tested. SQLite mode is labeled; no cloud integration claim.
- UI: all requested pages implemented; desktop/mobile screenshots inspected and revised. Chart axes fixed to numeric time/frequency; generated video preview uses WebM for bundled-browser support. Axe scan has no remaining WCAG A/AA violations across the scanned routes and sizes. Lighthouse accessibility measurement passed; source is `eval/results/lighthouse.json`.
- SDK MCP client listed seven tools and invoked the actual OpenCV measurement engine successfully. Local measured benchmarks saved; no cloud prices/capacity inferred.
- CDK stack synthesized offline; no AWS API calls or resources created. Cloud adapters are prepared separately; active application transport remains SQLite.
- Technical report, Mermaid/SVG workflow diagrams and full recording script created. PDF rendered and all pages visually inspected; reference formatting revised for readability.


## 2026-10-26 final build and handoff audit

- Implemented private camera-watch capture for file/RTSP/HLS sources, validated timestamps, a real excitation-trigger-to-record-to-measure test, and dropped-frame refusal. Real network-camera and semantic vehicle validation remain pending.
- Added existing-bridge uploads and protected human-designated baseline fitting. Private recordings cannot use generated demonstration baselines. Per-capture scale must be supplied again rather than inheriting a previous view's geometry.
- Fixed audification duration and comparative pitch: replay the measured waveform faster, resample to a standard audio rate, loop for listening, and share a baseline reference when available. This is explicitly labeled.
- Fresh Docker image built from application source without private recordings, downloaded weights or workstation outputs. Actual browser walkthrough exercised all pages at desktop/phone sizes, upload-to-worker, native WebSocket, protected baseline fit and approval-to-local-receipt. Container credentials were used only for that generated demonstration.
- Latest quality status and JUnit counts are in `eval/results/quality.json`; browser checks in `eval/results/browser.json` and `container_browser.json`; accessibility scans in `accessibility.json` and `lighthouse.json`. Host-specific profile and ROI-pool comparisons are in `bench/results/`. The pool is optional because this local measurement did not show a mean improvement.
- macOS requires root for py-spy. The attempted command refused; no system profiling privileges were changed. Actual cProfile timings are retained and identified as a fallback. Linux py-spy capture remains a later verification item, not fabricated evidence.
- No AWS resources were created, no SNS email was sent, and no desk/field/COOL result files were fabricated. The original P5 cloud, P7 public deployment and P8 cross-instance gates remain open. Offline adapters and CDK are preparation, not a completed cloud integration.
- Automatic approval review rejected the Git push to the configured public `rahulgunwanistudy-2005/Resonance` repository because the current source/artifact publication destination and payload require explicit human authorization. Nothing was pushed. Local commits and the release package remain reviewable; do not bypass the rejection through the connector or another transport.
- Preserved Rahul's unrelated untracked `original-vs-actual-tv.png`; excluded recordings, weights, outputs, local tokens and unrelated files from source release packaging.

- Final reliability regression: historical measurements whose uncertainty overlaps the healthy prediction interval cannot confirm an alert. The actual worker path is covered by a regression test.
- Native live-connection shutdown was exercised during an owned API restart (`eval/results/shutdown.json`). The runner now supervises both child processes and terminates cleanly.
- Feature-refresh comparison completed on identical synthetic inputs. The aggregate JSON records actual errors/timings and a single exploratory repeat per setting; no timing confidence interval or real-camera speed claim is inferred.
- Final local quality, frontend build, SDK MCP measurement, offline CDK synthesis, teardown preview, metric guard, fresh-container upload/review and accessibility checks passed. Final measurements and gate counts are referenced from JSON rather than copied into report source.
