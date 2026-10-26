from resonance.agent.policy import Observation, Plan
from resonance.config import MeasurementConfig, Settings
from resonance.io.video import probe_video, read_roi_frames
from resonance.models import Capture, ModalEstimate
from resonance.pipeline import measure
from resonance.quality.scene import assess_scene


class VideoTools:
    def __init__(
        self, capture: Capture, settings: Settings, config: MeasurementConfig | None = None
    ):
        self.capture = capture
        self.settings = settings
        self.config = config or MeasurementConfig()

    def observe(self) -> Observation:
        metadata = probe_video(self.capture, self.config)
        short = metadata.model_copy(update={"frame_count": 1})
        frames = read_roi_frames(self.capture.path, self.capture.rois, short, self.config)
        accepted: list[str] = []
        rejected: list[str] = []
        metrics: dict[str, float | str | bool | None] = {"fps": metadata.acquisition_fps}
        reasons = []
        for roi in self.capture.rois:
            quality = assess_scene(frames[roi.id][0], self.config)
            (accepted if quality.accepted else rejected).append(roi.id)
            metrics[f"{roi.id}_texture_std"] = quality.texture_std
            metrics[f"{roi.id}_blur_variance"] = quality.laplacian_variance
            reasons.extend(quality.reasons)
        return Observation(
            accepted_rois=accepted,
            rejected_rois=rejected,
            metrics=metrics,
            reason="; ".join(reasons) or "Selected regions contain usable texture",
        )

    def measure(self, plan: Plan) -> ModalEstimate:
        selected = self.capture.model_copy(
            update={"rois": [roi for roi in self.capture.rois if roi.id in plan.roi_ids]}
        )
        config = self.config.model_copy(
            update={
                "analysis_seconds": plan.window_seconds,
                "welch_seconds": plan.window_seconds,
                "extraction_method": plan.method,
            }
        )
        return measure(selected, config, self.settings)
