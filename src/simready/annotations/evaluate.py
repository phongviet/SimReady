"""COCO AP50 on explicitly approved reference boxes at frozen matched poses."""

import argparse
import copy
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from simready.data.dataset import atomic_dataset, sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import verify_evaluation_binding
from simready.reconstruction.gsplat import load_records
from simready.storage import PROJECT_ROOT


def validate_review(
    coco, approval, *, coco_sha256, manifest_sha256, split_sha256, frame_ids, rules_sha256=None
):
    """Check a supplied review attestation; this function never creates approval."""
    expected = {
        "status": "approved",
        "reviewer_kind": "human",
        "annotations_sha256": coco_sha256,
        "dataset_manifest_sha256": manifest_sha256,
        "split_sha256": split_sha256,
    }
    if rules_sha256 is not None:
        expected["annotation_protocol_sha256"] = rules_sha256
    if any(approval.get(k) != v for k, v in expected.items()):
        raise ValueError("ground-truth evaluation pending: missing/mismatched human approval")
    if not isinstance(approval.get("reviewed_by"), str) or not approval["reviewed_by"].strip():
        raise ValueError("human reviewer identity is required")
    try:
        stamp = datetime.fromisoformat(approval["reviewed_at"])
        if stamp.tzinfo is None:
            raise ValueError("review timestamp requires timezone")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("valid dated human review is required") from exc
    images = coco.get("images", [])
    ids = [im["id"] for im in images]
    names = [im["frame_id"] for im in images]
    if len(set(ids)) != len(ids) or len(set(names)) != len(names) or set(names) != set(frame_ids):
        raise ValueError("COCO images must exactly cover the frozen evaluation frames")
    reviewed = approval.get("reviewed_frame_ids", [])
    if len(reviewed) != len(set(reviewed)) or set(reviewed) != set(frame_ids):
        raise ValueError("all frozen frames require explicit review, including empty frames")
    categories = coco.get("categories", [])
    category_ids = [c["id"] for c in categories]
    if not categories or len(set(category_ids)) != len(category_ids):
        raise ValueError("categories must be nonempty and unique")
    by_id = {im["id"]: im for im in images}
    annotation_ids = set()
    for im in images:
        if (
            type(im["width"]) is not int
            or type(im["height"]) is not int
            or min(im["width"], im["height"]) <= 0
        ):
            raise ValueError("COCO dimensions must be positive integers")
    for ann in coco.get("annotations", []):
        if (
            ann["id"] in annotation_ids
            or ann["image_id"] not in by_id
            or ann["category_id"] not in category_ids
        ):
            raise ValueError("duplicate/dangling COCO annotation")
        annotation_ids.add(ann["id"])
        x, y, w, h = ann["bbox"]
        im = by_id[ann["image_id"]]
        if (
            not np.isfinite([x, y, w, h]).all()
            or min(x, y) < 0
            or min(w, h) <= 0
            or x + w > im["width"]
            or y + h > im["height"]
        ):
            raise ValueError("COCO bounding box lies outside the reference image")
        if ann.get("ignore", False):
            raise ValueError(
                "arbitrary ignore boxes unsupported; declare COCO crowd regions explicitly"
            )
        if ann.get("iscrowd", 0) not in (0, 1):
            raise ValueError("invalid COCO crowd flag")
    return by_id


def coco_ap50(coco, predictions):
    """Official pycocotools bbox matching/101-point interpolation; IoU=.5, maxDets100."""
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    gt = COCO()
    gt.dataset = copy.deepcopy(coco)
    gt.dataset.setdefault("info", {})
    for ann in gt.dataset["annotations"]:
        ann.setdefault("area", ann["bbox"][2] * ann["bbox"][3])
        ann.setdefault("iscrowd", 0)
    gt.createIndex()
    if predictions:
        dt = gt.loadRes(predictions)
    else:
        dt = COCO()
        dt.dataset = {
            "images": copy.deepcopy(coco["images"]),
            "categories": copy.deepcopy(coco["categories"]),
            "annotations": [],
        }
        dt.createIndex()
    evaluator = COCOeval(gt, dt, "bbox")
    evaluator.params.iouThrs = np.array([0.5])
    evaluator.params.maxDets = [1, 10, 100]
    evaluator.evaluate()
    evaluator.accumulate()
    per_class = {}
    for k, category in enumerate(evaluator.params.catIds):
        precision = evaluator.eval["precision"][0, :, k, 0, 2]
        recall = evaluator.eval["recall"][0, k, 0, 2]
        values = precision[precision >= 0]
        per_class[str(category)] = {
            "ap50": float(values.mean()) if len(values) else None,
            "recall_at_100": float(recall) if recall >= 0 else None,
            "reference_instances": sum(
                a["category_id"] == category and not a.get("iscrowd", 0)
                for a in coco["annotations"]
            ),
        }
    aps = [v["ap50"] for v in per_class.values() if v["ap50"] is not None]
    recalls = [v["recall_at_100"] for v in per_class.values() if v["recall_at_100"] is not None]
    misses = []
    tp = fp = 0
    for item in evaluator.evalImgs:
        if item is None or item["aRng"] != evaluator.params.areaRng[0] or item["maxDet"] != 100:
            continue
        selected = np.asarray(item["dtScores"]) >= 0.5
        ignored = np.asarray(item["dtIgnore"])[0]
        matched = np.asarray(item["dtMatches"])[0] > 0
        tp += int((selected & ~ignored & matched).sum())
        fp += int((selected & ~ignored & ~matched).sum())
        matched_gt = set(
            int(x) for x, keep in zip(item["dtMatches"][0], selected, strict=True) if keep and x > 0
        )
        for ann_id, ignore in zip(item["gtIds"], item["gtIgnore"], strict=True):
            if not ignore and ann_id not in matched_gt:
                misses.append(
                    {
                        "image_id": item["image_id"],
                        "category_id": item["category_id"],
                        "annotation_id": int(ann_id),
                    }
                )
    return {
        "ap50": float(np.mean(aps)) if aps else None,
        "recall_at_100": float(np.mean(recalls)) if recalls else None,
        "per_class": per_class,
        "threshold_0_5": {
            "tp": tp,
            "fp": fp,
            "fn": len(misses),
            "recall": tp / (tp + len(misses)) if tp + len(misses) else None,
        },
        "missed_detections": misses,
    }


