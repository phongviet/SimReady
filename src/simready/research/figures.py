"""Measured study figures/reports; no hardcoded experiment values."""

import html
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

COLORS = {"base": "#555555", "risk": "#0072B2", "random": "#D55E00", "farthest": "#009E73"}


def plots(output, summary, rows, config):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ValueError("study figures require uv sync --extra research") from exc
    plt.rcParams.update(
        {
            "font.size": 10,
            "svg.fonttype": "none",
            "svg.hashsalt": "simready-m5-v1",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8), layout="constrained")
    ax = axes[0, 0]
    methods = list(config.methods)
    for i, method in enumerate(methods):
        stats = summary["methods"][method]["lpips"]
        ax.errorbar(
            i, stats["mean"], yerr=stats["sample_sd"], color=COLORS[method], marker="o", capsize=5
        )
        ax.scatter(
            np.full(len(stats["values"]), i) + np.linspace(-0.06, 0.06, len(stats["values"])),
            stats["values"],
            color=COLORS[method],
            marker="x",
            s=28,
        )
    for seed in config.seeds:
        values = [
            next(r for r in summary["runs"] if r["method"] == m and r["seed"] == seed)["means"][
                "lpips"
            ]
            for m in methods
        ]
        ax.plot(range(len(methods)), values, color=".8", linewidth=0.8, zorder=0)
    ax.set(
        xticks=range(len(methods)),
        xticklabels=methods,
        ylabel="Mean test LPIPS (lower is better)",
        title="E4 · Three paired seeds; dots ± sample SD",
    )
    ax.grid(axis="y", alpha=0.2)
    ax = axes[0, 1]
    base = [r for r in rows if r["method"] == "base" and r["seed"] == config.seeds[0]]
    usable = [r for r in base if r["unmatched_fraction"] is not None]
    ax.scatter(
        [r["lpips"] for r in usable],
        [r["unmatched_fraction"] for r in usable],
        color=COLORS["base"],
        marker="o",
    )
    ax.set(
        xlabel="LPIPS (lower is better)",
        ylabel="Unmatched / (real + rendered predictions)",
        ylim=(-0.03, 1.03),
        title=f"E1 · Base seed {config.seeds[0]}; correlated views",
    )
    corr = next(
        r
        for r in summary["correlations"]
        if r["run"] == f"base-s{config.seeds[0]}"
        and r["image_metric"] == "lpips"
        and r["task_metric"] == "unmatched_fraction"
    )
    text = (
        f"Spearman ρ={corr['rho']:.3f}"
        if corr["rho"] is not None
        else "ρ undefined: constant/insufficient input"
    )
    ax.text(0.03, 0.06, text, transform=ax.transAxes, fontsize=9)
    ax.grid(alpha=0.2)
    ax = axes[1, 0]
    edges = config.distance_bin_edges_m
    labels = [f"[{a:g}, {b:g})" for a, b in zip(edges[:-1], edges[1:], strict=True)]
    for j, method in enumerate(methods):
        means = []
        for low in edges[:-1]:
            values = [
                b["means"]["lpips"]
                for b in summary["novelty_bins"]
                if b["dimension"] == "distance_m"
                and b["method"] == method
                and b["low"] == low
                and b["views"]
            ]
            means.append(float(np.mean(values)) if values else np.nan)
        ax.plot(
            np.arange(len(labels)) + (j - 1.5) * 0.04,
            means,
            label=method,
            marker=("o", "s", "^", "D")[j],
            color=COLORS[method],
            linewidth=1,
        )
    for i, low in enumerate(edges[:-1]):
        entry = next(
            b
            for b in summary["novelty_bins"]
            if b["dimension"] == "distance_m"
            and b["run"] == f"base-s{config.seeds[0]}"
            and b["low"] == low
        )
        ax.text(
            i,
            0.02,
            f"n={entry['views']}" + (" · N/A" if not entry["views"] else ""),
            transform=ax.get_xaxis_transform(),
            ha="center",
            fontsize=8,
        )
    ax.set(
        xticks=range(len(labels)),
        xticklabels=labels,
        xlabel="Distance to original50training cameras (m)",
        ylabel="LPIPS, mean over seed means",
        title="E2 · Common camera bins; empty bins unmeasured",
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    ax = axes[1, 1]
    for row in summary["calibration"]:
        ax.scatter(
            row["check_targets"], row["check_predictions"], label=f"seed {row['seed']}", s=25
        )
    values = [
        v
        for r in summary["calibration"]
        for k in ("check_targets", "check_predictions")
        for v in r[k]
    ]
    low, high = min(values), max(values)
    ax.plot([low, high], [low, high], "--", color=".5", linewidth=1)
    ax.set(
        xlabel="Validation check LPIPS",
        ylabel="Predicted LPIPS",
        title="Calibration · Check8views excluded from fit",
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    fig.suptitle(
        "One TUM desk capture · 18 held-out views · detector agreement is not accuracy", fontsize=12
    )
    fig.savefig(output / "study-figures.svg", metadata={"Date": None})
    fig.savefig(output / "study-figures.png", dpi=180)
    plt.close(fig)


def failure_montage(study: Path, output: Path, rows: list[dict], config) -> None:
    seed = config.seeds[0]
    risk = {r["frame_id"]: r for r in rows if r["method"] == "risk" and r["seed"] == seed}
    random = {r["frame_id"]: r for r in rows if r["method"] == "random" and r["seed"] == seed}
    chosen = sorted(risk, key=lambda name: (-(risk[name]["lpips"] - random[name]["lpips"]), name))[
        :3
    ]
    width, height, header = 320, 240, 42
    result = Image.new("RGB", (width * 5, (height + header) * len(chosen)), "#f5f5f1")
    draw = ImageDraw.Draw(result)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        font = ImageFont.load_default(size=12)
    for i, name in enumerate(chosen):
        y = i * (height + header)
        for j, method in enumerate(("reference", *config.methods)):
            folder = (
                study
                / "evaluations"
                / f"{'base' if method == 'reference' else method}-s{seed}-test/images"
            )
            path = folder / f"{name}-{'real' if method == 'reference' else 'rendered'}.png"
            with Image.open(path) as image:
                result.paste(image.convert("RGB"), (j * width, y + header))
            measured = next(
                (
                    r
                    for r in rows
                    if r["method"] == method and r["seed"] == seed and r["frame_id"] == name
                ),
                None,
            )
            text = (
                f"{name} · {method}"
                if method == "reference"
                else (f"{method} · LPIPS {measured['lpips']:.4f}")
            )
            draw.text((j * width + 6, y + 6), text, fill="#202625", font=font)
            if method == "reference":
                draw.text(
                    (j * width + 6, y + 23),
                    "TUM RGB-D · Sturm et al. · CC BY4.0",
                    fill="#202625",
                    font=font,
                )
    result.save(output / "failure-comparisons.png")
    (output / "failure-selection.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "frames": chosen,
                "rule": "Three largest risk-minus-random LPIPS losses, ties by frame ID; "
                "diagnostic post-hoc selection.",
                "attribution": "TUM RGB-D benchmark, Sturm et al., IROS2012, CC-BY-4.0",
            },
            indent=2,
        )
        + "\n"
    )


