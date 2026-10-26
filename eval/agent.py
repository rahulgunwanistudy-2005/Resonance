import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from eval.synthetic import SyntheticConfig, generate, git_revision, source_tree_sha256
from resonance.agent.loop import run
from resonance.agent.policy import Observation, Plan
from resonance.agent.trace import write_trace
from resonance.config import MeasurementConfig
from resonance.models import FrequencyBand, ModalEstimate, TraceEvent
from resonance.physics.baseline import HealthyCapture, fit_baseline
from resonance.pipeline import measure_frames
from resonance.quality.scene import assess_scene


class SyntheticTools:
    def __init__(
        self, frames: dict[str, list[NDArray[np.float32]]], *, narrow_ci: bool = False
    ):
        self.frames = frames
        self.calls: list[Plan] = []
        self.config = MeasurementConfig(
            bootstrap_repeats=20, max_ci_width_hz=0.15 if narrow_ci else 0.5
        )

    def observe(self) -> Observation:
        quality = {
            key: assess_scene(values[0], self.config)
            for key, values in self.frames.items()
        }
        return Observation(
            accepted_rois=[key for key, value in quality.items() if value.accepted],
            rejected_rois=[key for key, value in quality.items() if not value.accepted],
            metrics={
                f"{key}_texture_std": value.texture_std
                for key, value in quality.items()
            },
            reason="Synthetic scene quality measured by OpenCV",
        )

    def measure(self, plan: Plan) -> ModalEstimate:
        self.calls.append(plan.model_copy(deep=True))
        return measure_frames(
            {key: self.frames[key] for key in plan.roi_ids},
            fps=60,
            band=FrequencyBand(low_hz=1, high_hz=15),
            capture_id="synthetic",
            bridge_id="synthetic-agent",
            config=self.config.model_copy(
                update={
                    "analysis_seconds": plan.window_seconds,
                    "welch_seconds": plan.window_seconds,
                    "extraction_method": plan.method,
                }
            ),
        )


def main() -> None:
    healthy = []
    for index, frequency in enumerate((7.98, 8, 8.02)):
        frames, _ = generate(
            SyntheticConfig(
                roi_size=64,
                duration_seconds=8,
                frequency_hz=frequency,
                amplitude_rms_px=0.5,
            )
        )
        estimate = SyntheticTools({"deck": frames}).measure(Plan(roi_ids=["deck"]))
        assert estimate.spectrum is not None
        healthy.append(
            HealthyCapture(
                capture_id=f"healthy-{index}",
                frequency_hz=estimate.spectrum.peak_hz,
                temperature_c=20,
            )
        )
    baseline = fit_baseline("synthetic-agent", healthy)
    rows: list[dict[str, object]] = []
    traces: list[TraceEvent] = []
    for index in range(24):
        scenario = ("normal", "watch", "alert", "adapt", "retry", "refusal")[index % 6]
        frequency = 7.75 if scenario == "watch" else 7.1 if scenario == "alert" else 8
        frames, _ = generate(
            SyntheticConfig(
                seed=42 + index,
                roi_size=64,
                duration_seconds=8,
                frequency_hz=frequency,
                amplitude_rms_px=0.5,
            )
        )
        blank = [np.full_like(frame, 128) for frame in frames]
        regions = {"deck": blank if scenario == "refusal" else frames}
        if scenario == "adapt":
            regions["bad"] = blank
        tools = SyntheticTools(regions, narrow_ci=scenario == "retry")
        result = run(
            tools,
            bridge_id="synthetic-agent",
            capture_id=f"replay-{index}",
            initial_plan=Plan(roi_ids=["bad" if scenario == "adapt" else "deck"]),
            baseline=baseline,
            temperature_c=20,
            previous_drops=[("independent-previous-synthetic-capture", True)]
            if scenario == "alert"
            else [],
            planner=(lambda _: '{"tool":"send_alert","reason":"bypass"}')
            if scenario == "adapt"
            else None,
        )
        expected = {
            "normal": "NORMAL",
            "watch": "WATCH",
            "alert": "ALERT",
            "adapt": "NORMAL",
            "retry": "NORMAL",
            "refusal": "INSUFFICIENT_EVIDENCE",
        }[scenario]
        rows.append(
            {
                "capture_id": f"replay-{index}",
                "scenario": scenario,
                "expected": expected,
                "actual": result.decision.status.value,
                "success": result.decision.status.value == expected,
                "plans_executed": [plan.model_dump() for plan in tools.calls],
                "retries": sum(event.state == "RETRY" for event in result.trace),
                "approval_required": result.decision.approval_id is not None,
                "sampling_multiplier": result.sampling_multiplier,
                "actions": [event.action for event in result.trace],
                "measurement": result.estimate.spectrum.model_dump()
                if result.estimate and result.estimate.spectrum
                else None,
            }
        )
        traces.extend(result.trace)
    result_json = {
        "kind": "synthetic_agent_replay",
        "git_revision": git_revision(),
        "source_tree_sha256": source_tree_sha256(),
        "baseline": baseline.model_dump(),
        "summary": {
            "captures": len(rows),
            "successes": sum(bool(row["success"]) for row in rows),
            "retries": sum(event.state == "RETRY" for event in traces),
            "refusals": sum(row["actual"] == "INSUFFICIENT_EVIDENCE" for row in rows),
            "approval_requests": sum(bool(row["approval_required"]) for row in rows),
        },
        "captures": rows,
        "limitations": [
            "Generated videos, designated synthetic healthy baseline and synthetic prior history",
            "No real structural damage claim",
            "Human approval dispatch is tested separately at the service boundary",
        ],
    }
    Path("eval/results/agent.json").write_text(json.dumps(result_json, indent=2) + "\n")
    write_trace(Path("eval/results/agent_trace.jsonl"), traces)
    print(json.dumps(result_json["summary"], indent=2))


if __name__ == "__main__":
    main()
