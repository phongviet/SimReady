"""Study orchestration failures must not turn into new successful runs on resume."""

import json

import pytest

from simready.data.dataset import write_json
from simready.research.runner import StageCache


def test_stage_resume_revalidates_artifact_and_never_retrains_success(tmp_path):
    output = tmp_path / "model"
    calls = []

    def action():
        calls.append("trained")
        output.mkdir()
        write_json(output / "artifact.json", {"fixture": True})

    def validate(path):
        return json.loads((path / "artifact.json").read_text())

    cache = StageCache(tmp_path)
    cache.run("model", output, "artifact.json", {"seed": 1}, action, validate)
    StageCache(tmp_path).run("model", output, "artifact.json", {"seed": 1}, action, validate)
    assert calls == ["trained"]
    with pytest.raises(ValueError, match="inputs changed"):
        StageCache(tmp_path).run("model", output, "artifact.json", {"seed": 2}, action, validate)
    write_json(output / "artifact.json", {"changed": True})
    with pytest.raises(ValueError, match="manifest changed"):
        StageCache(tmp_path).run("model", output, "artifact.json", {"seed": 1}, action, validate)
    assert calls == ["trained"]
    assert (
        "manifest changed"
        in json.loads((tmp_path / "stages.json").read_text())["failures"][-1]["traceback"]
    )


def test_stage_failure_is_recorded_and_existing_recovery_has_no_invented_timing(tmp_path):
    def failed():
        raise ValueError("injected worker failure")

    output = tmp_path / "model"
    with pytest.raises(ValueError, match="injected"):
        StageCache(tmp_path).run("model", output, "artifact.json", {}, failed, lambda _: {})
    assert not output.exists()
    output.mkdir()
    write_json(output / "artifact.json", {"fixture": True})
    cache = StageCache(tmp_path)
    cache.run("model", output, "artifact.json", {}, failed, lambda _: {"fixture": True})
    assert cache.state["stages"]["model"]["wall_seconds"] is None
    assert cache.state["stages"]["model"]["recovered_existing_output"]
    assert len(cache.state["failures"]) == 1
