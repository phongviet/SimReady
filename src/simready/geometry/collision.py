"""Box/surface intersection. Open TSDF surfaces are not treated as solid volumes."""

import numpy as np

from simready.scene.models import ProxyObject, object_matrix


def mesh_intersects_box(vertices: np.ndarray, triangles: np.ndarray, box: ProxyObject) -> bool:
    if not box.collidable:
        return False
    inverse = np.linalg.inv(object_matrix(box))
    local = np.asarray(vertices) @ inverse[:3, :3].T + inverse[:3, 3]
    faces = local[np.asarray(triangles)]
    # Transforming into box local coordinates makes the box axis-aligned at +/-0.5.
    broad = (faces.min(axis=1) <= 0.5 + 1e-8).all(axis=1) & (faces.max(axis=1) >= -0.5 - 1e-8).all(
        axis=1
    )
    faces = faces[broad]
    if not len(faces):
        return False
    edges = np.stack(
        [faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 1], faces[:, 0] - faces[:, 2]], axis=1
    )
    axes = [np.cross(edges[:, 0], edges[:, 1])]
    for edge in range(3):
        for axis in np.eye(3):
            axes.append(np.cross(edges[:, edge], axis))
    overlap = np.ones(len(faces), dtype=bool)
    for axis in axes:
        projection = (faces * axis[:, None, :]).sum(axis=2)
        radius = np.abs(axis).sum(axis=1) * 0.5
        overlap &= (projection.min(axis=1) <= radius + 1e-8) & (
            projection.max(axis=1) >= -radius - 1e-8
        )
    return bool(overlap.any())
