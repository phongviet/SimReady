"""Portable reports generated exclusively from saved measurements and images."""

import html
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from simready.data.dataset import write_json


def heatmap(values: np.ndarray, maximum: float, valid: np.ndarray | None = None) -> Image.Image:
    scaled = np.clip(np.nan_to_num(values, nan=0, posinf=0, neginf=0) / maximum, 0, 1)
    rgb = np.stack([scaled, np.minimum(scaled * 2, 1), 1 - scaled], axis=-1)
    if valid is not None:
        rgb[~valid] = 0  # Explicit unknown/invalid black, not zero-error color.
    return Image.fromarray(np.round(rgb * 255).astype(np.uint8))


def overlay(path: Path, predictions: list[dict], categories: list[str], output: Path):
    with Image.open(path) as source:
        image = source.copy()
    draw = ImageDraw.Draw(image)
    for prediction in predictions:
        box = prediction["box"]
        draw.rectangle(box, outline="#d3ed8b", width=2)
        label = prediction["label"]
        name = categories[label] if 0 <= label < len(categories) else str(label)
        text = f"{name} {prediction['score']:.2f}"
        x, y = max(0, box[0]), max(0, box[1] - 12)
        draw.text((x, y), text, fill="white", stroke_width=1, stroke_fill="black")
    image.save(output)


def build_report(root: Path, summary: dict, views: list[dict]) -> None:
    means = summary["means"]
    counts = summary["detection_totals"]
    text = [
        "# SimReady frozen-view evaluation",
        "",
        summary["scope"],
        "",
        f"Dataset: {summary['dataset_scene_id']} ({summary['dataset_kind']}). "
        f"Split: {summary['split']}; {len(views)} views.",
        "",
        "## Measured per-view means",
        "",
        "| Metric | Mean |",
        "|---|---:|",
    ]
    text += [f"| {key} | {value if value is not None else 'N/A'} |" for key, value in means.items()]
    text += [
        "",
        "Detector totals: " + json.dumps(counts),
        "",
        "Geometry accuracy: N/A (no aligned ground-truth mesh).",
        "",
        "## Failure ranking",
        "",
        "Sorted by measured LPIPS, descending; inspect images and raw predictions.",
        "",
    ]
    order = sorted(views, key=lambda v: v["metrics"]["lpips"], reverse=True)
    for view in order[:10]:
        m, d = view["metrics"], view["detection"]
        text.append(
            f"- {view['frame_id']}: LPIPS={m['lpips']:.4f}, PSNR={m['psnr_db']}, "
            f"depth MAE={m['depth_mae_m']} m, disappeared={d['disappeared_count']}, "
            f"appeared={d['appeared_count']}."
        )
    text += ["", "## Limits", ""] + [f"- {limit}" for limit in summary["limitations"]]
    text += [
        "",
        "Protocol/config, input hashes, environment/weight hashes, raw predictions and per-view "
        "diagnostics are adjacent JSON/CSV files. The report contains no edited-scene evaluation.",
    ]
    (root / "report.md").write_text("\n".join(text) + "\n")
    bars = []
    maximum = max(1.0, max(view["metrics"]["lpips"] for view in views))
    for index, view in enumerate(views):
        value = view["metrics"]["lpips"]
        x, h = 45 + index * 28, value / maximum * 190
        bars.append(
            f'<rect x="{x}" y="{220 - h}" width="20" height="{h}" fill="#b4d687"><title>'
            f"{html.escape(view['frame_id'])}: {value:.4f}</title></rect>"
            f'<text x="{x}" y="240" fill="white" font-size="8">{index + 1}</text>'
        )
    width = max(480, len(views) * 28 + 70)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 260">'
        '<rect width="100%" height="100%" fill="#18231e"/>'
        '<text x="16" y="20" fill="white">LPIPS by frozen view (higher = more discrepancy)</text>'
        f'<text x="3" y="40" fill="white" font-size="10">{maximum:.2f}</text>'
        f'<text x="17" y="220" fill="white" font-size="10">0</text>'
        f'{"".join(bars)}<path d="M40 30V220H{width - 15}" fill="none" stroke="white"/></svg>'
    )
    (root / "lpips-distribution.svg").write_text(svg)
    panels = []
    for view in order:
        assets = view["assets"]
        figures = "".join(
            f'<figure><img loading="lazy" src="{html.escape(assets[key])}" alt="{title}">'
            f"<figcaption>{title}</figcaption></figure>"
            for key, title in (
                ("real_overlay", "Real / detector"),
                ("rendered_overlay", "Rendered / detector"),
                ("residual", "RGB residual: blue 0 → yellow/red 1"),
                ("depth_error", "Depth error: blue 0 → yellow/red ≥1 m; black invalid"),
            )
        )
        counts = {
            key: view["detection"][key]
            for key in (
                "real_count",
                "rendered_count",
                "matched_count",
                "disappeared_count",
                "appeared_count",
            )
        }
        panels.append(
            f'<section><h2>{html.escape(view["frame_id"])}</h2><div class="images">{figures}</div>'
            f"<pre>{html.escape(json.dumps(view['metrics'], indent=2))}</pre>"
            f"<p>Detector: {html.escape(json.dumps(counts))}</p></section>"
        )
    escaped = html.escape("\n".join(text))
    (root / "report.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>SimReady evaluation</title><style>"
        "body{background:#111b17;color:#e2ebe4;font:16px system-ui;max-width:1400px;"
        "margin:30px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}"
        ".images{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}"
        "figure{margin:0}img{width:100%}section{border-top:1px solid #496052;"
        "margin-top:25px;padding-top:12px}figcaption{font-size:12px}a{color:#c9e798}</style>"
        '<h1>Frozen-view evaluation</h1><a href="per_view.csv">Per-view CSV</a> · '
        '<a href="summary.json">Summary JSON</a> · <a href="predictions.json">Raw predictions</a>'
        f'<pre>{escaped}</pre><img src="lpips-distribution.svg" alt="LPIPS distribution">'
        f"{''.join(panels)}</html>"
    )
    write_json(root / "views.json", views)
