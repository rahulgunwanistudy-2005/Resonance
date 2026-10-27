"""Generate reproducible desk examples, kept separate from real sensor evidence."""

import hashlib
import json
from pathlib import Path

import numpy as np

from eval.synthetic import SyntheticConfig, generate, git_revision
from resonance.modal.spectrum import estimate_spectrum
from resonance.models import FrequencyBand
from resonance.motion.phase_corr import extract_phase_correlation


def run() -> dict[str, object]:
    band = FrequencyBand(low_hz=1, high_hz=15)
    rows = []
    for state, frequency in (
        ("healthy", 7.1),
        ("loosened", 6.8),
        ("mass", 6.5),
        ("cut", 6.1),
    ):
        config = SyntheticConfig(frequency_hz=frequency, amplitude_rms_px=0.5)
        frames, _ = generate(config)
        series = extract_phase_correlation(frames, config.fps, "example-deck")
        video = estimate_spectrum(np.asarray(series.displacement_px), config.fps, band)
        # Analytical acceleration from the same ideal harmonic motion. This is
        # a simulated sensor signal, never an accelerometer recording.
        sample_rate = 240.0
        times = np.arange(round(config.duration_seconds * sample_rate)) / sample_rate
        acceleration = -((2 * np.pi * frequency) ** 2) * np.sin(
            2 * np.pi * frequency * times
        )
        sensor = estimate_spectrum(acceleration, sample_rate, band)
        rows.append(
            {
                "capture_id": f"simulated_{state}_1",
                "state": state,
                "accelerometer_hz": sensor.peak_hz,
                "accelerometer_sample_rate": sample_rate,
                "video_hz": video.peak_hz,
                "frequency_error_percent": abs(video.peak_hz / sensor.peak_hz - 1)
                * 100,
                "outcome": "measured",
                "reasons": ["Generated example; no physical sensor recording"],
                "configuration": config.model_dump(),
                "video_sha256": hashlib.sha256(np.stack(frames).tobytes()).hexdigest(),
                "accelerometer_sha256": hashlib.sha256(
                    acceleration.tobytes()
                ).hexdigest(),
            }
        )
    return {
        "kind": "simulated_desk_example",
        "synthetic": True,
        "git_revision": git_revision(),
        "captures": rows,
        "limitations": [
            "Generated video textures and analytical sensor signals, not real desk trials",
            "State frequencies illustrate changes; they do not predict a physical rig",
            "No desk ground-truth or structural safety validation is claimed",
        ],
    }


def main() -> None:
    path = Path("eval/results/desk_example.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run(), indent=2) + "\n")
    print(f"Wrote labeled simulated examples to {path}")


if __name__ == "__main__":
    main()
