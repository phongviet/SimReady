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


def test_future_commands_are_not_advertised():
    help_result = run("--help")
    assert help_result.returncode == 0
    assert "recon" not in help_result.stdout
    assert run("recon", "train").returncode == 2
