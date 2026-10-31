"""Post-run acceptance replay. Read-only toward all training/evaluation outputs.

Run: uv run --frozen python docs/evidence/reconstruction-quality-1/replay.py
LPIPS network inference is NOT repeated: its saved per-view values are aggregated.
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.dataset import sha256_file, write_json
from simready.evaluation.metrics import depth_metrics, detection_metrics, image_metrics
from simready.research.quality import SEEDS, digest, select_validation, verify_protocol
from simready.storage import PROJECT_ROOT, check_budget


def replay(root, output):
    if output.exists():
        raise ValueError("replay output exists; use a new filename")
    check_budget(30_000_000)
    protocol = verify_protocol(root)
    selection_path = root / "analysis/selection.json"
    selection = json.loads(selection_path.read_text())
    rows = selection["candidates"]
    assert len(rows) == 67 and digest(rows) == selection["candidates_sha256"]
    scene = Path(protocol["scene"])
    manifest = json.loads((scene / "manifest.json").read_text())
    records = {
        f["frame_id"]: f for f in map(json.loads, (scene / "frames.jsonl").read_text().splitlines())
    }
    splits = json.loads((scene / "splits.json").read_text())
    allowed = set(splits["validation"])
    for observation in protocol["allowed_observations"].values():
        for kind in ("rgb", "depth"):
            path = observation[f"{kind}_path"]
            if path:
                assert sha256_file(scene / path) == observation[f"{kind}_sha256"]
    pairs = 0
    gt_cache = {}
    for row in rows:
        report = root / row["report"]
        summary = json.loads((report / "summary.json").read_text())
        views = json.loads((report / "views.json").read_text())
        predictions = json.loads((report / "predictions.json").read_text())
        predicted = {v["frame_id"]: v for v in predictions["views"]}
        assert summary["split"] == "validation" and {v["frame_id"] for v in views} == allowed
        assert len(views) == 16 and len(predicted) == 16
        means = {key: [] for key in summary["means"]}
        for view in views:
            name = view["frame_id"]
            width, height = view["camera"]["width"], view["camera"]["height"]
            cache_key = name, width, height
            if cache_key not in gt_cache:
                frame = records[name]
                with Image.open(scene / frame["rgb_path"]) as image:
                    rgb = np.asarray(
                        image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
                    )
                with Image.open(scene / frame["depth_path"]) as image:
                    raw = np.asarray(
                        image.resize((width, height), Image.Resampling.NEAREST)
                    ).astype(np.float32)
                depth = np.where(
                    (raw != manifest["depth"]["invalid_value"]) & (raw > 0),
                    raw * manifest["depth"]["meters_per_unit"],
                    np.nan,
                )
                gt_cache[cache_key] = rgb, depth
            reference, gt_depth = gt_cache[cache_key]
            with Image.open(report / view["assets"]["real"]) as image:
                np.testing.assert_array_equal(reference, np.asarray(image))
            with Image.open(report / view["assets"]["rendered"]) as image:
                metrics = image_metrics(reference, np.asarray(image))
            renders = report.parent / "renders"
            depth, _ = depth_metrics(
                gt_depth,
                np.load(renders / f"{name}-depth.npy", allow_pickle=False),
                np.load(renders / f"{name}-alpha.npy", allow_pickle=False),
                protocol["evaluation"]["depth_alpha_threshold"],
            )
            metrics.update(depth)
            metrics["lpips"] = predicted[name]["lpips"]
            for key, value in metrics.items():
                saved = view["metrics"][key]
                if value is None:
                    assert saved is None
                else:
                    assert np.isclose(value, saved, rtol=0, atol=1e-12), (row["run"], name, key)
            detection = detection_metrics(
                predicted[name]["real"],
                predicted[name]["rendered"],
                width,
                height,
                protocol["evaluation"]["confidence_threshold"],
                protocol["evaluation"]["match_iou_threshold"],
            )
            assert detection == view["detection"]
            for key in means:
                if metrics[key] is not None:
                    means[key].append(metrics[key])
            pairs += 1
        for key, values in means.items():
            value = float(np.mean(values)) if values else None
            if value is None:
                assert summary["means"][key] is row[key] is None
            else:
                assert np.isclose(value, summary["means"][key], rtol=0, atol=1e-12)
                assert np.isclose(value, row[key], rtol=0, atol=1e-12)
    chosen = {
        str(seed): select_validation(
            [r for r in rows if r["seed"] == seed and r["arm"] not in ("reference", "baseline")],
            protocol["split_sha256"],
            16,
        )
        for seed in SEEDS
    }
    assert chosen == selection["selected"]
    comparisons = []
    for seed in SEEDS:
        a = next(r for r in rows if r["run"] == f"control-s{seed}" and r["step"] == 1200)
        b = next(r for r in rows if r["run"] == f"baseline-s{seed}")
        delta = {k: a[k] - b[k] for k in ("lpips", "psnr_db")}
        comparisons.append(
            {
                "seed": seed,
                "comparison": "trajectory1200 minus independent1200",
                "delta": delta,
                "discrepancy_flag": abs(delta["lpips"]) > 0.03 or abs(delta["psnr_db"]) > 0.5,
            }
        )
    stages = {f.name: json.loads(f.read_text()) for f in (root / "ledger").glob("*.json")}
    assert len(stages) == 91 and all(r["status"] == "complete" for r in stages.values())
    first = min(datetime.fromisoformat(r["started_utc"]) for r in stages.values())
    last = max(
        datetime.fromisoformat(r["started_utc"]) + timedelta(seconds=r["seconds"])
        for r in stages.values()
    )
    models = [json.loads(f.read_text())["worker"] for f in root.glob("*-s*/model/artifact.json")]
    assert len(models) == 24 and sum(m["iterations"] for m in models) == 79200
    result = {
        "type": "post_run_acceptance_replay",
        "study_id": root.name,
        "training_source_commit": protocol["git_commit"],
        "verifier_sha256": sha256_file(Path(__file__)),
        "protocol_sha256": sha256_file(root / "protocol.json"),
        "selection_sha256": sha256_file(selection_path),
        "historical_files_verified": len(protocol["historical_sha256"]),
        "allowed_observation_files_verified": sum(
            1
            for o in protocol["allowed_observations"].values()
            for k in ("rgb_path", "depth_path")
            if o[k]
        ),
        "training_runs": 24,
        "updates": 79200,
        "evaluations": 67,
        "view_pairs_replayed": pairs,
        "stages_complete": 91,
        "failed_stages": 0,
        "stage_span_seconds": (last - first).total_seconds(),
        "optimization_seconds_sum": sum(m["optimization_seconds"] for m in models),
        "checkpoint_io_seconds_sum": sum(m["checkpoint_seconds"] for m in models),
        "peak_training_allocated_bytes": max(m["peak_vram_allocated_bytes"] for m in models),
        "peak_training_reserved_bytes": max(m["peak_vram_reserved_bytes"] for m in models),
        "baseline_comparisons_all_seeds": comparisons,
        "lpips_scope": (
            "Saved per-view network values and aggregation replayed; inference not rerun."
        ),
        "image_depth_detection_scope": (
            "All pairs recomputed from frozen validation GT and saved predictions."
        ),
        "ledger_sha256": {name: sha256_file(root / "ledger" / name) for name in stages},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    check_budget()
    print(json.dumps({k: v for k, v in result.items() if k != "ledger_sha256"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--study", type=Path, default=PROJECT_ROOT / "experiments/reconstruction-quality-1"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT
        / "experiments/reconstruction-quality-1/verification/replay-result.json",
    )
    args = parser.parse_args()
    replay(args.study, args.out)
