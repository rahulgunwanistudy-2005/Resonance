# Decisions

## 2026-10-23 — Workflow and scope

Use the supplied engineering-workflow gates and frontend-design skill. The build prompt already authorizes the architecture and phase plan, overriding the skill's generic plan-confirmation step. Start with P0 and continue to P1 when the required runtime is available. Scaffolded, unavailable modules must fail explicitly and remain absent from the UI.

## 2026-10-23 — Deadline ambiguity

The prompt's calendar dates and weekday names disagree. Use the conservative provisional internal target 2026-10-26 08:00 IST until the official competition deadline is verified. Do not silently promise the later date.

## 2026-10-23 — Evidence discipline

Published measurements come only from generated eval/bench results with inputs, seed, configuration and runtime provenance. Empty/missing real-data runs remain pending; no placeholder values. This project is triage support, not inspection or safety certification.
