# Decisions

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
