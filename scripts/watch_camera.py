"""Run an operator-configured source; private URLs stay outside the public API."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from api.app.schemas import BridgeRecord, CaptureRecord
from api.app.services.catalog import Catalog
from resonance.agent.monitor import MonitorConfig, monitor
from resonance.config import Settings
from resonance.excitation.detector import VehicleDetector
from resonance.io.stream import frames
from resonance.models import Capture


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--bridge-id", required=True)
    args = parser.parse_args()
    config = MonitorConfig.model_validate_json(args.config.read_text())
    settings = Settings.from_env()
    catalog = Catalog(settings)
    bridge = catalog.store.get("bridge", args.bridge_id, BridgeRecord).bridge
    detector = (
        VehicleDetector(settings.vehicle_model) if settings.vehicle_model else None
    )

    def submit(capture: Capture) -> None:
        catalog.store.put(
            "capture",
            capture.id,
            CaptureRecord(
                capture=capture, created_at=datetime.now(UTC), status="queued"
            ),
            bridge.id,
        )
        catalog.store.enqueue(capture.id)

    result = monitor(
        frames(config.source),
        bridge=bridge,
        config=config,
        output_dir=settings.upload_dir,
        submit=submit,
        detector=detector,
        sampling_multiplier=lambda: catalog.store.get(
            "bridge", bridge.id, BridgeRecord
        ).sampling_multiplier,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
