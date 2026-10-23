import hashlib
import platform
from pathlib import Path

import cv2

from resonance.config import Settings
from resonance.models import RuntimeProvenance


def provenance(
    settings: Settings | None = None, *, require_cool: bool = False
) -> RuntimeProvenance:
    settings = settings or Settings()
    version = str(cv2.__version__)
    path = Path(cv2.__file__).resolve()
    if not version.startswith("5."):
        raise RuntimeError(f"OpenCV 5 is required; imported {version} from {path}")
    cool = path.is_relative_to(Path("/opt/cool"))
    if require_cool and not cool:
        raise RuntimeError(f"COOL verification failed: cv2 resolves to {path}, outside /opt/cool")
    return RuntimeProvenance(
        cv2_version=version,
        cv2_path=str(path),
        build_info_sha=hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest(),
        machine=platform.machine(),
        instance_type=settings.instance_type,
        ami_id=settings.ami_id,
        cool_verified=cool,
    )
