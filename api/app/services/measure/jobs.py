import logging
import hashlib
from datetime import UTC, datetime, timedelta

from api.app.schemas import ApprovalRecord, BridgeRecord, CaptureRecord, DomainError
from api.app.services.catalog import Catalog
from resonance.agent.loop import run
from resonance.agent.policy import Plan
from resonance.agent.tools import VideoTools
from resonance.agent.trace import write_trace
from resonance.errors import EvidenceError
from resonance.models import Baseline
from resonance.agent.policy import Policy
from resonance.physics.baseline import predict

logger = logging.getLogger(__name__)


def process_one(catalog: Catalog) -> bool:
    key = catalog.store.claim_job()
    if key is None:
        catalog.store.local_receipts()
        return False
    record = catalog.store.get("capture", key, CaptureRecord)
    record.status = "processing"
    catalog.store.put("capture", key, record, record.capture.bridge_id)
    try:
        try:
            baseline = catalog.store.get("baseline", record.capture.bridge_id, Baseline)
        except DomainError as exc:
            if exc.status_code != 404:
                raise
            baseline = None
        history = catalog.history(record.capture.bridge_id)
        with record.capture.path.open("rb") as stream:
            current_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        try:
            policy = catalog.store.get("policy", record.capture.bridge_id, Policy)
        except DomainError as exc:
            if exc.status_code != 404:
                raise
            policy = Policy()
        drops: list[tuple[str, bool]] = []
        for item in reversed(history):
            estimate = item.result.estimate if item.result else None
            if (
                estimate is None
                or estimate.spectrum is None
                or estimate.outcome != "MEASURED"
                or estimate.ci_hz is None
                or not estimate.input_sha256
                or estimate.input_sha256 == current_hash
                or item.capture.temperature_c is None
                or baseline is None
            ):
                continue
            try:
                prediction = predict(baseline, item.capture.temperature_c)
                expected = prediction.frequency_hz
            except EvidenceError:
                continue
            drop = (expected - estimate.spectrum.peak_hz) / expected
            drops.append(
                (
                    estimate.input_sha256,
                    drop >= policy.alert_drop_fraction
                    and estimate.ci_hz[1] < prediction.lower_hz,
                )
            )
        tools = VideoTools(record.capture, catalog.settings)
        record.result = run(
            tools,
            bridge_id=record.capture.bridge_id,
            capture_id=key,
            initial_plan=Plan(roi_ids=[roi.id for roi in record.capture.rois]),
            baseline=baseline,
            temperature_c=record.capture.temperature_c,
            previous_drops=drops,
            policy=policy,
            trigger_source=record.capture.trigger_source,
        )
        record.status = "complete"
        folder = catalog.settings.artifact_dir / key
        folder.mkdir(parents=True, exist_ok=True)
        write_trace(folder / "trace.jsonl", record.result.trace)
        (folder / "measurement.json").write_text(
            record.result.model_dump_json(indent=2)
        )
        record.artifacts = ["trace.jsonl", "measurement.json"]
        if (
            record.result.estimate
            and record.result.estimate.selected
            and record.result.estimate.spectrum
        ):
            from resonance.render.audify import audify
            from resonance.render.plots import plot_measurement

            reference_hz = None
            if baseline is not None and record.capture.temperature_c is not None:
                try:
                    reference_hz = predict(
                        baseline, record.capture.temperature_c
                    ).frequency_hz
                except EvidenceError:
                    reference_hz = None
            audify(
                record.result.estimate.selected,
                record.result.estimate.spectrum.peak_hz,
                folder / "motion.wav",
                reference_hz=reference_hz,
            )
            plot_measurement(record.result.estimate, folder / "spectrum.png")
            record.artifacts.extend(["motion.wav", "spectrum.png"])
        if record.result.decision.approval_id:
            approval = ApprovalRecord(
                id=record.result.decision.approval_id,
                bridge_id=record.capture.bridge_id,
                capture_id=key,
                created_at=datetime.now(UTC),
            )
            catalog.store.put("approval", approval.id, approval, approval.bridge_id)
        bridge = catalog.store.get("bridge", record.capture.bridge_id, BridgeRecord)
        bridge.sampling_multiplier = record.result.sampling_multiplier
        catalog.store.put("bridge", bridge.bridge.id, bridge, bridge.bridge.id)
        catalog.store.put("capture", key, record, record.capture.bridge_id)
        catalog.store.finish_job(key)
        catalog.store.local_receipts()
    except (EvidenceError, OSError, ValueError, RuntimeError, DomainError):
        logger.exception("Capture processing failed: capture_id=%s", key)
        record.status = "failed"
        record.error = "Measurement could not complete. Check the recording, timing and selected regions."
        catalog.store.put("capture", key, record, record.capture.bridge_id)
        catalog.store.finish_job(key, record.error)
    return True


def expire_uploads(catalog: Catalog) -> int:
    deleted = 0
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    for record in catalog.store.expired_captures(cutoff.timestamp()):
        if (
            not record.synthetic
            and record.created_at < cutoff
            and record.status not in ("processing", "queued")
        ):
            if record.capture.path.exists():
                record.capture.path.unlink()
                deleted += 1
            if record.status == "awaiting_upload":
                record.status = "expired"
                catalog.store.put(
                    "capture", record.capture.id, record, record.capture.bridge_id
                )
    return deleted
