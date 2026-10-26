from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app.main import create_app
from api.app.schemas import ApprovalRecord, DomainError
from api.app.storage.local import LocalStore
from resonance.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "db.sqlite3",
        upload_dir=tmp_path / "uploads",
        artifact_dir=tmp_path / "artifacts",
        admin_token="test-admin-token-long-enough-to-be-private",
    )


def test_queue_claim_is_exclusive_and_durable(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / "db.sqlite3")
    store.enqueue("unique-capture")
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: store.claim_job(), range(2)))
    assert claims.count("unique-capture") == 1 and claims.count(None) == 1
    assert LocalStore(tmp_path / "db.sqlite3").claim_job() is None


def test_approval_auth_rejection_and_idempotence(settings: Settings) -> None:
    store = LocalStore(settings.database_path)
    for key in ("reject", "approve"):
        store.put(
            "approval",
            key,
            ApprovalRecord(
                id=key,
                bridge_id="bridge",
                capture_id="capture",
                created_at=datetime.now(UTC),
            ),
        )
    with TestClient(create_app(settings)) as client:
        assert (
            client.post(
                "/api/approvals/approve", json={"approved": True, "reason": "reviewed"}
            ).status_code
            == 401
        )
        assert store.local_receipts() == 0
        headers = {"Authorization": "Bearer " + str(settings.admin_token)}
        rejected = client.post(
            "/api/approvals/reject",
            json={"approved": False, "reason": "insufficient context"},
            headers=headers,
        )
        assert rejected.status_code == 200
        assert store.local_receipts() == 0
        response = client.post(
            "/api/approvals/approve",
            json={"approved": True, "reason": "reviewed evidence"},
            headers=headers,
        )
        assert response.status_code == 200
        assert (
            client.post(
                "/api/approvals/approve",
                json={"approved": True, "reason": "reviewed evidence"},
                headers=headers,
            ).status_code
            == 200
        )
        assert store.local_receipts() == 1
        assert store.local_receipts() == 0
        assert (
            client.post(
                "/api/approvals/approve",
                json={"approved": False, "reason": "changed mind"},
                headers=headers,
            ).status_code
            == 409
        )


def test_upload_ticket_replay_empty_body_and_request_id(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        bridge = client.post(
            "/api/bridges",
            json={
                "name": "Test beam",
                "band": {"low_hz": 1, "high_hz": 15},
                "rois": [{"id": "deck", "x": 0, "y": 0, "width": 64, "height": 64}],
            },
        ).json()
        ticket = client.post(
            "/api/captures",
            json={
                "bridge_id": bridge["bridge"]["id"],
                "acquisition_fps": 60,
                "acquisition_fps_verified": True,
            },
        ).json()
        path = ticket["upload_url"]
        headers = {"Authorization": "Bearer " + ticket["upload_token"]}
        assert (
            client.put(
                path, content=b"video", headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 403
        )
        response = client.put(path, content=b"", headers=headers)
        assert response.status_code == 400 and response.headers.get("X-Request-ID")
        assert client.put(path, content=b"video", headers=headers).status_code == 403
        assert client.get("/api/captures/does-not-exist").status_code == 404
        assert client.get("/openapi.json").status_code == 200


def test_upload_rate_limit_and_expired_token(settings: Settings) -> None:
    store = LocalStore(settings.database_path)
    store.ticket("expired", "private-token", 0)
    with pytest.raises(DomainError):
        store.claim_upload("expired", "private-token")
    for _ in range(12):
        store.limit("client")
    with pytest.raises(DomainError):
        store.limit("client")


def test_schema_and_body_limits_and_websocket(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect("/ws/live/missing") as socket:
            assert socket.receive_json() == []
        assert client.post("/api/bridges", content=b"x" * 65537).status_code == 413
        assert (
            client.post(
                "/api/bridges",
                content=iter([b"{}"]),
                headers={"Content-Type": "application/json"},
            ).status_code
            == 411
        )
        headers = {"Authorization": "Bearer " + str(settings.admin_token)}
        assert (
            client.post(
                "/api/approvals/any",
                json={"approved": False, "reason": "   "},
                headers=headers,
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/captures",
                json={
                    "bridge_id": "any",
                    "acquisition_fps": 60,
                    "acquisition_fps_verified": True,
                    "stabilize": True,
                },
            ).status_code
            == 422
        )


def test_private_capture_cannot_use_synthetic_baseline_or_inherit_scale(
    settings: Settings,
) -> None:
    from api.app.schemas import BridgeRecord

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/bridges",
            json={
                "name": "Calibration boundary",
                "band": {"low_hz": 1, "high_hz": 15},
                "rois": [{"id": "deck", "x": 0, "y": 0, "width": 64, "height": 64}],
                "calibration": {
                    "mm_per_pixel": 2,
                    "reference_length_mm": 20,
                    "points": [[0, 0], [10, 0]],
                },
            },
        )
        record = BridgeRecord.model_validate(response.json())
        request = {
            "bridge_id": record.bridge.id,
            "acquisition_fps": 60,
            "acquisition_fps_verified": True,
        }
        ticket = client.post("/api/captures", json=request).json()
        capture = client.get("/api/captures/" + ticket["capture_id"]).json()
        assert capture["capture"]["calibration"] is None
        record.synthetic = True
        LocalStore(settings.database_path).put(
            "bridge", record.bridge.id, record, record.bridge.id
        )
        assert client.post("/api/captures", json=request).status_code == 400
