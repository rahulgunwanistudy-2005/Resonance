from fastapi import APIRouter, Depends, Request

from api.app.deps import CatalogDep, require_admin
from api.app.schemas import BaselineInput, BridgeCreate, BridgeRecord, CaptureRecord
from resonance.models import Baseline

router = APIRouter()


@router.get("/bridges", response_model=list[BridgeRecord])
def list_bridges(service: CatalogDep) -> list[BridgeRecord]:
    return service.store.list("bridge", BridgeRecord)


@router.post("/bridges", response_model=BridgeRecord, status_code=201)
def create_bridge(
    value: BridgeCreate, request: Request, service: CatalogDep
) -> BridgeRecord:
    service.store.limit(
        f"enroll:{request.client.host if request.client else 'unknown'}"
    )
    return service.create_bridge(value)


@router.get("/bridges/{bridge_id}/history", response_model=list[CaptureRecord])
def history(bridge_id: str, service: CatalogDep) -> list[CaptureRecord]:
    return service.history(bridge_id)


@router.post(
    "/bridges/{bridge_id}/baseline",
    response_model=Baseline,
    dependencies=[Depends(require_admin)],
)
def fit(bridge_id: str, value: BaselineInput, service: CatalogDep) -> Baseline:
    return service.baseline(bridge_id, value)
