from datetime import UTC, datetime
from pathlib import Path

from api.app.schemas import BridgeRecord, CaptureRecord
from api.app.services.catalog import Catalog
from api.app.services.measure.jobs import process_one
from resonance.agent.loop import AgentResult
from resonance.config import Settings
from resonance.models import (
    Baseline,
    Bridge,
    Capture,
    Decision,
    DecisionStatus,
    FrequencyBand,
    ModalEstimate,
    Roi,
    Spectrum,
)
from resonance.runtime import provenance
from scripts.seed_demo import create_video


def test_overlapping_historical_interval_cannot_confirm_an_alert(
    tmp_path: Path,
) -> None:
    catalog = Catalog(
        Settings(
            database_path=tmp_path / "db",
            upload_dir=tmp_path / "uploads",
            artifact_dir=tmp_path / "artifacts",
        )
    )
    bridge = Bridge(
        id="test",
        name="Confirmation regression",
        band=FrequencyBand(low_hz=1, high_hz=15),
        rois=[Roi(id="deck", x=128, y=96, width=96, height=64)],
    )
    now = datetime.now(UTC)
    catalog.store.put(
        "bridge", bridge.id, BridgeRecord(bridge=bridge, created_at=now), bridge.id
    )
    baseline = Baseline(
        bridge_id=bridge.id,
        f0_hz=8,
        temperature_reference_c=20,
        alpha_per_c=0,
        residual_std_hz=0.05,
        capture_ids=["healthy-a", "healthy-b", "healthy-c"],
        temperature_min_c=20,
        temperature_max_c=20,
        regression_inverse=[[1 / 3]],
    )
    catalog.store.put("baseline", bridge.id, baseline, bridge.id)
    path = tmp_path / "current.mp4"
    create_video(path, 7.1, 42)
    capture = Capture(
        id="current",
        bridge_id=bridge.id,
        path=path,
        rois=bridge.rois,
        band=bridge.band,
        temperature_c=20,
        acquisition_fps=60,
        acquisition_fps_verified=True,
    )
    historical = capture.model_copy(update={"id": "history"})
    estimate = ModalEstimate(
        capture_id=historical.id,
        bridge_id=bridge.id,
        outcome="MEASURED",
        reasons=[],
        spectrum=Spectrum(
            frequency_hz=[7.55],
            psd_px2_per_hz=[1.0],
            peak_hz=7.55,
            snr_db=20,
            amplitude_rms_px=0.5,
            resolution_hz=0.25,
        ),
        ci_hz=(7.3, 7.8),
        input_sha256="independent-historical-input",
        provenance=provenance(),
        config_sha256="0" * 64,
    )
    old = AgentResult(
        estimate=estimate,
        decision=Decision(
            bridge_id=bridge.id,
            capture_id=historical.id,
            status=DecisionStatus.NORMAL,
            reason="Overlaps healthy interval",
            action="log",
        ),
        trace=[],
    )
    catalog.store.put(
        "capture",
        historical.id,
        CaptureRecord(
            capture=historical, created_at=now, status="complete", result=old
        ),
        bridge.id,
    )
    catalog.store.put(
        "capture",
        capture.id,
        CaptureRecord(capture=capture, created_at=now, status="queued"),
        bridge.id,
    )
    catalog.store.enqueue(capture.id)
    assert process_one(catalog)
    result = catalog.store.get("capture", capture.id, CaptureRecord).result
    assert result is not None
    assert result.decision.status == DecisionStatus.WATCH
    assert result.decision.approval_id is None
