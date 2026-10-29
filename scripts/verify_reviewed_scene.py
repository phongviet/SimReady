"""Automated local-role acceptance on real scene evidence; no human endorsement."""

import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from simready.api.app import create_app
from simready.data.dataset import atomic_dataset, sha256_file, write_json
from simready.storage import PROJECT_ROOT, check_budget


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scene", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("acceptance evidence directory already exists")
    app = create_app(args.root)
    state = app.state.store.get(args.scene)
    if state["status"] != "draft":
        raise ValueError("acceptance needs a draft; do not overwrite a prior review")
    credentials = json.loads(app.state.auth.bootstrap().read_text())
    builder = TestClient(
        app, headers={"Authorization": "Bearer " + credentials["builder"]["token"]}
    )
    reviewer = TestClient(
        app, headers={"Authorization": "Bearer " + credentials["reviewer"]["token"]}
    )
    report_id = "baseline-test-1"
    if not any(r["run_id"] == report_id for r in app.state.evaluations.reports(args.scene)):
        app.state.evaluations.register(args.scene, report_id, args.report)
    runs = [
        r for r in app.state.simulations.runs(args.scene) if r["scene_version"] == state["version"]
    ]
    if not runs:
        raise ValueError("run a saved scenario for the current revision before acceptance")
    run = runs[-1]
    base = f"/api/v1/scenes/{args.scene}"
    qa_before = builder.get(base + "/readiness").json()
    scope = {
        "task": "occupancy_navigation_regression",
        "name": "TUM known-map obstruction rejection regression",
        "camera_ids": [v["frame_id"] for v in qa_before["coverage"]["views"]],
        "bounds_xz_m": run["scenario"]["bounds_xz_m"],
        "expected_navigation": "goal_reached"
        if run["result_summary"]["route_success"]
        else "no_route",
        "limitations_acknowledged": True,
    }
    submitted = builder.post(
        base + "/submit",
        json={
            "expected_version": state["version"],
            "report_run_id": report_id,
            "simulation_run_id": run["run_id"],
            "scope": scope,
        },
    )
    if submitted.status_code != 200:
        raise ValueError(submitted.text)
    request = {
        "expected_version": submitted.json()["version"],
        "decision": "approve",
        "reason": (
            "Automated acceptance fixture only: approve the declared known-map obstruction "
            "regression and listed measured cameras. Perception failure and unknown space remain "
            "explicit; no human, safety or detection-accuracy endorsement."
        ),
    }
    denied = builder.post(base + "/review", json=request, headers={"X-Role": "reviewer"})
    anonymous = TestClient(app).post(base + "/review", json=request)
    assert denied.status_code == 403 and anonymous.status_code == 401
    approved = reviewer.post(base + "/review", json=request)
    if approved.status_code != 200:
        raise ValueError(approved.text)
    approved_state = approved.json()
    qa_approved = reviewer.get(base + "/readiness").json()
    exported = reviewer.post(base + "/export", json={"version": approved_state["version"]})
    if exported.status_code != 201:
        raise ValueError(exported.text)
    registration = exported.json()
    response = reviewer.get(base + "/exports/" + registration["export_id"])
    data = response.content
    assert hashlib.sha256(data).hexdigest() == registration["sha256"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert set(manifest["files_sha256"]) == set(archive.namelist()) - {"manifest.json"}
        for name, digest in manifest["files_sha256"].items():
            payload = archive.read(name)
            assert hashlib.sha256(payload).hexdigest() == digest
            assert all(
                credentials[role]["token"].encode() not in payload
                for role in ("builder", "reviewer")
            )
        assert archive.read("render/gaussian.ply").startswith(b"ply\n")
        assert "collision/collision_mesh.npz" in archive.namelist()
    audit = app.state.workflow.records(args.scene)
    assert (
        qa_before["outcome"] == "needs_review"
        and qa_approved["outcome"] == "usable_for_declared_test"
    )
    with atomic_dataset(args.out, 100_000_000) as stage:
        write_json(stage / "qa-before.json", qa_before)
        write_json(stage / "qa-approved.json", qa_approved)
        write_json(stage / "audit.json", audit)
        write_json(stage / "export-manifest.json", manifest)
        (stage / "reviewed-scene.zip").write_bytes(data)
        evidence = {
            "schema_version": "1.0",
            "mode": "automated local-account acceptance; not human approval",
            "scene_id": args.scene,
            "source_version": state["version"],
            "approved_version": approved_state["version"],
            "builder_role_spoof_status": denied.status_code,
            "anonymous_review_status": anonymous.status_code,
            "export": registration,
            "scope": scope,
            "actual_source_kind": state["base"]["dataset_kind"],
            "git_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
            ).strip(),
            "git_dirty": bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True
                )
            ),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "files_sha256": {p.name: sha256_file(p) for p in stage.iterdir() if p.is_file()},
        }
        write_json(stage / "evidence.json", evidence)
    check_budget()
    print(
        json.dumps(
            {
                "evidence": str(args.out),
                "source_version": state["version"],
                "approved_version": approved_state["version"],
                "export_sha256": registration["sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
