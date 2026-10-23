"""Deterministic image-space evaluation; synthetic motion is never labeled field evidence."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from resonance.errors import EvidenceError
from resonance.modal.spectrum import estimate_spectrum
from resonance.models import Contract, FrequencyBand
from resonance.motion.phase_corr import extract_phase_correlation
from resonance.motion.riesz import extract_riesz
from resonance.runtime import provenance


class SyntheticConfig(Contract):
    seed: int = 42
    roi_size: int = Field(default=128, ge=32, le=512)
    fps: float = Field(default=60, gt=0)
    duration_seconds: float = Field(default=8, ge=2, le=60)
    frequency_hz: float = Field(default=7.1, gt=0)
    amplitude_rms_px: float = Field(default=0.1, ge=0)
    noise_std: float = Field(default=0.5, ge=0)
    camera_shake_rms_px: float = Field(default=0, ge=0)


def generate(
    config: SyntheticConfig,
) -> tuple[list[NDArray[np.float32]], NDArray[np.float64]]:
    if config.frequency_hz >= config.fps / 2:
        raise EvidenceError("Synthetic input frequency must be below Nyquist")
    rng = np.random.default_rng(config.seed)
    size = config.roi_size
    base = rng.normal(size=(size, size)).astype(np.float32)
    base = np.asarray(cv2.GaussianBlur(base, (0, 0), 1.2), dtype=np.float32)
    base = (base - np.mean(base)) / np.std(base) * 30 + 128
    time = np.arange(round(config.duration_seconds * config.fps)) / config.fps
    truth = (
        config.amplitude_rms_px
        * np.sqrt(2)
        * np.sin(2 * np.pi * config.frequency_hz * time)
    )
    shake = config.camera_shake_rms_px * np.sqrt(2) * np.sin(2 * np.pi * 1.7 * time)
    frames: list[NDArray[np.float32]] = []
    for shift in truth + shake:
        transform = np.array([[1, 0, 0], [0, 1, shift]], dtype=np.float32)
        warped = cv2.warpAffine(
            base,
            transform,
            (size, size),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        noise = rng.normal(0, config.noise_std, size=(size, size))
        frames.append(np.clip(warped + noise, 0, 255).astype(np.float32))
    return frames, truth


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return (
        result.stdout.strip() if result.returncode == 0 else "uncommitted-initial-build"
    )


def source_tree_sha256() -> str:
    digest = hashlib.sha256()
    paths = sorted(
        [*Path("engine/resonance").rglob("*.py"), *Path("eval").rglob("*.py")]
    )
    for path in paths:
        digest.update(str(path).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for size in (64, 128, 256):
        for amplitude in (0.025, 0.05, 0.1, 0.5):
            for frequency in (3.7, 7.1):
                config = SyntheticConfig(
                    roi_size=size, amplitude_rms_px=amplitude, frequency_hz=frequency
                )
                frames, truth = generate(config)
                digest = hashlib.sha256(np.stack(frames).tobytes()).hexdigest()
                for extractor in (extract_phase_correlation, extract_riesz):
                    row: dict[str, object] = {
                        "config": config.model_dump(),
                        "method": extractor.__name__,
                        "input_sha256": digest,
                        "truth_rms_px": float(np.std(truth)),
                    }
                    try:
                        series = extractor(frames, config.fps, "synthetic-deck")
                        spectrum = estimate_spectrum(
                            np.asarray(series.displacement_px),
                            config.fps,
                            FrequencyBand(low_hz=1, high_hz=15),
                        )
                        frequency_error = abs(spectrum.peak_hz / frequency - 1) * 100
                        amplitude_error = (
                            abs(spectrum.amplitude_rms_px / amplitude - 1) * 100
                        )
                        row.update(
                            {
                                "outcome": "measured",
                                "peak_hz": spectrum.peak_hz,
                                "frequency_error_percent": frequency_error,
                                "amplitude_rms_px": spectrum.amplitude_rms_px,
                                "amplitude_error_percent": amplitude_error,
                                "snr_db": spectrum.snr_db,
                                "frequency_target_met": frequency_error <= 0.5,
                                "amplitude_target_met": amplitude_error <= 10,
                                "eligible_for_target": amplitude >= 0.05,
                            }
                        )
                    except EvidenceError as exc:
                        row.update(
                            {"outcome": "insufficient_evidence", "reason": str(exc)}
                        )
                    rows.append(row)
    noise_floor: list[dict[str, object]] = []
    for size in (64, 128, 256):
        config = SyntheticConfig(roi_size=size, amplitude_rms_px=0)
        frames, _ = generate(config)
        for extractor in (extract_phase_correlation, extract_riesz):
            series = extractor(frames, config.fps, "stationary")
            noise_floor.append(
                {
                    "config": config.model_dump(),
                    "method": series.method,
                    "noise_rms_px": float(np.std(series.displacement_px)),
                }
            )
    eligible = [row for row in rows if row.get("eligible_for_target")]
    return {
        "schema_version": 1,
        "kind": "synthetic_image_space",
        "created_at": datetime.now(UTC).isoformat(),
        "git_revision": git_revision(),
        "source_tree_sha256": source_tree_sha256(),
        "provenance": provenance().model_dump(),
        "targets": {
            "frequency_error_percent": 0.5,
            "amplitude_error_percent": 10,
            "minimum_amplitude_rms_px": 0.05,
        },
        "summary": {
            "experiments": len(rows),
            "eligible_experiments": len(eligible),
            "frequency_passes": sum(
                bool(row.get("frequency_target_met")) for row in eligible
            ),
            "amplitude_passes": sum(
                bool(row.get("amplitude_target_met")) for row in eligible
            ),
            "both_passes": sum(
                bool(row.get("frequency_target_met"))
                and bool(row.get("amplitude_target_met"))
                for row in eligible
            ),
        },
        "experiments": rows,
        "noise_floor": noise_floor,
        "limitations": [
            "Synthetic texture and planar vertical translation only",
            "OpenCV warpAffine interpolation quantizes fractional shifts",
            "No camera stabilization or real bridge accuracy claim in this evaluation",
            "SNR does not establish displacement amplitude calibration",
        ],
    }


def main() -> None:
    result = run()
    path = Path("eval/results/synthetic.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
