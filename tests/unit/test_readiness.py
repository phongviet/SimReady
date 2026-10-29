import numpy as np
import pytest

from simready.evaluation.readiness import mesh_diagnostics, pose_diagnostics


def test_pose_distance_full_rotation_and_known_vs_untested_volume():
    train = np.repeat(np.eye(4)[None], 2, axis=0)
    train[1, :3, 3] = [2, 2, 2]
    queries = np.repeat(np.eye(4)[None], 3, axis=0)
    queries[1, :3, 3] = [0.1, 0.1, 0.1]
    queries[2, :3, 3] = [3, 3, 3]
    queries[2, :3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    result = pose_diagnostics(train, queries)
    assert result[0]["classification"] == "observed_training_pose"
    assert result[1]["classification"] == "interpolated_but_tested"
    assert result[1]["distance_m"] == pytest.approx(np.sqrt(0.03))
    assert result[2]["classification"] == "tested_extrapolation"
    assert result[2]["rotation_deg"] == pytest.approx(90)
    with pytest.raises(ValueError):
        pose_diagnostics(np.empty((0, 4, 4)), queries)


def test_mesh_edges_area_and_no_invented_accuracy():
    v = np.array([[0.0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]])
    result = mesh_diagnostics(v, np.array([[0, 1, 2], [0, 2, 3]]))
    assert result["boundary_edges"] == 4 and result["nonmanifold_edges"] == 0
    assert result["surface_area_m2"] == pytest.approx(1)
    assert result["chamfer_m"] is None and result["f_score"] is None
    assert not result["aligned_ground_truth_evaluated"]
