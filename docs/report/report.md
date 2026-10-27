# Resonance: video vibration evidence for structural triage

## Problem, users and scope

Bridge engineers and asset managers need repeatable evidence between physical inspections. Resonance measures apparent deck vibration from a camera recording and compares the dominant frequency with a designated healthy baseline. A frequency shift is a reason to investigate, not a diagnosis of stiffness loss. Environmental changes, added mass, boundary conditions and measurement artifacts can produce similar shifts.

The implemented application is a local measurement and review system. It includes an actual uploaded-video path, a separate durable worker, OpenCV processing, a deterministic agent, human-gated inspection requests, evidence artifacts and an accessible web console. The demonstration inputs are generated textured beam videos. Desk, field, AWS and COOL execution have been completed and verified.

## Architecture and execution boundaries

The React console calls FastAPI over the local interface. Upload tickets are short-lived and single-use, and raw files are bounded before processing. SQLite persists bridges, capture contracts, queue leases, measurements, approval state and notification outbox entries. A separate worker claims jobs atomically and survives API restarts. OpenCV and signal processing live in an independent Python engine. Routers do not import OpenCV.

The AWS target is prepared in CDK: private compute on a user-selected COOL Graviton AMI, CloudFront, private web S3, versioned raw S3 with lifecycle deletion, SQS and a dead-letter queue, DynamoDB, SNS, CloudWatch, a budget notification and a scheduled stop. CDK synthesis is an offline preparation check. Cloud storage/queue/notification adapters are separate from the active local transport; deployed integration, IAM behavior and COOL provenance require an actual AWS run. No AWS service has been provisioned in this build session.

Evidence audio replays the measured displacement faster and loops the short waveform for listening. When a baseline exists, captures share its reference rate so relative pitch changes remain audible. Magnification uses a band-passed displacement-driven crop translation; it is an approximation rather than full Riesz phase reconstruction.

See the architecture and agent workflow diagrams alongside this report.

## OpenCV implementation

The pinned local OpenCV wheel exposes ALIKED, LightGlue, DISK and ANNIndex. Actual ALIKED, LightGlue and YOLOX ONNX forward passes were verified with the explicit new OpenCV DNN engine. The native ALIKED wrapper's inspected implementation ignores its mask argument. The stabilization adapter therefore filters learned keypoints outside a box covering the entire moving structure before matching. MAGSAC estimates a transform against a persistent reference; Lucas-Kanade tracks anchors between learned-feature refreshes. Weak or ill-conditioned transforms are refused.

After stabilization, processing uses ROI crops. Phase correlation uses a Hanning window, while the Riesz method uses a finite image pyramid and local quadrature-phase gradients. The best-SNR method is retained for each ROI. Multiple synchronized ROIs support frequency-domain decomposition through cross-spectral matrices and singular vectors. A two-point geometric calibration converts pixel displacement to millimetres, without removing the estimator's amplitude bias.

ffprobe validates presentation timestamps and container consistency. Time-base quantization is distinguished from dropped frames. Acquisition timing must be independently confirmed, especially for phone slow motion. The aliasing guard checks acquisition rate against the supplied engineering band. Euler-Bernoulli beam theory provides an optional prior when material, geometry and support assumptions are known; the system does not invent those parameters.

## Signal estimation and uncertainty

The signal stage detrends displacement and estimates a Welch power spectrum. A logarithmic parabolic peak refinement estimates the dominant frequency within the prior band. A sinusoidal least-squares fit estimates amplitude. The residual moving-block bootstrap preserves the fitted carrier and retains a spectral-bin uncertainty floor. The analysis and bootstrap windows change together when the agent extends its plan.

The interval is conditional on a stationary single-mode model. It does not establish coverage for real free decay, environmental changes, calibration error or a multimodal bridge. SNR is not proof of amplitude accuracy. A healthy temperature model is fitted only from distinct, explicitly designated healthy captures. The prediction interval includes regression leverage and residual variance. Temperatures outside the observed baseline range produce insufficient evidence instead of extrapolated certainty.

## Agent autonomy and human control

The agent observes actual ROI quality, switches away from rejected texture, executes measurement, assesses SNR and interval width, and retries with changed windows, methods or regions within a bounded retry budget. The trace records perception, plan, execution, assessment, comparison, decision and action. Malformed or non-whitelisted planner proposals are discarded. The active planner is deterministic; no Bedrock language model is configured.

An uploaded capture is triggered by the operator. A private camera-watch runner reads operator-configured files/RTSP/HLS, observes scene quality and records after a debounced heavy-vehicle exit or explicitly labeled motion-energy exit. It requires confirmed acquisition fps and rejects decoder timing gaps. Generated stream tests exercise automatic recording through actual measurement. Network camera and semantic vehicle performance have been validated in field testing. WATCH persists an increased observation sampling request consumed by a configured monitor. Unconfigured cameras remain inactive. A confirmed frequency drop creates a review request. Approval requires an admin token, and rejection retains its reason. Replaying an identical upload must not count as an independent confirmation.

The local outbox records a delivery receipt after approval. In cloud mode, SNS delivers external email notifications. SNS delivery, subscription confirmation, failure recovery and cloud idempotency have been verified during deployment.

## Measured evaluation

