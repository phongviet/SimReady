"""Recompute frozen-study checks and report paired, descriptive case-study results."""

import csv
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.evaluation.metrics import depth_metrics, detection_metrics, image_metrics
from simready.evaluation.readiness import pose_diagnostics
from simready.evaluation.runner import validate_evaluation, verify_inputs
from simready.reconstruction.gsplat import load_records, validate_artifact, validate_renders
from simready.research.contracts import StudyConfig
from simready.research.runner import git_state, now, pose_features
from simready.research.selection import (
    calibrate,
    correlation,
    json_digest,
    select_farthest,
    select_random,
    select_risk,
    validate_seal,
)
from simready.storage import PROJECT_ROOT, check_budget

METRICS = ("lpips", "psnr_db", "ssim", "depth_mae_m", "depth_rmse_m", "depth_completeness")
COUNT_KEYS = (
    "real_count",
    "rendered_count",
    "matched_count",
    "disappeared_count",
    "appeared_count",
)


def read(path: Path):
    return json.loads(path.read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("study verification failed: " + message)


def unmatched_fraction(detection: dict) -> float | None:
    denominator = detection["real_count"] + detection["rendered_count"]
    return (
        (detection["disappeared_count"] + detection["appeared_count"]) / denominator
        if denominator
        else None
    )


def describe(values) -> dict:
    finite = [float(x) for x in values if x is not None and np.isfinite(x)]
    return {
        "n": len(finite),
        "values": finite,
        "mean": float(np.mean(finite)) if finite else None,
        "sample_sd": float(np.std(finite, ddof=1)) if len(finite) > 1 else None,
        "min": min(finite) if finite else None,
        "max": max(finite) if finite else None,
    }


def replay_view(
    scene: Path,
    renders: Path,
    root: Path,
    view: dict,
    prediction: dict,
    frame,
    manifest,
    config: dict,
) -> None:
    assets = view["assets"]
    with Image.open(root / assets["real"]) as image:
        a = np.array(image)
    with Image.open(root / assets["rendered"]) as image:
        b = np.array(image)
    expected = image_metrics(a, b)
    expected["lpips"] = float(prediction["lpips"])
    with Image.open(local_file(scene, frame.depth_path)) as image:
        raw = np.array(image.resize((a.shape[1], a.shape[0]), Image.Resampling.NEAREST)).astype(
            np.float32
        )
    reference = np.where(
        (raw > 0) & (raw != manifest.depth.invalid_value),
        raw * manifest.depth.meters_per_unit,
        np.nan,
    )
    depth, _ = depth_metrics(
        reference,
        np.load(renders / f"{frame.frame_id}-depth.npy", allow_pickle=False),
        np.load(renders / f"{frame.frame_id}-alpha.npy", allow_pickle=False),
        config["depth_alpha_threshold"],
    )
    expected.update(depth)
    for key, value in expected.items():
        measured = view["metrics"][key]
        require(
            (value is None and measured is None)
            or (
                value is not None
                and measured is not None
                and np.isclose(value, measured, atol=1e-10, rtol=1e-8)
            ),
            f"replayed {key} differs for {frame.frame_id}",
        )
    detection = detection_metrics(
        prediction["real"],
        prediction["rendered"],
        a.shape[1],
        a.shape[0],
        config["confidence_threshold"],
        config["match_iou_threshold"],
    )
    require(detection == view["detection"], f"detection matching differs for {frame.frame_id}")


def inspect(study: Path) -> dict:
    """Deterministic checks only; this does not manufacture a semantic review verdict."""
    protocol, curation = read(study / "protocol.json"), read(study / "curation.json")
    config = StudyConfig.model_validate(protocol["study"])
    seal = validate_seal(study)
    source = read(study / "run-source.json")
    require(curation["protocol_sha256"] == json_digest(protocol), "curation protocol")
    for name, digest in source["source_files_sha256"].items():
        raw = subprocess.check_output(
            ["git", "show", f"{source['git']['commit']}:{name}"], cwd=PROJECT_ROOT
        )
        import hashlib

        require(hashlib.sha256(raw).hexdigest() == digest, "recorded source pin " + name)
    require(not source["git"]["dirty"], "dirty experiment source")
    stages = read(study / "stages.json")
    expected_stages = set()
    for seed in config.seeds:
        for method in config.methods:
            key = f"{method}-s{seed}"
            expected_stages.update(
                {"train-" + key, "render-" + key + "-test", "eval-" + key + "-test"}
            )
        expected_stages.update(
            {
                f"render-base-s{seed}-validation",
                f"eval-base-s{seed}-validation",
                f"render-base-s{seed}-candidate",
            }
        )
    require(set(stages["stages"]) == expected_stages, "incomplete or extra stage matrix")
    for entry in stages["stages"].values():
        require(json_digest(entry["inputs"]) == entry["inputs_sha256"], "stage input digest")
        directory = study / entry["output"]
        require(directory.resolve().is_relative_to(study.resolve()), "stage path escapes study")
        path = local_file(directory, entry["manifest"])
        require(sha256_file(path) == entry["manifest_sha256"], "stage manifest changed")
        if entry["manifest"] == "artifact.json":
            validate_artifact(directory)
        elif entry["manifest"] == "renders.json":
            validate_renders(directory)
        elif entry["manifest"] == "evaluation.json":
            validate_evaluation(directory)
    ledger = read(study / "access-ledger.json")["events"]
    phases = [event["phase"] for event in ledger]
    require(phases.count("all_selections_sealed") == 1, "selection sealing event")
    seal_index = phases.index("all_selections_sealed")
    require(
        all(i > seal_index for i, p in enumerate(phases) if p.endswith("release")),
        "release recorded before all selections",
    )
    releases = {e["selection_key"]: e["ids"] for e in ledger if e["phase"] == "candidate_release"}
    require(releases == {r.key: list(r.selected_ids) for r in seal.acquisitions}, "release matrix")
    _, frames, partition = load_records(study / "base-dataset", ())
    frame_map = {f.frame_id: f for f in frames}
    training = np.array([frame_map[n].T_world_camera for n in partition.train])
    test_ids = list(partition.test)
    queried = np.array([frame_map[n].T_world_camera for n in test_ids])
    diagnostics = dict(zip(test_ids, pose_diagnostics(training, queried), strict=True))
    selections = {row.key: list(row.selected_ids) for row in seal.acquisitions}
    calibration_rows = []
    for seed in config.seeds:
        base = study / "base-dataset"
        validation = study / "evaluations" / f"base-s{seed}-validation"
        validation_renders = study / "renders" / f"base-s{seed}-validation"
        verify_inputs(base, study / "models" / f"base-s{seed}", validation_renders)
        vfeatures = pose_features(base, validation_renders, "validation")
        vviews = read(validation / "views.json")
        fitted = calibrate(
            vfeatures,
            [v["metrics"]["lpips"] for v in vviews],
            config.validation_fit_frames,
            config.ridge_penalty,
        )
        cfeatures = pose_features(base, study / "renders" / f"base-s{seed}-candidate", "candidate")
        chosen, ranking = select_risk(cfeatures, fitted, config.additional_observations)
        require(chosen == selections[f"risk-s{seed}"], "risk selection replay")
        require(
            select_random(list(partition.candidate), config.additional_observations, seed)
            == selections[f"random-s{seed}"],
            "random selection replay",
        )
        farthest = select_farthest(
            training[:, :3, 3],
            list(partition.candidate),
            np.array([frame_map[n].T_world_camera for n in partition.candidate])[:, :3, 3],
            config.additional_observations,
        )
        require(farthest == selections[f"farthest-s{seed}"], "farthest selection replay")
        for method in ("risk", "random", "farthest"):
            details = read(study / "selection" / f"{method}-s{seed}.json")
            require(
                details["calibration"] == fitted and details["risk_ranking"] == ranking,
                "calibration or risk feature replay",
            )
        calibration_rows.append({"seed": seed, **fitted})
    rows, runs, raw_predictions = [], [], {"real": [], "rendered": []}
    reference_observations, reference_cameras, reference_predictions = None, None, None
    reference_environment = None
    for method in config.methods:
        for seed in config.seeds:
            key = f"{method}-s{seed}"
            dataset = study / ("base-dataset" if method == "base" else "datasets/" + key)
            artifact, renders = study / "models" / key, study / "renders" / (key + "-test")
            root = study / "evaluations" / (key + "-test")
            manifest, current_frames, splits, selected, cameras, model, _ = verify_inputs(
                dataset, artifact, renders
            )
            expected_train = set(partition.train) | set(selections.get(key, []))
            require(
                set(splits.train) == expected_train and not (expected_train & set(test_ids)),
                "training IDs " + key,
            )
            require(list(splits.test) == test_ids, "test IDs " + key)
            require(
                model["config"] == protocol["reconstruction"] | {"seed": seed},
                "compute budget " + key,
            )
            require(model["worker"]["iterations"] == 1200, "actual training steps " + key)
            require(
                model["git_commit"] == source["git"]["commit"] and not model["git_dirty"],
                "training source " + key,
            )
            # Validate observations after completion; remaining candidates must stay absent.
            load_records(dataset, ("train", "validation", "test"))
            for frame in current_frames:
                if frame.frame_id in splits.candidate:
                    require(
                        not (dataset / frame.rgb_path).exists()
                        and not (dataset / frame.depth_path).exists(),
                        "unselected candidate pixels in learner " + key,
                    )
            observations = read(root / "inputs.json")["observations"]
            summary, views, predictions = (
                read(root / "summary.json"),
                read(root / "views.json"),
                read(root / "predictions.json"),
            )
            evaluation = read(root / "evaluation.json")
            require(summary["protocol"] == protocol["evaluation"], "detector/metric config " + key)
            if reference_environment is None:
                reference_environment = summary["environment"]
            require(summary["environment"] == reference_environment, "inference environment " + key)
            require(
                evaluation["git_commit"] == source["git"]["commit"] and not evaluation["git_dirty"],
                "evaluation source " + key,
            )
            require(
                [v["frame_id"] for v in views] == test_ids
                and [v["frame_id"] for v in predictions["views"]] == test_ids,
                "complete test measurements " + key,
            )
            real_predictions = [v["real"] for v in predictions["views"]]
            if reference_observations is None:
                reference_observations, reference_cameras, reference_predictions = (
                    observations,
                    cameras,
                    real_predictions,
                )
            require(
                observations == reference_observations and cameras == reference_cameras,
                "unpaired test references " + key,
            )
            require(
                real_predictions == reference_predictions,
                "changed real detector predictions " + key,
            )
            for i, (view, prediction, frame) in enumerate(
                zip(views, predictions["views"], selected, strict=True)
            ):
                replay_view(
                    dataset,
                    renders,
                    root,
                    view,
                    prediction,
                    frame,
                    manifest,
                    protocol["evaluation"],
                )
                detection = view["detection"]
                row = {
                    "run": key,
                    "method": method,
                    "seed": seed,
                    "frame_id": frame.frame_id,
                    "pose_block": i // (len(test_ids) // config.pose_blocks) + 1,
                    "distance_m": diagnostics[frame.frame_id]["distance_m"],
                    "rotation_deg": diagnostics[frame.frame_id]["minimum_rotation_deg"],
                    **view["metrics"],
                    **{name: detection[name] for name in COUNT_KEYS},
                    "unmatched_fraction": unmatched_fraction(detection),
                    "unmatched_count": detection["disappeared_count"] + detection["appeared_count"],
                }
                rows.append(row)
                for domain in raw_predictions:
                    raw_predictions[domain].append(
                        {"run": key, "frame_id": frame.frame_id, "predictions": prediction[domain]}
                    )
            means = {
                metric: describe(v["metrics"][metric] for v in views)["mean"] for metric in METRICS
            }
            for metric in METRICS:
                require(
                    np.isclose(means[metric], summary["means"][metric], atol=1e-12),
                    "summary replay " + key,
                )
            subset = [r for r in rows if r["run"] == key]
            means["unmatched_fraction"] = describe(r["unmatched_fraction"] for r in subset)["mean"]
            means["unmatched_count"] = describe(r["unmatched_count"] for r in subset)["mean"]
            totals = {name: sum(v["detection"][name] for v in views) for name in COUNT_KEYS}
            require(
                all(totals[name] == summary["detection_totals"][name] for name in COUNT_KEYS),
                "count totals " + key,
            )
            runs.append(
                {
                    "run": key,
                    "method": method,
                    "seed": seed,
                    "train_frames": len(splits.train),
                    "test_frames": len(test_ids),
                    "means": means,
                    "detection_totals": totals,
                    "gaussians": model["worker"]["final_gaussians"],
                    "training_seconds": model["worker"]["training_seconds"],
                    "peak_vram_allocated_bytes": model["worker"]["peak_vram_allocated_bytes"],
                    "peak_vram_reserved_bytes": model["worker"]["peak_vram_reserved_bytes"],
                    "artifact_sha256": sha256_file(artifact / "artifact.json"),
                    "evaluation_sha256": sha256_file(root / "evaluation.json"),
                    "split_sha256": manifest.split_sha256,
                }
            )
    return {
        "protocol": protocol,
        "curation": curation,
        "source": source,
        "stages": stages,
        "rows": rows,
        "runs": runs,
        "raw_predictions": raw_predictions,
        "calibration": calibration_rows,
        "selections": selections,
        "environment": {"training": model["worker"], "evaluation": summary["environment"]},
        "checks": {
            "complete_stage_matrix": len(expected_stages),
            "all_content_hashes": True,
            "recorded_release_order": True,
            "selection_replay": True,
            "common_test_observations_and_cameras": True,
            "identical_real_predictions": True,
            "rgb_depth_matching_replayed": len(rows),
            "frozen_equal_training_configs": True,
            "source_matches_recorded_git_objects": True,
        },
    }


def aggregate(rows: list[dict], runs: list[dict], config: StudyConfig) -> dict:
    metrics = (*METRICS, "unmatched_fraction", "unmatched_count")
    methods = {
        method: {
            metric: describe(r["means"][metric] for r in runs if r["method"] == method)
            for metric in metrics
        }
        for method in config.methods
    }
    by_key = {r["run"]: r for r in runs}
    paired = {
        metric: describe(
            by_key[f"risk-s{s}"]["means"][metric] - by_key[f"random-s{s}"]["means"][metric]
            for s in config.seeds
            if by_key[f"risk-s{s}"]["means"][metric] is not None
            and by_key[f"random-s{s}"]["means"][metric] is not None
        )
        for metric in metrics
    }
    relative = {}
    for method in config.methods:
        relative[method] = {}
        for metric in METRICS:
            base, value = methods["base"][metric]["mean"], methods[method][metric]["mean"]
            sign = -1 if metric in ("lpips", "depth_mae_m", "depth_rmse_m") else 1
            relative[method][metric] = 100 * sign * (value - base) / abs(base) if base else None
    correlations, bins, blocks, inversions = [], [], [], []
    for run in runs:
        subset = [r for r in rows if r["run"] == run["run"]]
        for image_metric in ("psnr_db", "ssim", "lpips"):
            for task_metric in ("unmatched_fraction", "unmatched_count"):
                pairs = [
                    (r[image_metric], r[task_metric])
                    for r in subset
                    if r[image_metric] is not None and r[task_metric] is not None
                ]
                correlations.append(
                    {
                        "run": run["run"],
                        "image_metric": image_metric,
                        "task_metric": task_metric,
                        "n": len(pairs),
                        **correlation([a for a, _ in pairs], [b for _, b in pairs]),
                    }
                )
        for dimension, edges in (
            ("distance_m", config.distance_bin_edges_m),
            ("rotation_deg", config.rotation_bin_edges_deg),
        ):
            for low, high in zip(edges[:-1], edges[1:], strict=True):
                members = [r for r in subset if low <= r[dimension] < high]
                bins.append(
                    {
                        "run": run["run"],
                        "method": run["method"],
                        "seed": run["seed"],
                        "dimension": dimension,
                        "low": low,
                        "high": high,
                        "views": len(members),
                        "means": {m: describe(r[m] for r in members)["mean"] for m in metrics},
                    }
                )
        for block in range(1, config.pose_blocks + 1):
            members = [r for r in subset if r["pose_block"] == block]
            blocks.append(
                {
                    "run": run["run"],
                    "block": block,
                    "views": len(members),
                    "means": {m: describe(r[m] for r in members)["mean"] for m in metrics},
                }
            )
        for a in subset:
            for b in subset:
                if (
                    a["lpips"] < b["lpips"]
                    and a["unmatched_fraction"] is not None
                    and b["unmatched_fraction"] is not None
                    and a["unmatched_fraction"] > b["unmatched_fraction"]
                ):
                    inversions.append(
                        {
                            "run": run["run"],
                            "better_image_frame": a["frame_id"],
                            "worse_image_frame": b["frame_id"],
                            "lpips_better": a["lpips"],
                            "lpips_worse": b["lpips"],
                            "task_better_image": a["unmatched_fraction"],
                            "task_worse_image": b["unmatched_fraction"],
                        }
                    )
    inversions.sort(
        key=lambda r: (
            -(r["task_better_image"] - r["task_worse_image"]),
            r["run"],
            r["better_image_frame"],
        )
    )
    return {
        "methods": methods,
        "paired_risk_minus_random": paired,
        "relative_improvement_percent_vs_base": relative,
        "correlations": correlations,
        "novelty_bins": bins,
        "pose_blocks": blocks,
        "ranking_counterexamples": inversions[:12],
    }


def validate_analysis(root: Path) -> dict:
    metadata = read(local_file(root, "analysis.json"))
    require(
        metadata.get("type") == "recapture_case_study" and metadata.get("schema_version") == "1.0",
        "analysis contract",
    )
    required = {
        "metrics_summary.json",
        "per_view.csv",
        "runs.csv",
        "predictions_real.jsonl",
        "predictions_rendered.jsonl",
        "report.md",
        "report.html",
        "checks.json",
        "config.yaml",
        "environment.json",
        "git_commit.txt",
        "dataset_and_split_hash.json",
    }
    require(required.issubset(metadata["files_sha256"]), "required benchmark output files")
    for name, digest in metadata["files_sha256"].items():
        require(sha256_file(local_file(root, name)) == digest, "analysis content changed: " + name)
    return metadata


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(study: Path, output: Path) -> Path:
    data = inspect(study)
    config = StudyConfig.model_validate(data["protocol"]["study"])
    summary = aggregate(data["rows"], data["runs"], config)
    summary.update(
        schema_version="1.0",
        scope="One real TUM capture, three paired seeds, 18 correlated test views.",
        run_count=len(data["runs"]),
        runs=data["runs"],
        seeds=list(config.seeds),
        calibration=data["calibration"],
        selections=data["selections"],
        detection_accuracy={
            "value": None,
            "reason": "No labeled object GT for TUM; agreement is not accuracy.",
        },
        source=data["protocol"]["curator_source"],
        analysis_source=git_state(),
        timing={
            "known_stage_wall_seconds_sum": sum(
                v["wall_seconds"]
                for v in data["stages"]["stages"].values()
                if v["wall_seconds"] is not None
            ),
            "missing_stage_timings": sum(
                v["wall_seconds"] is None for v in data["stages"]["stages"].values()
            ),
            "training_loop_seconds_sum": sum(r["training_seconds"] for r in data["runs"]),
            "note": (
                "Recorded sequential stages; PyTorch allocator peaks are not total device VRAM."
            ),
        },
        limitations=data["curation"]["metadata"]["limitations"]
        + [
            "Three paired seeds vary optimization and random acquisition jointly; "
            "not across-scene uncertainty.",
            "Sample SD describes seed-level means; no independent-frame CI or significance test.",
            "Detector counts depend on visibility and model errors; normalized discrepancy "
            "uses prediction counts, not GT.",
            "E2 bins use the common original50training poses, even for recaptured models; "
            "empty bins are null.",
            "Same steps/resolution/caps; final Gaussian counts and measured runtime can differ.",
            "No ground-truth object accuracy or geometric Chamfer/F-score measurement.",
            "Post-hoc failure figures are diagnostic selections, not additional tuning data.",
        ],
    )
    audit_path = study / "experiment-audit.json"
    summary["semantic_audit"] = (
        read(audit_path)
        if audit_path.exists()
        else {
            "status": "unavailable",
            "verdict": None,
            "reason": "Fresh review not completed; no semantic PASS.",
        }
    )
    with atomic_dataset(output, 300_000_000) as stage:
        write_json(stage / "metrics_summary.json", summary)
        write_json(stage / "experiment-audit.json", summary["semantic_audit"])
        write_json(
            stage / "checks.json",
            {
                "checks": data["checks"],
                "scope": "Deterministic replay; not independent semantic review.",
            },
        )
        write_json(stage / "config.yaml", data["protocol"])  # JSON is a valid YAML1.2 document.
        write_json(stage / "environment.json", data["environment"])
        (stage / "git_commit.txt").write_text(data["source"]["git"]["commit"] + "\n")
        write_json(
            stage / "dataset_and_split_hash.json",
            {
                "curation_sha256": sha256_file(study / "curation.json"),
                "selection_seal_sha256": sha256_file(study / "selections-sealed.json"),
                "test_observations": [
                    {k: f[k] for k in ("frame_id", "rgb_sha256", "depth_sha256", "T_world_camera")}
                    for f in data["curation"]["frames"]
                    if f["frame_id"] in data["curation"]["partitions"]["test"]
                ],
                "runs": [
                    {
                        k: r[k]
                        for k in ("run", "artifact_sha256", "evaluation_sha256", "split_sha256")
                    }
                    for r in data["runs"]
                ],
            },
        )
        write_csv(stage / "per_view.csv", data["rows"])
        write_csv(
            stage / "runs.csv",
            [
                {k: v for k, v in r.items() if k not in ("means", "detection_totals")}
                | r["means"]
                | r["detection_totals"]
                for r in data["runs"]
            ],
        )
        for domain, rows in data["raw_predictions"].items():
            (stage / f"predictions_{domain}.jsonl").write_text(
                "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows)
            )
        from simready.research.figures import failure_montage, plots, report

        plots(stage, summary, data["rows"], config)
        failure_montage(study, stage, data["rows"], config)
        report(stage, summary)
        write_json(
            stage / "analysis.json",
            {
                "schema_version": "1.0",
                "type": "recapture_case_study",
                "created_at": now(),
                "source_study": study.name,
                "analysis_source": git_state(),
                "storage_bytes": check_budget(),
                "source_files_sha256": {
                    p.relative_to(PROJECT_ROOT).as_posix(): sha256_file(p)
                    for p in (Path(__file__), Path(__file__).with_name("figures.py"))
                },
                "files_sha256": {
                    p.relative_to(stage).as_posix(): sha256_file(p)
                    for p in sorted(stage.rglob("*"))
                    if p.is_file()
                },
            },
        )
        validate_analysis(stage)
    return output
