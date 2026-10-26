import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.app.routers import agent, bridges, captures, evidence
from api.app.schemas import DomainError
from api.app.services.catalog import Catalog
from api.app.ws import router as ws_router
from resonance.config import Settings
from resonance.errors import EvidenceError

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.catalog = Catalog(settings)
        yield

    app = FastAPI(title="Resonance", lifespan=lifespan)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid4().hex
        length = request.headers.get("content-length")
        limit = 200_000_000 if request.url.path.endswith("/content") else 65536
        if (
            request.method in {"POST", "PUT", "PATCH"}
            and length is None
            and not request.url.path.endswith("/content")
        ):
            return JSONResponse(
                {
                    "error": "A Content-Length header is required for JSON requests",
                    "request_id": request.state.request_id,
                },
                status_code=411,
            )
        if length and (not length.isdecimal() or int(length) > limit):
            return JSONResponse(
                {
                    "error": "Request exceeds the size limit",
                    "request_id": request.state.request_id,
                },
                status_code=413,
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        logger.info(
            "request_id=%s method=%s path=%s status=%s",
            request.state.request_id,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            {"error": str(exc), "request_id": request.state.request_id},
            status_code=exc.status_code,
        )

    @app.exception_handler(EvidenceError)
    async def evidence_error(request: Request, exc: EvidenceError) -> JSONResponse:
        return JSONResponse(
            {"error": str(exc), "request_id": request.state.request_id}, status_code=422
        )

    for router in (agent.router, bridges.router, captures.router, evidence.router):
        app.include_router(router, prefix="/api")
    app.include_router(ws_router)
    static = Path(__file__).resolve().parents[2] / "web/dist"
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="console")
    return app


app = create_app()
