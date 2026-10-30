import json
import subprocess

import pytest

from simready.research.history import source_at


def test_historical_source_resolves_when_old_commit_is_absent(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "fixture"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "fixture@example.test"], check=True
    )
    (tmp_path / "source.txt").write_bytes(b"immutable source\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "source.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "fixture"], check=True)
    current = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    old = "1" * 40
    assert (
        subprocess.run(
            ["git", "-C", str(tmp_path), "cat-file", "-e", old], capture_output=True
        ).returncode
        != 0
    )
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/git-author-map.json").write_text(json.dumps({"commits": {old: current}}))
    assert source_at(old, "source.txt", tmp_path) == b"immutable source\n"
    assert source_at(current, "source.txt", tmp_path) == b"immutable source\n"


def test_invalid_alias_target_rejected_before_git(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/git-author-map.json").write_text(
        json.dumps({"commits": {"1" * 40: "--help"}})
    )
    with pytest.raises(ValueError, match="invalid historical"):
        source_at("1" * 40, "source.txt", tmp_path)
