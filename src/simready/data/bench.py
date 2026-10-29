"""Authored bench geometry and ray-derived truth, independent of learned outputs."""

from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.dataset import atomic_dataset, finalize_dataset, sha256_file, write_json
from simready.data.schema import DepthEncoding, Frame, Intrinsics, Source


def bench_boxes():
    boxes = [
        ([-0.8, 0.45, -0.24], [0.8, 0.53, 0.24]),
        ([-0.8, 0.75, -0.27], [0.8, 0.88, -0.19]),
        ([-0.8, 0.95, -0.27], [0.8, 1.08, -0.19]),
    ]
    for x in (-0.68, 0.68):
        for z in (-0.16, 0.16):
            boxes.append(([x - 0.045, 0, z - 0.045], [x + 0.045, 0.45, z + 0.045]))
        boxes.append(([x - 0.04, 0.53, -0.26], [x + 0.04, 1.08, -0.20]))
    return np.asarray(boxes, dtype=float)


def ray_box(origin, directions, low, high):
    """Positive entry/exit distance for rays; direction z=1 yields axial depth."""
    parallel = np.abs(directions) < 1e-12
    safe = np.where(parallel, 1.0, directions)
    a, b = (low - origin) / safe, (high - origin) / safe
    near = np.where(parallel, -np.inf, np.minimum(a, b))
    far = np.where(parallel, np.inf, np.maximum(a, b))
    outside = np.any(parallel & ((origin < low) | (origin > high)), axis=-1)
    start, end = near.max(axis=-1), far.min(axis=-1)
    distance = np.where(start > 0, start, end)
    return np.where((end >= np.maximum(start, 0)) & (distance > 0) & ~outside, distance, np.inf)


def look_at(eye, target):
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    pose = np.eye(4)
    pose[:3, :3] = np.column_stack([right, down, forward])
    pose[:3, 3] = eye
    return pose


def render_truth(camera, pose, boxes):
    y, x = np.mgrid[: camera.height, : camera.width]
    rays = np.stack(
        [(x - camera.cx) / camera.fx, (y - camera.cy) / camera.fy, np.ones_like(x)], axis=-1
    )
    directions = rays @ pose[:3, :3].T
    origin = pose[:3, 3]
    distances = np.stack([ray_box(origin, directions, b[0], b[1]) for b in boxes])
    nearest = np.argmin(distances, axis=0)
    depth = distances.min(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        floor = -origin[1] / directions[..., 1]
        wall = (-1.2 - origin[2]) / directions[..., 2]
    floor = np.where(floor > 0, floor, np.inf)
    wall = np.where(wall > 0, wall, np.inf)
    mask = np.isfinite(depth) & (depth < floor) & (depth < wall)
    axial = np.minimum(depth, np.minimum(floor, wall))
    axial = np.where(np.isfinite(axial) & (axial < 20), axial, 0)
    points = origin + directions * axial[..., None]
    checker = (np.floor(points[..., 0] * 5) + np.floor(points[..., 2] * 5)) % 2
    rgb = np.stack([120 + checker * 20, 130 + checker * 20, 140 + checker * 20], axis=-1)
    rgb[wall < floor] = [185, 195, 205]
    grain = (np.sin(points[..., 0] * 80) + 1) * 10
    wood = np.stack([140 + grain, 80 + grain, 35 + grain], axis=-1)
    shade = 0.75 + 0.2 * (nearest % 3) / 2
    rgb[mask] = (wood * shade[..., None])[mask]
    return rgb.clip(0, 255).astype(np.uint8), axial, mask


def mask_box(mask):
    y, x = np.nonzero(mask)
    if len(x) < 20:
        raise ValueError("bench must be visible; never silently drop a view")
    return [int(x.min()), int(y.min()), int(x.max() + 1), int(y.max() + 1)]


def make_bench(output: Path):
    camera = Intrinsics(width=128, height=96, fx=100, fy=100, cx=63.5, cy=47.5)
    boxes = bench_boxes()
    with atomic_dataset(output, 30_000_000) as stage:
        for folder in ("rgb", "depth", "masks"):
            (stage / folder).mkdir()
        write_json(
            stage / "geometry.json",
            {"units": "meters", "object": "authored bench", "boxes": boxes.tolist()},
        )
        frames, annotations = [], []
        for i, angle in enumerate(np.linspace(-35, 35, 28)):
            t = np.radians(angle)
            eye = np.array([2.5 * np.sin(t), 1.25, 2.5 * np.cos(t)])
            pose = look_at(eye, np.array([0.0, 0.55, 0.0]))
            rgb, depth, mask = render_truth(camera, pose, boxes)
            name = f"frame_{i:05d}"
            Image.fromarray(rgb).save(stage / f"rgb/{name}.png")
            Image.fromarray(np.rint(depth * 1000).astype(np.uint16)).save(
                stage / f"depth/{name}.png"
            )
            Image.fromarray(mask.astype(np.uint8) * 255).save(stage / f"masks/{name}.png")
            frames.append(
                Frame(
                    frame_id=name,
                    timestamp=i,
                    depth_timestamp=i,
                    camera_id="camera0",
                    sequence_id="authored_bench",
                    rgb_path=f"rgb/{name}.png",
                    depth_path=f"depth/{name}.png",
                    rgb_sha256=sha256_file(stage / f"rgb/{name}.png"),
                    depth_sha256=sha256_file(stage / f"depth/{name}.png"),
                    T_world_camera=pose.tolist(),
                )
            )
            annotations.append(
                {
                    "frame_id": name,
                    "category_name": "bench",
                    "box": mask_box(mask),
                    "mask": f"masks/{name}.png",
                    "mask_sha256": sha256_file(stage / f"masks/{name}.png"),
                }
            )
        write_json(
            stage / "annotations.json",
            {
                "truth_origin": "Authored geometry ray intersections; no model outputs",
                "geometry_sha256": sha256_file(stage / "geometry.json"),
                "views": annotations,
            },
        )
        finalize_dataset(
            stage,
            dict(
                scene_id="authored_bench",
                kind="synthetic",
                source=Source(
                    name="SimReady authored bench",
                    url="local:authored-bench-v1",
                    license="CC0-1.0",
                    attribution="SimReady Development",
                    description="Procedural bench and ray-derived labels; not real capture.",
                ),
                cameras={"camera0": camera},
                depth=DepthEncoding(meters_per_unit=0.001, invalid_value=0),
                pose_provenance="Exact authored optical camera-to-world matrices.",
                timestamp_provenance="Synthetic indices.",
                association_tolerance=0,
                capture_conditions="Static procedural bench, floor and wall; no sensor noise.",
                privacy="Synthetic; no personal information.",
                limitations=[
                    "One authored object with correlated views; no real-domain accuracy inference."
                ],
                T_canonical_source_world=np.eye(4).tolist(),
            ),
            frames,
        )
