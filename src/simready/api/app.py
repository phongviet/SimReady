"""Local FastAPI application with registered assets and optimistic scene revisions."""

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from simready.scene.models import ObjectUpdate
from simready.scene.store import SceneStore, VersionConflict
from simready.storage import PROJECT_ROOT


def create_app(root: Path | None = None) -> FastAPI:
    store = SceneStore(root or PROJECT_ROOT / "artifacts/studio")
    app = FastAPI(title="SimReady local studio", version="0.1.0")
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "PUT"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error(request, status, code, message, **extra):
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request.state.request_id,
                    **extra,
                }
            },
        )

    @app.exception_handler(VersionConflict)
    async def version_conflict(request: Request, exc: VersionConflict):
        return error(request, 409, "version_conflict", str(exc), current_version=exc.actual)

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError):
        return error(request, 400, "invalid_request", str(exc))

    @app.exception_handler(KeyError)
    async def missing(request: Request, exc: KeyError):
        return error(request, 404, "not_found", str(exc.args[0]))

    @app.exception_handler(RequestValidationError)
    async def malformed(request: Request, exc: RequestValidationError):
        return error(
            request,
            422,
            "validation_error",
            "Request does not match the scene contract",
            details=[{"location": e["loc"], "message": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(Exception)
    async def failed(request: Request, exc: Exception):
        logging.exception("Request %s failed", request.state.request_id, exc_info=exc)
        return error(
            request, 500, "internal_error", "Operation failed; inspect server logs using request ID"
        )

    @app.get("/api/v1/health")
    def health():
        return {
            "status": "ok",
            "service": "SimReady local scene editor",
            "scope": "loopback development; review authentication not implemented yet",
        }

    @app.get("/api/v1/scenes")
    def scenes():
        return store.list_scenes()

    @app.get("/api/v1/scenes/{scene_id}")
    def scene(scene_id: str):
        return store.get(scene_id)

    @app.put("/api/v1/scenes/{scene_id}/objects")
    def objects(scene_id: str, change: ObjectUpdate):
        return store.update_objects(scene_id, change)

    @app.get("/api/v1/scenes/{scene_id}/history")
    def history(scene_id: str):
        return store.history(scene_id)

    @app.get("/api/v1/scenes/{scene_id}/versions/{version}")
    def revision(scene_id: str, version: int):
        return store.get(scene_id, version)

    @app.get("/api/v1/scenes/{scene_id}/assets/{asset_id}")
    def asset(scene_id: str, asset_id: str):
        path = store.asset(scene_id, asset_id)
        return FileResponse(path, filename=path.name, headers={"Cache-Control": "no-cache"})

    build = PROJECT_ROOT / "frontend/dist"
    if build.is_dir():
        app.mount("/", StaticFiles(directory=build, html=True), name="frontend")
    return app
