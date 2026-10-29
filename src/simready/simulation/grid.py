"""Conservative surface projection and explicit observed/unknown floor support."""

import math

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import ConvexHull, QhullError

from simready.scene.models import ProxyObject, object_corners
from simready.simulation.models import Scenario


def clip_height(polygon: np.ndarray, lower: float, upper: float) -> np.ndarray:
    for bound, sign in ((lower, 1), (upper, -1)):
        result = []
        if not len(polygon):
            break
        previous = polygon[-1]
        previous_inside = sign * (previous[1] - bound) >= -1e-10
        for current in polygon:
            inside = sign * (current[1] - bound) >= -1e-10
            if inside != previous_inside:
                fraction = (bound - previous[1]) / (current[1] - previous[1])
                result.append(previous + fraction * (current - previous))
            if inside:
                result.append(current)
            previous, previous_inside = current, inside
        polygon = np.asarray(result).reshape(-1, 3)
    return polygon


def rasterize(grid: np.ndarray, polygon: np.ndarray, scenario: Scenario) -> None:
    """Mark all cells intersecting a convex XZ polygon/line, including boundaries."""
    if not len(polygon):
        return
    origin = np.array(scenario.bounds_xz_m[:2])
    resolution = scenario.resolution_m
    low = np.maximum(np.floor((polygon.min(0) - origin) / resolution).astype(int) - 1, 0)
    high = np.minimum(
        np.floor((polygon.max(0) - origin) / resolution).astype(int) + 1,
        np.array([grid.shape[1] - 1, grid.shape[0] - 1]),
    )
    if np.any(low > high):
        return
    zz, xx = np.mgrid[low[1] : high[1] + 1, low[0] : high[0] + 1]
    centers = np.column_stack([xx.ravel(), zz.ravel()]) * resolution + origin + resolution / 2
    edges = np.roll(polygon, -1, axis=0) - polygon
    axes = np.concatenate([np.eye(2), np.column_stack([-edges[:, 1], edges[:, 0]])])
    axes = axes[np.linalg.norm(axes, axis=1) > 1e-12]
    projected, center_projection = polygon @ axes.T, centers @ axes.T
    radius = resolution / 2 * np.abs(axes).sum(axis=1)
    hit = np.all(
        (center_projection + radius >= projected.min(0) - 1e-10)
        & (center_projection - radius <= projected.max(0) + 1e-10),
        axis=1,
    )
    grid[zz.ravel()[hit], xx.ravel()[hit]] = True


def build_grid(
    vertices: np.ndarray, triangles: np.ndarray, objects: list[ProxyObject], scenario: Scenario
) -> dict:
    xmin, zmin, xmax, zmax = scenario.bounds_xz_m
    width = math.ceil((xmax - xmin) / scenario.resolution_m)
    height = math.ceil((zmax - zmin) / scenario.resolution_m)
    observed = np.zeros((height, width), dtype=bool)
    declared = scenario.floor_mode == "declared_virtual_plane"
    if declared:
        observed[:] = True
    occupied = np.zeros_like(observed)
    floor, tolerance = scenario.floor_y_m, scenario.floor_tolerance_m
    lower, upper = floor + scenario.ground_clearance_m, floor + scenario.robot_height_m
    for triangle in vertices[triangles]:
        ymin, ymax = triangle[:, 1].min(), triangle[:, 1].max()
        if not declared and ymin >= floor - tolerance and ymax <= floor + tolerance:
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            if np.linalg.norm(normal) > 1e-10 and abs(normal[1]) >= 0.85 * np.linalg.norm(normal):
                rasterize(observed, triangle[:, [0, 2]], scenario)
        if ymax >= lower and ymin <= upper:
            rasterize(occupied, clip_height(triangle, lower, upper)[:, [0, 2]], scenario)
    # Convex box volumes, including their interiors, use exactly the editor's world transform.
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if (i ^ j) in (1, 2, 4)]
    for obj in objects:
        if not obj.collidable:
            continue
        corners = object_corners(obj)
        points = [p for p in corners if lower <= p[1] <= upper]
        for i, j in edges:
            a, b = corners[i], corners[j]
            if abs(a[1] - b[1]) > 1e-12:
                for bound in (lower, upper):
                    fraction = (bound - a[1]) / (b[1] - a[1])
                    if 0 <= fraction <= 1:
                        points.append(a + fraction * (b - a))
        if not points:
            continue
        footprint = np.unique(np.asarray(points)[:, [0, 2]], axis=0)
        try:
            if len(footprint) >= 3:
                footprint = footprint[ConvexHull(footprint).vertices]
        except QhullError:
            pass
        rasterize(occupied, footprint, scenario)
    raw_blocked = occupied | ~observed
    # Exterior is blocked too; partial final cells crossing declared bounds are unknown.
    xcenters = xmin + (np.arange(width) + 0.5) * scenario.resolution_m
    zcenters = zmin + (np.arange(height) + 0.5) * scenario.resolution_m
    raw_blocked[:, xcenters + scenario.resolution_m / 2 > xmax + 1e-10] = True
    raw_blocked[zcenters + scenario.resolution_m / 2 > zmax + 1e-10, :] = True
    distance = distance_transform_edt(np.pad(~raw_blocked, 1), sampling=scenario.resolution_m)[
        1:-1, 1:-1
    ]
    # Cell surface and within-cell location uncertainty: conservative robot-center mask.
    inflation = scenario.robot_radius_m + math.sqrt(2) * scenario.resolution_m
    blocked = raw_blocked | (distance <= inflation)
    return {
        "floor_support": observed,
        "surface_occupied": occupied,
        "raw_blocked": raw_blocked,
        "blocked": blocked,
    }


def point_cell(point, scenario: Scenario) -> tuple[int, int]:
    cell = np.floor((np.asarray(point) - scenario.bounds_xz_m[:2]) / scenario.resolution_m).astype(
        int
    )
    return int(cell[0]), int(cell[1])


def collides(point, blocked: np.ndarray, scenario: Scenario) -> bool:
    x, z = point_cell(point, scenario)
    return not (0 <= x < blocked.shape[1] and 0 <= z < blocked.shape[0]) or bool(blocked[z, x])
