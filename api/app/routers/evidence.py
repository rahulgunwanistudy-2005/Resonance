import json
from pathlib import Path
from typing import TypeAlias

from fastapi import APIRouter
from pydantic import JsonValue

from api.app.deps import CatalogDep
from api.app.schemas import Health

router = APIRouter()
Evidence: TypeAlias = dict[str, JsonValue]
ROOT = Path(__file__).resolve().parents[3]


def results(folder: Path) -> Evidence:
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted(folder.glob("*.json"))
    }


@router.get("/health", response_model=Health)
def health(service: CatalogDep) -> Health:
    settings = service.settings

    def present(path: Path | None) -> bool:
        return path is not None and path.is_file()

    return Health(
        admin_configured=bool(settings.admin_token and len(settings.admin_token) >= 24),
        stabilization_ready=present(settings.aliked_model)
        and present(settings.lightglue_model),
        vehicle_detection_ready=present(settings.vehicle_model),
    )


@router.get("/eval", response_model=Evidence)
def evaluations() -> Evidence:
    return results(ROOT / "eval/results")


@router.get("/bench", response_model=Evidence)
def benchmarks() -> Evidence:
    return results(ROOT / "bench/results")
