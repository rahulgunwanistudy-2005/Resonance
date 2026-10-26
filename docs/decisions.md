# Decisions

## 2026-10-24 — Complete the local path while external inputs wait

Rahul explicitly deferred AWS access and confirmed desk recordings are unavailable. Continue with all independent implementation and verification. Use SQLite for the local durable job queue, measurements and approval outbox; retain separate API/worker processes and cloud adapters so the local demo exercises actual persistence and measurements. Label the local transport and generated inputs. Do not claim cloud/COOL/desk execution, provision paid resources, or ask for AWS again until deployment is otherwise ready.

## 2026-10-23 — Workflow and scope

Use the supplied engineering-workflow gates and frontend-design skill. The build prompt already authorizes the architecture and phase plan, overriding the skill's generic plan-confirmation step. Start with P0 and continue to P1 when the required runtime is available. Scaffolded, unavailable modules must fail explicitly and remain absent from the UI.

## 2026-10-23 — Deadline ambiguity

The prompt's calendar dates and weekday names disagree. Use the conservative provisional internal target 2026-10-26 08:00 IST until the official competition deadline is verified. Do not silently promise the later date.

## 2026-10-23 — Evidence discipline

Published measurements come only from generated eval/bench results with inputs, seed, configuration and runtime provenance. Empty/missing real-data runs remain pending; no placeholder values. This project is triage support, not inspection or safety certification.

## 2026-10-23 — Numerical uncertainty and amplitude limits

Use a moving-block residual bootstrap conditional on a fitted stationary sinusoid, with a spectral-bin uncertainty floor. It does not establish environmental uncertainty or frequentist coverage on real free-decay recordings. Keep that limitation alongside the reported interval. The initial synthetic run meets frequency targets and misses amplitude targets in many cases; do not compensate with a gain fit on the same evaluation set. Millimetre series are geometric conversions of the displacement estimate, not proof of amplitude accuracy.

## 2026-10-23 — Acquisition timing

ffprobe presentation timestamps can detect dropped/variable frames and contradict container fps, but cannot prove a phone's slow-motion acquisition rate. File measurement requires externally confirmed acquisition fps; absent confirmation produces INSUFFICIENT_EVIDENCE. Keep ROI storage bounded and reject overly large inputs instead of exhausting memory.

## 2026-10-23 — Background masking needs explicit filtering

The inspected OpenCV ALIKED implementation marks its mask argument unused. A native detectAndCompute call alone therefore does not enforce a static-background mask. The P2 adapter must filter keypoints explicitly outside structure ROIs before LightGlue; this is required to avoid subtracting deck motion as camera shake.

## 2026-10-23 — Stabilization boundary

Require a separate box covering the entire moving structure, rather than treating small measurement ROIs as the entire exclusion mask. Features and homography are full-scene operations; after stabilization, color conversion and motion extraction operate on ROI crops only. Retain the first frame as the global reference and estimate transforms from independent static anchors. Reject weak/ill-conditioned transforms. This estimates planar camera motion; it does not correct parallax, rolling shutter or atmospheric effects.

## 2026-10-23 — Excitation model and evaluation boundaries

Use the existing Apache-licensed OpenCV Zoo YOLOX export rather than bringing a training framework into the project. Heavy vehicle absence is debounced; the motion-energy fallback is labeled separately and never described as vehicle detection. Blank-frame inference and trigger unit tests do not establish semantic vehicle performance. Keep the P2 real-clip gate open until an actual vehicle clip is evaluated.

## 2026-10-23 — Checkpoint commits

The first P1 Git permission review timed out without a safety finding. Retried once with explicit file paths and saved the verified phase commit. No publication or cloud changes occurred.


## 2026-10-26 — Bounded ROI pool and measured default

Per-region extraction can run in a spawned process pool with bounded worker count and one OpenCV thread per child. Identical inputs preserve the numerical result. The measured startup/serialization-inclusive comparison is `bench/results/roi_pool.json`; its intervals overlap and the pool did not improve the mean on this local run. Keep serial extraction as the default and make parallelism explicit in `MeasurementConfig.roi_workers`. Do not infer Graviton behavior from this host. The workload includes extraction, spectra, FDD and bootstrap, rather than attributing the entire time to process startup.

Attempted py-spy on the owned generated benchmark process. macOS reported that root access is required. Do not alter system profiling privileges during this session. Saved an actual cProfile run and function timings in `bench/results/profile.json` as a clearly identified fallback; this is not represented as a py-spy capture. Riesz quadrature/FFT and local phase dominate that profile. Reproduce py-spy on the later Linux worker using the documented command from https://github.com/benfred/py-spy.

## 2026-10-26 — Automatic camera capture without timing fabrication

The private camera-watch runner reads files/RTSP/HLS through OpenCV and requires independently confirmed acquisition fps plus strictly increasing decoder timestamps. It observes actual scene quality and debounced heavy-vehicle exit when verified YOLOX weights are configured, otherwise an explicitly labeled motion-energy exit. It records the subsequent bounded window, rejects timing gaps, and submits through the same durable queue. WATCH changes the configured monitor's observation cadence; absent cameras remain inactive. Generated stream tests validate the trigger-to-record-to-measure path and refusal on a dropped frame. Real camera/network/semantic vehicle performance remains unverified.


## 2026-10-26 — Confirmation intervals and graceful live shutdown

Historical confirmations must satisfy the same uncertainty separation used for a current drop: the full measured interval must sit below the healthy prediction interval. Merely exceeding a frequency-drop threshold is insufficient. A real worker regression covers the case where historical uncertainty overlaps the healthy range. Distinct recording hashes remain required.

WebSocket handlers consume disconnect events while waiting for snapshots, so idle connections do not prevent server shutdown. The local runner supervises API and worker children together, bounds message size and escalates termination only after a bounded grace period. An actual native WebSocket connection was closed during an owned server restart.

## 2026-10-26 — Public publication needs explicit approval

The configured public repository exists and is empty. Automatic approval review rejected the attempt to push the local build because explicit authorization is required for that public destination and payload. Keep the reviewed local commits and release package ready. Do not retry publication through another transport without approval. AWS remains deferred and independent of this publication decision.
