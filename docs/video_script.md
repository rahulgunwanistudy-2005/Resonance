# Judge video script and shot list

Target duration: less than five minutes. Rahul records the final video and team segment. Use actual application outputs; do not substitute a generated demonstration for desk or field evidence. Replace the cloud shots only after a real deployment exists.

| Time | Picture and action | Spoken script |
|---|---|---|
| 0:00–0:10 | Play the generated beam capture and its time-compressed, looped motion audio. Keep the synthetic designation visible. | No narration. |
| 0:10–0:25 | Show the measurement and inspection review request. | “A vibrating structure leaves a signal in video. Resonance extracts that signal, tracks its uncertainty and asks an engineer to review a persistent change. This opening example is generated; it is not a real damaged bridge.” |
| 0:25–0:55 | Rahul on camera, then a view of the instrument console. | “I’m Rahul. I built Resonance for bridge engineers and asset managers who need evidence between inspections. The goal is continuous triage, not structural certification. A frequency shift is a reason to investigate; it does not, by itself, prove damage.” |
| 0:55–1:35 | Show the architecture diagram and point to the actual local components. | “OpenCV measures sub-pixel deck motion using phase correlation and Riesz local phase. ALIKED and LightGlue anchor camera motion to the static background. The spectrum and a conditional interval become evidence for a deterministic agent. The API and worker run separately, and the local job queue is durable. The AWS target is prepared; cloud execution is not yet claimed.” |
| 1:35–2:25 | Choose a video, confirm acquisition timing, select the region and optional scale, run a measurement, then open the numeric chart table. | “This is the same upload-to-worker path used for your own recording. Camera acquisition timing must be confirmed; playback metadata alone is insufficient. Every measurement includes its displacement trace, spectrum and runtime provenance. Amplitude is still experimental, even after pixel-to-millimetre conversion.” |
| 2:25–3:05 | Open the agent trace. Select an ADAPT replay and a RETRY replay from the generated evaluation trace. | “Visual evidence changes the next action. Low texture switches the selected region. Weak confidence extends the analysis window or changes the extraction method. Missing baseline or repeated failures produce insufficient evidence. A language-model proposal cannot bypass these deterministic gates.” |
| 3:05–3:35 | In Agent review, enter the local admin token privately, enter a review reason, approve or reject. Do not expose the token in the recording. | “The agent can request an inspection, but a reviewer controls the next step. Rejection keeps its reason. In this local demonstration, approval creates a delivery receipt and sends no external email. SNS delivery will be shown only after cloud validation.” |
| 3:35–4:10 | Show Methods and evaluation; read the current values below from the rendered script and JSON. Show blur and aliasing refusals. | “These are measured synthetic results. Frequency recovery reaches its target in the eligible cases; amplitude often does not. We report that miss. The agent replay includes changed plans, refusals and human-review requests. The failure cases are part of the result, not hidden exceptions.” |
| 4:10–4:30 | Show the local benchmark table and its runtime designation. | “This table measures this machine. It is not a COOL speedup or a cloud-cost claim. COOL eligibility depends on running this workload on the actual Graviton image and recording its build provenance.” |
| 4:30–4:50 | Rahul on camera. | “The next scientific gate is synchronized desk video and accelerometer evidence, followed by real bridge repeatability. Environmental effects and real interval coverage still need validation. Resonance supports engineering review. It does not replace inspection.” |
| 4:50–4:58 | End frame: verified repository and endpoint from the submission manifest. | “The repository contains the inputs, methods, tests and measured evidence. Thank you.” |

## Values to read from generated evidence

- Frequency target passes: {{metric:eval/results/synthetic.json#/summary/frequency_passes}} of {{metric:eval/results/synthetic.json#/summary/eligible_experiments}} eligible comparisons.
- Amplitude target passes: {{metric:eval/results/synthetic.json#/summary/amplitude_passes}} of {{metric:eval/results/synthetic.json#/summary/eligible_experiments}} eligible comparisons.
- Agent expected outcomes: {{metric:eval/results/agent.json#/summary/successes}} of {{metric:eval/results/agent.json#/summary/captures}} generated captures.

If real data or AWS become available, regenerate the evidence and revise the relevant script sections before recording. Do not read prepared cloud architecture as a claim that it has been deployed. No repository URL or public endpoint is invented here; the submission manifest records their pending state.
