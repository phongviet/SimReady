"""CPU metrics with explicit empty/invalid semantics and gated one-to-one matches."""

import numpy as np
from scipy.optimize import linear_sum_assignment
from skimage.metrics import structural_similarity


def image_metrics(real: np.ndarray, rendered: np.ndarray) -> dict:
    if real.shape != rendered.shape or real.ndim != 3 or real.shape[2] != 3:
        raise ValueError("RGB pairs must have the same HxWx3 shape")
    if real.dtype != np.uint8 or rendered.dtype != np.uint8 or min(real.shape[:2]) < 7:
        raise ValueError("RGB metrics require uint8 images at least 7 pixels per dimension")
    a, b = real.astype(np.float64) / 255, rendered.astype(np.float64) / 255
    mse = float(np.mean((a - b) ** 2))
    return {
        "rgb_mse": mse,
        # JSON cannot encode infinity. Exact matches are counted separately in summaries.
        "psnr_db": float(-10 * np.log10(mse)) if mse else None,
        "rgb_exact_match": mse == 0,
        "ssim": float(structural_similarity(a, b, data_range=1, channel_axis=-1, win_size=7)),
    }


def depth_metrics(real: np.ndarray, rendered: np.ndarray, alpha: np.ndarray, threshold=0.1):
    if real.shape != rendered.shape or real.shape != alpha.shape or real.ndim != 2:
        raise ValueError("depth/alpha pairs must have the same HxW shape")
    reference = np.isfinite(real) & (real > 0)
    support = reference & np.isfinite(rendered) & (rendered > 0)
    support &= np.isfinite(alpha) & (alpha >= threshold)
    errors = rendered[support].astype(np.float64) - real[support]
    n_ref, n = int(reference.sum()), int(support.sum())
    values = {
        "depth_reference_pixels": n_ref,
        "depth_evaluated_pixels": n,
        "depth_completeness": n / n_ref if n_ref else None,
        "depth_mae_m": float(np.abs(errors).mean()) if n else None,
        "depth_rmse_m": float(np.sqrt(np.mean(errors**2))) if n else None,
    }
    return values, support


def iou_matrix(left: list[dict], right: list[dict]) -> np.ndarray:
    if not left or not right:
        return np.zeros((len(left), len(right)))
    a, b = (
        np.array([p["box"] for p in left], dtype=float),
        np.array([p["box"] for p in right], dtype=float),
    )
    intersection = np.maximum(
        0, np.minimum(a[:, None, 2:], b[None, :, 2:]) - np.maximum(a[:, None, :2], b[None, :, :2])
    ).prod(axis=2)
    area_a = np.maximum(0, a[:, 2:] - a[:, :2]).prod(axis=1)
    area_b = np.maximum(0, b[:, 2:] - b[:, :2]).prod(axis=1)
    union = area_a[:, None] + area_b[None, :] - intersection
    return np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)


def gated_pairs(ious: np.ndarray, allowed: np.ndarray) -> list[tuple[int, int]]:
    if not ious.size:
        return []
    # Maximizes cardinality first, total IoU second. Invalid pairs cannot steal valid matches.
    bonus = min(ious.shape) + 1
    rows, cols = linear_sum_assignment(np.where(allowed, bonus + ious, 0), maximize=True)
    return [(int(i), int(j)) for i, j in zip(rows, cols, strict=True) if allowed[i, j]]


def detection_metrics(
    real: list[dict], rendered: list[dict], width: int, height: int, confidence=0.5, iou_gate=0.5
) -> dict:
    for prediction in real + rendered:
        box = np.asarray(prediction["box"])
        if (
            box.shape != (4,)
            or not np.isfinite(box).all()
            or np.any(box[2:] <= box[:2])
            or not 0 <= prediction["score"] <= 1
            or type(prediction["label"]) is not int
        ):
            raise ValueError("invalid detector prediction")
    a = [p for p in real if p["score"] >= confidence]
    b = [p for p in rendered if p["score"] >= confidence]
    ious = iou_matrix(a, b)
    labels = np.array([[p["label"] == q["label"] for q in b] for p in a], dtype=bool)
    labels = labels.reshape(ious.shape)
    pairs = gated_pairs(ious, (ious >= iou_gate) & labels)
    used_a, used_b = {i for i, _ in pairs}, {j for _, j in pairs}
    missing, appeared = (
        [i for i in range(len(a)) if i not in used_a],
        [j for j in range(len(b)) if j not in used_b],
    )
    unmatched_iou = ious[np.ix_(missing, appeared)]
    mismatch = gated_pairs(
        unmatched_iou, (unmatched_iou >= iou_gate) & ~labels[np.ix_(missing, appeared)]
    )
    matches = []
    for i, j in pairs:
        center_a = (np.array(a[i]["box"][:2]) + a[i]["box"][2:]) / 2
        center_b = (np.array(b[j]["box"][:2]) + b[j]["box"][2:]) / 2
        matches.append(
            {
                "real_index": i,
                "rendered_index": j,
                "label": a[i]["label"],
                "iou": float(ious[i, j]),
                "center_error_normalized": float(
                    np.linalg.norm((center_a - center_b) / [width, height])
                ),
                "confidence_gap": float(b[j]["score"] - a[i]["score"]),
            }
        )
    per_class = {}
    for label in sorted({p["label"] for p in a + b}):
        per_class[str(label)] = {
            "real": sum(p["label"] == label for p in a),
            "rendered": sum(p["label"] == label for p in b),
            "matched": sum(m["label"] == label for m in matches),
        }
    return {
        "real_count": len(a),
        "rendered_count": len(b),
        "matched_count": len(pairs),
        "disappeared_count": len(missing),
        "appeared_count": len(appeared),
        "count_gap": len(b) - len(a),
        "mean_confidence_real": float(np.mean([p["score"] for p in a])) if a else None,
        "mean_confidence_rendered": float(np.mean([p["score"] for p in b])) if b else None,
        "mean_matched_iou": float(np.mean([m["iou"] for m in matches])) if matches else None,
        "mean_center_error_normalized": float(
            np.mean([m["center_error_normalized"] for m in matches])
        )
        if matches
        else None,
        "mean_confidence_gap": float(np.mean([m["confidence_gap"] for m in matches]))
        if matches
        else None,
        "class_mismatch_candidates": [
            {
                "real_index": missing[i],
                "rendered_index": appeared[j],
                "iou": float(unmatched_iou[i, j]),
            }
            for i, j in mismatch
        ],
        "real": a,
        "rendered": b,
        "matches": matches,
        "unmatched_real_indices": missing,
        "unmatched_rendered_indices": appeared,
        "per_class": per_class,
        "empty_both": not a and not b,
    }
