"""Opt-in actual queue/render/perception run, using the known analytic checkpoint."""

import os
import time

import pytest

from simready.api.app import create_app
from simready.scene.demo import seed_demo
from simready.scene.models import ObjectUpdate
from tests.auth_helpers import authorized_client


@pytest.mark.gpu
@pytest.mark.skipif(
    os.environ.get("SIMREADY_GPU_TESTS") != "1", reason="opt-in isolated CUDA worker"
)
def test_actual_queued_evaluation_and_revision_binding(tmp_path):
    app = create_app(tmp_path / "studio")
    seed_demo(app.state.store)
    api = authorized_client(app)
    response = api.post("/api/v1/scenes/analytic-demo/evaluate", json={"expected_version": 1})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    app.state.store.update_objects("analytic-demo", ObjectUpdate(expected_version=1, objects=[]))
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        job = api.get(f"/api/v1/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.5)
    assert job["status"] == "succeeded", job
    report = api.get(f"/api/v1/scenes/analytic-demo/reports/{job_id}").json()
    assert report["scene_version"] == 1
    assert api.get("/api/v1/scenes/analytic-demo").json()["version"] == 2
    assert report["summary"]["view_count"] == 2
    assert report["summary"]["dataset_kind"] == "synthetic"
    assert report["summary"]["environment"]["torchvision"] == "0.19.1+cu124"
    assert report["summary"]["means"]["lpips"] >= 0
    assert (
        len(api.get(f"/api/v1/scenes/analytic-demo/reports/{job_id}/assets/views.json").json()) == 2
    )