def evaluate(scene, artifact, renders, evaluation, annotations, approval, output):
    if not approval.is_file():
        raise ValueError("ground-truth evaluation pending_human_review: approval is absent")
    config = EvaluationConfig()
    verify_evaluation_binding(evaluation, scene, artifact, renders, config)
    summary = json.loads((evaluation / "summary.json").read_text())
    if summary["split"] != "test":
        raise ValueError("annotated confirmation requires the frozen test split")
    manifest, frames, splits = load_records(scene, ("test",))
    coco = json.loads(annotations.read_text())
    review = json.loads(approval.read_text())
    by_id = validate_review(
        coco,
        review,
        coco_sha256=sha256_file(annotations),
        manifest_sha256=sha256_file(scene / "manifest.json"),
        split_sha256=manifest.split_sha256,
        frame_ids=splits.test,
        rules_sha256=sha256_file(PROJECT_ROOT / "docs/ANNOTATION_PROTOCOL.md"),
    )
    raw = json.loads((evaluation / "predictions.json").read_text())
    categories = raw["environment"]["categories"]
    for c in coco["categories"]:
        if not 0 < c["id"] < len(categories) or categories[c["id"]] != c["name"]:
            raise ValueError("approved categories differ from fixed detector vocabulary")
    views = {v["frame_id"]: v for v in json.loads((evaluation / "views.json").read_text())}
    native = {f.frame_id: manifest.cameras[f.camera_id] for f in frames}
    reference_hashes = {f.frame_id: f.rgb_sha256 for f in frames}
    resized = copy.deepcopy(coco)
    image_ids = {im["frame_id"]: im["id"] for im in resized["images"]}
    factors = {}
    for im in resized["images"]:
        name = im["frame_id"]
        if im.get("sha256") != reference_hashes[name]:
            raise ValueError("annotation image hash differs from frozen reference")
        camera = views[name]["camera"]
        if (im["width"], im["height"]) != (native[name].width, native[name].height):
            raise ValueError("annotation reference dimensions differ from original camera")
        factors[im["id"]] = (camera["width"] / im["width"], camera["height"] / im["height"])
        im["width"], im["height"] = camera["width"], camera["height"]
    for ann in resized["annotations"]:
        sx, sy = factors[ann["image_id"]]
        x, y, w, h = ann["bbox"]
        ann["bbox"] = [x * sx, y * sy, w * sx, h * sy]
        ann["area"] = w * h * sx * sy
    results = {}
    for domain in ["real", "rendered"]:
        predictions = []
        for view in raw["views"]:
            for det in view[domain]:
                if det["label"] not in {c["id"] for c in coco["categories"]}:
                    continue
                x1, y1, x2, y2 = det["box"]
                predictions.append(
                    {
                        "image_id": image_ids[view["frame_id"]],
                        "category_id": det["label"],
                        "bbox": [x1, y1, x2 - x1, y2 - y1],
                        "score": det["score"],
                    }
                )
        results[domain] = coco_ap50(resized, predictions)
    delta = (
        results["rendered"]["ap50"] - results["real"]["ap50"]
        if results["real"]["ap50"] is not None and results["rendered"]["ap50"] is not None
        else None
    )
    with atomic_dataset(output, 10_000_000) as stage:
        write_json(
            stage / "accuracy.json",
            {
                "status": "evaluated_with_supplied_human_approval",
                "scope": (
                    "Ground-truth bbox accuracy; separate from detector agreement. "
                    "Small correlated sample."
                ),
                "pycocotools": importlib.metadata.version("pycocotools"),
                "iou": 0.5,
                "max_detections": 100,
                "recall_score_threshold": 0.5,
                "classes": coco["categories"],
                "image_count": len(by_id),
                "annotation_count": len(coco["annotations"]),
                "domains": results,
                "delta_ap50": delta,
                "reconstruction_means": summary["means"],
                "annotations_sha256": sha256_file(annotations),
                "approval_sha256": sha256_file(approval),
                "evaluation_sha256": sha256_file(evaluation / "evaluation.json"),
                "split_sha256": manifest.split_sha256,
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["scene", "artifact", "renders", "evaluation", "annotations", "approval", "out"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    evaluate(
        args.scene,
        args.artifact,
        args.renders,
        args.evaluation,
        args.annotations,
        args.approval,
        args.out,
    )
