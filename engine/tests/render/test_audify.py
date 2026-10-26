from pathlib import Path

import numpy as np
from scipy.io import wavfile

from resonance.models import DisplacementSeries
from resonance.render.audify import audify


def test_audification_preserves_relative_frequency_with_shared_reference(tmp_path: Path) -> None:
    time = np.arange(240) / 60
    peaks = []
    for frequency in (8.0, 7.1):
        series = DisplacementSeries(
            roi_id="beam",
            method="phase_correlation",
            fps=60,
            time_seconds=time.tolist(),
            displacement_px=np.sin(2 * np.pi * frequency * time).tolist(),
            response=[1.0] * len(time),
        )
        path = tmp_path / f"{frequency}.wav"
        audify(series, frequency, path, reference_hz=8)
        rate, audio = wavfile.read(path)
        assert rate == 22050 and len(audio) == 3 * rate
        spectrum = np.abs(np.fft.rfft(audio.astype(float)))
        frequencies = np.fft.rfftfreq(len(audio), 1 / rate)
        peaks.append(float(frequencies[np.argmax(spectrum)]))
    assert 315 < peaks[0] < 345
    assert 275 < peaks[1] < 310
    assert peaks[1] < peaks[0]
