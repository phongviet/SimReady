"""CPU verification of an actual measured, bundled analytic report, not invented scores."""

import csv
import io
import json
import shutil
from pathlib import Path

import pytest

from simready.api.app import create_app
from simready.data.dataset import sha256_file
from simready.evaluation.runner import validate_evaluation
from simready.scene.demo import seed_demo
from tests.auth_helpers import authorized_client

FIXTURE = Path(__file__).resolve().parents[2] / "src/simready/demo/analytic-plane/evaluation"


def test_measured_report_package_and_export_consistency(tmp_path):
    metadata = validate_evaluation(FIXTURE)
    assert metadata["git_dirty"] is False
    assert metadata["git_commit"].startswith("06114ba")
    assert metadata["source_files_sha256"]
    summary = json.loads((FIXTURE / "summary.json").read_text())
    views = json.loads((FIXTURE / "views.json").read_text())
    predictions = json.loads((FIXTURE / "predictions.json").read_text())
    assert len(views) == summary["view_count"] == 2
    assert summary["dataset_kind"] == "synthetic" and summary["split"] == "test"
    assert summary["environment"]["weights_sha256"] == json.loads(
        Path("configs/perception-weights.json").read_text()
    )
    assert all(v["detection"]["empty_both"] for v in views)
    assert all(len(p["real"]) > 0 for p in predictions["views"])
    # Raw backend predictions include low confidence outputs that filtered overlays omit.
    assert summary["detection_totals"]["real_count"] == 0
    assert summary["means"]["lpips"] == pytest.approx(sum(v["metrics"]["lpips"] for v in views) / 2)
    rows = list(csv.DictReader(io.StringIO((FIXTURE / "per_view.csv").read_text())))
    assert [r["frame_id"] for r in rows] == [v["frame_id"] for v in views]
    assert float(rows[0]["lpips"]) == views[0]["metrics"]["lpips"]
    assert "not detection accuracy" in (FIXTURE / "report.md").read_text()
    modified = tmp_path / "tampered"
    shutil.copytree(FIXTURE, modified)
    (modified / "summary.json").write_text("{}")
    with pytest.raises(ValueError, match="content hash mismatch"):
        validate_evaluation(modified)


def test_report_api_assets_hashes_scene_binding_and_cpu_seed(tmp_path):
    app = create_app(tmp_path / "studio")
    state = seed_demo(app.state.store)
    api = authorized_client(app)
    reports = api.get("/api/v1/scenes/analytic-demo/reports").json()
    assert len(reports) == 1 and reports[0]["scene_version"] == state["version"]
    base = "/api/v1/scenes/analytic-demo/reports/bundled-test-1"
    assert api.get(base).json()["summary"]["view_count"] == 2
    assert api.get(base + "/assets/report.html").headers["content-type"].startswith("text/html")
    assert len(api.get(base + "/assets/views.json").json()) == 2
    for name in ("per_view.csv", "report.md", "predictions.json", "images/frame_00006-real.png"):
        assert api.get(base + "/assets/" + name).status_code == 200
    assert api.get(base + "/assets/studio.sqlite3").status_code == 404
    assert api.get(base + "/assets/%2E%2E%2Fsummary.json").status_code in (400, 404)
    assert api.get("/api/v1/scenes/analytic-demo/reports/missing").status_code == 404
    assert len(seed_demo(app.state.store)["objects"]) == 0  # Idempotent report seeding.
    wrong = tmp_path / "wrong"
    shutil.copytree(FIXTURE, wrong)
    metadata = json.loads((wrong / "evaluation.json").read_text())
    metadata["artifact_sha256"] = "0" * 64
    (wrong / "evaluation.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="different scene"):
        app.state.evaluations.register("analytic-demo", "wrong", wrong)
    registered = app.state.evaluations.report_root("analytic-demo", "bundled-test-1")
    path = registered / "views.json"
    path.chmod(0o644)
    path.write_text("[]")
    assert sha256_file(path) != validate_evaluation(FIXTURE)["files_sha256"]["views.json"]
    assert api.get(base + "/assets/views.json").status_code == 400
