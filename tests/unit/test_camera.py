import numpy as np
import pytest
from pydantic import ValidationError

from simready.data.camera import (
    CV_TO_GL,
    depth_to_meters,
    gsplat_viewmat,
    open3d_extrinsic,
    project,
    resize_intrinsics,
    threejs_camera_matrix,
    transform_points,
    unproject,
    world_to_camera,
)
from simready.data.schema import Intrinsics, rigid_matrix


@pytest.fixture
def camera():
    return Intrinsics(width=640, height=480, fx=500, fy=400, cx=319.5, cy=239.5)


def test_resize_independent_axes_and_half_pixel_centers(camera):
    resized = resize_intrinsics(camera, 320, 120)
    assert (resized.fx, resized.fy, resized.cx, resized.cy) == (250, 100, 159.5, 59.5)
    assert resize_intrinsics(resized, 640, 480) == camera


def test_known_marker_projection(camera):
    # x/z=.2, y/z=-.1 => u=419.5, v=199.5, independent expected values.
    np.testing.assert_allclose(project(np.array([[0.4, -0.2, 2]]), camera), [[419.5, 199.5]])


def test_nontrivial_world_camera_and_pixel_roundtrip(camera):
    pose = np.array([[0, 0, 1, 2], [0, 1, 0, -3], [-1, 0, 0, 4], [0, 0, 0, 1]])
    points = np.array([[0.4, -0.2, 2], [0.1, 0.3, 1], [-0.4, 0.2, 4]])
    world = transform_points(pose, points)
    restored = transform_points(world_to_camera(pose), world)
    np.testing.assert_allclose(restored, points, atol=1e-12)
    pixels = project(restored, camera)
    np.testing.assert_allclose(unproject(pixels, restored[:, 2], camera), points, atol=1e-12)
    # A rigid coordinate conversion preserves known one-meter separation.
    metric = transform_points(pose, np.array([[0, 0, 0], [1, 0, 0]]))
    assert np.linalg.norm(metric[1] - metric[0]) == pytest.approx(1.0)


def test_backend_conventions_have_expected_forward_axis():
    pose = CV_TO_GL.copy()
    pose[:3, 3] = [2, 3, 4]
    marker_world = np.array([[2, 3, 2]])  # two meters ahead of camera
    np.testing.assert_allclose(transform_points(gsplat_viewmat(pose), marker_world), [[0, 0, 2]])
    np.testing.assert_allclose(transform_points(open3d_extrinsic(pose), marker_world), [[0, 0, 2]])
    three = threejs_camera_matrix(pose)
    np.testing.assert_allclose(transform_points(np.linalg.inv(three), marker_world), [[0, 0, -2]])
    np.testing.assert_allclose(three @ CV_TO_GL, pose)


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf")])
def test_invalid_depth_scale_rejected(scale):
    with pytest.raises(ValueError, match="finite and positive"):
        depth_to_meters(np.array([1000]), scale)


def test_depth_units_and_invalids():
    raw = np.array([0, 1000, 2500, -1, np.nan, np.inf, 65535])
    depth = depth_to_meters(raw, 0.001, invalid_value=65535)
    np.testing.assert_allclose(depth[1:3], [1.0, 2.5])
    assert np.isnan(depth[[0, 3, 4, 5, 6]]).all()


@pytest.mark.parametrize("point", [[[0, 0, 0]], [[0, 0, -1]], [[np.nan, 0, 1]]])
def test_nonprojectable_points_fail(camera, point):
    with pytest.raises(ValueError):
        project(np.array(point), camera)


@pytest.mark.parametrize(
    "matrix",
    [
        np.zeros((4, 4)),
        np.eye(3),
        np.diag([-1, 1, 1, 1]),
        np.diag([2, 1, 1, 1]),
        np.full((4, 4), np.nan),
    ],
)
def test_improper_pose_rejected(matrix):
    with pytest.raises(ValueError):
        rigid_matrix(matrix)


@pytest.mark.parametrize(
    "change",
    [
        {"fx": 0},
        {"fy": float("nan")},
        {"cx": 640},
        {"width": 0},
        {"height": True},
        {"model": "fisheye"},
    ],
)
def test_invalid_intrinsics(camera, change):
    with pytest.raises(ValidationError):
        Intrinsics(**(camera.model_dump() | change))
