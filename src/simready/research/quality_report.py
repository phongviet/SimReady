"""Saved-measurement plots and deterministic qualitative failure selection."""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

from simready.data.dataset import write_json


def report(root, output, rows, selected):
    lines = [
        "# Reconstruction quality ablation",
        "",
        "Validation only; exposed single sequence, three seeds, no generalization claim.",
        "Optimization timing excludes checkpoint IO; historical runtime is not comparable.",
        "",
        "| Run | Step | LPIPS ↓ | PSNR dB ↑ | SSIM ↑ | Optimization s | Gaussians |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        seconds = r["optimization_seconds"]
        lines.append(
            f"| {r['run']} | {r['step']} | {r['lpips']:.5f} | {r['psnr_db']:.3f} | "
            f"{r['ssim']:.4f} | {seconds if seconds is not None else 'unavailable'} | "
            f"{r['gaussians']} |"
        )
    flags = []
    reference = next(r for r in rows if r["run"] == "reference")
    baseline = next(r for r in rows if r["run"] == "baseline-s42")
    for title, a, b in [
        ("fresh vs historical baseline", baseline, reference),
        (
            "trajectory-1200 vs standalone baseline",
            next(r for r in rows if r["run"] == "control-s42" and r["step"] == 1200),
            baseline,
        ),
    ]:
        delta = {k: a[k] - b[k] for k in ("lpips", "psnr_db")}
        flag = abs(delta["lpips"]) > 0.03 or abs(delta["psnr_db"]) > 0.5
        flags.append({"comparison": title, "delta": delta, "flag": flag})
        lines += ["", f"{title}: {delta}; predeclared discrepancy flag={flag}."]
    write_json(output / "baseline-checks.json", flags)
    lines += [
        "",
        "Per-seed selections: "
        + ", ".join(f"{seed}: {r['run']} at {r['step']}" for seed, r in selected.items())
        + ".",
        "",
        "All arms and budgets are included above, including regressions. Validation selection "
        "is exploratory and biased by prior sequence exposure and multiple comparisons.",
    ]
    # Paired deltas across the three seeds, no significance test or population CI.
    lines += [
        "",
        "| Arm | Step | Mean paired ΔLPIPS vs control | Seed range |",
        "|---|---:|---:|---|",
    ]
    for arm in sorted({r["arm"] for r in rows} - {"baseline", "reference", "control"}):
        for step in (1200, 2400, 3600):
            deltas = [
                r["lpips"]
                - next(
                    c["lpips"]
                    for c in rows
                    if c["arm"] == "control" and c["seed"] == r["seed"] and c["step"] == step
                )
                for r in rows
                if r["arm"] == arm and r["step"] == step
            ]
            if deltas:
                lines.append(
                    f"| {arm} | {step} | {np.mean(deltas):+.6f} | "
                    f"{min(deltas):+.6f} to {max(deltas):+.6f} |"
                )
    aggregates = []
    for arm in sorted({r["arm"] for r in rows}):
        for step in sorted({r["step"] for r in rows if r["arm"] == arm}):
            group = [r for r in rows if r["arm"] == arm and r["step"] == step]
            result = {"arm": arm, "step": step, "seed_count": len(group)}
            for metric in (
                "lpips",
                "psnr_db",
                "ssim",
                "depth_mae_m",
                "depth_rmse_m",
                "depth_completeness",
                "optimization_seconds",
            ):
                values = [r[metric] for r in group if r[metric] is not None]
                result[metric] = {
                    "mean": float(np.mean(values)) if values else None,
                    "sample_sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
                }
            aggregates.append(result)
    write_json(output / "aggregates.json", aggregates)
    lines += [
        "",
        "| Arm | Step | LPIPS mean ± sample SD | PSNR mean ± sample SD |",
        "|---|---:|---:|---:|",
    ]
    for a in aggregates:

        def formatted(metric, a=a):
            v = a[metric]
            return (
                f"{v['mean']:.5f} ± {v['sample_sd']:.5f}"
                if v["sample_sd"] is not None
                else f"{v['mean']:.5f} (one run)"
            )

        lines.append(
            f"| {a['arm']} | {a['step']} | {formatted('lpips')} | {formatted('psnr_db')} |"
        )
    (output / "report.md").write_text("\n".join(lines) + "\n")
    fig, ax = plt.subplots(figsize=(9, 6))
    for arm in sorted({r["arm"] for r in rows} - {"reference", "baseline"}):
        candidates = [r for r in rows if r["arm"] == arm]
        xs = [r["optimization_seconds"] for r in candidates]
        ys = [r["lpips"] for r in candidates]
        ax.scatter(xs, ys, label=arm, s=24)
    measured = [r for r in rows if r["optimization_seconds"] is not None and r["arm"] != "baseline"]
    pareto = [
        r
        for r in measured
        if not any(
            q["optimization_seconds"] <= r["optimization_seconds"]
            and q["lpips"] <= r["lpips"]
            and (q["optimization_seconds"] < r["optimization_seconds"] or q["lpips"] < r["lpips"])
            for q in measured
        )
    ]
    pareto.sort(key=lambda r: r["optimization_seconds"])
    ax.plot(
        [r["optimization_seconds"] for r in pareto], [r["lpips"] for r in pareto], "k--", alpha=0.5
    )
    write_json(output / "pareto.json", pareto)
    ax.set(
        xlabel="Cumulative optimization wall seconds (checkpoint IO excluded)",
        ylabel="Validation LPIPS ↓",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "quality-runtime.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    for folder in sorted(root.glob("*-s42/model")):
        log = [
            json.loads(line) for line in (folder / "training-log.jsonl").read_text().splitlines()
        ]
        axes[0].plot(
            [r["completed_steps"] for r in log],
            [r["total_loss"] for r in log],
            label=folder.parent.name,
        )
        axes[1].plot([r["completed_steps"] for r in log], [r["gaussians"] for r in log])
    axes[0].set(ylabel="Stochastic training objective (different units across arms)")
    axes[0].legend(fontsize=8)
    axes[1].set(xlabel="Completed updates", ylabel="Gaussians")
    fig.tight_layout()
    fig.savefig(output / "convergence.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 6))
    for arm in sorted({r["arm"] for r in rows} - {"baseline", "reference"}):
        for seed in (42, 43, 44):
            points = sorted(
                [r for r in rows if r["arm"] == arm and r["seed"] == seed], key=lambda r: r["step"]
            )
            ax.plot(
                [r["step"] for r in points],
                [r["lpips"] for r in points],
                marker="o",
                alpha=0.7,
                label=arm if seed == 42 else None,
            )
    ax.set(xlabel="Completed updates", ylabel="Validation LPIPS ↓")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "checkpoint-quality.png")
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    for folder in sorted(root.glob("*-s42/model")):
        log = [
            json.loads(line) for line in (folder / "training-log.jsonl").read_text().splitlines()
        ]
        for ax, key in zip(axes, ("photometric", "depth_objective"), strict=True):
            ax.plot(
                [r["completed_steps"] for r in log], [r[key] for r in log], label=folder.parent.name
            )
            ax.set(xlabel="Completed updates", ylabel=key)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "loss-components.png")
    plt.close(fig)
    # Deterministic actual-image montage: worst LPIPS and largest paired degradation.
    failures = []
    for seed, winner in selected.items():
        current = root / winner["report"]
        control = root / next(
            r["report"]
            for r in rows
            if r["arm"] == "control" and r["seed"] == int(seed) and r["step"] == 1200
        )
        views = json.loads((current / "views.json").read_text())
        controls = {v["frame_id"]: v for v in json.loads((control / "views.json").read_text())}
        worst = max(views, key=lambda v: (v["metrics"]["lpips"], v["frame_id"]))
        degraded = max(
            views,
            key=lambda v: (
                v["metrics"]["lpips"] - controls[v["frame_id"]]["metrics"]["lpips"],
                v["frame_id"],
            ),
        )
        for label, view in [("worst", worst), ("largest-paired-degradation", degraded)]:
            failures.append(
                {
                    "seed": seed,
                    "rule": label,
                    "run": winner["run"],
                    "step": winner["step"],
                    "frame_id": view["frame_id"],
                    "lpips": view["metrics"]["lpips"],
                    "paired_delta": view["metrics"]["lpips"]
                    - controls[view["frame_id"]]["metrics"]["lpips"],
                }
            )
            paths = [
                current / view["assets"][key]
                for key in ("real", "rendered", "residual", "depth_error", "depth_mask")
            ]
            paths.insert(1, control / controls[view["frame_id"]]["assets"]["rendered"])
            images = [Image.open(p).convert("RGB") for p in paths]
            w, h = images[0].size
            canvas = Image.new("RGB", (w * 6, h + 36), "white")
            draw = ImageDraw.Draw(canvas)
            for i, (image, title) in enumerate(
                zip(
                    images,
                    (
                        "RGB reference",
                        "Control-1200",
                        "Selected render",
                        "RGB residual",
                        "Depth error",
                        "Depth mask",
                    ),
                    strict=True,
                )
            ):
                canvas.paste(image, (i * w, 36))
                draw.text((i * w + 4, 3), title, fill="black")
            draw.text(
                (4, 19),
                f"{winner['run']} / step {winner['step']} / {view['frame_id']} / {label}",
                fill="black",
            )
            canvas.save(output / f"failure-s{seed}-{label}.png")
    write_json(output / "failure-selection.json", failures)
    figures = [p.name for p in output.glob("*.png")]
    import html

    (output / "report.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Reconstruction study</title><pre>'
        + html.escape("\n".join(lines))
        + "</pre>"
        + "".join(
            f"<figure><figcaption>{html.escape(name)}</figcaption>"
            f'<img style="max-width:100%" src="{name}"></figure>'
            for name in figures
        )
    )
