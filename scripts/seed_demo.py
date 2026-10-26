"""Generate labeled camera inputs and run the same durable worker used for uploads."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from api.app.schemas import BaselineInput, BridgeRecord, CaptureRecord, DomainError
from api.app.services.catalog import Catalog
from api.app.services.measure.jobs import process_one
from resonance.config import Settings
from resonance.models import Bridge, Capture, FrequencyBand, Roi


def create_video(path: Path, frequency: float, seed: int) -> None:
    rng = np.random.default_rng(seed)
    texture = rng.normal(size=(256, 384)).astype(np.float32)
    texture = np.asarray(cv2.GaussianBlur(texture, (0, 0), 1), dtype=np.float32)
    texture = np.clip(
        (texture - texture.mean()) / texture.std() * 30 + 128, 0, 255
    ).astype(np.uint8)
    intermediate = path.with_suffix(".avi")
    writer = cv2.VideoWriter(
        str(intermediate), cv2.VideoWriter.fourcc(*"MJPG"), 60, (384, 256)
    )
    if not writer.isOpened():
        raise RuntimeError("Synthetic video writer could not start")
    try:
        for index in range(480):
            shift = np.sqrt(2) * 0.5 * np.sin(2 * np.pi * frequency * index / 60)
            image = cv2.warpAffine(
                texture,
                np.array([[1, 0, 0], [0, 1, shift]], np.float32),
                (384, 256),
                borderMode=cv2.BORDER_REFLECT_101,
            )
            canvas = np.full((256, 384, 3), (45, 55, 60), np.uint8)
            canvas[80:176, 32:352] = cv2.cvtColor(
                image[80:176, 32:352], cv2.COLOR_GRAY2BGR
            )
            cv2.line(canvas, (32, 78), (352, 78), (170, 177, 177), 2)
            cv2.rectangle(canvas, (42, 177), (60, 220), (120, 134, 140), -1)
            cv2.rectangle(canvas, (324, 177), (342, 220), (120, 134, 140), -1)
            writer.write(canvas)
    finally:
        writer.release()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(intermediate),
            "-c:v",
            "libx264",
            "-crf",
            "15",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ],
        check=True,
        timeout=60,
    )
    intermediate.unlink()


def prepare_evidence(catalog: Catalog) -> None:
    from resonance.render.magnify import magnify

    for record in catalog.history("demo-bridge"):
        if not record.synthetic:
            continue
        preview = record.capture.path.with_suffix(".webm")
        if not preview.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    str(record.capture.path),
                    "-c:v",
                    "libvpx-vp9",
                    "-crf",
                    "25",
                    "-b:v",
                    "0",
                    "-deadline",
                    "realtime",
                    "-cpu-used",
                    "6",
                    "-threads",
                    "2",
                    str(preview.with_suffix(".partial.webm")),
                ],
                check=True,
                timeout=120,
            )
            preview.with_suffix(".partial.webm").replace(preview)
        if record.result and record.result.estimate and record.result.estimate.selected:
            artifact = (
                catalog.settings.artifact_dir / record.capture.id / "magnified.webm"
            )
            if not artifact.exists():
                magnify(record.capture, record.result.estimate, artifact)
            if "magnified.webm" not in record.artifacts:
                record.artifacts.append("magnified.webm")
                catalog.store.put(
                    "capture", record.capture.id, record, record.capture.bridge_id
                )


def main() -> None:
    catalog = Catalog(Settings.from_env())
    try:
        catalog.store.get("bridge", "demo-bridge", BridgeRecord)
        prepare_evidence(catalog)
        print("Synthetic demonstration already exists; evidence previews verified")
        return
    except DomainError as exc:
        if exc.status_code != 404:
            raise
    bridge = Bridge(
        id="demo-bridge",
        name="Desk beam / synthetic demonstration",
        band=FrequencyBand(low_hz=1, high_hz=15),
        rois=[Roi(id="deck", x=128, y=96, width=96, height=64)],
    )
    catalog.store.put(
        "bridge",
        bridge.id,
        BridgeRecord(bridge=bridge, created_at=datetime.now(UTC), synthetic=True),
        bridge.id,
    )
    healthy = []
    rows = []
    for index, frequency in enumerate((7.98, 8, 8.02, 7.1, 7.1)):
        key = f"demo-capture-{index}"
        video = catalog.settings.upload_dir / f"{key}.mp4"
        create_video(video, frequency, 42 + index)
        capture = Capture(
            id=key,
            bridge_id=bridge.id,
            path=video,
            rois=bridge.rois,
            band=bridge.band,
            acquisition_fps=60,
            acquisition_fps_verified=True,
            temperature_c=20,
        )
        record = CaptureRecord(
            capture=capture,
            created_at=datetime.now(UTC),
            status="queued",
            synthetic=True,
        )
        catalog.store.put("capture", key, record, bridge.id)
        catalog.store.enqueue(key)
        process_one(catalog)
        record = catalog.store.get("capture", key, CaptureRecord)
        if (
            record.result is None
            or record.result.estimate is None
            or record.result.estimate.outcome != "MEASURED"
        ):
            raise RuntimeError(f"Generated demo measurement failed: {record.error}")
        rows.append(
            {
                "capture_id": key,
                "known_generated_frequency_hz": frequency,
                "estimate": record.result.estimate.spectrum.model_dump()
                if record.result.estimate.spectrum
                else None,
                "decision": record.result.decision.model_dump(),
            }
        )
        if index < 3:
            healthy.append(key)
        if index == 2:
            catalog.baseline(
                bridge.id, BaselineInput(capture_ids=healthy, confirmed_healthy=True)
            )
    prepare_evidence(catalog)
    Path("eval/results/demo.json").write_text(
        json.dumps({"kind": "synthetic_local_worker_demo", "captures": rows}, indent=2)
        + "\n"
    )
    print(
        "Generated camera inputs processed through the local worker; approval remains pending"
    )


if __name__ == "__main__":
    main()
