# Current evaluation evidence

This is a local synthetic evaluation. No desk, field, AWS or COOL result is available yet. The measured results are loaded from committed JSON; references below resolve to those files and must not be replaced by literal numbers in report source.

| Check | Observed result |
|---|---|
| Synthetic method/input combinations | {{metric:eval/results/synthetic.json#/summary/experiments}} |
| Combinations eligible for the amplitude-floor target | {{metric:eval/results/synthetic.json#/summary/eligible_experiments}} |
| Frequency target passes among eligible combinations | {{metric:eval/results/synthetic.json#/summary/frequency_passes}} |
| Amplitude target passes among eligible combinations | {{metric:eval/results/synthetic.json#/summary/amplitude_passes}} |
| Both targets passed among eligible combinations | {{metric:eval/results/synthetic.json#/summary/both_passes}} |
| Synthetic failure scenarios correctly refused | {{metric:eval/results/failures.json#/summary/correct_refusals}} out of {{metric:eval/results/failures.json#/summary/scenarios}} |

The initial implementation meets the specified frequency target on these eligible inputs but misses the amplitude target in many combinations. The experiment table includes method, ROI size, displacement amplitude, frequency, noise, seed, input hash, measured error and SNR. Stationary-image noise floors by ROI size are included in the same JSON. Do not turn these synthetic results into a minimum detectable amplitude for real bridges.

## Reproduction

```sh
make setup
make check
make eval
```

The tests generate a small encoded clip and exercise ffprobe, ROI decode, both extractors, spectrum, uncertainty and runtime provenance. A property test checks frequency recovery over generated sinusoids. Failure evaluation covers low texture, aliasing risk, low light, clipping, occlusion and blur. Handheld stabilization is a separate pending P2 evaluation.

## Interpretation limits

- Synthetic images use textured planar vertical translation and additive noise. Real perspective, rolling shutter, structural modes and atmospheric shimmer are not represented.
- Interpolated peak location does not improve the underlying spectral resolution. Bootstrap intervals retain a resolution floor and are conditional on a stationary single-mode fit; empirical coverage on free decay is unverified.
- The Riesz implementation uses a finite pyramid and local phase-gradient approximation. Its amplitude gain is not calibrated; phase-correlation amplitude is also biased at small shifts. Selecting the highest SNR does not fix amplitude bias.
- A geometric scale converts pixels to millimetres but does not validate the displacement estimator. Do not use the current amplitude estimate for an engineering load or deflection decision.
- Camera-shake cancellation, accelerated cloud execution, human-gated alerts, and the public upload flow are not yet implemented in this checkpoint.
- Presentation timestamps validate playback cadence. A confirmed camera acquisition rate is required for file measurements, particularly slow motion. Missing confirmation produces insufficient evidence.
- Scene quality is sampled during capture; brief occlusions between samples remain an explicit limitation.

Resonance supports structural triage. It does not replace inspection or certify structural safety.
