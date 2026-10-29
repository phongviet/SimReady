"""CPU orchestration for the isolated upstream gsplat worker."""

import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.camera import resize_intrinsics, transform_points, unproject, world_to_camera
from simready.data.dataset import (
    atomic_dataset,
    local_file,
    sha256_file,
    validate_scene,
    write_json,
)
from simready.data.schema import DatasetManifest, Frame, Splits
from simready.reconstruction.contracts import ReconstructionConfig
from simready.storage import PROJECT_ROOT

SPLIT_NAMES = ("train", "validation", "candidate", "test")


def validate_renders(output: Path) -> dict:
    metadata = json.loads(local_file(output, "renders.json").read_text())
    if metadata.get("schema_version") != "1.0" or metadata.get("renderer") != "gsplat":
        raise ValueError("unsupported render artifact")
    for camera in metadata["cameras"]:
        name = camera["frame_id"]
        for filename in (f"{name}.png", f"{name}-depth.npy", f"{name}-alpha.npy"):
            path = local_file(output, filename)
            if sha256_file(path) != metadata["files_sha256"].get(filename):
                raise ValueError(f"render content hash mismatch: {filename}")
        with Image.open(output / f"{name}.png") as image:
            if image.size != (camera["width"], camera["height"]) or image.mode != "RGB":
                raise ValueError("saved RGB dimensions/channels differ from camera")
        for channel in ("depth", "alpha"):
            values = np.load(output / f"{name}-{channel}.npy", allow_pickle=False)
            if values.shape != (camera["height"], camera["width"]) or not np.isfinite(values).all():
                raise ValueError(f"invalid saved {channel}")
            if np.any(values < 0) or (channel == "alpha" and np.any(values > 1.0001)):
                raise ValueError(f"saved {channel} outside valid range")
    return metadata


def cpu_smoke() -> dict:
    fixture = Path(__file__).resolve().parents[1] / "demo/analytic-plane"
    artifact = validate_artifact(fixture / "reconstruction")
    renders = validate_renders(fixture / "renders")
    if renders["artifact_sha256"] != sha256_file(fixture / "reconstruction/artifact.json"):
        raise ValueError("CPU fixture render belongs to a different reconstruction")
    return {
        "mode": "CPU validation of a trained analytic synthetic checkpoint and saved views",
        "dataset_kind": artifact["provenance"]["dataset_kind"],
        "gaussians": artifact["worker"]["final_gaussians"],
        "saved_views": len(renders["cameras"]),
        "gpu_used": False,
        "runtime_rendering_performed": False,
    }


def load_records(scene: Path) -> tuple[DatasetManifest, list[Frame], Splits]:
    validate_scene(scene)
    manifest = DatasetManifest.model_validate_json((scene / "manifest.json").read_text())
    frames = [
        Frame.model_validate_json(line)
        for line in (scene / "frames.jsonl").read_text().splitlines()
    ]
    splits = Splits.model_validate_json((scene / "splits.json").read_text())
    return manifest, frames, splits


def camera_record(frame: Frame, manifest: DatasetManifest, width: int) -> dict:
    camera = manifest.cameras[frame.camera_id]
    width = min(width, camera.width)
    height = max(1, round(camera.height * width / camera.width))
    resized = resize_intrinsics(camera, width, height)
    return {
        "frame_id": frame.frame_id,
        "width": width,
        "height": height,
        "K": [[resized.fx, 0, resized.cx], [0, resized.fy, resized.cy], [0, 0, 1]],
        "viewmat": world_to_camera(np.array(frame.T_world_camera)).tolist(),
    }


