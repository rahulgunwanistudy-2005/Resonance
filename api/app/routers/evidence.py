import json
from pathlib import Path
from typing import TypeAlias

from fastapi import APIRouter
from pydantic import JsonValue

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
def health() -> Health:
    return Health()


@router.get("/eval", response_model=Evidence)
def evaluations() -> Evidence:
    return results(ROOT / "eval/results")


@router.get("/bench", response_model=Evidence)
def benchmarks() -> Evidence:
    return results(ROOT / "bench/results")
