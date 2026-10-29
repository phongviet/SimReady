import json

import numpy as np
from PIL import Image

from simready.data.bench import bench_boxes, look_at, make_bench, mask_box, ray_box
from simready.data.dataset import sha256_file, validate_scene
from simready.data.schema import rigid_matrix


def test_ray_box_distances_and_parallel_misses():
    rays = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])
    distances = ray_box(
        np.array([0.0, 0.0, 0.0]), rays, np.array([-1.0, -1.0, 2.0]), np.array([1.0, 1.0, 3.0])
    )
    assert distances[0] == 2 and np.isinf(distances[1:]).all()
    assert (
        ray_box(
            np.array([0.0, 0.0, 2.5]),
            rays[:1],
            np.array([-1.0, -1.0, 2.0]),
            np.array([1.0, 1.0, 3.0]),
        )[0]
        == 0.5
    )
    pose = look_at(np.array([0.0, 1.0, 3.0]), np.array([0.0, 0.5, 0.0]))
    rigid_matrix(pose)
    assert bench_boxes()[:, 0, 1].min() == 0


def test_authored_truth_masks_boxes_and_frozen_partitions(tmp_path):
    root = tmp_path / "bench"
    make_bench(root)
    result = validate_scene(root)
    assert result["kind"] == "synthetic"
    assert result["splits"] == dict(train=14, validation=4, candidate=4, test=6)
    labels = json.loads((root / "annotations.json").read_text())
    assert labels["geometry_sha256"] == sha256_file(root / "geometry.json")
    for row in labels["views"]:
        mask = np.array(Image.open(root / row["mask"])) > 0
        assert row["box"] == mask_box(mask)
        assert sha256_file(root / row["mask"]) == row["mask_sha256"]
        depth = np.array(Image.open(root / "depth" / f"{row['frame_id']}.png"))
        assert (depth[mask] > 0).all()
        assert row["category_name"] == "bench"
