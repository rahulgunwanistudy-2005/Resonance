import secrets
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from api.app.schemas import (
    ApprovalInput,
    ApprovalRecord,
    BaselineInput,
    BridgeCreate,
    BridgeDeleted,
    BridgeRecord,
    CaptureCreate,
    CaptureRecord,
    DomainError,
    UploadTicket,
)
from api.app.storage.local import LocalStore
from resonance.config import MeasurementConfig, Settings
from resonance.models import Baseline, Bridge, Capture, TraceEvent
from resonance.physics.baseline import HealthyCapture, fit_baseline


class Catalog:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = LocalStore(settings.database_path)
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        settings.artifact_dir.mkdir(parents=True, exist_ok=True)

    def create_bridge(self, value: BridgeCreate) -> BridgeRecord:
        bridge = Bridge(
            id=uuid4().hex,
            name=value.name,
            span_type=value.span_type,
            span_length_m=value.span_length_m,
            band=value.band,
            rois=value.rois,
            calibration=value.calibration,
        )
        record = BridgeRecord(bridge=bridge, created_at=datetime.now(UTC))
        self.store.put("bridge", bridge.id, record, bridge.id)
        return record

    def create_capture(self, value: CaptureCreate, client: str) -> UploadTicket:
        self.store.limit(f"upload:{client}")
        bridge_record = self.store.get("bridge", value.bridge_id, BridgeRecord)
        if bridge_record.synthetic:
            raise DomainError(
                "Enroll your own bridge; private recordings cannot share a generated demonstration baseline"
            )
        bridge = bridge_record.bridge
        key = uuid4().hex
        capture = Capture(
            id=key,
            bridge_id=bridge.id,
            path=self.settings.upload_dir / f"{key}.video",
            rois=value.rois or bridge.rois,
            band=bridge.band,
            calibration=value.calibration,
            temperature_c=value.temperature_c,
            acquisition_fps=value.acquisition_fps,
            acquisition_fps_verified=value.acquisition_fps_verified,
            stabilize=value.stabilize,
            structure_box=value.structure_box,
        )
        if not value.acquisition_fps_verified:
            raise DomainError(
                "Confirm camera acquisition timing before requesting an upload"
            )
        record = CaptureRecord(
            capture=capture, created_at=datetime.now(UTC), status="awaiting_upload"
        )
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(minutes=15)
        self.store.put("capture", key, record, bridge.id)
        self.store.ticket(key, token, expires.timestamp())
        return UploadTicket(
            capture_id=key,
            upload_url=f"/api/captures/{key}/content",
            upload_token=token,
            expires_at=expires,
            max_bytes=MeasurementConfig().max_upload_bytes,
        )

    def received(self, key: str) -> CaptureRecord:
        record = self.store.get("capture", key, CaptureRecord)
        record.status = "queued"
        self.store.received(record)
        return record

    def history(self, bridge_id: str | None = None) -> list[CaptureRecord]:
        return self.store.list("capture", CaptureRecord, bridge_id)

    def traces(self, capture_id: str | None = None) -> list[TraceEvent]:
        records = (
            [self.store.get("capture", capture_id, CaptureRecord)]
            if capture_id
            else self.history()
        )
        return [
            event
            for record in records
            if record.result
            for event in record.result.trace
        ][-1000:]

    def approve(self, key: str, value: ApprovalInput) -> ApprovalRecord:
        return self.store.resolve_approval(key, value)

    def baseline(self, bridge_id: str, value: BaselineInput) -> Baseline:
        if not value.confirmed_healthy:
            raise DomainError(
                "Explicitly designate the selected captures as healthy before fitting a baseline"
            )
        observations = []
        hashes: set[str] = set()
        for key in value.capture_ids:
            record = self.store.get("capture", key, CaptureRecord)
            estimate = record.result.estimate if record.result else None
            if (
                record.capture.bridge_id != bridge_id
                or estimate is None
                or estimate.outcome != "MEASURED"
                or estimate.spectrum is None
                or record.capture.temperature_c is None
            ):
                raise DomainError(
                    "Baseline captures must be measured, belong to this bridge and include temperature"
                )
            if not estimate.input_sha256 or estimate.input_sha256 in hashes:
                raise DomainError(
                    "A healthy baseline needs distinct recording files, not repeated uploads"
                )
            hashes.add(estimate.input_sha256)
            observations.append(
                HealthyCapture(
                    capture_id=key,
                    frequency_hz=estimate.spectrum.peak_hz,
                    temperature_c=record.capture.temperature_c,
                )
            )
        baseline = fit_baseline(bridge_id, observations)
        self.store.put("baseline", bridge_id, baseline, bridge_id)
        return baseline

    def current_baseline(self, bridge_id: str) -> Baseline | None:
        self.store.get("bridge", bridge_id, BridgeRecord)
        try:
            return self.store.get("baseline", bridge_id, Baseline)
        except DomainError as exc:
            if exc.status_code == 404:
                return None
            raise

    def delete_bridge(self, bridge_id: str) -> BridgeDeleted:
        record = self.store.get("bridge", bridge_id, BridgeRecord)
        if record.synthetic:
            raise DomainError("The generated demonstration cannot be deleted", 409)
        captures = self.store.list("capture", CaptureRecord, bridge_id, limit=100_000)
        if any(item.status in ("queued", "processing") for item in captures):
            raise DomainError(
                "A measurement is still running; delete after it finishes", 409
            )
        uploads = self.settings.upload_dir.resolve()
        artifacts = self.settings.artifact_dir.resolve()
        for item in captures:
            video = item.capture.path.resolve()
            if video.is_relative_to(uploads) and video.is_file():
                video.unlink()
            folder = (self.settings.artifact_dir / item.capture.id).resolve()
            if (
                folder.is_relative_to(artifacts)
                and folder != artifacts
                and folder.is_dir()
            ):
                shutil.rmtree(folder)
        self.store.delete_bridge(bridge_id, [item.capture.id for item in captures])
        return BridgeDeleted(bridge_id=bridge_id, captures_deleted=len(captures))

    def artifact(self, capture_id: str, name: str) -> Path:
        record = self.store.get("capture", capture_id, CaptureRecord)
        if name not in record.artifacts or Path(name).name != name:
            raise DomainError("Artifact not found", 404)
        path = (self.settings.artifact_dir / capture_id / name).resolve()
        if (
            not path.is_relative_to(self.settings.artifact_dir.resolve())
            or not path.is_file()
        ):
            raise DomainError("Artifact not found", 404)
        return path
