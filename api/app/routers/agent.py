from fastapi import APIRouter, Depends

from api.app.deps import CatalogDep, require_admin
from api.app.schemas import ApprovalInput, ApprovalRecord
from resonance.models import TraceEvent

router = APIRouter()


@router.get("/agent/trace", response_model=list[TraceEvent])
def trace(service: CatalogDep, capture_id: str | None = None) -> list[TraceEvent]:
    return service.traces(capture_id)


@router.get("/approvals", response_model=list[ApprovalRecord])
def approvals(service: CatalogDep) -> list[ApprovalRecord]:
    return service.store.list("approval", ApprovalRecord)


@router.post(
    "/approvals/{approval_id}",
    response_model=ApprovalRecord,
    dependencies=[Depends(require_admin)],
)
def resolve(
    approval_id: str, value: ApprovalInput, service: CatalogDep
) -> ApprovalRecord:
    return service.approve(approval_id, value)
