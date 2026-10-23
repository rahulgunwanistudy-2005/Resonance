"""Pure numerical measurement boundary; no web framework, cloud client or environment reads."""

import hashlib
from collections.abc import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from resonance.config import MeasurementConfig, Settings
from resonance.errors import EvidenceError
from resonance.io.video import probe_video, read_roi_frames
from resonance.modal.spectrum import estimate_spectrum
from resonance.modal.uncertainty import bootstrap_frequency_ci
from resonance.models import Capture, DisplacementSeries, FrequencyBand, ModalEstimate, Spectrum
from resonance.motion.phase_corr import extract_phase_correlation
from resonance.motion.riesz import extract_riesz
from resonance.quality.scene import assess_scene, check_sampling
from resonance.runtime import provenance


def measure_frames(
    frames_by_roi: Mapping[str, Sequence[NDArray[np.generic]]],
    *,
    fps: float,
    band: FrequencyBand,
    capture_id: str,
    bridge_id: str,
    config: MeasurementConfig | None = None,
    settings: Settings | None = None,
    mm_per_pixel: float | None = None,
) -> ModalEstimate:
    config = config or MeasurementConfig()
    runtime = provenance(settings)
    config_sha = hashlib.sha256(config.model_dump_json().encode()).hexdigest()
    candidates: list[tuple[DisplacementSeries, Spectrum]] = []
    reasons: list[str] = []
    try:
        check_sampling(fps, band)
        if not frames_by_roi or len(frames_by_roi) > config.max_rois:
            raise EvidenceError("Select at least one ROI within the configured limit")
        lengths = {len(frames) for frames in frames_by_roi.values()}
        if len(lengths) != 1 or min(lengths) < 32:
            raise EvidenceError("ROIs need matching frame counts and enough samples")
        if min(lengths) / fps > config.max_duration_seconds:
            raise EvidenceError("Capture exceeds the configured duration limit")
        if mm_per_pixel is not None and (not np.isfinite(mm_per_pixel) or mm_per_pixel <= 0):
            raise EvidenceError("Calibration scale must be finite and positive")
        for roi_id, frames in frames_by_roi.items():
            if frames[0].size > config.max_roi_pixels:
                raise EvidenceError("ROI exceeds the configured pixel limit")
            quality_reasons = [
                reason
                for index in range(0, len(frames), max(1, round(fps)))
                for reason in assess_scene(frames[index], config).reasons
            ]
            if quality_reasons:
                reasons.extend(f"{roi_id}: {reason}" for reason in dict.fromkeys(quality_reasons))
                continue
            for extractor in (extract_phase_correlation, extract_riesz):
                try:
                    series = extractor(frames, fps, roi_id)
                    spectrum = estimate_spectrum(
                        np.asarray(series.displacement_px),
                        fps,
                        band,
                        window_seconds=config.welch_seconds,
                    )
                    if mm_per_pixel is not None:
                        series.displacement_mm = [v * mm_per_pixel for v in series.displacement_px]
                    candidates.append((series, spectrum))
                except EvidenceError as exc:
                    reasons.append(f"{roi_id}/{extractor.__name__}: {exc}")
        if not candidates:
            raise EvidenceError("No ROI and extraction method produced a resolvable mode")
        selected, spectrum = max(candidates, key=lambda candidate: candidate[1].snr_db)
        ci = bootstrap_frequency_ci(
            np.asarray(selected.displacement_px),
            fps,
            band,
            repeats=config.bootstrap_repeats,
            block_seconds=config.block_seconds,
            seed=config.seed,
        )
        if spectrum.snr_db < config.min_snr_db:
            reasons.append("SNR is below the configured evidence threshold")
        if ci[1] - ci[0] > config.max_ci_width_hz:
            reasons.append("Frequency interval is too wide; record a longer window")
        accepted = spectrum.snr_db >= config.min_snr_db and ci[1] - ci[0] <= config.max_ci_width_hz
        return ModalEstimate(
            capture_id=capture_id,
            bridge_id=bridge_id,
            outcome="MEASURED" if accepted else "INSUFFICIENT_EVIDENCE",
            reasons=reasons,
            selected=selected,
            spectrum=spectrum,
            ci_hz=ci,
            candidates=[entry[1] for entry in candidates],
            provenance=runtime,
            config_sha256=config_sha,
        )
    except EvidenceError as exc:
        return ModalEstimate(
            capture_id=capture_id,
            bridge_id=bridge_id,
            outcome="INSUFFICIENT_EVIDENCE",
            reasons=[*reasons, str(exc)],
            provenance=runtime,
            config_sha256=config_sha,
        )


def measure(
    capture: Capture, config: MeasurementConfig | None = None, settings: Settings | None = None
) -> ModalEstimate:
    config = config or MeasurementConfig()
    try:
        metadata = probe_video(capture, config)
        check_sampling(metadata.acquisition_fps, capture.band)
        frames = read_roi_frames(capture.path, capture.rois, metadata, config)
    except (EvidenceError, FileNotFoundError) as exc:
        return ModalEstimate(
            capture_id=capture.id,
            bridge_id=capture.bridge_id,
            outcome="INSUFFICIENT_EVIDENCE",
            reasons=[str(exc)],
            provenance=provenance(settings),
            config_sha256=hashlib.sha256(config.model_dump_json().encode()).hexdigest(),
        )
    result = measure_frames(
        frames,
        fps=metadata.acquisition_fps,
        band=capture.band,
        capture_id=capture.id,
        bridge_id=capture.bridge_id,
        config=config,
        settings=settings,
        mm_per_pixel=capture.calibration.mm_per_pixel if capture.calibration else None,
    )
    with capture.path.open("rb") as stream:
        result.input_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    return result
