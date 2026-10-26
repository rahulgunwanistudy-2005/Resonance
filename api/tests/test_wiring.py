from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app.main import create_app
from api.app.schemas import ApprovalInput, ApprovalRecord, BridgeRecord, CaptureRecord
from api.app.services.catalog import Catalog
from api.app.services.measure import jobs
from api.app.storage.local import LocalStore
from resonance.config import Settings, load_env_file
from resonance.models import Baseline, Capture, FrequencyBand, Roi

BRIDGE = {
    "name": "Wiring rig",
    "span_type": "simply_supported",
    "span_length_m": 1.2,
    "band": {"low_hz": 1, "high_hz": 15},
    "rois": [
        {"id": "deck", "x": 0, "y": 0, "width": 64, "height": 64},
        {"id": "quarter", "x": 64, "y": 0, "width": 64, "height": 64},
    ],
}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "db.sqlite3",
        upload_dir=tmp_path / "uploads",
        artifact_dir=tmp_path / "artifacts",
        admin_token="test-admin-token-long-enough-to-be-private",
    )


def admin(settings: Settings) -> dict[str, str]:
    return {"Authorization": "Bearer " + str(settings.admin_token)}


def test_span_fields_and_current_baseline(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/bridges", json=BRIDGE).json()
        bridge_id = created["bridge"]["id"]
        assert created["bridge"]["span_type"] == "simply_supported"
        assert created["bridge"]["span_length_m"] == 1.2
        assert client.get(f"/api/bridges/{bridge_id}/baseline").json() is None
        LocalStore(settings.database_path).put(
            "baseline",
            bridge_id,
            Baseline(
                bridge_id=bridge_id,
                f0_hz=8,
                temperature_reference_c=20,
                alpha_per_c=0,
                residual_std_hz=0.01,
                capture_ids=["a", "b", "c"],
            ),
            bridge_id,
        )
        assert client.get(f"/api/bridges/{bridge_id}/baseline").json()["f0_hz"] == 8
        assert client.get("/api/bridges/unknown/baseline").status_code == 404


def test_delete_bridge_removes_records_and_files(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        bridge_id = client.post("/api/bridges", json=BRIDGE).json()["bridge"]["id"]
        ticket = client.post(
            "/api/captures",
            json={
                "bridge_id": bridge_id,
                "acquisition_fps": 60,
                "acquisition_fps_verified": True,
            },
        ).json()
        store = LocalStore(settings.database_path)
        record = store.get("capture", ticket["capture_id"], CaptureRecord)
        record.capture.path.write_bytes(b"video")
        artifacts = settings.artifact_dir / record.capture.id
        artifacts.mkdir(parents=True)
        (artifacts / "trace.jsonl").write_text("{}\n")
        store.put(
            "approval",
            "rejected-one",
            ApprovalRecord(
                id="rejected-one",
                bridge_id=bridge_id,
                capture_id=record.capture.id,
                created_at=datetime.now(UTC),
            ),
            bridge_id,
        )
        assert client.delete(f"/api/bridges/{bridge_id}").status_code == 401
        response = client.delete(f"/api/bridges/{bridge_id}", headers=admin(settings))
        assert response.status_code == 200
        assert response.json() == {"bridge_id": bridge_id, "captures_deleted": 1}
        assert not record.capture.path.exists() and not artifacts.exists()
        assert client.get("/api/bridges").json() == []
        assert client.get(f"/api/bridges/{bridge_id}/history").json() == []
        assert client.get("/api/approvals").json() == []
        assert (
            client.delete(
                f"/api/bridges/{bridge_id}", headers=admin(settings)
            ).status_code
            == 404
        )


def test_delete_bridge_refusals(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        store = LocalStore(settings.database_path)
        synthetic = BridgeRecord.model_validate(
            client.post("/api/bridges", json=BRIDGE).json()
        )
        synthetic.synthetic = True
        store.put("bridge", synthetic.bridge.id, synthetic, synthetic.bridge.id)
        assert (
            client.delete(
                f"/api/bridges/{synthetic.bridge.id}", headers=admin(settings)
            )
        ).status_code == 409

        busy = client.post("/api/bridges", json=BRIDGE).json()["bridge"]["id"]
        ticket = client.post(
            "/api/captures",
            json={
                "bridge_id": busy,
                "acquisition_fps": 60,
                "acquisition_fps_verified": True,
            },
        ).json()
        record = store.get("capture", ticket["capture_id"], CaptureRecord)
        record.status = "queued"
        store.put("capture", record.capture.id, record, busy)
        assert (
            client.delete(f"/api/bridges/{busy}", headers=admin(settings)).status_code
            == 409
        )

        notified = client.post("/api/bridges", json=BRIDGE).json()["bridge"]["id"]
        store.put(
            "approval",
            "approved-one",
            ApprovalRecord(
                id="approved-one",
                bridge_id=notified,
                capture_id="c",
                created_at=datetime.now(UTC),
            ),
            notified,
        )
        store.resolve_approval(
            "approved-one", ApprovalInput(approved=True, reason="ok")
        )
        assert (
            client.delete(
                f"/api/bridges/{notified}", headers=admin(settings)
            ).status_code
            == 409
        )


def test_health_reports_optional_capabilities(
    settings: Settings, tmp_path: Path
) -> None:
    with TestClient(create_app(settings)) as client:
        body = client.get("/api/health").json()
        assert body["admin_configured"] is True
        assert body["stabilization_ready"] is False
        assert body["vehicle_detection_ready"] is False
    for name in ("aliked.onnx", "lightglue.onnx", "yolox.onnx"):
        (tmp_path / name).write_bytes(b"weights")
    ready = settings.model_copy(
        update={
            "aliked_model": tmp_path / "aliked.onnx",
            "lightglue_model": tmp_path / "lightglue.onnx",
            "vehicle_model": tmp_path / "yolox.onnx",
        }
    )
    with TestClient(create_app(ready)) as client:
        body = client.get("/api/health").json()
        assert body["stabilization_ready"] is True
        assert body["vehicle_detection_ready"] is True


def test_worker_plans_every_region(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog = Catalog(settings)
    rois = [Roi(id=f"r{i}", x=16 * i, y=0, width=16, height=16) for i in range(3)]
    video = settings.upload_dir / "plan.video"
    video.write_bytes(b"video")
    capture = Capture(
        id="plan",
        bridge_id="b",
        path=video,
        rois=rois,
        band=FrequencyBand(low_hz=1, high_hz=15),
        acquisition_fps=60,
        acquisition_fps_verified=True,
    )
    record = CaptureRecord(
        capture=capture, created_at=datetime.now(UTC), status="queued"
    )
    catalog.store.put("capture", "plan", record, "b")
    catalog.store.enqueue("plan")
    seen: dict[str, Any] = {}

    def fake_run(*_: Any, **kwargs: Any) -> None:
        seen["plan"] = kwargs["initial_plan"]
        raise RuntimeError("stop after planning")

    monkeypatch.setattr(jobs, "run", fake_run)
    assert jobs.process_one(catalog)
    assert seen["plan"].roi_ids == ["r0", "r1", "r2"]


def test_env_file_fills_missing_variables_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\nRESONANCE_PORT=9000\nexport RESONANCE_HOST='0.0.0.0'\n"
        'RESONANCE_AWS_REGION="eu-west-1"\nnot a setting\n'
    )
    monkeypatch.delenv("RESONANCE_PORT", raising=False)
    monkeypatch.delenv("RESONANCE_HOST", raising=False)
    monkeypatch.setenv("RESONANCE_AWS_REGION", "us-east-1")
    loaded = load_env_file(env)
    assert sorted(loaded) == ["RESONANCE_HOST", "RESONANCE_PORT"]
    settings = Settings.from_env()
    assert settings.port == 9000 and settings.host == "0.0.0.0"
    assert settings.aws_region == "us-east-1"
    assert load_env_file(tmp_path / "missing") == []
