import time

from fastapi.testclient import TestClient

from simready.api.app import create_app
from tests.auth_helpers import authorized_client


def test_authenticated_import_runs_real_subprocess_and_validates_dataset(tmp_path):
    app = create_app(tmp_path)
    request = {"scene_id": "ingress-fixture", "format": "synthetic"}
    assert TestClient(app).post("/api/v1/scenes/import", json=request).status_code == 401
    client = authorized_client(app, "builder")
    response = client.post("/api/v1/scenes/import", json=request)
    assert response.status_code == 202, response.text
    job = response.json()
    deadline = time.monotonic() + 30
    while job["status"] in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(0.1)
        job = client.get("/api/v1/jobs/" + job["job_id"]).json()
    assert job["status"] == "succeeded", job
    assert job["result"]["frames"] == 8 and job["result"]["kind"] == "synthetic"
    assert client.post("/api/v1/scenes/import", json=request).status_code == 400
    assert (
        client.post(
            "/api/v1/scenes/import",
            json={"scene_id": "invalid", "format": "tum_rgbd", "source_key": "../escape"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/scenes/import",
            json={"scene_id": "missing", "format": "tum_rgbd", "source_key": "missing"},
        ).status_code
        == 400
    )
