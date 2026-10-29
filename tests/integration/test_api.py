import numpy as np

from simready.api.app import create_app
from simready.scene.demo import seed_demo
from tests.auth_helpers import authorized_client


def client(tmp_path):
    app = create_app(tmp_path / "studio")
    seed_demo(app.state.store)
    return authorized_client(app)


def test_api_edit_reload_history_and_version_conflict(tmp_path):
    api = client(tmp_path)
    state = api.get("/api/v1/scenes/analytic-demo").json()
    value = {
        "object_id": "box1",
        "name": "Visible box",
        "position": [0.1, 0.2, -1.5],
        "quaternion_xyzw": [0, 0, float(np.sqrt(0.5)), float(np.sqrt(0.5))],
        "scale": [0.3, 0.5, 0.2],
        "visible": True,
        "collidable": True,
    }
    response = api.put(
        "/api/v1/scenes/analytic-demo/objects",
        json={"expected_version": state["version"], "objects": [value]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    saved = api.get("/api/v1/scenes/analytic-demo").json()
    assert saved["objects"][0]["position"] == value["position"]
    conflict = api.put(
        "/api/v1/scenes/analytic-demo/objects", json={"expected_version": 1, "objects": []}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["current_version"] == 2
    assert conflict.headers["X-Request-ID"] == conflict.json()["error"]["request_id"]
    assert api.get("/api/v1/scenes/analytic-demo/versions/1").json()["objects"] == []
    assert len(api.get("/api/v1/scenes/analytic-demo/history").json()) == 2


def test_assets_and_requests_are_controlled(tmp_path):
    api = client(tmp_path)
    assert api.get("/api/v1/health").status_code == 200
    assert api.get("/api/v1/scenes/analytic-demo/assets/gaussian.ply").content.startswith(b"ply\n")
    assert api.get("/api/v1/scenes/analytic-demo/assets/studio.sqlite3").status_code == 404
    assert api.get("/api/v1/scenes/not-a-scene").status_code == 404
    bad = api.put(
        "/api/v1/scenes/analytic-demo/objects",
        json={"expected_version": 1, "objects": [], "status": "approved"},
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"
    assert "local_dataset_path" not in api.get("/api/v1/scenes/analytic-demo").text
