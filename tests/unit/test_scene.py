from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from simready.geometry.collision import mesh_intersects_box
from simready.scene.demo import seed_demo
from simready.scene.models import ObjectUpdate, ProxyObject, object_corners, object_matrix
from simready.scene.store import SceneStore, VersionConflict


def box(**changes):
    return ProxyObject(object_id="box1", name="Known box", position=(0, 0, -2), **changes)


def test_metric_box_transform_and_rotation():
    rotation = (0, np.sqrt(0.5), 0, np.sqrt(0.5))
    value = box(scale=(2, 1, 0.5), quaternion_xyzw=rotation)
    corners = object_corners(value)
    np.testing.assert_allclose(corners.max(axis=0) - corners.min(axis=0), [0.5, 1, 2], atol=1e-12)
    np.testing.assert_allclose(object_matrix(value)[:3, 3], [0, 0, -2])


@pytest.mark.parametrize(
    "change",
    [
        {"quaternion_xyzw": (0, 0, 0, 0)},
        {"scale": (0, 1, 1)},
        {"scale": (-1, 1, 1)},
        {"position": (float("nan"), 0, 0)},
        {"kind": "remove_base_object"},
        {"color": "url(secret)"},
    ],
)
def test_invalid_objects_rejected(change):
    data = box().model_dump() | change
    with pytest.raises(ValidationError):
        ProxyObject(**data)


def test_surface_intersection_is_metric_and_handles_rotated_box():
    vertices = np.array([[-2, -2, -2], [2, -2, -2], [2, 2, -2], [-2, 2, -2]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    assert mesh_intersects_box(vertices, faces, box())
    far = box().model_copy(update={"position": (0, 0, 0)})
    assert not mesh_intersects_box(vertices, faces, far)
    rotated = box(quaternion_xyzw=(0, 0, np.sqrt(0.5), np.sqrt(0.5)))
    assert mesh_intersects_box(vertices, faces, rotated)
    assert not mesh_intersects_box(vertices, faces, box(collidable=False))


def test_save_reload_history_deletion_and_immutable_assets(tmp_path: Path):
    store = SceneStore(tmp_path / "studio")
    original = seed_demo(store)
    asset_before = store.asset("analytic-demo", "gaussian.ply").read_bytes()
    updated = store.update_objects(
        "analytic-demo", ObjectUpdate(expected_version=1, objects=(box(),))
    )
    assert updated["version"] == 2
    reloaded = SceneStore(store.root).get("analytic-demo")
    assert reloaded["objects"][0]["position"] == [0, 0, -2]
    assert reloaded["objects"][0]["scale"] == [0.5, 0.5, 0.5]
    assert store.get("analytic-demo", 1)["objects"] == original["objects"] == []
    deleted = store.update_objects("analytic-demo", ObjectUpdate(expected_version=2, objects=()))
    assert deleted["version"] == 3 and deleted["objects"] == []
    assert len(store.history("analytic-demo")) == 3
    assert store.asset("analytic-demo", "gaussian.ply").read_bytes() == asset_before
    assert (store.package("analytic-demo") / "scene.json").is_file()


def test_concurrent_expected_version_has_one_winner(tmp_path):
    store = SceneStore(tmp_path / "studio")
    seed_demo(store)

    def save():
        try:
            return store.update_objects(
                "analytic-demo", ObjectUpdate(expected_version=1, objects=(box(),))
            )["version"]
        except VersionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: save(), range(2)))
    assert outcomes.count(2) == outcomes.count("conflict") == 1
    assert len(store.history("analytic-demo")) == 2


def test_duplicate_object_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        ObjectUpdate(expected_version=1, objects=(box(), box()))


def test_scene_path_and_unregistered_assets_are_rejected(tmp_path):
    store = SceneStore(tmp_path / "studio")
    seed_demo(store)
    with pytest.raises(ValidationError):
        store.get("../secret")
    with pytest.raises(KeyError):
        store.asset("analytic-demo", "../../../etc/passwd")


def test_registered_asset_tampering_is_detected(tmp_path):
    store = SceneStore(tmp_path / "studio")
    seed_demo(store)
    path = store.asset("analytic-demo", "gaussian.ply")
    path.chmod(0o644)
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        store.asset("analytic-demo", "gaussian.ply")


def test_bundled_tsdf_surface_matches_known_plane(tmp_path):
    store = SceneStore(tmp_path / "studio")
    scene = seed_demo(store)
    geometry = store.asset(scene["scene_id"], "collision_mesh.npz")
    with np.load(geometry, allow_pickle=False) as data:
        assert np.max(np.abs(data["vertices"][:, 2] + 2)) < 0.03
        assert mesh_intersects_box(data["vertices"], data["triangles"], box())
