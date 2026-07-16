"""Explicit OpenCV camera / canonical world / backend coordinate operations."""

import numpy as np

from simready.data.schema import Intrinsics, rigid_matrix

CV_TO_GL = np.diag([1.0, -1.0, -1.0, 1.0])


def resize_intrinsics(camera: Intrinsics, width: int, height: int) -> Intrinsics:
    """Integer pixel centers with half-pixel image-resampling convention."""
    sx, sy = width / camera.width, height / camera.height
    return Intrinsics(
        width=width,
        height=height,
        fx=camera.fx * sx,
        fy=camera.fy * sy,
        cx=(camera.cx + 0.5) * sx - 0.5,
        cy=(camera.cy + 0.5) * sy - 0.5,
    )


def world_to_camera(c2w: np.ndarray) -> np.ndarray:
    return np.linalg.inv(rigid_matrix(c2w))


def gsplat_viewmat(c2w: np.ndarray) -> np.ndarray:
    """gsplat uses an OpenCV world-to-camera view matrix."""
    return world_to_camera(c2w)


def open3d_extrinsic(c2w: np.ndarray) -> np.ndarray:
    """Open3D integration extrinsic is OpenCV world-to-camera."""
    return world_to_camera(c2w)


def threejs_camera_matrix(c2w: np.ndarray) -> np.ndarray:
    """Three.js camera local axes: X right, Y up, forward -Z; world stays Y-up."""
    return rigid_matrix(c2w) @ CV_TO_GL


def transform_points(transform: np.ndarray, points: np.ndarray) -> np.ndarray:
    matrix = rigid_matrix(transform)
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("points must have finite shape (N, 3)")
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def project(points_camera: np.ndarray, camera: Intrinsics) -> np.ndarray:
    points = np.asarray(points_camera, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("camera points must have finite shape (N, 3)")
    if np.any(points[:, 2] <= 0):
        raise ValueError("projection requires positive camera Z")
    return points[:, :2] / points[:, 2:] * [camera.fx, camera.fy] + [camera.cx, camera.cy]


def unproject(pixels: np.ndarray, depth_z: np.ndarray, camera: Intrinsics) -> np.ndarray:
    pixels = np.asarray(pixels, dtype=np.float64)
    depth_z = np.asarray(depth_z, dtype=np.float64)
    if pixels.ndim != 2 or pixels.shape[1] != 2 or depth_z.shape != (len(pixels),):
        raise ValueError("pixels must be (N, 2), depths must be (N,)")
    if not np.isfinite(pixels).all() or not np.isfinite(depth_z).all() or np.any(depth_z <= 0):
        raise ValueError("unprojection requires finite pixels and positive depths")
    xy = (pixels - [camera.cx, camera.cy]) / [camera.fx, camera.fy]
    return np.column_stack([xy * depth_z[:, None], depth_z])


def depth_to_meters(raw: np.ndarray, meters_per_unit: float, invalid_value: int = 0) -> np.ndarray:
    if not np.isfinite(meters_per_unit) or meters_per_unit <= 0:
        raise ValueError("meters_per_unit must be finite and positive")
    values = np.asarray(raw, dtype=np.float64)
    valid = np.isfinite(values) & (values > 0) & (values != invalid_value)
    return np.where(valid, values * meters_per_unit, np.nan)
