from pathlib import Path

import numpy as np
from scipy.io import wavfile

from resonance.errors import EvidenceError
from resonance.models import DisplacementSeries


def audify(series: DisplacementSeries, peak_hz: float, path: Path) -> None:
    if peak_hz <= 0:
        raise EvidenceError("Audification requires a positive measured frequency")
    displacement = np.asarray(series.displacement_px, dtype=np.float64)
    displacement -= np.mean(displacement)
    maximum = float(np.max(np.abs(displacement)))
    if maximum <= 1e-12:
        raise EvidenceError("No motion is available to audify")
    # Preserve waveform samples: changing playback rate is time compression, not a synthesized tone.
    rate = round(series.fps * 330 / peak_hz)
    audio = (displacement / maximum * 0.8 * 32767).astype(np.int16).reshape(-1)
    wavfile.write(path, rate, audio)
