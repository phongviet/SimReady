import os
import time

import pytest
from fastapi.testclient import TestClient

from simready.api.app import create_app
from tests.auth_helpers import authorized_client


def wait(client, job):
    deadline = time.monotonic() + 90
    while job["status"] in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(0.1)
        job = client.get("/api/v1/jobs/" + job["job_id"]).json()
    return job


@pytest.mark.gpu
def test_actual_import_to_reconstruction_http_pipeline(tmp_path):
    if os.environ.get("SIMREADY_GPU_TESTS") != "1":
        pytest.skip("opt-in actual CUDA pipeline")
    app = create_app(tmp_path)
    client = authorized_client(app)
    job = wait(
        client,
        client.post(
            "/api/v1/scenes/import", json={"scene_id": "new-scene", "format": "synthetic"}
        ).json(),
    )
    assert job["status"] == "succeeded", job
    assert TestClient(app).post("/api/v1/scenes/new-scene/reconstruct", json={}).status_code == 401
    response = client.post("/api/v1/scenes/new-scene/reconstruct", json={"preset": "smoke"})
    assert response.status_code == 202, response.text
    job = wait(client, response.json())
    assert job["status"] == "succeeded", job
    result = client.get("/api/v1/reconstruction-jobs/" + job["job_id"] + "/assets/artifact.json")
    assert result.status_code == 200
    assert result.json()["worker"]["final_gaussians"] > 0
    assert result.json()["provenance"]["training_frame_ids"] == [
        "frame_00000",
        "frame_00001",
        "frame_00002",
        "frame_00003",
    ]
    assert (
        client.get(
            "/api/v1/reconstruction-jobs/" + job["job_id"] + "/assets/not-registered"
        ).status_code
        == 404
    )


def test_changed_queued_source_fails_without_training(tmp_path, monkeypatch):
    from simready.pipeline.reconstruction import work
    from simready.scene.demo import seed_demo
    from simready.scene.store import SceneStore

    seed_demo(SceneStore(tmp_path))
    app = create_app(tmp_path)
    client = authorized_client(app)
    monkeypatch.setattr("simready.pipeline.reconstruction.subprocess.Popen", lambda *a, **k: None)
    response = client.post("/api/v1/scenes/analytic-demo/reconstruct", json={"preset": "smoke"})
    assert response.status_code == 202
    manifest = tmp_path / "demo-dataset/manifest.json"
    manifest.chmod(0o644)
    manifest.write_text(manifest.read_text() + "\n")
    work(tmp_path)
    job = client.get("/api/v1/jobs/" + response.json()["job_id"]).json()
    assert job["status"] == "failed" and "manifest changed" in job["error"]
    assert not (tmp_path / "reconstruction-jobs" / job["job_id"] / "model").exists()
