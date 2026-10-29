"""Local FastAPI application with registered assets and optimistic scene revisions."""

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from simready.data.schema import Contract
from simready.evaluation.readiness import readiness
from simready.evaluation.store import EvaluationRequest, EvaluationStore
from simready.research.store import StudyStore
from simready.review.auth import AuthenticationError, AuthorizationError, AuthStore, Principal
from simready.review.export import ExportStore
from simready.review.workflow import ReviewRequest, SubmitRequest, Workflow
from simready.scene.models import ObjectUpdate
from simready.scene.store import SceneStore, VersionConflict
from simready.simulation.models import ScenarioUpdate, SimulationRequest
from simready.simulation.store import SimulationStore
from simready.storage import PROJECT_ROOT


class ExportRequest(Contract):
    version: int = Field(ge=1, strict=True)


def create_app(root: Path | None = None) -> FastAPI:
    store = SceneStore(root or PROJECT_ROOT / "artifacts/studio")
    evaluations = EvaluationStore(store)
    simulations = SimulationStore(store)
    auth, workflow, exports = AuthStore(store), Workflow(store), ExportStore(store)
    app = FastAPI(title="SimReady local studio", version="0.1.0")
    app.state.store = store
    app.state.evaluations = evaluations
    app.state.simulations = simulations
    app.state.auth = auth
    app.state.workflow = workflow
    app.state.exports = exports
    research = StudyStore(store.root)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "PUT", "POST"],
        allow_headers=["Content-Type", "Authorization"],
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

    @app.exception_handler(AuthenticationError)
    async def unauthenticated(request: Request, exc: AuthenticationError):
        response = error(request, 401, "authentication_required", str(exc))
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(AuthorizationError)
    async def unauthorized(request: Request, exc: AuthorizationError):
        return error(request, 403, "permission_denied", str(exc))

    def current_user(request: Request) -> Principal:
        return auth.authenticate(request.headers.get("Authorization"))

    def builder(user: Annotated[Principal, Depends(current_user)]) -> Principal:
        auth.require(user, "builder")
        return user

    def reviewer(user: Annotated[Principal, Depends(current_user)]) -> Principal:
        auth.require(user, "reviewer")
        return user

    @app.get("/api/v1/auth/me")
    def identity(user: Annotated[Principal, Depends(current_user)]):
        return user.model_dump(mode="json")

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
            "scope": "loopback local accounts; scoped review only; not production IAM",
        }

    @app.get("/api/v1/scenes")
    def scenes():
        return store.list_scenes()

    @app.get("/api/v1/research/studies")
    def studies():
        return research.list()

    @app.get("/api/v1/research/studies/{study_id}")
    def study(study_id: str):
        return research.get(study_id)

    @app.get("/api/v1/research/studies/{study_id}/assets/{name:path}")
    def study_asset(study_id: str, name: str):
        path = research.asset(study_id, name)
        return FileResponse(
            path,
            filename=path.name,
            content_disposition_type="inline",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/api/v1/scenes/{scene_id}")
    def scene(scene_id: str):
        return store.get(scene_id)

    @app.put("/api/v1/scenes/{scene_id}/objects")
    def objects(scene_id: str, change: ObjectUpdate, user: Annotated[Principal, Depends(builder)]):
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

    @app.post("/api/v1/scenes/{scene_id}/evaluate", status_code=202)
    def start_evaluation(
        scene_id: str, request: EvaluationRequest, user: Annotated[Principal, Depends(builder)]
    ):
        return evaluations.enqueue(scene_id, request)

    @app.get("/api/v1/scenes/{scene_id}/jobs")
    def scene_jobs(scene_id: str):
        return evaluations.jobs(scene_id)

    @app.get("/api/v1/jobs/{job_id}")
    def job(job_id: str):
        return evaluations.job(job_id)

    @app.get("/api/v1/scenes/{scene_id}/reports")
    def reports(scene_id: str):
        return evaluations.reports(scene_id)

    @app.get("/api/v1/scenes/{scene_id}/reports/{run_id}")
    def report(scene_id: str, run_id: str):
        return evaluations.get(scene_id, run_id)

    @app.get("/api/v1/scenes/{scene_id}/reports/{run_id}/assets/{name:path}")
    def report_asset(scene_id: str, run_id: str, name: str):
        path = evaluations.asset(scene_id, run_id, name)
        return FileResponse(
            path,
            filename=path.name,
            content_disposition_type="inline",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.put("/api/v1/scenes/{scene_id}/scenarios")
    def scenarios(
        scene_id: str, change: ScenarioUpdate, user: Annotated[Principal, Depends(builder)]
    ):
        return store.update_scenarios(scene_id, change)

    @app.post("/api/v1/scenes/{scene_id}/scenarios/run", status_code=201)
    def run_scenario(
        scene_id: str, request: SimulationRequest, user: Annotated[Principal, Depends(builder)]
    ):
        return simulations.run(scene_id, request.scenario_id, request.expected_version)

    @app.get("/api/v1/scenes/{scene_id}/simulations")
    def simulation_runs(scene_id: str):
        return simulations.runs(scene_id)

    @app.get("/api/v1/scenes/{scene_id}/simulations/{run_id}")
    def simulation_run(scene_id: str, run_id: str):
        return simulations.get(scene_id, run_id)

    @app.get("/api/v1/scenes/{scene_id}/simulations/{run_id}/assets/{name}")
    def simulation_asset(scene_id: str, run_id: str, name: str):
        path = simulations.asset(scene_id, run_id, name)
        return FileResponse(path, filename=path.name, content_disposition_type="inline")

    @app.get("/api/v1/scenes/{scene_id}/readiness")
    def scene_readiness(scene_id: str, version: int | None = None):
        return readiness(store, scene_id, version)

    @app.post("/api/v1/scenes/{scene_id}/submit")
    def submit(scene_id: str, request: SubmitRequest, user: Annotated[Principal, Depends(builder)]):
        return workflow.submit(scene_id, request, user)

    @app.post("/api/v1/scenes/{scene_id}/review")
    def review(
        scene_id: str, request: ReviewRequest, user: Annotated[Principal, Depends(reviewer)]
    ):
        return workflow.decide(scene_id, request, user)

    @app.get("/api/v1/scenes/{scene_id}/audit")
    def audit(scene_id: str):
        return workflow.records(scene_id)

    @app.post("/api/v1/scenes/{scene_id}/export", status_code=201)
    def export(
        scene_id: str, request: ExportRequest, user: Annotated[Principal, Depends(current_user)]
    ):
        return exports.build(scene_id, request.version, user)

    @app.get("/api/v1/scenes/{scene_id}/exports/{export_id}")
    def export_asset(scene_id: str, export_id: str):
        path = exports.asset(scene_id, export_id)
        return FileResponse(path, filename=f"{scene_id}-reviewed.zip")

    build = PROJECT_ROOT / "frontend/dist"
    if build.is_dir():
        app.mount("/", StaticFiles(directory=build, html=True), name="frontend")
    return app
