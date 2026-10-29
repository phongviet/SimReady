"""Serve genuine measured snapshots with explicit raw-data omissions and path guards."""

import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from simready.api.app import create_app
from simready.research.store import StudyStore, validate_package
from simready.scene.demo import seed_demo
from simready.scene.store import SceneStore

FIXTURE = Path("src/simready/demo/tum-recapture-evidence")


def test_measured_snapshot_keeps_scope_and_does_not_fabricate_raw_assets(tmp_path):
    package = validate_package(FIXTURE)
    assert package["summary_snapshot"] is True
    assert "Values are unchanged" in package["text_serialization"]
    assert b"\r\n" not in (FIXTURE / "per_view.csv").read_bytes()
    with (FIXTURE / "per_view.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 216
    store = StudyStore(tmp_path)
    value = store.import_package("measured-1", FIXTURE)
    assert value["summary"]["run_count"] == 12
    assert value["summary"]["semantic_audit"]["verdict"] == "WARN"
    assert value["summary"]["paired_risk_minus_random"]["lpips"]["mean"] > 0
    assert value["summary"]["detection_accuracy"]["value"] is None
    assert len(store.list()) == 1
    (store.root / "in-progress.import-lock").mkdir()
    (store.root / ".in-progress-staging").mkdir()
    assert len(store.list()) == 1  # Pending atomic imports never appear as broken studies.
    with pytest.raises(KeyError):
        store.asset("measured-1", "predictions_real.jsonl")
    with pytest.raises(ValueError, match="already exists"):
        store.import_package("measured-1", FIXTURE)
    with pytest.raises(ValueError):
        store.directory("../escape")
    (store.directory("measured-1") / "per_view.csv").write_text("tampered")
    with pytest.raises(ValueError, match="content changed"):
        store.get("measured-1")


def test_http_research_serves_only_registered_verified_assets(tmp_path):
    seed_demo(SceneStore(tmp_path))
    client = TestClient(create_app(tmp_path))
    values = client.get("/api/v1/research/studies").json()
    assert len(values) == 1
    sid = values[0]["study_id"]
    response = client.get(f"/api/v1/research/studies/{sid}/assets/metrics_summary.json")
    assert response.status_code == 200
    assert response.json()["source"]["commit"].startswith("6947fb8")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    # Encoded traversal reaches the asset route instead of client-side URL normalization.
    blocked = client.get(f"/api/v1/research/studies/{sid}/assets/%2e%2e%2flocal-credentials.json")
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "not_found"
    assert client.get(f"/api/v1/research/studies/{sid}/assets/not-registered").status_code == 404
    directory = StudyStore(tmp_path).directory(sid)
    (directory / "private.txt").write_text("must not be served")
    assert client.get(f"/api/v1/research/studies/{sid}/assets/private.txt").status_code == 404
    expected = json.loads((FIXTURE / "metrics_summary.json").read_text())
    assert response.json()["paired_risk_minus_random"] == expected["paired_risk_minus_random"]
