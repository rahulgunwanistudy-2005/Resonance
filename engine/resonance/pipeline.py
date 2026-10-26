"""Pure numerical measurement boundary; no web framework, cloud client or environment reads."""

import hashlib
import multiprocessing
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np
from numpy.typing import NDArray

from resonance.config import MeasurementConfig, Settings
from resonance.errors import EvidenceError
from resonance.io.video import probe_video, read_roi_frames
from resonance.modal.fdd import decompose
from resonance.modal.uncertainty import bootstrap_frequency_ci
from resonance.models import (
    Capture,
    DisplacementSeries,
    FrequencyBand,
    ModalEstimate,
    RoiEstimate,
    Spectrum,
)
from resonance.motion.extract import RoiWork, extract, initialize_worker
from resonance.quality.scene import assess_scene, check_sampling
from resonance.runtime import provenance
from resonance.stabilize.ego_motion import EgoMotion


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
        if config.analysis_seconds is not None:
            if (
                frames_by_roi
                and config.analysis_seconds
                > min(len(frames) for frames in frames_by_roi.values()) / fps + 1e-9
            ):
                raise EvidenceError("Requested window exceeds the capture; record a longer clip")
            frames_by_roi = {
                key: frames[: round(config.analysis_seconds * fps)]
                for key, frames in frames_by_roi.items()
            }
        if not frames_by_roi or len(frames_by_roi) > config.max_rois:
            raise EvidenceError("Select at least one ROI within the configured limit")
        lengths = {len(frames) for frames in frames_by_roi.values()}
        if len(lengths) != 1 or min(lengths) < 32:
            raise EvidenceError("ROIs need matching frame counts and enough samples")
        if min(lengths) / fps > config.max_duration_seconds:
            raise EvidenceError("Capture exceeds the configured duration limit")
        if mm_per_pixel is not None and (not np.isfinite(mm_per_pixel) or mm_per_pixel <= 0):
            raise EvidenceError("Calibration scale must be finite and positive")
        work: list[RoiWork] = []
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
            work.append(RoiWork(roi_id, frames, fps, band, config))
        if config.roi_workers > 1 and len(work) > 1:
            with ProcessPoolExecutor(
                max_workers=min(config.roi_workers, len(work)),
                mp_context=multiprocessing.get_context("spawn"),
                initializer=initialize_worker,
            ) as pool:
                results = list(pool.map(extract, work))
        else:
            results = [extract(item) for item in work]
        for region_candidates, region_reasons in results:
            for series, spectrum in region_candidates:
                if mm_per_pixel is not None:
                    series.displacement_mm = [
                        value * mm_per_pixel for value in series.displacement_px
                    ]
                candidates.append((series, spectrum))
            reasons.extend(region_reasons)
        if not candidates:
            raise EvidenceError("No ROI and extraction method produced a resolvable mode")
        roi_estimates: list[RoiEstimate] = []
        for roi_id in frames_by_roi:
            roi_candidates = [item for item in candidates if item[0].roi_id == roi_id]
            if roi_candidates:
                series, roi_spectrum = max(
                    roi_candidates, key=lambda candidate: candidate[1].snr_db
                )
                roi_estimates.append(RoiEstimate(series=series, spectrum=roi_spectrum))
        selected, spectrum = max(candidates, key=lambda candidate: candidate[1].snr_db)
        fdd = None
        if len(roi_estimates) >= 2:
            try:
                fdd = decompose(
                    [item.series for item in roi_estimates],
                    band,
                    window_seconds=config.welch_seconds,
                )
            except EvidenceError as exc:
                reasons.append(f"Mode shape unavailable: {exc}")
        ci = bootstrap_frequency_ci(
            np.asarray(selected.displacement_px),
            fps,
            band,
            repeats=config.bootstrap_repeats,
            block_seconds=config.block_seconds,
            seed=config.seed,
            window_seconds=config.welch_seconds,
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
            roi_estimates=roi_estimates,
            fdd=fdd,
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
    settings = settings or Settings()
    stabilizer: EgoMotion | None = None
    model_hashes: dict[str, str] = {}
    try:
        metadata = probe_video(capture, config)
        check_sampling(metadata.acquisition_fps, capture.band)
        if capture.stabilize:
            box = capture.structure_box
            if (
                box is None
                or box.x + box.width > metadata.width
                or box.y + box.height > metadata.height
            ):
                raise EvidenceError("Select a valid box covering the entire moving structure")
            if settings.aliked_model is None or settings.lightglue_model is None:
                raise EvidenceError(
                    "Stabilization models are missing; configure ALIKED and LightGlue weights"
                )
            stabilizer = EgoMotion(settings.aliked_model, settings.lightglue_model, [box])
            for model_path in (settings.aliked_model, settings.lightglue_model):
                model_hashes[model_path.name] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        frames = read_roi_frames(
            capture.path,
            capture.rois,
            metadata,
            config,
            frame_transform=stabilizer.apply if stabilizer else None,
        )
    except (EvidenceError, FileNotFoundError, cv2.error) as exc:
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
    result.stabilization_applied = stabilizer is not None
    result.model_sha256 = model_hashes
    return result
