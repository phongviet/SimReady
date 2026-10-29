import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from simready.data.dataset import block_splits, sha256_file, validate_scene
from simready.data.schema import DatasetManifest, Frame, ScenePackage, Splits
from simready.data.synthetic import make_synthetic


def edit_json(path: Path, edit):
    data = json.loads(path.read_text())
    edit(data)
    path.chmod(0o644)
    path.write_text(json.dumps(data))


def edit_frames(scene: Path, edit):
    path = scene / "frames.jsonl"
    frames = [json.loads(line) for line in path.read_text().splitlines()]
    edit(frames)
    path.chmod(0o644)
    path.write_text("".join(json.dumps(frame) + "\n" for frame in frames))
    frames_hash = sha256_file(path)
    edit_json(scene / "splits.json", lambda s: s.update(frames_sha256=frames_hash))
    edit_json(
        scene / "manifest.json",
        lambda m: m.update(
            frames_sha256=frames_hash, split_sha256=sha256_file(scene / "splits.json")
        ),
    )


def test_fixture_is_valid_reproducible_and_has_metric_mesh(scene, tmp_path):
    result = validate_scene(scene)
    assert result["kind"] == "synthetic"
    assert result["frames"] == 8
    assert result["splits"] == {"train": 4, "validation": 1, "candidate": 1, "test": 2}
    assert result["valid_depth_pixels"] == 8 * 64 * 48
    assert "v 2 2 -2" in (scene / "ground_truth.obj").read_text()
    other = tmp_path / "other"
    make_synthetic(other)
    assert validate_scene(other)["frames_sha256"] == result["frames_sha256"]
    assert validate_scene(other)["split_sha256"] == result["split_sha256"]


def test_refuses_overwrite(scene):
    before = sha256_file(scene / "manifest.json")
    with pytest.raises(ValueError, match="already exists"):
        make_synthetic(scene)
    assert sha256_file(scene / "manifest.json") == before


def test_four_frame_minimum_and_smaller_dataset_rejection(scene):
    frames = [
        Frame.model_validate_json(line)
        for line in (scene / "frames.jsonl").read_text().splitlines()
    ]
    split = block_splits(frames[:4], "0" * 64)
    assert all(
        len(getattr(split, group)) == 1 for group in ("train", "validation", "candidate", "test")
    )
    with pytest.raises(ValueError, match="at least four"):
        block_splits(frames[:3], "0" * 64)


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "2.0"},
        {"world_units": "mm"},
        {"world_frame": "z_up"},
        {"unexpected": 1},
        {"depth": {"meters_per_unit": 0, "invalid_value": 0}},
        {"source": {}},
        {"cameras": {}},
    ],
)
def test_bad_manifest_rejected(scene, change):
    data = json.loads((scene / "manifest.json").read_text())
    with pytest.raises(ValidationError):
        DatasetManifest(**(data | change))


@pytest.mark.parametrize(
    "field", ["schema_version", "world_units", "world_frame", "camera_axes", "pose_provenance"]
)
def test_missing_required_manifest_field(scene, field):
    data = json.loads((scene / "manifest.json").read_text())
    del data[field]
    with pytest.raises(ValidationError):
        DatasetManifest(**data)


def test_legacy_redwood_real_classification_is_rejected(scene):
    def wrong_source(manifest):
        manifest["kind"] = "real"
        manifest["source"]["name"] = "Open3D SampleRedwoodRGBDImages"

    edit_json(scene / "manifest.json", wrong_source)
    with pytest.raises(ValueError, match="misclassified as real"):
        validate_scene(scene)


def test_split_overlap_and_duplicate_rejected(scene):
    data = json.loads((scene / "splits.json").read_text())
    data["test"] = data["train"]
    with pytest.raises(ValidationError, match="overlap"):
        Splits(**data)


@pytest.mark.parametrize("target", ["splits.json", "frames.jsonl"])
def test_frozen_files_detect_edits_even_whitespace(scene, target):
    path = scene / target
    path.chmod(0o644)
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_scene(scene)


def test_split_coverage_not_just_disjointness(scene):
    edit_json(scene / "splits.json", lambda s: s.update(test=["missing_frame"]))
    edit_json(
        scene / "manifest.json", lambda m: m.update(split_sha256=sha256_file(scene / "splits.json"))
    )
    with pytest.raises(ValueError, match="cover exactly"):
        validate_scene(scene)


@pytest.mark.parametrize(
    "mode, message",
    [
        ("missing", "missing file"),
        ("corrupt", "unreadable image"),
        ("size", "dimensions"),
        ("color", "RGB channels"),
        ("content", "content hash mismatch"),
    ],
)
def test_bad_rgb_files(scene, mode, message):
    path = scene / "rgb/00000.png"
    if mode == "missing":
        path.unlink()
    elif mode == "corrupt":
        path.write_bytes(b"not an image")
    elif mode == "size":
        Image.new("RGB", (20, 30)).save(path)
    elif mode == "color":
        Image.new("L", (64, 48)).save(path)
    else:
        Image.new("RGB", (64, 48), color=(1, 2, 3)).save(path)
    with pytest.raises(ValueError, match=message):
        validate_scene(scene)


def test_depth_cannot_be_8bit(scene):
    Image.fromarray(np.ones((48, 64), dtype=np.uint8)).save(scene / "depth/00000.png")
    with pytest.raises(ValueError, match="uint16"):
        validate_scene(scene)


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda fs: fs[1].update(timestamp=0), "strictly increasing"),
        (lambda fs: fs[0].update(depth_timestamp=0.1), "timestamp mismatch"),
        (lambda fs: fs[0].update(camera_id="missing"), "unknown camera"),
        (lambda fs: fs[0].update(frame_id=fs[1]["frame_id"]), "duplicate frame IDs"),
        (lambda fs: fs[1].update(rgb_sha256=fs[0]["rgb_sha256"]), "duplicate RGB"),
    ],
)
def test_invalid_frame_relationships(scene, edit, message):
    edit_frames(scene, edit)
    with pytest.raises(ValueError, match=message):
        validate_scene(scene)


@pytest.mark.parametrize("path", ["../secret.png", "/tmp/secret.png", "C:/secret.png", r"..\x.png"])
def test_traversal_rejected_in_contract(scene, path):
    frame = json.loads((scene / "frames.jsonl").read_text().splitlines()[0])
    with pytest.raises(ValidationError, match="scene-relative"):
        Frame(**(frame | {"rgb_path": path}))


def test_symlink_escape_rejected(scene, tmp_path):
    path = scene / "rgb/00000.png"
    external = tmp_path / "external.png"
    path.rename(external)
    path.symlink_to(external)
    with pytest.raises(ValueError, match="escapes scene"):
        validate_scene(scene)


def test_scene_package_is_a_draft_contract_only():
    scene = ScenePackage(
        schema_version="1.0",
        scene_id="example",
        version=1,
        dataset_manifest="dataset/manifest.json",
    )
    assert scene.render_asset is None and scene.collision_asset is None
    for change in (
        {"status": "approved"},
        {"render_asset": "../model.ply"},
        {"schema_version": "9.0"},
    ):
        with pytest.raises(ValidationError):
            ScenePackage(**(scene.model_dump() | change))
