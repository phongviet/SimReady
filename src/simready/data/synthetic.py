"""Analytic textured plane with known metric mesh; never a 3DGS reconstruction."""

from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.camera import CV_TO_GL, transform_points, unproject
from simready.data.dataset import atomic_dataset, finalize_dataset, sha256_file
from simready.data.schema import DepthEncoding, Frame, Intrinsics, Source


def make_synthetic(output: Path) -> None:
    camera = Intrinsics(width=64, height=48, fx=50, fy=50, cx=31.5, cy=23.5)
    metadata = dict(
        scene_id="synthetic_plane",
        kind="synthetic",
        source=Source(
            name="SimReady analytic fixture",
            url="local:analytic-plane-v1",
            license="CC0-1.0",
            attribution="SimReady Development",
            description="Analytic plane at world Z=-2m; no learned rendering.",
        ),
        cameras={"camera0": camera},
        depth=DepthEncoding(meters_per_unit=0.001, invalid_value=0),
        pose_provenance="Exact analytic camera-to-world matrices, translated along world X.",
        timestamp_provenance="Synthetic frame indices, not capture seconds.",
        association_tolerance=0,
        capture_conditions="Static analytic textured plane, no distortion.",
        privacy="Synthetic, no personal information.",
        limitations=(
            "Synthetic unit-test fixture; not real data or a reconstruction.",
            "Small split blocks lack spatial separation; not an evaluation benchmark.",
        ),
        T_canonical_source_world=np.eye(4).tolist(),
    )
    with atomic_dataset(output, reserve_bytes=1_000_000) as stage:
        (stage / "rgb").mkdir()
        (stage / "depth").mkdir()
        frames = []
        yy, xx = np.mgrid[: camera.height, : camera.width]
        pixels = np.column_stack([xx.ravel(), yy.ravel()])
        camera_points = unproject(pixels, np.full(len(pixels), 2.0), camera)
        for i in range(8):
            pose = CV_TO_GL.copy()
            pose[0, 3] = (i - 3.5) * 0.05
            world = transform_points(pose, camera_points)
            checker = ((np.floor(world[:, 0] * 10) + np.floor(world[:, 1] * 10)) % 2) * 120
            colors = (
                np.column_stack([checker + 50, (world[:, 0] + 2) * 50, (world[:, 1] + 2) * 50])
                .clip(0, 255)
                .astype(np.uint8)
            )
            rgb_path, depth_path = f"rgb/{i:05d}.png", f"depth/{i:05d}.png"
            Image.fromarray(colors.reshape(camera.height, camera.width, 3)).save(stage / rgb_path)
            Image.fromarray(np.full((camera.height, camera.width), 2000, dtype=np.uint16)).save(
                stage / depth_path
            )
            frames.append(
                Frame(
                    frame_id=f"frame_{i:05d}",
                    timestamp=i,
                    depth_timestamp=i,
                    camera_id="camera0",
                    sequence_id="analytic_plane",
                    rgb_path=rgb_path,
                    rgb_sha256=sha256_file(stage / rgb_path),
                    depth_path=depth_path,
                    depth_sha256=sha256_file(stage / depth_path),
                    T_world_camera=pose.tolist(),
                )
            )
        (stage / "ground_truth.obj").write_text(
            "# Analytic plane in meters, world Y-up\n"
            "v -2 -2 -2\nv 2 -2 -2\nv 2 2 -2\nv -2 2 -2\nf 1 2 3\nf 1 3 4\n"
        )
        finalize_dataset(stage, metadata, frames)
