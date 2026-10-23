import numpy as np
from eval.synthetic import SyntheticConfig, generate

from resonance.config import MeasurementConfig
from resonance.models import FrequencyBand
from resonance.pipeline import measure_frames


def test_pipeline_returns_frequency_and_calibrated_series() -> None:
    config = SyntheticConfig(roi_size=64, duration_seconds=4, amplitude_rms_px=0.5)
    frames, _ = generate(config)
    result = measure_frames(
        {"deck": frames},
        fps=60,
        band=FrequencyBand(low_hz=1, high_hz=15),
        capture_id="synthetic",
        bridge_id="desk",
        mm_per_pixel=2,
        config=MeasurementConfig(bootstrap_repeats=20),
    )
    assert result.outcome == "MEASURED", result.reasons
    assert result.spectrum is not None
    assert abs(result.spectrum.peak_hz - config.frequency_hz) < 0.05
    assert result.selected is not None
    assert result.selected.displacement_mm is not None
    assert len(result.candidates) == 2
    np.testing.assert_allclose(
        result.selected.displacement_mm, np.asarray(result.selected.displacement_px) * 2
    )


def test_bad_scene_and_aliasing_are_first_class_outcomes() -> None:
    frames = [np.zeros((64, 64), np.float32)] * 240
    for fps in (24, 60):
        result = measure_frames(
            {"deck": frames},
            fps=fps,
            band=FrequencyBand(low_hz=1, high_hz=15),
            capture_id="invalid",
            bridge_id="desk",
        )
        assert result.outcome == "INSUFFICIENT_EVIDENCE"
        assert result.reasons
        assert result.spectrum is None


def test_multiple_rois_record_selected_methods_and_mode_shape() -> None:
    frames, _ = generate(SyntheticConfig(roi_size=64, duration_seconds=4, amplitude_rms_px=0.5))
    result = measure_frames(
        {"left": frames, "right": frames},
        fps=60,
        band=FrequencyBand(low_hz=1, high_hz=15),
        capture_id="two-rois",
        bridge_id="desk",
        config=MeasurementConfig(bootstrap_repeats=20),
    )
    assert result.outcome == "MEASURED"
    assert len(result.roi_estimates) == 2
    assert result.fdd is not None
    np.testing.assert_allclose(result.fdd.mode_shape_real, [1, 1], atol=1e-6)
