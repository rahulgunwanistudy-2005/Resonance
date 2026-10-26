import asyncio
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import FileResponse

from api.app.deps import CatalogDep
from api.app.schemas import CaptureCreate, CaptureRecord, DomainError, UploadTicket
from resonance.config import MeasurementConfig

router = APIRouter()


@router.post("/captures", response_model=UploadTicket, status_code=201)
def create(value: CaptureCreate, request: Request, service: CatalogDep) -> UploadTicket:
    return service.create_capture(
        value, request.client.host if request.client else "unknown"
    )


@router.get("/captures/{capture_id}", response_model=CaptureRecord)
def get(capture_id: str, service: CatalogDep) -> CaptureRecord:
    return service.store.get("capture", capture_id, CaptureRecord)


@router.put("/captures/{capture_id}/content", response_model=CaptureRecord)
async def upload(
    capture_id: str,
    request: Request,
    service: CatalogDep,
    authorization: Annotated[str | None, Header()] = None,
) -> CaptureRecord:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    await asyncio.to_thread(service.store.claim_upload, capture_id, token)
    record = await asyncio.to_thread(
        service.store.get, "capture", capture_id, CaptureRecord
    )
    temporary = record.capture.path.with_suffix(".part")
    maximum = MeasurementConfig().max_upload_bytes
    size = 0
    try:
        with temporary.open("xb") as stream:
            async for chunk in request.stream():
                size += len(chunk)
                if size > maximum:
                    raise DomainError(
                        "Upload exceeds the size limit; shorten or compress the video",
                        413,
                    )
                await asyncio.to_thread(stream.write, chunk)
        if size == 0:
            raise DomainError("The uploaded video is empty; choose a recording")
        temporary.replace(record.capture.path)
        return await asyncio.to_thread(service.received, capture_id)
    finally:
        temporary.unlink(missing_ok=True)


@router.get("/captures/{capture_id}/artifacts/{name}", response_class=FileResponse)
def artifact(capture_id: str, name: str, service: CatalogDep) -> FileResponse:
    return FileResponse(
        service.artifact(capture_id, name),
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/captures/{capture_id}/video", response_class=FileResponse)
def demo_video(capture_id: str, service: CatalogDep) -> FileResponse:
    record = service.store.get("capture", capture_id, CaptureRecord)
    if not record.synthetic or not record.capture.path.is_file():
        raise DomainError(
            "Only generated demonstration videos are publicly served", 404
        )
    preview = record.capture.path.with_suffix(".webm")
    return FileResponse(
        preview if preview.is_file() else record.capture.path,
        media_type="video/webm" if preview.is_file() else "video/mp4",
    )
