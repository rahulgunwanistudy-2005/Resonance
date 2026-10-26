from datetime import UTC, datetime
from pathlib import Path

from api.app.schemas import CaptureRecord
from api.app.services.catalog import Catalog
from api.app.services.measure.jobs import expire_uploads
from resonance.config import Settings
from resonance.models import Capture, FrequencyBand, Roi


def test_expiry_is_not_limited_to_the_latest_history_page(tmp_path: Path) -> None:
    service = Catalog(
        Settings(
            database_path=tmp_path / "db",
            upload_dir=tmp_path / "uploads",
            artifact_dir=tmp_path / "artifacts",
        )
    )
    for index in range(105):
        key = str(index)
        path = service.settings.upload_dir / f"{key}.video"
        path.write_bytes(b"private")
        capture = Capture(
            id=key,
            bridge_id="bridge",
            path=path,
            band=FrequencyBand(low_hz=1, high_hz=15),
            rois=[Roi(id="deck", x=0, y=0, width=64, height=64)],
        )
        service.store.put(
            "capture",
            key,
            CaptureRecord(
                capture=capture,
                created_at=datetime(2000, 1, 1, tzinfo=UTC),
                status="complete",
            ),
            "bridge",
        )
    with service.store.connection() as db:
        db.execute("UPDATE documents SET created=0 WHERE kind='capture'")
    assert expire_uploads(service) == 105
    assert not list(service.settings.upload_dir.glob("*.video"))


def test_exhausted_worker_lease_becomes_an_explicit_failure(tmp_path: Path) -> None:
    service = Catalog(
        Settings(
            database_path=tmp_path / "db",
            upload_dir=tmp_path / "uploads",
            artifact_dir=tmp_path / "artifacts",
        )
    )
    capture = Capture(
        id="exhausted",
        bridge_id="bridge",
        path=tmp_path / "missing",
        band=FrequencyBand(low_hz=1, high_hz=15),
        rois=[Roi(id="deck", x=0, y=0, width=64, height=64)],
    )
    service.store.put(
        "capture",
        "exhausted",
        CaptureRecord(
            capture=capture, created_at=datetime.now(UTC), status="processing"
        ),
        "bridge",
    )
    service.store.enqueue("exhausted")
    with service.store.connection() as db:
        db.execute("UPDATE jobs SET state='processing',attempts=3,lease=0")
    assert service.store.claim_job() is None
    assert service.store.get("capture", "exhausted", CaptureRecord).status == "failed"
