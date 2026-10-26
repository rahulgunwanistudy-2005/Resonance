"""Evidence changes executed measurement plans; external notifications are never sent here."""

from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

from resonance.agent.planner import validate_proposal
from resonance.agent.policy import Observation, Plan, Policy
from resonance.errors import EvidenceError
from resonance.models import Baseline, Contract, Decision, DecisionStatus, ModalEstimate, TraceEvent
from resonance.physics.baseline import predict


class Tools(Protocol):
    def observe(self) -> Observation: ...
    def measure(self, plan: Plan) -> ModalEstimate: ...


class AgentResult(Contract):
    estimate: ModalEstimate | None
    decision: Decision
    trace: list[TraceEvent]
    sampling_multiplier: float = 1


def run(
    tools: Tools,
    *,
    bridge_id: str,
    capture_id: str,
    initial_plan: Plan,
    baseline: Baseline | None,
    temperature_c: float | None,
    previous_drops: list[tuple[str, bool]] | None = None,
    policy: Policy | None = None,
    planner: Callable[[Observation], str] | None = None,
    trigger_source: str = "operator_upload",
) -> AgentResult:
    policy = policy or Policy()
    events: list[TraceEvent] = []

    def event(
        state: str,
        decision: str,
        action: str,
        outcome: str,
        metrics: dict[str, float | str | bool | None] | None = None,
        proposal: str | None = None,
    ) -> None:
        events.append(
            TraceEvent(
                bridge_id=bridge_id,
                state=state,
                inputs_ref=capture_id,
                evidence=metrics or {},
                decision=decision,
                action=action,
                outcome=outcome,
                proposal=proposal,
            )
        )

    def finish(
        status: DecisionStatus,
        reason: str,
        action: str,
        estimate: ModalEstimate | None,
        *,
        sampling: float = 1,
    ) -> AgentResult:
        approval_id = uuid4().hex if status == DecisionStatus.ALERT else None
        event("DECIDE", reason, action, status.value)
        event(
            "ACT",
            "Human approval is required before an inspection notification",
            action,
            "pending_approval" if approval_id else status.value,
        )
        return AgentResult(
            estimate=estimate,
            decision=Decision(
                bridge_id=bridge_id,
                capture_id=capture_id,
                status=status,
                reason=reason,
                action=action,
                approval_id=approval_id,
            ),
            trace=events,
            sampling_multiplier=sampling,
        )

    try:
        observation = tools.observe()
    except EvidenceError as exc:
        event("OBSERVE", str(exc), "inspect_scene", "insufficient_evidence")
        return finish(DecisionStatus.INSUFFICIENT_EVIDENCE, str(exc), "defer", None)
    event("OBSERVE", observation.reason, "inspect_scene", "observed", observation.metrics)
    plan = initial_plan.model_copy(deep=True)
    if any(roi not in observation.accepted_rois for roi in plan.roi_ids):
        payload = planner(observation) if planner else None
        proposal, disposition = validate_proposal(payload, {"switch_roi", "defer"})
        event(
            "ADAPT",
            disposition,
            "validate_proposal",
            "validated" if proposal else "deterministic_default",
            proposal=payload,
        )
        if not observation.accepted_rois or proposal and proposal.tool == "defer":
            event("ADAPT", observation.reason, "defer", "insufficient_evidence")
            return finish(DecisionStatus.INSUFFICIENT_EVIDENCE, observation.reason, "defer", None)
        plan.roi_ids = observation.accepted_rois
        event(
            "ADAPT",
            "Vision rejected the selected ROI; use the available textured region",
            "switch_roi",
            "plan_changed",
            {"roi_ids": ",".join(plan.roi_ids)},
        )
    event(
        "TRIGGER",
        "Uploaded capture selected by operator; no vehicle event is inferred"
        if trigger_source == "operator_upload"
        else "Camera excitation exited; source timing checked during recording",
        "use_uploaded_capture" if trigger_source == "operator_upload" else trigger_source,
        "triggered",
    )
    estimate: ModalEstimate | None = None
    for attempt in range(policy.retries + 1):
        event(
            "CAPTURE",
            "Use the requested window of the recorded capture",
            "select_window",
            "ready",
            {"window_seconds": plan.window_seconds},
        )
        estimate = tools.measure(plan)
        event(
            "MEASURE",
            "Executed OpenCV measurement tool",
            "measure",
            estimate.outcome,
            {
                "attempt": attempt,
                "window_seconds": plan.window_seconds,
                "method": plan.method,
                "roi_ids": ",".join(plan.roi_ids),
                "frequency_hz": estimate.spectrum.peak_hz if estimate.spectrum else None,
            },
        )
        event(
            "ASSESS",
            "; ".join(estimate.reasons) or "SNR, interval and physics-band gates passed",
            "assess_evidence",
            estimate.outcome,
        )
        if estimate.outcome == "MEASURED":
            break
        if attempt == policy.retries:
            return finish(
                DecisionStatus.INSUFFICIENT_EVIDENCE,
                "Changed-plan retries exhausted; no inspection conclusion",
                "defer",
                estimate,
            )
        if attempt == 0:
            plan.window_seconds = min(60, plan.window_seconds * 2)
            action = "extend_window"
        elif attempt == 1:
            plan.method = "riesz"
            action = "method_b"
        else:
            plan.roi_ids = observation.accepted_rois
            plan.window_seconds = min(60, plan.window_seconds * 2)
            action = "more_rois"
        event("RETRY", "Weak visual evidence changed the next tool call", action, "plan_changed")
    assert estimate is not None and estimate.spectrum is not None and estimate.ci_hz is not None
    if baseline is None or temperature_c is None:
        return finish(
            DecisionStatus.INSUFFICIENT_EVIDENCE,
            "Measurement complete; a healthy baseline and temperature are required for comparison",
            "collect_baseline",
            estimate,
        )
    try:
        prediction = predict(baseline, temperature_c)
    except EvidenceError as exc:
        return finish(DecisionStatus.INSUFFICIENT_EVIDENCE, str(exc), "collect_baseline", estimate)
    peak = estimate.spectrum.peak_hz
    drop = (prediction.frequency_hz - peak) / prediction.frequency_hz
    outside = estimate.ci_hz[1] < prediction.lower_hz or estimate.ci_hz[0] > prediction.upper_hz
    event(
        "COMPARE",
        "Compare the entire measurement interval with the healthy prediction interval",
        "compare_baseline",
        "outside_interval" if outside else "within_interval",
        {
            "drop_fraction": drop,
            "baseline_hz": prediction.frequency_hz,
            "prediction_lower_hz": prediction.lower_hz,
            "prediction_upper_hz": prediction.upper_hz,
        },
    )
    if not outside:
        return finish(
            DecisionStatus.NORMAL,
            "No change detected within measurement confidence",
            "log",
            estimate,
        )
    unique = {key: value for key, value in previous_drops or [] if key != capture_id}
    recent = (
        list(unique.values())[-max(0, policy.confirmation_window - 1) :]
        if policy.confirmation_window > 1
        else []
    )
    confirmed = sum(recent) + int(drop >= policy.alert_drop_fraction)
    if drop >= policy.alert_drop_fraction and confirmed >= policy.confirmations:
        return finish(
            DecisionStatus.ALERT,
            "Confirmed frequency drop needs human review; this is not a safety assessment",
            "request_approval",
            estimate,
            sampling=policy.sampling_multiplier,
        )
    return finish(
        DecisionStatus.WATCH,
        "Frequency shift exceeds the healthy prediction interval; increase sampling",
        "raise_sampling",
        estimate,
        sampling=policy.sampling_multiplier,
    )
