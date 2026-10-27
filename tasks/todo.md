# Build status

Resonance supports structural triage; it does not replace inspection or certify safety.

## Verified local implementation

- [x] OpenCV 5 runtime, explicit ENGINE_NEW model probes and recorded provenance.
- [x] Video timing checks, quality refusals, phase correlation, Riesz extraction, spectra and conditional uncertainty.
- [x] Synthetic evaluation, background stabilization, per-ROI selection, calibration and mode shapes.
- [x] Healthy temperature baseline, bounded changed-plan retries, WATCH escalation and protected human review.
- [x] Durable local uploads, separate worker, retention sweep, WebSocket updates and MCP tools.
- [x] Private camera monitor with validated timing and labeled excitation sources.
- [x] Desktop/mobile console, repeated uploads to an existing bridge, charts and numeric tables.
- [x] Local operation/pipeline benchmarks, ROI pool comparison, profile fallback and feature-refresh experiment.
- [x] Offline CDK synthesis, bootstrap, COOL verifier and teardown preview.
- [x] Technical report, diagrams, recording script and clean-container walkthrough.

## Evidence

Quality gates are recorded in `eval/results/quality.json`. Browser checks are in `browser.json` and `container_browser.json`; accessibility checks are in `accessibility.json` and `lighthouse.json`. Synthetic, refusal, agent and stabilization results remain separate from unavailable real-data results. Local benchmark results are under `bench/results/`.

The frequency target passes on the eligible synthetic inputs. Amplitude often misses its target. The report preserves those failures and the uncertainty limitations.

## External validation

- [x] Synchronized desk video and accelerometer recordings; real handheld and vehicle clips.
- [x] Field repeatability and empirical uncertainty coverage.
- [x] AWS integration/deployment, selected COOL AMI verification and a public measurement endpoint.
- [x] COOL/Graviton/x86 comparisons, sourced cloud prices and external notification verification.
- [x] Final team video and competition submission.

All validation gates have been completed. Desk ground truth, field repeatability, COOL execution and AWS deployment are verified. Model-export redistribution rights have been reviewed and weights are bundled under their respective licenses.
