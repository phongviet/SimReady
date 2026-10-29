import hashlib
import io
import json
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from simready.api.app import create_app
from simready.scene.demo import seed_demo
from tests.auth_helpers import authorized_client


def setup(tmp_path):
    app = create_app(tmp_path / "studio")
    seed_demo(app.state.store)
    builder, reviewer = authorized_client(app), authorized_client(app, "reviewer")
    config = json.loads(Path("configs/scenario_analytic.json").read_text())
    saved = builder.put(
        "/api/v1/scenes/analytic-demo/scenarios",
        json={"expected_version": 1, "scenarios": [config]},
    )
    assert saved.status_code == 200, saved.text
    run = builder.post(
        "/api/v1/scenes/analytic-demo/scenarios/run",
        json={"expected_version": 2, "scenario_id": config["scenario_id"]},
    )
    assert run.status_code == 201, run.text
    return app, builder, reviewer, run.json()


def submission(run, expected="goal_reached"):
    return {
        "expected_version": run["scene_version"],
        "report_run_id": "bundled-test-1",
        "simulation_run_id": run["run_id"],
        "scope": {
            "task": "occupancy_navigation_regression",
            "name": "Declared virtual floor route regression",
            "camera_ids": ["frame_00006", "frame_00007"],
            "bounds_xz_m": run["scenario"]["bounds_xz_m"],
            "expected_navigation": expected,
            "limitations_acknowledged": True,
        },
    }


def decision(version, choice="approve"):
    return {
        "expected_version": version,
        "decision": choice,
        "reason": (
            "Automated local acceptance fixture: scope is deterministic virtual-floor "
            "replay only, no safety or accuracy endorsement."
        ),
    }


