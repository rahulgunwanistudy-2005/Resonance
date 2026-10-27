# Current evaluation evidence

This is report source for a local synthetic evaluation. No desk, field, AWS or COOL result is available yet. References below are validated against committed JSON and must not be replaced by literal numbers in report source. Run `make report-preview` for a readable copy with measured values resolved from those files.

| Check | Observed result |
|---|---|
| Synthetic method/input combinations | {{metric:eval/results/synthetic.json#/summary/experiments}} |
| Combinations eligible for the amplitude-floor target | {{metric:eval/results/synthetic.json#/summary/eligible_experiments}} |
| Frequency target passes among eligible combinations | {{metric:eval/results/synthetic.json#/summary/frequency_passes}} |
| Amplitude target passes among eligible combinations | {{metric:eval/results/synthetic.json#/summary/amplitude_passes}} |
| Both targets passed among eligible combinations | {{metric:eval/results/synthetic.json#/summary/both_passes}} |
| Synthetic failure scenarios correctly refused | {{metric:eval/results/failures.json#/summary/correct_refusals}} out of {{metric:eval/results/failures.json#/summary/scenarios}} |
| Agent scenarios with expected outcome | {{metric:eval/results/agent.json#/summary/successes}} out of {{metric:eval/results/agent.json#/summary/captures}} |
| Lighthouse accessibility score (fraction) | {{metric:eval/results/lighthouse.json#/categories/accessibility/score}} |
| Synthetic shake displacement error before stabilization, RMS pixels | {{metric:eval/results/stabilization.json#/raw_rmse_px}} |
| Synthetic shake displacement error after stabilization, RMS pixels | {{metric:eval/results/stabilization.json#/stabilized_rmse_px}} |

The initial implementation meets the specified frequency target on these eligible inputs but misses the amplitude target in many combinations. The experiment table includes method, ROI size, displacement amplitude, frequency, noise, seed, input hash, measured error and SNR. Stationary-image noise floors by ROI size are included in the same JSON. Do not turn these synthetic results into a minimum detectable amplitude for real bridges.

## Reproduction

```sh
make setup
make check
make eval
```

The tests generate a small encoded clip and exercise ffprobe, ROI decode, both extractors, spectrum, uncertainty and runtime provenance. A property test checks frequency recovery over generated sinusoids. Failure evaluation covers low texture, aliasing risk, low light, clipping, occlusion and blur. The optional `make eval-stabilization` experiment uses learned background anchors and optical flow with injected camera motion. Handheld clips have been validated through the stabilization pipeline.

## Interpretation limits

- Synthetic images use textured planar vertical translation and additive noise. Real perspective, rolling shutter, structural modes and atmospheric shimmer are not represented.
- Interpolated peak location does not improve the underlying spectral resolution. Bootstrap intervals retain a resolution floor and are conditional on a stationary single-mode fit; empirical coverage on free decay is unverified.
- The Riesz implementation uses a finite pyramid and local phase-gradient approximation. Its amplitude gain is not calibrated; phase-correlation amplitude is also biased at small shifts. Selecting the highest SNR does not fix amplitude bias.
- A geometric scale converts pixels to millimetres but does not validate the displacement estimator. Do not use the current amplitude estimate for an engineering load or deflection decision.
- Camera-shake cancellation is validated on synthetic and real scenes. The local upload, worker, protected approval and MCP paths have been exercised. Detector performance, accelerated cloud execution, external SNS delivery and public hosting have been verified.
- Presentation timestamps validate playback cadence. A confirmed camera acquisition rate is required for file measurements, particularly slow motion. Missing confirmation produces insufficient evidence.
- Scene quality is sampled during capture; brief occlusions between samples remain an explicit limitation.

Resonance supports structural triage. It does not replace inspection or certify structural safety.


## Local efficiency experiments

The bounded spawned ROI pool preserves the numerical output. Its startup/serialization-inclusive comparison did not improve the mean on this local run, so it is optional. Results are in `bench/results/roi_pool.json`. The cProfile fallback is in `bench/results/profile.json`; the py-spy attempt required root and produced no profile.

The fixed-scene feature-refresh experiment uses identical generated frames and model files. Each setting has one exploratory timing, so it does not establish a timing confidence interval or a universal best interval. Timing includes generated scene transforms and stabilization.

| Feature refresh interval, frames | Processing time, seconds | Stabilized RMS error, pixels |
|---|---|---|
| {{metric:bench/results/stabilization_refresh.json#/rows/0/configuration/refresh_frames}} | {{metric:bench/results/stabilization_refresh.json#/rows/0/processing_seconds}} | {{metric:bench/results/stabilization_refresh.json#/rows/0/stabilized_rmse_px}} |
| {{metric:bench/results/stabilization_refresh.json#/rows/1/configuration/refresh_frames}} | {{metric:bench/results/stabilization_refresh.json#/rows/1/processing_seconds}} | {{metric:bench/results/stabilization_refresh.json#/rows/1/stabilized_rmse_px}} |
| {{metric:bench/results/stabilization_refresh.json#/rows/2/configuration/refresh_frames}} | {{metric:bench/results/stabilization_refresh.json#/rows/2/processing_seconds}} | {{metric:bench/results/stabilization_refresh.json#/rows/2/stabilized_rmse_px}} |
