"""Export every frozen confirmation/densification measurement, including failures."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from run_improvement_studies import ROOT, verify

from simready.data.dataset import sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import verify_evaluation_binding
from simready.reconstruction.gsplat import validate_artifact
from simready.storage import check_budget


def analyze(root, output):
    if output.exists():
        raise ValueError("analysis output exists; preserve it and use a new export path")
    p = verify(root)
    rows = []
    missing = []
    failures = []
    for study in p["study_order"]:
        child = p["studies"][study]
        scene = Path(child["scene"])
        for run, item in child["runs"].items():
            model = root / study / run / "model"
            config = item["config"]
            steps = config["checkpoint_steps"] or [config["iterations"]]
            for n in steps:
                evaluation = root / study / run / f"step-{n}" / "evaluation"
                if not evaluation.exists():
                    missing.append({"study": study, "run": run, "step": n, "status": "unmeasured"})
                    continue
                artifact = (
                    model / "checkpoints" / f"step_{n:06d}" if config["checkpoint_steps"] else model
                )
                verify_evaluation_binding(
                    evaluation,
                    scene,
                    artifact,
                    evaluation.parent / "renders",
                    EvaluationConfig.model_validate(p["evaluation"]),
                )
                summary = json.loads((evaluation / "summary.json").read_text())
                if summary["split"] != child["evaluation_split"] or summary["view_count"] != len(
                    child["evaluation_frames"]
                ):
                    raise ValueError("measurement differs from complete declared split")
                worker = validate_artifact(artifact)["worker"]
                model_info = validate_artifact(model)
                timing = json.loads(
                    (root / study / "ledger" / f"evaluate-{run}-{n}.json").read_text()
                )
                rows.append(
                    {
                        "study": study,
                        "run": run,
                        "policy": run.rsplit("-s", 1)[0],
                        "seed": config["seed"],
                        "step": n,
                        "split": summary["split"],
                        "views": summary["view_count"],
                        **summary["means"],
                        "gaussians": worker["final_gaussians"],
                        "max_gaussians_seen": worker["max_gaussians_seen"],
                        "growth_guard_activated": worker["max_gaussians_seen"] * 2
                        > config["max_gaussians"],
                        "optimization_seconds": worker["optimization_seconds"],
                        "trajectory_worker_seconds": model_info["worker"]["training_seconds"],
                        "trajectory_adapter_seconds": model_info["total_seconds"],
                        "evaluation_stage_seconds": timing["seconds"],
                        "peak_allocated_bytes": worker["peak_vram_allocated_bytes"],
                        "peak_reserved_bytes": worker["peak_vram_reserved_bytes"],
                        "config_sha256": item["config_sha256"],
                        "actual_artifact_commit": model_info["git_commit"],
                        "actual_artifact_dirty": model_info["git_dirty"],
                        "evaluation_sha256": sha256_file(evaluation / "evaluation.json"),
                        "report": str(evaluation.relative_to(root)),
                    }
                )
        for log in (root / study / "ledger").glob("*.json"):
            record = json.loads(log.read_text())
            if record["status"] != "complete":
                failures.append(record)
    check_budget(30_000_000)
    output.mkdir(parents=True)
    write_json(output / "measurements.json", rows)
    write_json(
        output / "status.json",
        {
            "complete": not missing and not failures,
            "evaluations_expected": 45,
            "evaluations_measured": len(rows),
            "unmeasured": missing,
            "failed_or_interrupted_stages": failures,
            "ground_truth_detection": "pending_human_review; no AP50/accuracy result claimed",
        },
    )
    if rows:
        with (output / "quality-runtime.csv").open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    aggregates = []
    for study in p["study_order"]:
        policies = sorted({r["policy"] for r in rows if r["study"] == study})
        for policy in policies:
            for step in sorted(
                {r["step"] for r in rows if r["study"] == study and r["policy"] == policy}
            ):
                group = [
                    r
                    for r in rows
                    if r["study"] == study and r["policy"] == policy and r["step"] == step
                ]
                stats = {}
                for key in [
                    "lpips",
                    "psnr_db",
                    "ssim",
                    "depth_mae_m",
                    "depth_rmse_m",
                    "depth_completeness",
                    "optimization_seconds",
                    "gaussians",
                    "peak_allocated_bytes",
                ]:
                    values = [r[key] for r in group if r[key] is not None]
                    stats[key] = {
                        "mean": float(np.mean(values)) if values else None,
                        "sample_sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
                    }
                aggregates.append(
                    {
                        "study": study,
                        "policy": policy,
                        "step": step,
                        "seeds": len(group),
                        "statistics": stats,
                    }
                )
    write_json(output / "aggregates.json", aggregates)
    deltas = []
    for row in rows:
        reference = "refine900" if row["study"].startswith("densification") else "matched"
        controls = [
            r
            for r in rows
            if r["study"] == row["study"]
            and r["policy"] == reference
            and r["seed"] == row["seed"]
            and r["step"] == row["step"]
        ]
        if controls and row["policy"] != reference:
            deltas.append(
                {
                    "study": row["study"],
                    "policy": row["policy"],
                    "seed": row["seed"],
                    "step": row["step"],
                    "reference": reference,
                    **{
                        k: row[k] - controls[0][k]
                        if row[k] is not None and controls[0][k] is not None
                        else None
                        for k in [
                            "lpips",
                            "psnr_db",
                            "ssim",
                            "depth_mae_m",
                            "depth_completeness",
                            "optimization_seconds",
                            "gaussians",
                        ]
                    },
                }
            )
    write_json(output / "paired-deltas.json", deltas)
    lines = [
        "# Frozen reconstruction confirmation and densification",
        "",
        (
            "Additional captures; fr1 room overlaps the original office. "
            "No unseen-site or significance claim."
        ),
        (
            "No target-scene test selection. "
            "Ground-truth AP50 remains pending actual human-approved annotations."
        ),
        (
            "Depth errors are conditional on prediction support; inspect completeness. "
            "Timings are ordered local observations."
        ),
        "",
        (
            f"Measured {len(rows)} /45 planned evaluations; "
            "incomplete or failed arms are listed in status.json."
        ),
        "",
        (
            "| Study | Policy | Updates | Seeds | LPIPS mean | PSNR mean | "
            "Depth MAE | Support | Optimizer s | Gaussians |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a in aggregates:
        values = [
            a["statistics"][k]["mean"]
            for k in [
                "lpips",
                "psnr_db",
                "depth_mae_m",
                "depth_completeness",
                "optimization_seconds",
                "gaussians",
            ]
        ]
        formatted = ["undefined" if v is None else f"{v:.5f}" for v in values]
        lines.append(
            f"| {a['study']} | {a['policy']} | {a['step']} | {a['seeds']} | "
            + " | ".join(formatted)
            + " |"
        )
    # Fixed per-run worst LPIPS view, never selected for favorable visual appearance.
    cases = []
    for row in rows:
        evaluation = root / row["report"]
        views = json.loads((evaluation / "views.json").read_text())
        worst = max(views, key=lambda v: (v["metrics"]["lpips"], v["frame_id"]))
        case = {
            "study": row["study"],
            "run": row["run"],
            "step": row["step"],
            "split": row["split"],
            "frame_id": worst["frame_id"],
            "metrics": worst["metrics"],
            "rule": "maximum per-view LPIPS; tie frame ID",
        }
        # Final-budget montage for every run; originals stay unchanged.
        if row["step"] == max(
            r["step"] for r in rows if r["study"] == row["study"] and r["run"] == row["run"]
        ):
            pictures = [
                Image.open(evaluation / worst["assets"][k]).convert("RGB")
                for k in ["real", "rendered", "residual", "depth_error", "depth_mask"]
            ]
            w, h = pictures[0].size
            canvas = Image.new("RGB", (5 * w, h + 32), "white")
            draw = ImageDraw.Draw(canvas)
            for i, pic in enumerate(pictures):
                canvas.paste(pic, (i * w, 32))
            draw.text(
                (4, 3),
                (
                    f"{row['study']} / {row['run']} / {row['step']} / "
                    f"{worst['frame_id']} / worst LPIPS"
                ),
                fill="black",
            )
            filename = f"{row['study']}-{row['run']}-worst.png"
            canvas.save(output / filename)
            case["montage"] = filename
        cases.append(case)
    write_json(output / "failure-cases.json", cases)
    (output / "report.md").write_text("\n".join(lines) + "\n")
    import html

    (output / "report.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Reconstruction confirmation</title><pre>'
        + html.escape("\n".join(lines))
        + "</pre>"
        + "".join(
            "<figure><figcaption>"
            + html.escape(c["study"] + " / " + c["run"] + " / " + c["frame_id"])
            + "</figcaption>"
            f'<img style="max-width:100%" src="{c["montage"]}"></figure>'
            for c in cases
            if "montage" in c
        )
    )
    write_json(
        output / "files.json",
        {str(f.relative_to(output)): sha256_file(f) for f in output.rglob("*") if f.is_file()},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=ROOT / "analysis")
    args = parser.parse_args()
    analyze(args.root, args.out)
