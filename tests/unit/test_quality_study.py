import json

import pytest

from simready.reconstruction.contracts import QualityTrainingConfig, ReconstructionConfig
from simready.research.quality import configurations, select_validation, stage
from simready.storage import PROJECT_ROOT


def base():
    return json.loads((PROJECT_ROOT / "configs/recon_local_6gb.json").read_text())


def test_legacy_serialization_unchanged():
    assert ReconstructionConfig(**base()).model_dump(mode="json") == base()


def test_matrix_and_limits():
    runs = dict(configurations())
    assert len(runs) == 24
    assert sum(c.iterations for c in runs.values()) == 79200
    assert sum(len(c.checkpoint_steps) or 1 for c in runs.values()) + 1 == 67
    assert runs["control-s42"].refine_stop == runs["baseline-s42"].refine_stop == 900
    for changes in (
        {"checkpoint_steps": [2400, 1200]},
        {"checkpoint_steps": [0]},
        {"checkpoint_steps": [True]},
        {"memory_limit_bytes": 4_500_000_001},
        {"depth_supervision": "none"},
        {"photometric_loss": "invented"},
    ):
        with pytest.raises(ValueError):
            QualityTrainingConfig(**(base() | changes))


def test_selection_only_complete_validation():
    a = dict(
        arm="a",
        split="validation",
        split_sha256="frozen",
        view_count=16,
        lpips=0.2,
        psnr_db=20.0,
        step=1200,
    )
    b = a | dict(arm="b", lpips=0.2000005, psnr_db=21.0)
    assert select_validation([a, b], "frozen", 16) == b
    for bad in (
        {"split": "test"},
        {"split": "candidate"},
        {"split_sha256": "different"},
        {"view_count": 15},
        {"lpips": float("nan")},
        {"psnr_db": None},
    ):
        with pytest.raises(ValueError):
            select_validation([a | bad], "frozen", 16)
    with pytest.raises(ValueError):
        select_validation([], "frozen", 16)


def test_failed_stage_is_visible_and_cannot_retry(tmp_path, monkeypatch):
    monkeypatch.setattr("simready.research.quality.check_budget", lambda *_: 0)

    def fail():
        raise RuntimeError("actual failure")

    with pytest.raises(RuntimeError):
        stage(tmp_path, "loss", "hash", fail, lambda: None)
    record = json.loads((tmp_path / "ledger/loss.json").read_text())
    assert record["status"] == "failed" and "actual failure" in record["error"]
    with pytest.raises(ValueError, match="new study ID"):
        stage(tmp_path, "loss", "hash", lambda: None, lambda: None)


def test_success_resume_revalidates(tmp_path, monkeypatch):
    monkeypatch.setattr("simready.research.quality.check_budget", lambda *_: 0)
    calls = []
    stage(tmp_path, "ok", "hash", lambda: calls.append("run"), lambda: calls.append("verify"))
    stage(tmp_path, "ok", "hash", lambda: calls.append("run"), lambda: calls.append("verify"))
    assert calls == ["run", "verify", "verify"]


def test_nonvalidation_report_rejected_before_metrics(tmp_path):
    from simready.research.quality import verify_validation

    (tmp_path / "renders.json").write_text('{"split":"test"}')
    with pytest.raises(ValueError, match="validation evaluation only"):
        verify_validation(tmp_path / "missing-metrics", None, None, tmp_path, None)


def test_quality_preparation_never_reads_heldout_pixels(scene, tmp_path, monkeypatch):
    from PIL import Image

    from simready.reconstruction.gsplat import prepare_training

    splits = json.loads((scene / "splits.json").read_text())
    records = [json.loads(line) for line in (scene / "frames.jsonl").read_text().splitlines()]
    forbidden = {
        str(scene / f[key])
        for f in records
        if f["frame_id"] not in splits["train"]
        for key in ("rgb_path", "depth_path")
    }
    original = Image.open

    def guarded(path, *args, **kwargs):
        assert str(path) not in forbidden, "held-out pixel read during training"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Image, "open", guarded)
    output = tmp_path / "training"
    output.mkdir()
    config = QualityTrainingConfig(**base())
    provenance = prepare_training(scene, config, output)
    assert provenance["training_frame_ids"] == splits["train"]


def test_execution_seal_detects_source_protocol_history_changes(scene, tmp_path, monkeypatch):
    """Unit-only metadata fixture; no model training or experimental measurements."""
    import simready.research.quality as q

    project = tmp_path / "project"
    (project / "configs").mkdir(parents=True)
    (project / "configs/recon_local_6gb.json").write_text(json.dumps(base()))
    spec = project / "refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("unit fixture specification")
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "artifact.json").write_text("{}")
    reference_config = base()
    monkeypatch.setattr(q, "PROJECT_ROOT", project)
    monkeypatch.setattr(q, "check_budget", lambda *_: 0)
    monkeypatch.setattr(q, "source_pins", lambda: {"worker": "frozen-source"})
    monkeypatch.setattr(q, "historical_pins", lambda: {"old-artifact": "frozen-history"})
    monkeypatch.setattr(
        q,
        "validate_artifact",
        lambda _: {"config": reference_config, "worker": {"iterations": 1200}},
    )
    monkeypatch.setattr(
        q.subprocess, "check_output", lambda args, **kw: "" if "status" in args else "f" * 40
    )
    study = tmp_path / "new-study"
    q.freeze(study, scene, reference)
    assert len(q.verify_protocol(study)["runs"]) == 24
    with pytest.raises(ValueError, match="already exists"):
        q.freeze(study, scene, reference)
    monkeypatch.setattr(q, "source_pins", lambda: {"worker": "changed"})
    with pytest.raises(ValueError, match="source changed"):
        q.verify_protocol(study)
    monkeypatch.setattr(q, "source_pins", lambda: {"worker": "frozen-source"})
    monkeypatch.setattr(q, "historical_pins", lambda: {"old-artifact": "changed"})
    with pytest.raises(ValueError, match="historical artifacts changed"):
        q.verify_protocol(study)
    monkeypatch.setattr(q, "historical_pins", lambda: {"old-artifact": "frozen-history"})
    spec.write_text("changed")
    with pytest.raises(ValueError, match="specification changed"):
        q.verify_protocol(study)
    spec.write_text("unit fixture specification")
    (study / "protocol.json").write_text("{}")
    with pytest.raises(ValueError, match="protocol changed"):
        q.verify_protocol(study)