def fmt(value):
    return "N/A" if value is None else f"{value:.5f}"


def report(output: Path, summary: dict) -> None:
    import re
    from textwrap import dedent

    raw_table = [
        "|Run|Train|LPIPS|PSNR dB|SSIM|Depth MAE m|Real/rendered/matched|",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in summary["runs"]:
        m, d = r["means"], r["detection_totals"]
        raw_table.append(
            f"|{r['run']}|{r['train_frames']}|{fmt(m['lpips'])}|{fmt(m['psnr_db'])}|"
            f"{fmt(m['ssim'])}|{fmt(m['depth_mae_m'])}|"
            f"{d['real_count']}/{d['rendered_count']}/{d['matched_count']}|"
        )
    seed_table = [
        "|Method|LPIPS mean|Sample SD|LPIPS improvement vs base %|",
        "|---|---:|---:|---:|",
    ]
    for method, values in summary["methods"].items():
        improvement = summary["relative_improvement_percent_vs_base"][method]["lpips"]
        seed_table.append(
            f"|{method}|{fmt(values['lpips']['mean'])}|"
            f"{fmt(values['lpips']['sample_sd'])}|{fmt(improvement)}|"
        )
    delta = summary["paired_risk_minus_random"]["lpips"]
    direction = "lower" if delta["mean"] < 0 else "higher"
    count = len(summary["ranking_counterexamples"])
    coefficients = [r["coefficients"] for r in summary["calibration"]]
    reduced_rule = (
        "All fits set distance and rotation coefficients to zero; the ranking "
        "reduces to alpha-hole fraction."
        if all(c[1] == 0 and c[2] == 0 for c in coefficients)
        else "The learned coefficients are recorded separately for each seed."
    )
    audit = {
        k: v
        for k, v in summary["semantic_audit"].items()
        if k
        in (
            "verdict",
            "integrity_status",
            "review_independence",
            "acceptance_status",
            "summary",
        )
    }
    paragraphs = dedent(f"""
    ## Findings and limits

    1. Risk-minus-random LPIPS is {fmt(delta["mean"])} ± {fmt(delta["sample_sd"])}
    (sample SD), with seed deltas {delta["values"]}. Risk has {direction} aggregate
    LPIPS than random here; this does not establish general superiority.

    2. E1 reports Spearman for normalized unmatched fraction and raw counts
    separately. Constant inputs produce null plus a reason. Raw counts depend
    on object visibility; neither quantity measures true detection error.

    3. {count} normalized-discrepancy ranking counterexamples are exported
    (capped at 12). An empty list means no such inversion was found. It is not
    evidence of safety or accuracy.

    4. E2 uses the same original 50 training cameras for all arms, three
    chronological six-view blocks and explicit empty bins. Scene/visibility
    confounding cannot be controlled in this one-capture case study.

    5. Calibration fits 8 validation views and checks 8 other views. Coefficients,
    check MAE/correlation, risk features and sealed choices are saved. Weak
    checks were not used to tune or replace the method.

    {reduced_rule} Coefficient order is intercept, distance, rotation, alpha hole:
    {coefficients}

    Interpretation: any observed difference combines where four observations
    were acquired and seeded optimization. Coverage, visibility and holes are
    plausible contributors, not established causal explanations.

    Next experiments: use independently captured scenes and valid object labels;
    pre-register calibration/feature ablations before new test exposure.
    Do not retune this completed test study.

    ## Provenance and integrity

    Experiment source: `{summary["source"]["commit"]}`. All 12 models use 1,200
    fresh steps at 320px. Recapture arms add exactly 4 frames; base has 50.
    Final Gaussian counts and measured costs vary under the same fixed caps.

    checks.json contains deterministic hash, selection, matching and metric
    replays. It is not a substitute for independent semantic review.

    Fresh semantic audit: {json.dumps(audit, sort_keys=True)}

    Benchmark outputs: config.yaml (JSON-compatible YAML1.2), environment.json,
    git_commit.txt, dataset_and_split_hash.json, runs.csv, per_view.csv,
    raw prediction JSONL, metrics_summary.json, figures and this report.

    ## Relation to prior work

    [ActiveNeRF](https://arxiv.org/abs/2209.08546),
    [ActiveSplat](https://li-yuetao.github.io/ActiveSplat/) and
    [ActiveGAMER](https://arxiv.org/abs/2501.06897) study broader active
    reconstruction/exploration methods. They are related work, not reproduced
    baselines. Farthest-pose acquisition here is a local coverage control.

    [YUBI-Real2Sim](https://arxiv.org/abs/2610.17521) studies scene verification
    and robot-policy evaluation. This pinhole detector study does not reproduce
    its policy benchmark. No research novelty is claimed.

    ## Limitations
    """).strip()
    text = (
        "# M5 — Frozen-budget TUM recapture case study\n\n"
        + summary["scope"]
        + "\n\nDescriptive engineering case study; no novelty, population significance, "
        "safety or transfer claim.\n\n## Raw run table\n\n"
        + "\n".join(raw_table)
        + "\n\n## Seed summaries\n\nMean ± sample SD of three seed-level means. "
        "No independent-frame confidence interval.\n\n"
        + "\n".join(seed_table)
        + "\n\n"
        + paragraphs
        + "\n\n"
        + "\n".join("- " + v for v in summary["limitations"])
        + "\n\nDerived comparison images: TUM RGB-D benchmark, Sturm et al., IROS2012, "
        "CC-BY-4.0. Montage rows are selected after measurement for diagnosis, "
        "never for training or method selection.\n"
    )
    (output / "report.md").write_text(text)

    def inline(value):
        escaped = html.escape(value)
        return re.sub(r"\[([^\]]+)\]\((https://[^)]+)\)", r'<a href="\2">\1</a>', escaped)

    rendered, in_table = [], False
    for line in text.splitlines():
        if not line.startswith("|") and in_table:
            rendered.append("</table>")
            in_table = False
        if line.startswith("|"):
            if not in_table:
                rendered.append("<table>")
                in_table = True
            if set(line.replace("|", "").replace(":", "").replace("-", "").strip()):
                rendered.append(
                    "<tr>"
                    + "".join(
                        "<td>" + inline(cell.strip()) + "</td>"
                        for cell in line.strip("|").split("|")
                    )
                    + "</tr>"
                )
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            rendered.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line:
            rendered.append("<p>" + inline(line) + "</p>")
    if in_table:
        rendered.append("</table>")
    rendered += [
        '<h2>Measured figures</h2><img src="study-figures.svg" '
        'alt="Measured recapture, discrepancy, pose-bin and calibration plots">',
        '<h2>Post-hoc failure comparisons</h2><img src="failure-comparisons.png" '
        'alt="Reference and four methods on three diagnostic frames">',
    ]
    (output / "report.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>M5 TUM recapture study</title><style>"
        "body{max-width:1160px;margin:32px auto;padding:0 20px;"
        "font:16px/1.5 system-ui;color:#20332f}"
        "table{border-collapse:collapse;width:100%;font-size:14px}"
        "td{border-bottom:1px solid #ccd7d1;padding:8px}"
        "tr:first-child{font-weight:700;background:#edf3ef}"
        "img{max-width:100%;height:auto}p{overflow-wrap:anywhere}</style>"
        + "\n".join(rendered)
        + "</html>"
    )