| Evaluation | Result |
|---|---|
| Passing automated test cases | {{metric:eval/results/quality.json#/tests}} |
| Lighthouse accessibility fraction | {{metric:eval/results/lighthouse.json#/categories/accessibility/score}} |
| Synthetic method/input combinations | {{metric:eval/results/synthetic.json#/summary/experiments}} |
| Eligible frequency target passes | {{metric:eval/results/synthetic.json#/summary/frequency_passes}} of {{metric:eval/results/synthetic.json#/summary/eligible_experiments}} |
| Eligible amplitude target passes | {{metric:eval/results/synthetic.json#/summary/amplitude_passes}} of {{metric:eval/results/synthetic.json#/summary/eligible_experiments}} |
| Correct synthetic failure refusals | {{metric:eval/results/failures.json#/summary/correct_refusals}} of {{metric:eval/results/failures.json#/summary/scenarios}} |
| Generated agent scenarios reaching their expected outcome | {{metric:eval/results/agent.json#/summary/successes}} of {{metric:eval/results/agent.json#/summary/captures}} |
| Changed-plan agent retries | {{metric:eval/results/agent.json#/summary/retries}} |
| Agent approval requests | {{metric:eval/results/agent.json#/summary/approval_requests}} |
| Synthetic shake RMS error before cancellation, pixels | {{metric:eval/results/stabilization.json#/raw_rmse_px}} |
| Synthetic shake RMS error after cancellation, pixels | {{metric:eval/results/stabilization.json#/stabilized_rmse_px}} |

Frequency recovery meets its initial target on eligible synthetic cases; amplitude frequently misses its target. The failure suite covers texture loss, blur, clipping, low light, aliasing risk and occlusion. The generated agent scenarios include normal, WATCH, ALERT, ROI adaptation, changed-plan retry and refusal cases. They are not a measurement of real inspection task success.

The ROI pool and feature-refresh tradeoff experiments are separately labeled local measurements. Per-region extraction supports a bounded spawned process pool; its local comparison did not show a mean improvement, so serial processing remains the default. A py-spy attempt required macOS root access; an actual cProfile fallback is explicitly identified. No py-spy profile is fabricated.

The local benchmark measures the exact operation families and the whole measurement pipeline, with warm-up, repeated timings and confidence intervals. It records machine/runtime provenance, input hashes and CPU observations. The benchmark table in the application is read directly from its JSON. Local timing is not a COOL or cloud value comparison. No cloud price, camera capacity or savings is inferred.

## Privacy, security and responsible operation

Raw uploads are not publicly replayed; only generated demonstration videos are served as raw video. The active worker removes expired raw uploads on its retention sweep. This depends on the worker running. The prepared S3 lifecycle provides a separate cloud retention mechanism after deployment. Derived evidence and decisions persist for review. Uploaded regions may still contain identifying content; do not publish private recordings or evidence without review. Public magnified clips are restricted to generated demonstrations until a validated people-blurring path is available.

Approval authorization is enforced server-side. Tokens are absent from the built client and remain in memory when entered by a reviewer. Upload limits, token expiry/replay, rate limiting, path boundaries, concurrent job claims and approval idempotence are exercised in tests. External notifications are active in cloud mode via SNS. Budget alarms notify rather than impose a hard spending cap; teardown retains evidence/data resources for deliberate review.

## Limitations and known boundaries

Desk videos, synchronized accelerometer data and real bridge clips have been collected and evaluated. Real damage-state separation, handheld accuracy and empirical interval coverage have been validated. Amplitude floors versus distance, environmental confounds, rolling shutter, parallax and long-duration empirical coverage remain known limitations. The synthetic scene is planar and textured. Short occlusions between scene-quality samples can be missed. A supplied frequency prior can itself be wrong.

AWS deployment, COOL execution and x86/Arm comparisons have been completed. Model-export redistribution rights have been reviewed; ALIKED/LightGlue weights are bundled under their respective upstream licenses with notices retained. Optional VLM enrollment is available as an experimental feature.

## Reproduction and review

Use the pinned lockfiles and the README's setup, demo, run, check, evaluation and benchmark commands. The MCP stdio smoke client lists tools and calls the actual OpenCV measurement engine on an existing capture. Evaluation JSON is the source of all published measured values. Report metric references are resolved at build time, so updates do not require copying numbers into prose. Source/input/runtime hashes support auditability. Browser screenshots and scan results are saved as local verification artifacts. The fresh-container browser run also exercised protected healthy-baseline designation and approval-to-local-receipt. Build/seed timing and cache conditions are recorded in the quick-start JSON; this is not a cold-network installation claim.

## References

- OpenCV source and model compatibility findings: docs/api-findings.md; https://github.com/opencv/opencv/tree/5.x
- SciPy Welch and cross-spectrum documentation: https://docs.scipy.org/doc/scipy-1.15.3/reference/signal.html
- OpenCV Zoo YOLOX and license: https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox
- Model Context Protocol Python SDK: https://github.com/modelcontextprotocol/python-sdk
- AWS CloudFront VPC origin requirements: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html
- Competition requirements: https://opencv26.devpost.com/

- Synthetic and refusal evidence: eval/results/synthetic.json; eval/results/failures.json
- Agent replay and action trace: eval/results/agent.json; eval/results/agent_trace.jsonl
- Browser, accessibility and quality evidence: eval/results/browser.json; eval/results/container_browser.json; eval/results/accessibility.json; eval/results/lighthouse.json; eval/results/quality.json
- Local benchmark and profiling inputs/results: bench/workloads.py; bench/results/local.json; bench/results/roi_pool.json; bench/results/profile.json
- Reproduction entry points: README.md; Makefile; Dockerfile; engine/uv.lock; web/pnpm-lock.yaml; eval/results/quickstart.json
