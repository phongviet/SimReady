import numpy as np
import pytest

from simready.data.tum import (
    TUM_WORLD_TO_CANONICAL,
    interpolate_pose,
    parse_rows,
    quaternion_matrix,
)


def test_tum_index_preserves_original_timestamps():
    rows = parse_rows("# comment\n1.001 rgb/a.png\n1.02 rgb/b.png\n", 2)
    assert rows[0] == ["1.001", "rgb/a.png"]


@pytest.mark.parametrize("text", ["", "1 a\n1 b", "nan a", "2 a\n1 b", "1 a b"])
def test_bad_tum_index_rejected(text):
    with pytest.raises(ValueError):
        parse_rows(text, 2)


def test_tum_optical_center_interpolation_and_world_axes():
    # Original pose rotates 0 -> 180 degrees about Z over 20ms, translates X 0 -> 2m.
    truth = np.array([[1.0, 0, 0, 0, 0, 0, 0, 1], [1.02, 2, 0, 0, 0, 0, 1, 0]])
    pose = interpolate_pose(1.01, truth)
    source = np.array([[0, -1, 0, 1], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    np.testing.assert_allclose(pose, TUM_WORLD_TO_CANONICAL @ source, atol=1e-12)


def test_quaternion_sign_does_not_change_interpolated_rotation():
    truth = np.array([[1.0, 0, 0, 0, 0, 0, 0, 1], [1.02, 0, 0, 0, 0, 0, 0, -1]])
    np.testing.assert_allclose(interpolate_pose(1.01, truth), TUM_WORLD_TO_CANONICAL)


@pytest.mark.parametrize("time", [0.99, 1.03])
def test_pose_extrapolation_forbidden(time):
    truth = np.array([[1.0, 0, 0, 0, 0, 0, 0, 1], [1.02, 0, 0, 0, 0, 0, 0, 1]])
    with pytest.raises(ValueError, match="outside"):
        interpolate_pose(time, truth)


def test_zero_quaternion_rejected():
    with pytest.raises(ValueError, match="unit"):
        quaternion_matrix(np.zeros(4))


def test_fr2_duplicate_poses_are_all_excluded_and_logged():
    from simready.data.tum import groundtruth_rows

    text = "1 0 0 0 0 0 0 1\n1.01 1 0 0 0 0 0 1\n1.01 2 0 0 0 0 0 1\n1.02 3 0 0 0 0 0 1\n"
    rows, report = groundtruth_rows(text, "rgbd_dataset_freiburg2_desk")
    assert [float(r[0]) for r in rows] == [1, 1.02]
    assert report["excluded_records"] == 2
    assert report["duplicated_timestamps"] == [1.01]
    assert len(report["source_groundtruth_sha256"]) == 64
    with pytest.raises(ValueError, match="strictly ordered"):
        groundtruth_rows(text, "rgbd_dataset_freiburg1_desk")


def test_fr2_remaining_pose_reversal_still_fails():
    from simready.data.tum import groundtruth_rows

    text = "2 0 0 0 0 0 0 1\n1 1 0 0 0 0 0 1\n"
    with pytest.raises(ValueError, match="strictly ordered"):
        groundtruth_rows(text, "rgbd_dataset_freiburg2_desk")
