import io
import stat
import zipfile
from pathlib import Path

import pytest

from simready.data import redwood
from simready.data.dataset import atomic_dataset
from simready.data.redwood import fetch_sample, read_log, safe_extract
from simready.storage import check_budget, project_bytes


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/windows", r"..\escape"])
def test_archive_paths_cannot_escape(tmp_path, name):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(name, b"data")
    destination = tmp_path / "extract"
    destination.mkdir()
    with pytest.raises(ValueError):
        safe_extract(archive, destination)
    assert list(destination.iterdir()) == []


def test_archive_symlinks_rejected(tmp_path):
    archive = tmp_path / "bad.zip"
    entry = zipfile.ZipInfo("link")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(entry, b"../outside")
    with pytest.raises(ValueError, match="symlinks"):
        safe_extract(archive, tmp_path / "extract")


def test_extraction_limit_checked_before_writing(tmp_path, monkeypatch):
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("large.txt", b"0" * 1000)
    monkeypatch.setattr(redwood, "MAX_EXTRACT_BYTES", 100)
    with pytest.raises(ValueError, match="extraction limit"):
        safe_extract(archive, tmp_path / "extract")
    assert not (tmp_path / "extract").exists()


def test_storage_includes_hidden_files_and_blocks(tmp_path):
    hidden = tmp_path / ".git"
    hidden.mkdir()
    (hidden / "object").write_bytes(b"a" * 128)
    used = project_bytes(tmp_path)
    assert used >= 128
    with pytest.raises(ValueError, match="storage budget"):
        check_budget(additional_bytes=1, root=tmp_path, limit=used + 1)
    assert check_budget(root=tmp_path, limit=used + 1) == used


def test_missing_storage_root_rejected(tmp_path):
    with pytest.raises(ValueError, match="not a directory"):
        check_budget(root=tmp_path / "missing")


def test_failed_import_rolls_back_staging_and_lock(tmp_path):
    destination = tmp_path / "scene"
    with pytest.raises(RuntimeError):
        with atomic_dataset(destination, 100) as stage:
            (stage / "partial").write_text("partial")
            raise RuntimeError("import failed")
    assert list(tmp_path.iterdir()) == []


def test_active_import_lock_blocks_concurrent_writer(tmp_path):
    destination = tmp_path / "scene"
    with atomic_dataset(destination, 100):
        with pytest.raises(ValueError, match="in progress"):
            with atomic_dataset(destination, 100):
                pytest.fail("concurrent import should not proceed")


@pytest.mark.parametrize(
    "declared, payload, expected",
    [
        ("1000000000", b"tiny", "download limit"),
        ("0", b"a" * 100, "download limit"),
        ("0", b"wrong archive", "SHA-256 mismatch"),
    ],
)
def test_download_limits_and_checksum_cleanup(tmp_path, monkeypatch, declared, payload, expected):
    class Response(io.BytesIO):
        headers = {"Content-Length": declared}

    monkeypatch.setattr(redwood.urllib.request, "urlopen", lambda *a, **kw: Response(payload))
    monkeypatch.setattr(redwood, "MAX_ARCHIVE_BYTES", 50)
    with pytest.raises(ValueError, match=expected):
        fetch_sample(tmp_path / "sample")
    assert not list(tmp_path.glob("*.part"))
    assert not (tmp_path / "sample").exists()
    assert not (tmp_path / "SampleRedwoodRGBDImages.zip").exists()


def test_existing_archive_is_verified_without_network(tmp_path, monkeypatch):
    archive = tmp_path / "SampleRedwoodRGBDImages.zip"
    archive.write_bytes(b"wrong archive")
    monkeypatch.setattr(
        redwood.urllib.request, "urlopen", lambda *a, **kw: pytest.fail("must not contact network")
    )
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch_sample(tmp_path / "sample")


@pytest.mark.parametrize("content", ["", "0 0 1\n1 0 0 0\n", "1 1 2\n" + "1 0 0 0\n" * 4])
def test_bad_pose_log_rejected(tmp_path: Path, content):
    log = tmp_path / "pose.log"
    log.write_text(content)
    with pytest.raises(ValueError):
        read_log(log)
