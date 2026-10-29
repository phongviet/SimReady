import os

import pytest

from simready.storage import project_bytes


def test_sparse_hardlinks_and_both_symlink_types_are_counted_without_traversal(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    child = root / "subdir"
    child.mkdir()
    sparse = child / "sparse.dat"
    with sparse.open("wb") as file:
        file.truncate(1_000_000)
    hardlink = root / "hardlink.dat"
    os.link(sparse, hardlink)
    outside = tmp_path / "external"
    outside.mkdir()
    external_file = outside / "large-sparse.dat"
    with external_file.open("wb") as file:
        file.truncate(100_000_000)
    directory_link = root / "external-dir"
    directory_link.symlink_to(outside, target_is_directory=True)
    file_link = root / "external-file"
    file_link.symlink_to(external_file)
    loop = child / "cycle"
    loop.symlink_to(root, target_is_directory=True)
    expected = sum(path.lstat().st_blocks * 512 for path in (root, child))
    for path in (sparse, hardlink, directory_link, file_link, loop):
        metadata = path.lstat()
        expected += max(metadata.st_size, metadata.st_blocks * 512)
    assert project_bytes(root) == expected
    assert 2_000_000 <= expected < 3_000_000


def test_disappearing_cache_directory_triggers_complete_recount(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "temporary").write_bytes(b"x" * 5000)
    stable = tmp_path / "stable"
    stable.write_bytes(b"x" * 12000)
    original = os.scandir
    removed = False
    root_scans = 0

    def concurrent_cleanup(path):
        nonlocal removed, root_scans
        if os.fspath(path) == os.fspath(tmp_path):
            root_scans += 1
        if os.fspath(path) == os.fspath(cache) and not removed:
            removed = True
            (cache / "temporary").unlink()
            cache.rmdir()
        return original(path)

    monkeypatch.setattr(os, "scandir", concurrent_cleanup)
    measured = project_bytes(tmp_path)
    assert removed and root_scans == 2
    assert measured == project_bytes(tmp_path)
    assert measured >= stable.stat().st_size


def test_continuously_changing_scan_fails_closed(tmp_path, monkeypatch):
    def disappearing(_):
        raise FileNotFoundError("injected concurrent removal")

    monkeypatch.setattr(os, "scandir", disappearing)
    with pytest.raises(ValueError, match="changed repeatedly"):
        project_bytes(tmp_path)
