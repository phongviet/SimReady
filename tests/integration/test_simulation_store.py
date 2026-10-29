import json

import pytest
from fastapi.testclient import TestClient

from simready.api.app import create_app
from simready.scene.demo import seed_demo


def test_saved_scenario_actual_map_replay_provenance_and_api_guards(tmp_path):
    app = create_app(tmp_path / "studio")
    state = seed_demo(app.state.store)
    api = TestClient(app)
    scenario = {
        "scenario_id": "virtual-route",
        "name": "Declared virtual floor demo",
        "bounds_xz_m": [-1.0, -1.8, 1.0, -0.2],
        "floor_y_m": -0.7,
        "floor_mode": "declared_virtual_plane",
        "floor_note": "Virtual plane for the simplified demo only; no observed floor truth.",
        "start_xz_m": [-0.6, -1.4],
        "goal_xz_m": [0.6, -0.6],
    }
    saved = api.put(
        "/api/v1/scenes/analytic-demo/scenarios",
        json={"expected_version": state["version"], "scenarios": [scenario]},
    )
    assert saved.status_code == 200, saved.text
    version = saved.json()["version"]
    assert saved.json()["scenarios"][0]["unknown_policy"] == "blocked"
    response = api.post(
        "/api/v1/scenes/analytic-demo/scenarios/run",
        json={"expected_version": version, "scenario_id": "virtual-route"},
    )
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["scene_version"] == version
    assert run["floor_evidence"] == "declared_virtual_floor_assumption"
    assert run["result_summary"]["route_success"] and run["result_summary"]["collisions"] == 0
    assert run["result_summary"]["path_length_m"] == pytest.approx(
        run["result_summary"]["travel_distance_m"]
    )
    base = f"/api/v1/scenes/analytic-demo/simulations/{run['run_id']}"
    assert api.get(base).json()["simulation_sha256"] == run["simulation_sha256"]
    result = api.get(base + "/assets/result.json").json()
    assert len(result["trajectory"]) > 2
    assert api.get(base + "/assets/route.png").headers["content-type"] == "image/png"
    assert api.get(base + "/assets/studio.sqlite3").status_code == 404
    assert len(api.get("/api/v1/scenes/analytic-demo/simulations").json()) == 1
    assert (
        api.post(
            "/api/v1/scenes/analytic-demo/scenarios/run",
            json={"expected_version": 1, "scenario_id": "virtual-route"},
        ).status_code
        == 409
    )
    assert (
        api.post(
            "/api/v1/scenes/analytic-demo/scenarios/run",
            json={"expected_version": version, "scenario_id": "missing"},
        ).status_code
        == 404
    )
    assert (
        api.post(
            "/api/v1/scenes/analytic-demo/scenarios/run",
            json={
                "expected_version": version,
                "scenario_id": "virtual-route",
                "unknown_policy": "free",
            },
        ).status_code
        == 422
    )
    root = app.state.simulations.run_root("analytic-demo", run["run_id"])
    manifest = json.loads((root / "simulation.json").read_text())
    assert set(manifest["files_sha256"]) == {
        "occupancy.json",
        "occupancy.npz",
        "scenario.json",
        "scene-input.json",
        "result.json",
        "route.png",
    }
    assert (
        manifest["geometry_sha256"]
        == saved.json()["base"]["assets"]["collision_mesh.npz"]["sha256"]
    )
    (root / "route.png").write_bytes(b"tamper")
    assert api.get(base + "/assets/route.png").status_code == 400
