"""Open3D CPU TSDF fusion, explicitly independent of Gaussian rendering."""

import json
import time
from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.camera import world_to_camera
from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.reconstruction.gsplat import load_records


def validate_geometry(root: Path) -> dict:
    metadata = json.loads(local_file(root, "geometry.json").read_text())
    if metadata.get("schema_version") != "1.0" or metadata.get("method") != "open3d_tsdf":
        raise ValueError("unsupported geometry artifact")
    if (
        metadata.get("world_units") != "meters"
        or metadata.get("world_frame") != "canonical_right_handed_y_up"
        or not np.allclose(np.array(metadata["T_world_geometry"]), np.eye(4), atol=1e-8, rtol=0)
    ):
        raise ValueError("geometry must already be in the canonical metric world frame")
    required = {"collision_mesh.ply", "collision_mesh.npz", "collision_mesh.json"}
    if set(metadata["files_sha256"]) != required:
        raise ValueError("geometry content hashes are incomplete")
    for name, digest in metadata["files_sha256"].items():
        if sha256_file(local_file(root, name)) != digest:
            raise ValueError(f"geometry hash mismatch: {name}")
    with np.load(root / "collision_mesh.npz", allow_pickle=False) as arrays:
        vertices, triangles = arrays["vertices"], arrays["triangles"]
        if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
            raise ValueError("invalid geometry vertices")
        if triangles.ndim != 2 or triangles.shape[1] != 3 or triangles.dtype.kind not in "iu":
            raise ValueError("invalid geometry triangle indices")
        if (
            not len(vertices)
            or not len(triangles)
            or triangles.min() < 0
            or triangles.max() >= len(vertices)
        ):
            raise ValueError("empty or out-of-bounds geometry")
        if len(vertices) != metadata["vertices"] or len(triangles) != metadata["triangles"]:
            raise ValueError("geometry counts differ from metadata")
    return metadata


def build_tsdf(
    scene: Path,
    output: Path,
    voxel_size: float = 0.03,
    depth_trunc: float = 5.0,
    max_triangles: int = 50000,
) -> Path:
    if not 0.005 <= voxel_size <= 0.2 or not 0.1 <= depth_trunc <= 20:
        raise ValueError("invalid TSDF voxel/depth bounds")
    if not 100 <= max_triangles <= 200000:
        raise ValueError("TSDF triangle budget must be 100..200000")
    try:
        import open3d as o3d
    except ImportError as exc:
        raise ValueError(
            "TSDF requires the optional CPU geometry dependencies: uv sync --extra geometry"
        ) from exc
    manifest, frames, splits = load_records(scene)
    selected = [f for f in frames if f.frame_id in splits.train]
    if len(selected) > 128 or any(f.depth_path is None for f in selected):
        raise ValueError("local TSDF requires at most 128 training frames, all with depth")
    started = time.perf_counter()
    with atomic_dataset(output, 150_000_000) as stage:
        volume = o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=voxel_size,
            sdf_trunc=voxel_size * 3,
            color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
        )
        for frame in selected:
            calibration = manifest.cameras[frame.camera_id]
            with Image.open(local_file(scene, frame.rgb_path)) as image:
                color = np.array(image, dtype=np.uint8)
            with Image.open(local_file(scene, frame.depth_path)) as image:
                depth = np.array(image, dtype=np.uint16)
            depth[depth == manifest.depth.invalid_value] = 0
            rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
                o3d.geometry.Image(color),
                o3d.geometry.Image(depth),
                depth_scale=1 / manifest.depth.meters_per_unit,
                depth_trunc=depth_trunc,
                convert_rgb_to_intensity=False,
            )
            intrinsics = o3d.camera.PinholeCameraIntrinsic(
                calibration.width,
                calibration.height,
                calibration.fx,
                calibration.fy,
                calibration.cx,
                calibration.cy,
            )
            volume.integrate(rgbd, intrinsics, world_to_camera(np.array(frame.T_world_camera)))
        mesh = volume.extract_triangle_mesh()
        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()
        mesh.remove_unreferenced_vertices()
        if len(mesh.triangles) > max_triangles:
            mesh = mesh.simplify_quadric_decimation(max_triangles)
        mesh.compute_vertex_normals()
        vertices = np.asarray(mesh.vertices, dtype=np.float32)
        triangles = np.asarray(mesh.triangles, dtype=np.int32)
        if not len(triangles):
            raise ValueError("TSDF yielded no observed surface; no geometry was fabricated")
        np.savez_compressed(stage / "collision_mesh.npz", vertices=vertices, triangles=triangles)
        if not o3d.io.write_triangle_mesh(str(stage / "collision_mesh.ply"), mesh):
            raise ValueError("Open3D failed to save the coarse collision mesh")
        write_json(
            stage / "collision_mesh.json",
            {"vertices": vertices.tolist(), "triangles": triangles.tolist()},
        )
        write_json(
            stage / "geometry.json",
            {
                "schema_version": "1.0",
                "method": "open3d_tsdf",
                "quality": "coarse_proxy",
                "open3d_version": o3d.__version__,
                "world_units": "meters",
                "world_frame": manifest.world_frame,
                "T_world_geometry": np.eye(4).tolist(),
                "voxel_size_m": voxel_size,
                "sdf_trunc_m": voxel_size * 3,
                "depth_trunc_m": depth_trunc,
                "max_triangles": max_triangles,
                "training_frame_ids": [f.frame_id for f in selected],
                "frames_sha256": manifest.frames_sha256,
                "split_sha256": manifest.split_sha256,
                "dataset_manifest_sha256": sha256_file(scene / "manifest.json"),
                "vertices": len(vertices),
                "triangles": len(triangles),
                "bounds_min_m": vertices.min(axis=0).tolist(),
                "bounds_max_m": vertices.max(axis=0).tolist(),
                "elapsed_seconds": time.perf_counter() - started,
                "ground_truth_metrics": None,
                "limitations": [
                    "Observed surface proxy only; holes and unobserved space are unverified.",
                    "Not necessarily closed/watertight; no physical-accuracy certification.",
                    "No ground-truth geometric error measured.",
                ]
                + list(manifest.limitations),
                "files_sha256": {
                    name: sha256_file(stage / name)
                    for name in ("collision_mesh.ply", "collision_mesh.npz", "collision_mesh.json")
                },
            },
        )
        validate_geometry(stage)
    return output
