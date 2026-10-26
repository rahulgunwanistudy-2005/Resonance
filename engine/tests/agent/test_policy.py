from eval.agent import SyntheticTools
from eval.synthetic import SyntheticConfig, generate

from resonance.agent.loop import run
from resonance.agent.planner import validate_proposal
from resonance.agent.policy import Plan


def test_planner_cannot_bypass_policy() -> None:
    proposal, reason = validate_proposal('{"tool":"send_alert","reason":"bypass"}', {"switch_roi"})
    assert proposal is None
    assert "Discarded" in reason


def test_successful_measurement_without_baseline_is_not_normal() -> None:
    frames, _ = generate(SyntheticConfig(roi_size=64, duration_seconds=4, amplitude_rms_px=0.5))
    result = run(
        SyntheticTools({"deck": frames}),
        bridge_id="desk",
        capture_id="unknown",
        initial_plan=Plan(roi_ids=["deck"]),
        baseline=None,
        temperature_c=None,
    )
    assert result.estimate is not None and result.estimate.outcome == "MEASURED"
    assert result.decision.status == "INSUFFICIENT_EVIDENCE"
    assert result.decision.action == "collect_baseline"
