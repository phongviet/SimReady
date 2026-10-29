"""Custom single-class synthetic detection evaluation against geometry-derived boxes."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from simready.data.bench import mask_box, render_truth
from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.metrics import detection_metrics, iou_matrix
from simready.evaluation.runner import verify_evaluation_binding
from simready.reconstruction.gsplat import load_records
from simready.research.runner import git_state
from simready.research.selection import correlation


def class_accuracy(boxes, predictions, label, threshold=0.5):
    truth = [{"box": box, "label": label, "score": 1.0} for box in boxes]
    predicted = [p for p in predictions if p["label"] == label]
    matched = detection_metrics(truth, predicted, 128, 96, threshold, 0.5)
    tp, fp, fn = matched["matched_count"], matched["appeared_count"], matched["disappeared_count"]
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "error_count": fp + fn,
    }


def ap50(truth, predictions, label):
    """101-point precision-envelope AP; greedy score order; stable frame/index ties."""
    count = sum(len(boxes) for boxes in truth.values())
    if not count:
        return None
    ranked = sorted(
        [
            (-p["score"], frame, i, p)
            for frame, values in predictions.items()
            for i, p in enumerate(values)
            if p["label"] == label
        ],
        key=lambda r: r[:3],
    )
    used = {frame: set() for frame in truth}
    hits = []
    for _, frame, _, prediction in ranked:
        boxes = [{"box": b} for b in truth[frame]]
        overlap = iou_matrix([prediction], boxes)[0] if boxes else np.array([])
        eligible = [j for j in range(len(boxes)) if j not in used[frame] and overlap[j] >= 0.5]
        best = max(eligible, key=lambda j: overlap[j]) if eligible else None
        hits.append(best is not None)
        if best is not None:
            used[frame].add(best)
    if not hits:
        return 0.0
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(tp) + 1)
    recall = tp / count
    return float(
        np.mean(
            [
                precision[recall >= r].max() if np.any(recall >= r) else 0.0
                for r in np.linspace(0, 1, 101)
            ]
        )
    )


def analyze(scene, run, output):
    frozen = json.loads((run / "frozen-inputs.json").read_text())
    for name, key in [
        ("annotations.json", "annotations_sha256"),
        ("geometry.json", "geometry_sha256"),
        ("manifest.json", "manifest_sha256"),
    ]:
        if sha256_file(scene / name) != frozen[key]:
            raise ValueError("frozen truth changed: " + name)
    verify_evaluation_binding(
        run / "evaluation", scene, run / "model", run / "renders", EvaluationConfig()
    )
    manifest, frames, splits = load_records(scene)
    labels = json.loads((scene / "annotations.json").read_text())
    annotations = {a["frame_id"]: a for a in labels["views"]}
    geometry = np.asarray(json.loads((scene / "geometry.json").read_text())["boxes"])
    predictions = json.loads((run / "evaluation/predictions.json").read_text())
    categories = predictions["environment"]["categories"]
    label = categories.index("bench")
    views = json.loads((run / "evaluation/views.json").read_text())
    truth = {}
    rows = []
    frame_map = {f.frame_id: f for f in frames}
    for view in views:
        name = view["frame_id"]
        frame = frame_map[name]
        annotation = annotations[name]
        _, _, expected_mask = render_truth(
            manifest.cameras[frame.camera_id], np.array(frame.T_world_camera), geometry
        )
        mask = np.array(Image.open(local_file(scene, annotation["mask"]))) > 0
        if not np.array_equal(mask, expected_mask) or mask_box(mask) != annotation["box"]:
            raise ValueError("annotation does not reproduce from authored geometry")
        if sha256_file(scene / annotation["mask"]) != annotation["mask_sha256"]:
            raise ValueError("mask changed")
        truth[name] = [annotation["box"]]
    if list(truth) != list(splits.test):
        raise ValueError("labels must cover the exact frozen test set")
    raw = {p["frame_id"]: p for p in predictions["views"]}
    if list(raw) != list(truth):
        raise ValueError("prediction IDs differ from frozen labels")
    for view in views:
        name = view["frame_id"]
        row = {"frame_id": name, **view["metrics"]}
        for domain in ("real", "rendered"):
            row.update(
                {
                    domain + "_" + k: v
                    for k, v in class_accuracy(truth[name], raw[name][domain], label).items()
                }
            )
        row["prediction_disagreement"] = (
            detection_metrics(raw[name]["real"], raw[name]["rendered"], 128, 96)[
                "disappeared_count"
            ]
            + detection_metrics(raw[name]["real"], raw[name]["rendered"], 128, 96)["appeared_count"]
        )
        row["true_error_change"] = row["rendered_error_count"] - row["real_error_count"]
        rows.append(row)
    summary = {
        "schema_version": "1.0",
        "scope": "One authored synthetic bench; six correlated views. No real-domain inference.",
        "metric": "Custom bench-class 101-point AP50; not official COCO mAP.",
        "confidence_threshold": 0.5,
        "iou_threshold": 0.5,
        "label": label,
        "truth_origin": labels["truth_origin"],
        "test_ids": list(truth),
        "domains": {},
        "correlations": {},
        "frozen_inputs": frozen,
        "analysis_source": git_state(),
    }
    for domain in ("real", "rendered"):
        tp = sum(r[domain + "_tp"] for r in rows)
        fp = sum(r[domain + "_fp"] for r in rows)
        fn = sum(r[domain + "_fn"] for r in rows)
        summary["domains"][domain] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn),
            "ap50": ap50(truth, {n: raw[n][domain] for n in truth}, label),
        }
    for metric in ("lpips", "prediction_disagreement"):
        summary["correlations"][metric + "_vs_true_error_change"] = correlation(
            [r[metric] for r in rows], [r["true_error_change"] for r in rows]
        )
    summary["shared_missed_views"] = sum(r["real_fn"] > 0 and r["rendered_fn"] > 0 for r in rows)
    with atomic_dataset(output, 30_000_000) as stage:
        write_json(stage / "summary.json", summary)
        write_json(stage / "per_view.json", {"views": rows})
        with (stage / "per_view.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        canvas = Image.new("RGB", (512, 220 * 3), "white")
        draw = ImageDraw.Draw(canvas)
        for i, index in enumerate((0, 3, 5)):
            name = rows[index]["frame_id"]
            for j, domain in enumerate(("real", "rendered")):
                image = Image.open(run / "evaluation/images" / f"{name}-{domain}.png").convert(
                    "RGB"
                )
                overlay = ImageDraw.Draw(image)
                overlay.rectangle(truth[name][0], outline="lime", width=1)
                for p in raw[name][domain]:
                    if p["label"] == label and p["score"] >= 0.5:
                        overlay.rectangle(p["box"], outline="red", width=1)
                canvas.paste(image.resize((256, 192)), (j * 256, i * 220 + 25))
                draw.text((j * 256 + 4, i * 220 + 4), name + " " + domain, fill="black")
        canvas.save(stage / "comparison.png")
        text = (
            "# Labeled synthetic companion\n\n"
            + summary["scope"]
            + "\n\n"
            + summary["metric"]
            + "\n\n"
            + "Green: geometry truth. Red: bench predictions at confidence ≥0.5.\n\n"
            + "```json\n"
            + json.dumps(summary, indent=2)
            + "\n```\n\n"
            + "Six views contain six observations of one object, not six independent objects. "
            + "Other categories remain in raw predictions, outside this class-only metric. "
            + "Null correlations are undefined. Shared misses, when observed, undermine agreement. "
            + "TUM is unchanged. No human annotation, real-domain accuracy or significance claim.\n"
        )
        (stage / "report.md").write_text(text)
        write_json(
            stage / "analysis.json",
            {
                "files_sha256": {p.name: sha256_file(p) for p in stage.iterdir() if p.is_file()},
                "source_files_sha256": {str(Path(__file__)): sha256_file(Path(__file__))},
            },
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.scene, args.run, args.out), indent=2))
