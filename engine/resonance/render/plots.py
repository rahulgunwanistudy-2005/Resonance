from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from resonance.errors import EvidenceError
from resonance.models import ModalEstimate


def plot_measurement(estimate: ModalEstimate, path: Path) -> None:
    if estimate.selected is None or estimate.spectrum is None:
        raise EvidenceError("Plot requires a measured trace and spectrum")
    figure, axes = plt.subplots(2, 1, figsize=(9, 5), constrained_layout=True)
    axes[0].plot(estimate.selected.time_seconds, estimate.selected.displacement_px, color="#8A3B17")
    axes[0].set(xlabel="Time (s)", ylabel="Displacement (pixels)")
    axes[1].semilogy(
        estimate.spectrum.frequency_hz, estimate.spectrum.psd_px2_per_hz, color="#285C58"
    )
    axes[1].set(xlabel="Frequency (Hz)", ylabel="Power spectral density")
    figure.savefig(path, dpi=160)
    plt.close(figure)