def prepare_training(scene: Path, config: ReconstructionConfig, output: Path) -> dict:
    """Only train observations initialize/optimize splats; all others remain excluded."""
    manifest, frames, splits = load_records(scene)
    selected = [f for f in frames if f.frame_id in splits.train]
    if len({f.camera_id for f in selected}) != 1:
        raise ValueError("current gsplat adapter requires one calibrated training camera")
    if len(selected) > 128:
        raise ValueError("local adapter limits training to 128 frames")
    points, colors, scales, images, depths, views, intrinsics = [], [], [], [], [], [], []
    for frame in selected:
        if frame.depth_path is None:
            raise ValueError("RGB-D initialization requires depth for every training frame")
        camera = camera_record(frame, manifest, config.width)
        size = camera["width"], camera["height"]
        with Image.open(local_file(scene, frame.rgb_path)) as image:
            rgb = np.asarray(image.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 255
        with Image.open(local_file(scene, frame.depth_path)) as image:
            raw = np.asarray(image.resize(size, Image.Resampling.NEAREST)).astype(np.float32)
        valid = (raw != manifest.depth.invalid_value) & (raw > 0)
        depth = np.where(valid, raw * manifest.depth.meters_per_unit, 0)
        calibrated = resize_intrinsics(manifest.cameras[frame.camera_id], *size)
        yy, xx = np.mgrid[0 : size[1] : config.initial_stride, 0 : size[0] : config.initial_stride]
        z = depth[yy, xx].ravel()
        good = (z > 0.05) & (z < 20)
        pixels = np.column_stack([xx.ravel(), yy.ravel()])[good]
        if not len(pixels):
            raise ValueError(f"no valid initialization depth in frame {frame.frame_id}")
        camera_points = unproject(pixels, z[good], calibrated)
        points.append(transform_points(np.array(frame.T_world_camera), camera_points))
        colors.append(rgb[pixels[:, 1], pixels[:, 0]])
        spacing = np.clip(z[good] / calibrated.fx * config.initial_stride * 0.7, 0.001, 0.1)
        scales.append(np.repeat(spacing[:, None], 3, axis=1))
        images.append(rgb)
        depths.append(depth)
        views.append(camera["viewmat"])
        intrinsics.append(camera["K"])
    positions = np.concatenate(points)
    indices = np.random.default_rng(config.seed).choice(
        len(positions), min(len(positions), config.max_initial_gaussians), replace=False
    )
    if len(indices) < 8:
        raise ValueError("fewer than eight valid initialization points")
    np.savez_compressed(
        output / "training.npz",
        means=positions[indices].astype(np.float32),
        colors=np.concatenate(colors)[indices].astype(np.float32),
        scales=np.concatenate(scales)[indices].astype(np.float32),
        images=np.asarray(images, dtype=np.float32),
        depths=np.asarray(depths, dtype=np.float32),
        viewmats=np.asarray(views, dtype=np.float32),
        Ks=np.asarray(intrinsics, dtype=np.float32),
    )
    return {
        "initialization": "training-only registered RGB-D points",
        "training_frame_ids": [f.frame_id for f in selected],
        "frames_sha256": manifest.frames_sha256,
        "split_sha256": manifest.split_sha256,
        "dataset_manifest_sha256": sha256_file(scene / "manifest.json"),
        "dataset_kind": manifest.kind,
        "dataset_scene_id": manifest.scene_id,
        "source": manifest.source.model_dump(mode="json"),
        "limitations": list(manifest.limitations),
        "world_units": manifest.world_units,
        "world_frame": manifest.world_frame,
        "initial_points": len(indices),
    }


def validate_artifact(artifact: Path) -> dict:
    metadata = json.loads(local_file(artifact, "artifact.json").read_text())
    if metadata.get("schema_version") != "1.0" or metadata.get("backend") != "gsplat":
        raise ValueError("unsupported reconstruction artifact version/backend")
    provenance = metadata.get("provenance", {})
    if (
        provenance.get("source", {}).get("name") == "Open3D SampleRedwoodRGBDImages"
        and provenance.get("dataset_kind") == "real"
    ):
        raise ValueError(
            "legacy Redwood reconstruction has incorrect real-data provenance; "
            "retrain from the corrected synthetic import or use the real TUM capture"
        )
    required = {"gaussians.npz", "gaussian.ply", "training-log.jsonl", "train-job.json"}
    if not required.issubset(metadata.get("files_sha256", {})):
        raise ValueError("reconstruction artifact is missing required content digests")
    count = metadata["worker"]["final_gaussians"]
    degree = metadata["config"]["sh_degree"]
    if type(count) is not int or not 0 < count <= 200000 or degree not in (0, 1, 2, 3):
        raise ValueError("invalid Gaussian count or SH degree")
    for name, digest in metadata["files_sha256"].items():
        if sha256_file(local_file(artifact, name)) != digest:
            raise ValueError(f"reconstruction artifact hash mismatch: {name}")
    with np.load(local_file(artifact, "gaussians.npz"), allow_pickle=False) as arrays:
        expected = {
            "means": (count, 3),
            "scales": (count, 3),
            "quats": (count, 4),
            "opacities": (count,),
            "sh0": (count, 1, 3),
            "shN": (count, (metadata["config"]["sh_degree"] + 1) ** 2 - 1, 3),
        }
        if set(arrays.files) != set(expected):
            raise ValueError("checkpoint parameter names do not match the Gaussian contract")
        for name, shape in expected.items():
            values = arrays[name]
            if values.shape != shape or values.dtype != np.float32 or not np.isfinite(values).all():
                raise ValueError(f"invalid checkpoint tensor: {name}")
        if np.any(np.linalg.norm(arrays["quats"], axis=1) < 1e-8):
            raise ValueError("checkpoint contains a zero-norm quaternion")
    return metadata


class GsplatBackend:
    def __init__(self, python: Path | None = None):
        self.python = python or PROJECT_ROOT / ".venv-gpu/bin/python"
        self.worker = PROJECT_ROOT / "workers/gsplat_worker.py"

    def _run(self, action: str, job: Path, log: Path) -> None:
        if not self.python.is_file():
            raise ValueError("GPU worker is not installed; follow docs/GPU_SETUP.md")
        env = os.environ | {
            "OMP_NUM_THREADS": "4",
            "MKL_NUM_THREADS": "4",
            "OPENBLAS_NUM_THREADS": "4",
        }
        with log.open("w") as out:
            process = subprocess.run(
                [str(self.python), str(self.worker), action, str(job)],
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if process.returncode:
            # Keep useful diagnostics even though atomic staging will be removed.
            details = log.read_text()[-12000:]
            raise ValueError(f"gsplat {action} failed (exit {process.returncode}):\n{details}")

    def train(self, scene: Path, config: ReconstructionConfig, output: Path) -> Path:
        if not self.python.is_file():
            raise ValueError("GPU worker is not installed; follow docs/GPU_SETUP.md")
        started = time.perf_counter()
        with atomic_dataset(output, 300_000_000) as stage:
            provenance = prepare_training(scene, config, stage)
            job = {"schema_version": "1.0", "config": config.model_dump(mode="json")}
            write_json(stage / "train-job.json", job)
            self._run("train", stage / "train-job.json", stage / "worker.log")
            worker = json.loads((stage / "worker-result.json").read_text())
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
            ).strip()
            git_dirty = bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True
                )
            )
            write_json(
                stage / "artifact.json",
                {
                    "schema_version": "1.0",
                    "backend": "gsplat",
                    "provenance": provenance,
                    "config": config.model_dump(mode="json"),
                    "worker": worker,
                    "git_commit": git_commit,
                    "git_dirty": git_dirty,
                    "total_seconds": time.perf_counter() - started,
                    "files_sha256": {
                        name: sha256_file(stage / name)
                        for name in (
                            "gaussians.npz",
                            "gaussian.ply",
                            "training-log.jsonl",
                            "train-job.json",
                        )
                    },
                    "ply_dialect": "Graphdeco SH; wxyz quaternions, log scales, opacity logits",
                    "scope": "Learned 3D Gaussians; visual quality unassessed until M3.",
                },
            )
            validate_artifact(stage)
        return output

    def render(self, artifact: Path, scene: Path, split: str, output: Path) -> Path:
        if split not in SPLIT_NAMES:
            raise ValueError(f"unknown split: {split}")
        metadata = validate_artifact(artifact)
        manifest, frames, splits = load_records(scene)
        if (
            manifest.frames_sha256 != metadata["provenance"]["frames_sha256"]
            or manifest.split_sha256 != metadata["provenance"]["split_sha256"]
            or sha256_file(scene / "manifest.json")
            != metadata["provenance"]["dataset_manifest_sha256"]
        ):
            raise ValueError("render dataset or frozen split differs from training provenance")
        cameras = [
            camera_record(f, manifest, metadata["config"]["width"])
            for f in frames
            if f.frame_id in getattr(splits, split)
        ]
        with atomic_dataset(output, 300_000_000) as stage:
            job = {
                "schema_version": "1.0",
                "checkpoint": str((artifact / "gaussians.npz").resolve()),
                "sh_degree": metadata["config"]["sh_degree"],
                "cameras": cameras,
            }
            write_json(stage / "render-job.json", job)
            self._run("render", stage / "render-job.json", stage / "worker.log")
            for camera in cameras:
                name = camera["frame_id"]
                with Image.open(local_file(stage, f"{name}.png")) as image:
                    if image.size != (camera["width"], camera["height"]) or image.mode != "RGB":
                        raise ValueError("renderer returned invalid RGB dimensions/channels")
                for channel in ("depth", "alpha"):
                    values = np.load(local_file(stage, f"{name}-{channel}.npy"), allow_pickle=False)
                    if (
                        values.shape != (camera["height"], camera["width"])
                        or not np.isfinite(values).all()
                    ):
                        raise ValueError(f"renderer returned invalid {channel}")
            write_json(
                stage / "renders.json",
                {
                    "schema_version": "1.0",
                    "renderer": "gsplat",
                    "split": split,
                    "artifact_sha256": sha256_file(artifact / "artifact.json"),
                    "frames_sha256": manifest.frames_sha256,
                    "split_sha256": manifest.split_sha256,
                    "depth_semantics": "Expected alpha-normalized axial Z, meters; mask by alpha.",
                    "cameras": cameras,
                    "files_sha256": {
                        path.name: sha256_file(path)
                        for path in stage.iterdir()
                        if path.suffix in (".png", ".npy")
                    },
                },
            )
        return output
