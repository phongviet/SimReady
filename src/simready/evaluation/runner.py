"""Validate frozen provenance, stage paired observations, run inference and export."""

import csv
import importlib.metadata
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.metrics import depth_metrics, detection_metrics, image_metrics
from simready.evaluation.report import build_report, heatmap, overlay
from simready.reconstruction.gsplat import (
    camera_record,
    load_records,
    validate_artifact,
    validate_renders,
)
from simready.storage import PROJECT_ROOT


def verify_inputs(scene: Path, artifact: Path, renders: Path):
    model, images = validate_artifact(artifact), validate_renders(renders)
    split = images["split"]
    if split not in ("validation", "test"):
        raise ValueError("evaluation accepts only frozen validation or test views")
    manifest, frames, splits = load_records(scene, (split,))
    provenance = model["provenance"]
    if (
        provenance["dataset_manifest_sha256"] != sha256_file(scene / "manifest.json")
        or provenance["frames_sha256"] != manifest.frames_sha256
        or provenance["split_sha256"] != manifest.split_sha256
        or images["artifact_sha256"] != sha256_file(artifact / "artifact.json")
        or images["frames_sha256"] != manifest.frames_sha256
        or images["split_sha256"] != manifest.split_sha256
    ):
        raise ValueError("evaluation inputs differ from frozen reconstruction provenance")
    if provenance["training_frame_ids"] != [
        f.frame_id for f in frames if f.frame_id in splits.train
    ]:
        raise ValueError("training provenance does not match frozen training split")
    selected = [f for f in frames if f.frame_id in getattr(splits, split)]
    expected = [camera_record(f, manifest, model["config"]["width"]) for f in selected]
    if images["cameras"] != expected:
        raise ValueError("render cameras must exactly match the complete frozen evaluation split")
    return manifest, frames, splits, selected, expected, model, images


def validate_evaluation(root: Path) -> dict:
    metadata = json.loads(local_file(root, "evaluation.json").read_text())
    if metadata.get("schema_version") != "1.0" or metadata.get("type") != "frozen_view_evaluation":
        raise ValueError("unsupported evaluation artifact")
    required = {
        "summary.json",
        "views.json",
        "predictions.json",
        "per_view.csv",
        "report.html",
        "report.md",
        "protocol.json",
        "inputs.json",
        "worker.log",
        "lpips-distribution.svg",
    }
    if not required.issubset(metadata.get("files_sha256", {})):
        raise ValueError("evaluation is missing required content hashes")
    for name, digest in metadata["files_sha256"].items():
        if sha256_file(local_file(root, name)) != digest:
            raise ValueError(f"evaluation content hash mismatch: {name}")
    summary = json.loads((root / "summary.json").read_text())
    if summary["split_sha256"] != metadata["split_sha256"]:
        raise ValueError("evaluation split metadata mismatch")
    return metadata


def verify_evaluation_binding(
    output: Path, scene: Path, artifact: Path, renders: Path, config: EvaluationConfig
) -> dict:
    """Bind cached/recovered measurements to the exact requested observations and renders."""
    metadata = validate_evaluation(output)
    manifest, _, splits, selected, cameras, _, images = verify_inputs(scene, artifact, renders)
    expected = {
        "observations": [
            {
                "frame_id": frame.frame_id,
                "rgb_sha256": frame.rgb_sha256,
                "depth_sha256": frame.depth_sha256,
                "camera": camera,
                "timestamp": frame.timestamp,
            }
            for frame, camera in zip(selected, cameras, strict=True)
        ],
        "dataset_manifest": manifest.model_dump(mode="json"),
        "training_frame_ids": list(splits.train),
        "evaluation_frame_ids": [frame.frame_id for frame in selected],
        "artifact_sha256": sha256_file(artifact / "artifact.json"),
        "renders_index_sha256": sha256_file(renders / "renders.json"),
    }
    saved = json.loads(local_file(output, "inputs.json").read_text())
    summary = json.loads(local_file(output, "summary.json").read_text())
    if (
        saved != expected
        or summary["protocol"] != config.model_dump(mode="json")
        or summary["artifact_sha256"] != expected["artifact_sha256"]
        or summary["split"] != images["split"]
        or summary["split_sha256"] != manifest.split_sha256
    ):
        raise ValueError("cached evaluation differs from requested references, renders or protocol")
    return metadata


