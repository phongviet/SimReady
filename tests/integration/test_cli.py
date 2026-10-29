import json
import subprocess
import sys


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "simready.cli", *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_fixture_validate_and_frozen_split(tmp_path):
    scene = tmp_path / "fixture"
    created = run("data", "synthetic", "--out", scene)
    assert created.returncode == 0, created.stderr
    result = json.loads(created.stdout)
    assert result["frames"] == 8
    validated = run("data", "validate", "--scene", scene)
    split = run("data", "split", "--scene", scene)
    assert validated.returncode == split.returncode == 0
    assert json.loads(validated.stdout)["split_sha256"] == result["split_sha256"]
    assert json.loads(split.stdout)["split_sha256"] == result["split_sha256"]
    duplicate = run("data", "synthetic", "--out", scene)
    assert duplicate.returncode == 2
    assert "already exists" in duplicate.stderr


def test_cli_missing_scene_is_actionable(tmp_path):
    failed = run("data", "validate", "--scene", tmp_path / "missing")
    assert failed.returncode == 2
    assert "missing file: manifest.json" in failed.stderr
    assert "Traceback" not in failed.stderr


def test_unknown_commands_are_rejected():
    help_result = run("--help")
    assert help_result.returncode == 0
    assert run("nonexistent-command").returncode == 2


def test_reconstruction_commands_are_discoverable():
    result = run("recon", "--help")
    assert result.returncode == 0
    assert "train" in result.stdout and "render" in result.stdout and "validate" in result.stdout


def test_cpu_smoke_loads_genuinely_trained_synthetic_fixture():
    result = run("recon", "smoke")
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["dataset_kind"] == "synthetic"
    assert record["gaussians"] > 0 and record["saved_views"] == 2
    assert record["gpu_used"] is False and record["runtime_rendering_performed"] is False
