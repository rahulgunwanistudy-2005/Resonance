# Console design plan

Audience: bridge engineers, asset managers and judges. Primary task: inspect a video measurement, see the evidence and understand the next requested action. The app is structural triage, not certification.

## Tokens

| Name | Hex | Purpose |
|---|---|---|
| Concrete | #D5D7D3 | Application ground and chart margins |
| Steel | #1F2B33 | Text, navigation and video surround |
| Weathering steel | #8A3B17 | Primary action and deflection trace |
| Inspection paint | #A83800 | Alerts only |
| Patina | #285C58 | No change detected within confidence |
| Caution | #795500 | Watch and pending review |

Overpass throughout, locally bundled through Fontsource. Sentence case, tabular figures, readable form labels, no monospace labels. Large engineering title, quieter supporting text; left alignment. Use light neutral surfaces and strong structural boundaries, not cards or shadows. Buttons have modest corners and obvious focus rings.

## Layout

Desktop:
```
Resonance    Measure  Fleet  Agent review  Benchmarks  Methods
-----------------------------------------------------------
Bridge name / local synthetic designation       Status
-----------------------------------------------------------
|                                             | Measurement
|  Recorded video, ROI and calibration overlay | Frequency / CI
|  on the measurement plane                   | Next action
|                                             | Evidence links
-----------------------------------------------------------
| displacement trace                         | agent sequence
| frequency spectrum                         | evidence / tool
| chart table toggle                         | action / outcome
-----------------------------------------------------------
Triage only. Recording retention and measurement limitations.
```

Mobile:
```
Resonance                    Navigation
Bridge name / data designation
Video and region selection
Run measurement / upload progress
Result and next action
Trace / spectrum / numeric table
Agent sequence / approval form
```

Home opens with a playable generated desk-beam video and an explicit synthetic label. Own-video upload is the adjacent primary route. The video remains the dominant element; there is no invented real bridge photograph or fabricated healthy/damaged evidence. Fleet and benchmarks use real tables. Agent steps form a chronological list. Empty cloud/desk results explain the missing input.

## Critique and revision before implementation

The initial concept risked a generic instrument dashboard with large numerical tiles. Remove the tile row; readings belong in the evidence sidebar beside the video. A broad white display surround and dark steel navigation provide hierarchy without shadows or decorative hairline grids. Use the rust accent for decisions and the motion trace only. The requested recorded real-bridge motion moment depends on unavailable footage; use an honestly labeled generated beam capture for the working demo and keep it replaceable with a real recording later.

Do not introduce a dashboard of identical cards, gradients, uppercase eyebrows, animated section entrances or invented statistics. Forms use native controls with explicit validation. Reduced motion disables UI motion; playback and sound require the operator's action. Every chart has a numeric table. Live updates do not move focus. Admin tokens stay in memory and never enter URLs, storage or the built bundle.

## Verification

Review screenshots at the brief's desktop and mobile widths, revise after inspection, check keyboard paths, overflow, chart tables and the real upload/result flow. Run a measured accessibility scan; record its results rather than claiming a score in advance.