def evaluate(
    scene: Path,
    artifact: Path,
    renders: Path,
    output: Path,
    config: EvaluationConfig | None = None,
    python: Path | None = None,
) -> Path:
    config = config or EvaluationConfig()
    manifest, frames, splits, selected, cameras, model, images = verify_inputs(
        scene, artifact, renders
    )
    worker_python = python or PROJECT_ROOT / ".venv-gpu/bin/python"
    if not worker_python.is_file():
        raise ValueError("perception worker not installed; follow docs/GPU_SETUP.md")
    with atomic_dataset(output, 300_000_000) as stage:
        (stage / "images").mkdir()
        inputs, job_views = [], []
        for frame, camera in zip(selected, cameras, strict=True):
            name, size = frame.frame_id, (camera["width"], camera["height"])
            if min(size) < 32:
                raise ValueError("LPIPS evaluation requires both image dimensions >=32")
            real_name, render_name = f"images/{name}-real.png", f"images/{name}-rendered.png"
            with Image.open(local_file(scene, frame.rgb_path)) as image:
                image.resize(size, Image.Resampling.LANCZOS).save(stage / real_name)
            shutil.copyfile(renders / f"{name}.png", stage / render_name)
            inputs.append(
                {
                    "frame_id": name,
                    "rgb_sha256": sha256_file(local_file(scene, frame.rgb_path)),
                    "depth_sha256": sha256_file(local_file(scene, frame.depth_path))
                    if frame.depth_path
                    else None,
                    "camera": camera,
                    "timestamp": frame.timestamp,
                }
            )
            job_views.append({"frame_id": name, "real": real_name, "rendered": render_name})
        write_json(stage / "protocol.json", config.model_dump(mode="json"))
        write_json(
            stage / "inputs.json",
            {
                "observations": inputs,
                "dataset_manifest": manifest.model_dump(mode="json"),
                "training_frame_ids": splits.train,
                "evaluation_frame_ids": [f.frame_id for f in selected],
                "artifact_sha256": sha256_file(artifact / "artifact.json"),
                "renders_index_sha256": sha256_file(renders / "renders.json"),
            },
        )
        write_json(
            stage / "inference-job.json",
            {"config": config.model_dump(mode="json"), "views": job_views},
        )
        env = os.environ | {
            "OMP_NUM_THREADS": "4",
            "MKL_NUM_THREADS": "4",
            "OPENBLAS_NUM_THREADS": "4",
            "TORCH_HOME": str(PROJECT_ROOT / ".cache/torch"),
        }
        with (stage / "worker.log").open("w") as log:
            proc = subprocess.run(
                [
                    str(worker_python.absolute()),
                    str(PROJECT_ROOT / "workers/perception_worker.py"),
                    str((stage / "inference-job.json").resolve()),
                ],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        if proc.returncode:
            raise ValueError(
                f"perception worker exited {proc.returncode}:\n"
                + (stage / "worker.log").read_text()[-10000:]
            )
        predictions = json.loads((stage / "predictions.json").read_text())
        if [v["frame_id"] for v in predictions["views"]] != [f.frame_id for f in selected]:
            raise ValueError("worker predictions do not match requested frozen views")
        views, rows = [], []
        for frame, camera, pair, prediction in zip(
            selected, cameras, job_views, predictions["views"], strict=True
        ):
            name, size = frame.frame_id, (camera["width"], camera["height"])
            a, b = (
                np.array(Image.open(stage / pair["real"])),
                np.array(Image.open(stage / pair["rendered"])),
            )
            metrics = image_metrics(a, b)
            lpips_value = float(prediction["lpips"])
            if not np.isfinite(lpips_value):
                raise ValueError("non-finite LPIPS prediction")
            metrics["lpips"] = lpips_value
            if frame.depth_path:
                with Image.open(local_file(scene, frame.depth_path)) as image:
                    raw = np.asarray(image.resize(size, Image.Resampling.NEAREST)).astype(
                        np.float32
                    )
                real_depth = np.where(
                    (raw != manifest.depth.invalid_value) & (raw > 0),
                    raw * manifest.depth.meters_per_unit,
                    np.nan,
                )
            else:
                real_depth = np.full((size[1], size[0]), np.nan)
            rendered_depth = np.load(renders / f"{name}-depth.npy", allow_pickle=False)
            alpha = np.load(renders / f"{name}-alpha.npy", allow_pickle=False)
            dm, mask = depth_metrics(
                real_depth, rendered_depth, alpha, config.depth_alpha_threshold
            )
            metrics.update(dm)
            detection = detection_metrics(
                prediction["real"],
                prediction["rendered"],
                *size,
                config.confidence_threshold,
                config.match_iou_threshold,
            )
            assets = pair.copy()
            assets.pop("frame_id")
            for key in (
                "residual",
                "depth_error",
                "depth_mask",
                "real_overlay",
                "rendered_overlay",
            ):
                assets[key] = f"images/{name}-{key}.png"
            heatmap(np.abs(a.astype(float) - b).mean(axis=2) / 255, 1).save(
                stage / assets["residual"]
            )
            heatmap(np.abs(rendered_depth - real_depth), 1, mask).save(
                stage / assets["depth_error"]
            )
            Image.fromarray(mask.astype(np.uint8) * 255).save(stage / assets["depth_mask"])
            categories = predictions["environment"]["categories"]
            for domain in ("real", "rendered"):
                overlay(
                    stage / assets[domain],
                    detection[domain],
                    categories,
                    stage / assets[f"{domain}_overlay"],
                )
            view = {
                "frame_id": name,
                "metrics": metrics,
                "detection": detection,
                "assets": assets,
                "camera": camera,
            }
            views.append(view)
            row = {"frame_id": name, **metrics}
            row.update(
                {
                    f"detection_{key}": value
                    for key, value in detection.items()
                    if isinstance(value, (int, float, bool)) or value is None
                }
            )
            rows.append(row)
        means = {}
        for key in (
            "psnr_db",
            "ssim",
            "lpips",
            "depth_mae_m",
            "depth_rmse_m",
            "depth_completeness",
        ):
            values = [v["metrics"][key] for v in views if v["metrics"][key] is not None]
            means[key] = float(np.mean(values)) if values else None
        totals = {
            key: sum(v["detection"][key] for v in views)
            for key in (
                "real_count",
                "rendered_count",
                "matched_count",
                "disappeared_count",
                "appeared_count",
                "empty_both",
            )
        }
        per_class = {}
        for view in views:
            for label, counts in view["detection"]["per_class"].items():
                target = per_class.setdefault(label, {"real": 0, "rendered": 0, "matched": 0})
                for key, value in counts.items():
                    target[key] += value
        summary = {
            "schema_version": "1.0",
            "dataset_scene_id": manifest.scene_id,
            "dataset_kind": manifest.kind,
            "split": images["split"],
            "split_sha256": manifest.split_sha256,
            "frames_sha256": manifest.frames_sha256,
            "dataset_manifest_sha256": sha256_file(scene / "manifest.json"),
            "artifact_sha256": sha256_file(artifact / "artifact.json"),
            "view_count": len(views),
            "means": means,
            "detection_totals": totals,
            "per_class": per_class,
            "rgb_exact_matches": sum(v["metrics"]["rgb_exact_match"] for v in views),
            "psnr_finite_count": sum(v["metrics"]["psnr_db"] is not None for v in views),
            "geometry_chamfer": None,
            "geometry_f_score": None,
            "environment": predictions["environment"]
            | {p: importlib.metadata.version(p) for p in ("scipy", "scikit-image", "pillow")},
            "source": manifest.source.model_dump(mode="json"),
            "protocol": config.model_dump(mode="json"),
            "scope": (
                "Camera-aligned base reconstruction only. Detector consistency is not "
                "detection accuracy. No edited proxies are evaluated."
            ),
            "limitations": list(manifest.limitations)
            + [
                "One sequence with temporally correlated held-out views; no "
                "population or statistical significance claim.",
                "This generic report does not evaluate object annotations or compute "
                "precision, recall or mAP; a detector can share errors across domains. "
                "A separately labeled companion may evaluate accuracy.",
                "Fixed confidence/IoU/alpha thresholds are declared heuristics, "
                "not certified readiness thresholds.",
                "Whole-image sRGB RGB metrics and LPIPS include holes/background;"
                " no exposure or pose adjustment on test views.",
                "Depth MAE/RMSE use only finite positive GT/prediction with alpha"
                " >= threshold; completeness is separate.",
                "Means weight each view equally. Infinite exact-match PSNR is "
                "null with an exact-match flag; finite means exclude it.",
                "Class mismatch candidates are spatially matched unmatched boxes,"
                " not verified semantic errors.",
                "No aligned ground-truth mesh; Chamfer and F-score N/A. Coarse "
                "TSDF accuracy is unmeasured.",
            ],
        }
        with (stage / "per_view.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        write_json(stage / "summary.json", summary)
        build_report(stage, summary, views)
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip()
        git_dirty = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True)
        )
        write_json(
            stage / "evaluation.json",
            {
                "schema_version": "1.0",
                "type": "frozen_view_evaluation",
                "created_at": datetime.now(UTC).isoformat(),
                "git_commit": git_commit,
                "git_dirty": git_dirty,
                "source_files_sha256": {
                    p.relative_to(PROJECT_ROOT).as_posix(): sha256_file(p)
                    for p in sorted(
                        [
                            *(PROJECT_ROOT / "src/simready/evaluation").glob("*.py"),
                            PROJECT_ROOT / "workers/perception_worker.py",
                            PROJECT_ROOT / "configs/perception-weights.json",
                        ]
                    )
                },
                "split_sha256": manifest.split_sha256,
                "artifact_sha256": summary["artifact_sha256"],
                "files_sha256": {
                    p.relative_to(stage).as_posix(): sha256_file(p)
                    for p in sorted(stage.rglob("*"))
                    if p.is_file()
                },
            },
        )
        validate_evaluation(stage)
    return output
