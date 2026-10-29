# Frozen-view evaluation protocol (M3)

This configuration is fixed before measuring the real held-out TUM sequence.
`configs/evaluation.json` is expanded through the strict `EvaluationConfig`.
Confidence, IoU and alpha thresholds are heuristics, not validated readiness gates.
Changing a threshold creates a new run; do not tune it on reported test views.

## Inputs and leakage guard

Use a complete frozen **validation** or **test** split. Reject train/candidate,
subsets, duplicate/missing cameras, changed K/pose, and reconstruction/dataset/split
hash mismatches. Training provenance must list exactly the frozen train IDs.
Only saved gsplat base RGB, expected axial-Z depth and alpha enter evaluation.
Browser screenshots and inserted proxy overlays never enter scientific metrics.
Dataset validation reads hashes of all observations for integrity; held-out image
content is not fed back into optimization, reconstruction initialization or TSDF.

The evaluation directory contains copied paired RGB, PNG heatmaps/support masks,
protocol/input JSON, raw predictions, per-view diagnostics/CSV, summary JSON,
SVG distribution, Markdown/HTML report and worker log. `evaluation.json` hashes
all these files and records source revision, dirty state and creation time.
Source observation digests and dataset/render/reconstruction manifests bind the
input view IDs, cameras, units, calibration, source license and frozen split.
A clean source revision is required for the reported real acceptance run.

## Photometric and depth metrics

Both RGB images are uint8 sRGB, divided by 255, without linear-light conversion,
exposure correction, cropping, pose refinement or masking. Resize real RGB to the
saved render's exact resolution using Pillow LANCZOS; resize native GT depth with
NEAREST. Resized K uses the same half-pixel convention as training and rendering.
The real baseline is 320×240. Calibration, synchronization, distortion and dynamic
scene uncertainties inherited from the source remain explicit limitations.

- PSNR: whole-image mean squared RGB error, range 1, `-10 log10(MSE)` dB.
  Identical pairs have `psnr_db=null`, `rgb_exact_match=true`; the report counts
  them separately and excludes infinite values from finite PSNR means.
- SSIM: scikit-image **0.26.0**, `channel_axis=-1`, `data_range=1`, uniform
  7×7 window, default sample covariance and K1=.01/K2=.03, mean over RGB channels.
- LPIPS: **0.1.4**, **SqueezeNet1.1**, calibration **v0.1**, pretrained ImageNet
  trunk and learned perceptual calibration. Input NCHW RGB float32 **[-1,1]**,
  same evaluation resolution, evaluation mode, scalar spatial average. This
  explicitly uses Squeeze, not the AlexNet variant; cross-variant comparisons
  are inappropriate. No random or untrained perceptual weights.
- Depth reference: finite positive registered GT axial Z, native uint16 converted
  with manifest meters-per-unit. Evaluation support is that mask intersected with
  finite positive rendered Z and alpha **>=0.1**. MAE/RMSE are in **meters**.
  Completeness is supported pixels / valid GT pixels. No support gives null error;
  no GT gives null completeness; missing rendered support is never zero error.
- RGB heatmap: mean absolute RGB residual /255, blue 0 → yellow/red 1.
  Depth heatmap: absolute meters, blue 0 → yellow/red >=1m; **black is invalid**.
  Separate white/black depth support PNG removes ambiguity.
- Summary means weight each view equally, ignoring unavailable values. Per-view
  support counts remain available. No aligned ground-truth mesh exists for this
  capture, so Chamfer and F-score are N/A.

## Fixed detector and correspondence

Torch **2.4.1+cu124**, torchvision **0.19.1+cu124**,
`ssdlite320_mobilenet_v3_large`, **COCO_V1** weights. Full weight SHA-256 pins are
in `configs/perception-weights.json`; the worker rejects different content.
All COCO output classes are retained. Both domains use RGB float32 [0,1], model
mean/std .5/.5, internal fixed 320×320 resize, identical inference batch shape,
model score floor .001, class-wise NMS .55, top-k candidates 300 per class, and
at most 300 final predictions per image. Separate calls use the same model in
`eval()` mode. Seed 42, deterministic torch algorithms and CuDNN configuration
are recorded; this does not assert hardware-independent bitwise identity.

`predictions.json` stores **post-backend score-floor/NMS/top-k predictions**,
before our comparison confidence cutoff **>=0.5**. It is not a dump of pre-NMS
network logits. `views.json` keeps filtered predictions and every match/unmatched
index, enabling audit from pixels to discrepancy counts.

Correspondence uses class agreement and IoU **>=0.5**. Gated Hungarian assignment
maximizes valid match count first, then total IoU, preventing invalid pairs from
stealing valid matches. Report real/render counts, appeared/disappeared boxes,
matched IoU, center offset normalized separately by width/height (Euclidean norm),
and signed rendered-minus-real confidence gap. Spatially overlapping unmatched
boxes with different labels are secondary **class mismatch candidates**, not
verified semantic errors. Per-class and per-view counts are exported. Both-empty
views give null matching quality and no positive task-quality claim. There are
no annotated small/distant/occluded truth slices; no accuracy result is claimed.

**Agreement is not accuracy.** Without annotated GT boxes there is no precision,
recall or mAP. One sequence of temporally correlated held-out frames supports
only a measured case study, not population conclusions or confidence intervals.

## Commands and local queue

```bash
uv run --frozen simready eval run --scene data/scenes/tum-fr1-desk --artifact artifacts/scenes/tum-fr1-desk/baseline-1 --renders artifacts/renders/tum-fr1-desk-test-1 --config configs/evaluation.json --out artifacts/evaluations/tum-fr1-desk-test-1
uv run --frozen simready report build --run artifacts/evaluations/tum-fr1-desk-test-1
uv run --frozen simready scene attach-report --id tum-fr1-desk --run-id baseline-test-1 --run artifacts/evaluations/tum-fr1-desk-test-1
```

`eval run` builds reports automatically; `report build` verifies and locates the
already-built exports. Outputs never overwrite an existing run.

The explorer can queue a new complete frozen-test evaluation. POST
`/api/v1/scenes/{id}/evaluate` accepts only `expected_version` and split, returns
202/job ID. A local process queue uses an exclusive OS file lock to serialize GPU
jobs; persistent SQLite records queued/running/succeeded/failed status and logs.
Each job independently reloads/renders the base model, evaluates, registers an
immutable report bound to the submitted scene revision, and retains diagnostics.
HTTP workers do not run CUDA inference. A subsequent worker marks interrupted
running jobs failed, without silently retrying them. This is a loopback Linux/WSL
queue, not a production distributed scheduler; auth/reviewer permissions are M4.
Report assets are served only from registered hash-checked allowlists.

## Primary references

- [Torchvision SSDLite builder and exact defaults](https://github.com/pytorch/vision/blob/v0.19.1/torchvision/models/detection/ssdlite.py)
- [Torchvision SSD inference and NMS](https://github.com/pytorch/vision/blob/v0.19.1/torchvision/models/detection/ssd.py)
- [LPIPS implementation and normalization](https://github.com/richzhang/PerceptualSimilarity)
- [scikit-image SSIM](https://scikit-image.org/docs/0.26.x/api/skimage.metrics.html#skimage.metrics.structural_similarity)