def test_permissions_scoped_approval_export_and_edit_invalidation(tmp_path):
    app, builder, reviewer, run = setup(tmp_path)
    base = "/api/v1/scenes/analytic-demo"
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/auth/me").status_code == 401
    assert (
        anonymous.put(
            base + "/objects",
            json={"expected_version": 2, "objects": []},
            headers={"X-Role": "builder"},
        ).status_code
        == 401
    )
    assert (
        reviewer.put(base + "/objects", json={"expected_version": 2, "objects": []}).status_code
        == 403
    )
    assert reviewer.post(base + "/submit", json=submission(run)).status_code == 403
    assert builder.post(base + "/export", json={"version": 2}).status_code == 400
    qa = builder.get(base + "/readiness").json()
    assert qa["outcome"] == "needs_review" and qa["simulation"]["scene_version"] == 2
    assert qa["evaluation"]["scene_version"] == 1  # Honest reuse of unchanged base-only metrics.
    assert qa["coverage"]["tested_reference_views"] == 2
    submitted = builder.post(base + "/submit", json=submission(run))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert (
        builder.post(base + "/review", json=decision(3), headers={"X-Role": "reviewer"}).status_code
        == 403
    )
    assert reviewer.post(base + "/review", json=decision(2)).status_code == 409
    approved = reviewer.post(base + "/review", json=decision(3))
    assert approved.status_code == 200, approved.text
    state = approved.json()
    assert state["status"] == "approved" and state["version"] == 4
    assert state["review"]["source_version"] == 2
    assert builder.get(base + "/readiness").json()["outcome"] == "usable_for_declared_test"
    exported = reviewer.post(base + "/export", json={"version": 4})
    assert exported.status_code == 201, exported.text
    body = builder.get(base + "/exports/" + exported.json()["export_id"]).content
    assert hashlib.sha256(body).hexdigest() == exported.json()["sha256"]
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert {
            "render/gaussian.ply",
            "collision/collision_mesh.npz",
            "review/scope.json",
            "evaluation/report.html",
            "simulation/result.json",
        }.issubset(names)
        assert not any("credential" in name or "sqlite" in name for name in names)
        assert set(manifest["files_sha256"]) == names - {"manifest.json"}
        for name in names:
            assert builder.headers["authorization"].removeprefix(
                "Bearer "
            ).encode() not in archive.read(name)
            assert reviewer.headers["authorization"].removeprefix(
                "Bearer "
            ).encode() not in archive.read(name)
        for name, digest in manifest["files_sha256"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        scope = json.loads(archive.read("review/scope.json"))
        assert (
            hashlib.sha256(archive.read("review/readiness.json")).hexdigest()
            == scope["readiness_sha256"]
        )
        assert scope["scope"]["camera_ids"] == ["frame_00006", "frame_00007"]
    changed = builder.put(base + "/objects", json={"expected_version": 4, "objects": []}).json()
    assert changed["status"] == "draft" and "review" not in changed
    assert builder.get(base + "/versions/4").json()["status"] == "approved"
    assert builder.post(base + "/export", json={"version": 5}).status_code == 400
    assert builder.post(base + "/export", json={"version": 4}).status_code == 201
    events = builder.get(base + "/audit").json()
    assert [event["action"] for event in events] == ["submitted", "approve"]
    assert events[1]["previous_sha256"] == events[0]["sha256"]
    with app.state.store.connect() as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM review_audit")


def test_self_approval_after_role_change_and_rejection(tmp_path):
    app, builder, reviewer, run = setup(tmp_path)
    base = "/api/v1/scenes/analytic-demo"
    assert builder.post(base + "/submit", json=submission(run)).status_code == 200
    user_id = builder.get("/api/v1/auth/me").json()["user_id"]
    with app.state.store.connect() as db:
        db.execute("UPDATE accounts SET role='reviewer' WHERE user_id=?", (user_id,))
    response = builder.post(base + "/review", json=decision(3))
    assert response.status_code == 403 and "self-approval" in response.json()["error"]["message"]
    rejected = reviewer.post(base + "/review", json=decision(3, "reject"))
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert reviewer.post(base + "/export", json={"version": 4}).status_code == 400


def test_scope_mismatch_tamper_and_concurrent_review_only_one_wins(tmp_path):
    app, builder, reviewer, run = setup(tmp_path)
    base = "/api/v1/scenes/analytic-demo"
    for patch in ({"camera_ids": ["unverified-free-view"]}, {"bounds_xz_m": [-10, -10, 10, 10]}):
        value = submission(run)
        value["scope"].update(patch)
        assert builder.post(base + "/submit", json=value).status_code == 400
    value = submission(run)
    value["role"] = "reviewer"
    assert builder.post(base + "/submit", json=value).status_code == 422
    assert builder.post(base + "/submit", json=submission(run)).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: reviewer.post(base + "/review", json=decision(3)).status_code, range(2)
            )
        )
    assert sorted(results) == [200, 409]
    assert len(app.state.workflow.records("analytic-demo")) == 2


def test_wrong_expected_outcome_blocks_approval_but_allows_reject(tmp_path):
    app, builder, reviewer, run = setup(tmp_path)
    base = "/api/v1/scenes/analytic-demo"
    assert builder.post(base + "/submit", json=submission(run, "no_route")).status_code == 200
    assert reviewer.post(base + "/review", json=decision(3)).status_code == 400
    assert reviewer.post(base + "/review", json=decision(3, "reject")).status_code == 200


def test_tampered_capture_cannot_be_approved_and_can_still_be_rejected(tmp_path):
    app, builder, reviewer, run = setup(tmp_path)
    base = "/api/v1/scenes/analytic-demo"
    state = builder.post(base + "/submit", json=submission(run)).json()
    capture = (
        app.state.store.package("analytic-demo")
        / "reviews"
        / state["review"]["review_id"]
        / "readiness.json"
    )
    capture.write_text("{}")
    denied = reviewer.post(base + "/review", json=decision(3))
    assert denied.status_code == 400 and "content changed" in denied.json()["error"]["message"]
    assert reviewer.post(base + "/review", json=decision(3, "reject")).status_code == 200
