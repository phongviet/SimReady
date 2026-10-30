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

    camera = {
        "frame_id": "requested-view",
        "intrinsics": {"width": 64, "height": 48, "fx": 50, "fy": 50, "cx": 31.5, "cy": 23.5},
        "T_world_camera": [[1, 0, 0, 0.125], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]],
    }
    payload = {"reconstruction_job_id": job["job_id"], "cameras": [camera]}
    assert client.post("/api/v1/scenes/other-scene/render", json=payload).status_code == 400
    assert TestClient(app).post("/api/v1/scenes/new-scene/render", json=payload).status_code == 401
    response = client.post("/api/v1/scenes/new-scene/render", json=payload)
    assert response.status_code == 202, response.text
    rendered = wait(client, response.json())
    assert rendered["status"] == "succeeded", rendered
    prefix = "/api/v1/render-jobs/" + rendered["job_id"] + "/assets/"
    index = client.get(prefix + "renders.json").json()
    assert index["evaluation_eligible"] is False
    assert index["split"] == "custom_unverified"
    assert index["cameras"][0]["width"] == 64
    assert index["cameras"][0]["viewmat"][0][3] == -0.125
    assert len(index["files_sha256"]) == 3
    for name in index["files_sha256"]:
        assert client.get(prefix + name).status_code == 200
    assert client.get(prefix + "unknown").status_code == 404


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


def test_render_source_binding_and_camera_validation(tmp_path, monkeypatch):
    from simready.pipeline.reconstruction import work
    from simready.scene.demo import seed_demo
    from simready.scene.store import SceneStore

    seed_demo(SceneStore(tmp_path))
    client = authorized_client(create_app(tmp_path))
    monkeypatch.setattr("simready.pipeline.reconstruction.subprocess.Popen", lambda *a, **k: None)
    camera = {
        "frame_id": "view",
        "intrinsics": {"width": 64, "height": 48, "fx": 50, "fy": 50, "cx": 31.5, "cy": 23.5},
        "T_world_camera": [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]],
    }
    endpoint = "/api/v1/scenes/analytic-demo/render"
    assert client.post(endpoint, json={"cameras": []}).status_code == 422
    assert client.post(endpoint, json={"cameras": [camera, camera]}).status_code == 400
    invalid = {**camera, "T_world_camera": [[0] * 4] * 4}
    assert client.post(endpoint, json={"cameras": [invalid]}).status_code == 422
    invalid = {**camera, "frame_id": "../escape"}
    assert client.post(endpoint, json={"cameras": [invalid]}).status_code == 422
    response = client.post(endpoint, json={"cameras": [camera]})
    assert response.status_code == 202, response.text
    with SceneStore(tmp_path).connect() as db:
        model = db.execute("SELECT model_path FROM reconstruction_jobs").fetchone()[0]
    import shutil
    from pathlib import Path

    copied = tmp_path / "isolated-model"
    shutil.copytree(Path(model), copied)
    with SceneStore(tmp_path).connect() as db:
        db.execute("UPDATE reconstruction_jobs SET model_path=?", (str(copied),))
    manifest = copied / "artifact.json"
    manifest.chmod(0o644)
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    work(tmp_path)
    job = client.get("/api/v1/jobs/" + response.json()["job_id"]).json()
    assert job["status"] == "failed" and "model manifest changed" in job["error"]
    assert "model_path" not in job and "dataset_path" not in job
