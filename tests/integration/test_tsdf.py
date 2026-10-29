import importlib.util

import numpy as np
import pytest

from simready.geometry.collision import mesh_intersects_box
from simready.geometry.tsdf import build_tsdf, validate_geometry
from simready.scene.models import ProxyObject


@pytest.mark.geometry
def test_actual_tsdf_uses_train_only_and_preserves_metric_plane(scene, tmp_path):
    if importlib.util.find_spec("open3d") is None:
        pytest.skip("install the optional geometry extra to run actual CPU TSDF fusion")
    output = build_tsdf(scene, tmp_path / "geometry")
    metadata = validate_geometry(output)
    assert metadata["quality"] == "coarse_proxy"
    assert metadata["training_frame_ids"] == [f"frame_{i:05d}" for i in range(4)]
    assert metadata["ground_truth_metrics"] is None
    with np.load(output / "collision_mesh.npz", allow_pickle=False) as arrays:
        assert np.max(np.abs(arrays["vertices"][:, 2] + 2)) < metadata["voxel_size_m"]
        known = ProxyObject(
            object_id="known", name="Known metric box", position=(0, 0, -2), scale=(0.2, 0.4, 0.3)
        )
        assert mesh_intersects_box(arrays["vertices"], arrays["triangles"], known)
