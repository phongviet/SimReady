"""Mock-format tests; these generated inputs are not real-capture evidence."""

import io
import tarfile

import numpy as np
import pytest
from PIL import Image

from simready.data.dataset import validate_scene
from simready.data.tum import import_tum


def add_bytes(bundle, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    bundle.addfile(info, io.BytesIO(payload))


def mock_archive(path, depth_offset=0):
    root = "rgbd_dataset_freiburg1_desk/"
    rgb_index, depth_index = [], []
    with tarfile.open(path, "w:gz") as bundle:
        for i in range(8):
            timestamp = 1.01 + i * 0.02
            rgb_name, depth_name = f"rgb/{i}.png", f"depth/{i}.png"
            rgb_index.append(f"{timestamp:.6f} {rgb_name}")
            depth_index.append(f"{timestamp + depth_offset:.6f} {depth_name}")
            color = io.BytesIO()
            Image.new("RGB", (640, 480), (i * 20, 50, 100)).save(color, format="PNG")
            depth = io.BytesIO()
            Image.fromarray(np.full((480, 640), 5000, dtype=np.uint16)).save(depth, format="PNG")
            add_bytes(bundle, root + rgb_name, color.getvalue())
            add_bytes(bundle, root + depth_name, depth.getvalue())
        truth = "\n".join(f"{1 + i * 0.02:.6f} {i * 0.01:.6f} 0 0 0 0 0 1" for i in range(10))
        for name, text in (
            ("rgb.txt", "\n".join(rgb_index)),
            ("depth.txt", "\n".join(depth_index)),
            ("groundtruth.txt", truth),
        ):
            add_bytes(bundle, root + name, text.encode())


def test_mock_tum_format_import_keeps_units_and_all_split_groups(tmp_path):
    archive = tmp_path / "mock.tgz"
    mock_archive(archive)
    output = tmp_path / "scene"
    import_tum(archive, output, max_frames=8)
    record = validate_scene(output)
    assert record["frames"] == 8
    assert record["splits"] == {"train": 4, "validation": 1, "candidate": 1, "test": 2}
    assert record["valid_depth_pixels"] == 8 * 640 * 480


def test_tum_mismatched_associations_do_not_invent_poses(tmp_path):
    archive = tmp_path / "mock.tgz"
    mock_archive(archive, depth_offset=1)
    with pytest.raises(ValueError, match="only 0 posed pairs"):
        import_tum(archive, tmp_path / "scene", max_frames=8)
    assert not (tmp_path / "scene").exists()


@pytest.mark.parametrize("name", ["../outside", "/absolute", "C:/outside"])
def test_tum_tar_traversal_is_rejected(tmp_path, name):
    archive = tmp_path / "malicious.tgz"
    with tarfile.open(archive, "w:gz") as bundle:
        add_bytes(bundle, name, b"data")
    with pytest.raises(ValueError, match="scene-relative"):
        import_tum(archive, tmp_path / "scene", max_frames=8)
    assert not (tmp_path / "scene").exists()
