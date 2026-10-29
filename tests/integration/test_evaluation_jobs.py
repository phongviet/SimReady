"""Queue lifecycle tests use explicit failure injection, never experimental scores."""

import pytest
from fastapi.testclient import TestClient

from simready.api.app import create_app
from simready.evaluation.jobs import work
from simready.evaluation.store import EvaluationRequest
from simready.reconstruction.gsplat import GsplatBackend
from simready.scene.demo import seed_demo
from simready.scene.store import VersionConflict


def test_persistent_job_failure_and_request_guards(tmp_path, monkeypatch):
    app = create_app(tmp_path / "studio")
    seed_demo(app.state.store)
    store = app.state.evaluations
    # Intercept only the launcher: execute the queue synchronously with an injected backend failure.
    monkeypatch.setattr("simready.evaluation.store.subprocess.Popen", lambda *args, **kwargs: None)
    api = TestClient(app)
    queued = api.post("/api/v1/scenes/analytic-demo/evaluate", json={"expected_version": 1})
    assert queued.status_code == 202
    job_id = queued.json()["job_id"]
    assert queued.json()["status"] == "queued"
    assert api.get("/api/v1/scenes/analytic-demo/jobs").json()[0]["job_id"] == job_id
    assert api.get(f"/api/v1/jobs/{job_id}").json()["scene_version"] == 1
    assert (
        api.post(
            "/api/v1/scenes/analytic-demo/evaluate", json={"expected_version": 1, "split": "train"}
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/api/v1/scenes/analytic-demo/evaluate",
            json={"expected_version": 1, "python": "/tmp/anything"},
        ).status_code
        == 422
    )
    assert (
        api.post("/api/v1/scenes/analytic-demo/evaluate", json={"expected_version": 2}).status_code
        == 409
    )
    assert api.get("/api/v1/jobs/missing").status_code == 404

    def unavailable(*args, **kwargs):
        raise ValueError("injected backend unavailable")

    monkeypatch.setattr(GsplatBackend, "render", unavailable)
    work(store.scenes.root)
    failed = api.get(f"/api/v1/jobs/{job_id}").json()
    assert failed["status"] == "failed" and failed["run_id"] is None
    assert "injected backend unavailable" in failed["error"]
    assert "injected backend unavailable" in failed["log_tail"]
    # Reopening the application retains terminal job state, not an in-memory future.
    other = TestClient(create_app(store.scenes.root))
    assert other.get(f"/api/v1/jobs/{job_id}").json()["status"] == "failed"
    assert len(other.get("/api/v1/scenes/analytic-demo/reports").json()) == 1
    with pytest.raises(VersionConflict):
        store.enqueue("analytic-demo", EvaluationRequest(expected_version=9))


def test_interrupted_running_job_becomes_explicit_failure(tmp_path):
    app = create_app(tmp_path / "studio")
    store = app.state.evaluations
    with store.scenes.connect() as db:
        db.execute(
            "INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "interrupted",
                "old-scene",
                1,
                "test",
                "running",
                "2026-10-29",
                "2026-10-29",
                None,
                99999999,
            ),
        )
    work(store.scenes.root)
    result = store.job("interrupted")
    assert result["status"] == "failed" and "interrupted" in result["error"]
