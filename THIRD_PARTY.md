# Source, dependency and data notices

Original SimReady source is under the root MIT LICENSE. That license does not
replace licenses for dependencies, datasets, pretrained weights or derived media.
Packages are installed from locked distributions; their own notices remain in
those distributions. This repository does not vendor their implementations.

| Component | Observed distribution license / treatment |
|---|---|
|gsplat1.5.3+pt24cu124|Apache2.0; installed wheel `licenses/LICENSE`; upstream rasterization/DefaultStrategy used through an adapter|
|PyTorch2.4.1 / torchvision0.19.1|BSD-family notices retained in installed packages; no weights committed|
|LPIPS 0.1.4|BSD-style license in installed `lpips-0.1.4.dist-info/LICENSE`; SqueezeNet and package calibration hashes pinned separately|
|Open3D CPU0.19|MIT project license plus dependency notices in installed LICENSE.txt; geometry extra only|
|React / Three.js / Spark / Vite|MIT according to pinned installed package.json/license files|
|Playwright|Apache2.0 according to pinned package metadata; browser/tool binaries not redistributed|
|FastAPI / Pydantic|MIT according to installed metadata|
|NumPy / SciPy / scikit-image / Pillow / Uvicorn|BSD/MIT-family distributions with component-specific notices; consult installed license files for full dependency details|

These entries were inspected locally for the pinned installed versions; they do
not assert that a code license automatically covers a dataset or model's training
inputs. `configs/perception-weights.json` pins the exact official detector,
SqueezeNet and LPIPS calibration files used. Model inference limitations are in
EVALUATION_PROTOCOL.md. No third-party model weights are bundled in Git.

## Data and derived media

- Analytic plane/bench source fixtures are authored synthetic data, CC0. The
  bundled analytic model/renders/report derive from these fixtures; see
  `src/simready/demo/analytic-plane/LICENSE.txt` and their provenance.
- TUM RGB-D **freiburg1_desk** is attributed to Sturm et al., IROS 2012, under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), as identified by the
  [publisher](https://cvg.cit.tum.de/data/datasets/rgbd-dataset). Raw capture stays
  ignored and is fetched from the publisher with a pinned checksum.
- TUM-derived screenshots, comparisons, reports, research plots and
  `docs/media/tum-walkthrough.webm` preserve that attribution. They include modified
  images, learned renders, residuals, annotations or UI overlays. CC BY 4.0 applies
  to the included TUM-derived imagery; original product source remains MIT.
- The Open3D Redwood sample is **synthetic ICL-NUIM**, not a real capture. Its
  redistribution terms remain unverified here. It is fetched only for local
  testing, kept out of Git, and is not part of the bundled public demo.

The walkthrough and screenshots contain no account tokens. They show automated
local role fixtures and derived public desk imagery, not a private capture or
human endorsement. Local credentials, dataset archives and generated reviewed
ZIPs remain ignored. See docs/DATASET_PROTOCOL.md for source and privacy scope.

## Workstation and annotated-evaluation additions

The workstation retains React/Vite and adapts the structure of shadcn/ui
sidebar-07 (https://ui.shadcn.com/blocks), rather than incorporating a Next.js app.
New locked dependencies observed during implementation:

| Dependency | Version observed | License |
|---|---|---|
| Radix Collapsible | 1.2.1 | MIT |
| Radix Tooltip | 1.4.1 | MIT |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx | 2.1.1 | MIT |
| tailwind-merge | 3.7.0 | MIT |
| Tailwind CSS | 4.3.3 | MIT |
| Inter (@fontsource/inter) | 5.3.0 | SIL OFL-1.1 |
| pycocotools (optional CPU annotation extra) | 2.0.11 | BSD/FreeBSD |

Frontend package/font license texts are retained in frontend/public/licenses and
included in the Vite public build. Inter credits The Inter Project Authors.
pycocotools provides COCO bbox evaluation; installing it does not supply annotated
ScanNet data or grant ScanNet access. Official access terms remain separate.
No ScanNet data was acquired through an unofficial mirror or access bypass.
