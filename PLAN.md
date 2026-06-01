# SimReady — Perception-Validated Real2Sim Studio

**Project specification and execution plan for Codex**  
**Version:** 1.0 — 2026-10-29  
**Status:** Proposed, not yet implemented  
**Primary goal:** Portfolio-quality end-to-end AI engineering system with a rigorous, research-style evaluation.  
**Secondary goal:** A foundation for investigating task-aware validation and targeted recapture of 3D Gaussian Splatting (3DGS) reconstructions.

> **Instructions to Codex:** Treat this file as the project's source of truth. First inspect the environment and any existing repository. Create `docs/DECISIONS.md`, `docs/PROGRESS.md`, and a milestone-specific checklist. Implement one vertical slice at a time, run its acceptance tests, then proceed. Do **not** claim features or metrics are complete until they run on real inputs and produce verifiable output. Do not implement all milestones in one unreviewed code dump. If a library, dataset, GPU, or simulator is unavailable, implement a clean fallback and document the limitation rather than faking success. Never fabricate evaluation numbers.

---

## 0. Executive summary

### Elevator pitch

**SimReady converts real indoor environments captured with RGB-D or posed video into editable 3DGS scenes, then evaluates whether the rendered views are reliable enough for downstream robot-perception experiments.** An engineer can view the scene, add/move obstacles, inspect reconstruction and perception failures, run a lightweight simulated navigation scenario, and approve or reject the scene for a *specific, limited use case*.

### The problem

Photorealistic reconstruction does not imply trustworthy simulation. 3DGS can generate plausible novel views but may contain floaters, missing surfaces, geometry errors, and view-dependent artifacts. These can change the behavior of object detectors and other perception systems. Meanwhile, splats are a *rendering representation*, not collision geometry, so rendered scenes cannot be treated as physically interactive without separate meshes or collision proxies.

### Core research/engineering question

> **Can task-aware validation and failure localization identify simulation-relevant reconstruction defects that standard image metrics miss?**

### Possible research extension

> **Using a fixed number of additional observations, does recapturing camera poses in predicted weak regions improve held-out perception consistency more than random recapture?**

These are questions to test, not claims of novelty or predetermined improvement. Existing 2025–2026 research already studies perception-aware 3DGS and scene verification; the project's differentiator is its reproducible **reconstruct → edit → validate → diagnose → optionally recapture → re-evaluate** workflow.

### Primary target use case

A robotics engineer records a static warehouse aisle, corridor, or room. SimReady reconstructs it. The engineer inserts a box/barrier, defines a virtual camera path, checks where the reconstruction is untrustworthy, and tests a simple navigation scenario. The system generates an auditable report; approval is conditional on the specified experiment and observations, **not a claim of safety certification or sim-to-real transfer**.

---

## 1. Scope, priorities, and success criteria

### P0 — Minimum credible portfolio product (must complete)

- [ ] Import and validate a small, real RGB-D sequence **with known camera poses**, or a synthetic benchmark with known poses.
- [ ] Produce a 3DGS reconstruction using a reproducible training configuration; save checkpoints and a portable scene artifact.
- [ ] Render RGB **and depth where supported** from specified camera intrinsics/extrinsics.
- [ ] Display an interactive 3D scene; allow orbit/free-camera inspection.
- [ ] Insert, translate, rotate, scale, and delete **new rigid proxy assets** (boxes/barriers); persist edits separately from the original splat.
- [ ] Evaluate held-out real-versus-rendered RGB and, when valid, RGB-D pairs using PSNR/SSIM/LPIPS, depth error, and detection agreement.
- [ ] Show per-view errors and a visual failure overlay; export a JSON/CSV/HTML report including methodology and limitations.
- [ ] Provide scene `draft → submitted → approved/rejected` workflow and an audit trail.
- [ ] Offer a documented CPU-only smoke test (synthetic or precomputed assets) so reviewers can run the interface without training a 3DGS model.
- [ ] Demonstrate the product on **at least one genuinely reconstructed scene**, not just a mock UI.

### P1 — End-to-end simulation relevance (strongly recommended)

- [ ] Create a coarse static collision representation independent of the 3DGS scene (TSDF mesh, floor/walls/boxes, or manually validated proxies).
- [ ] Add a simple, reproducible 2D/2.5D navigation simulator: robot footprint, occupancy, waypoints, collision checks, route replay.
- [ ] Support at least two obstacle configurations on one reconstructed scene and compare route completion/collision results.
- [ ] Add a *simulation-readiness report* with supported camera region, observed coverage, perception discrepancy, geometry checks, and unsupported/unknown areas.
- [ ] Allow an engineer to review the report and approve a scene for a specified use case and camera region.

### P2 — Research extension: targeted recapture (do only after P0/P1 work)

- [ ] Build a viewpoint-risk score **without accessing held-out test images**.
- [ ] Acquire an equal number of extra images from an allowed candidate pool using risk ranking vs random selection.
- [ ] Retrain/update scenes under the same compute and acquisition budget.
- [ ] Compare results on the same untouched held-out test set, with repeated seeds or an uncertainty estimate.
- [ ] Report whether the method helps and where it fails.

### P3 — Advanced original RAV-01 features (optional, do not block release)

- [ ] Scene-level placement of animated agents following predefined trajectories.
- [ ] Advanced obstacle removal or 3D inpainting with explicit unsupported-hole handling.
- [ ] Weather/lighting variants; label postprocessing-only effects as **visual augmentation**, not physically correct sensor simulation.
- [ ] Export an OpenUSD/USD-based scene package with separately referenced render asset and collision representation; validate in a compatible simulator.
- [ ] CARLA/Isaac Sim integration, closed-loop policy evaluation, large-scale RGB/LiDAR capture, and multi-scene benchmarks.

**Deliberately out of scope for P0/P1:** full physically based weather, autonomous driving, safety certification, generating correct unseen geometry behind removed objects, general real-world dynamic reconstruction, high-fidelity robot dynamics, end-to-end policy training, and guaranteed real-to-sim equivalence.

### Objective acceptance signals (these are test conditions, not promised performance numbers)

1. **Product:** A new reviewer can launch the demo, inspect a reconstructed scene, add an obstacle, save/reload it, run evaluation, and read the report without editing source code.
2. **Scientific correctness:** No training/candidate/held-out leakage. Metrics have declared masks, alignment, and units. Raw predictions and per-view results are saved.
3. **Engineering:** API, geometry, metric, serialization, and workflow tests run in CI. GPU tests skip cleanly when CUDA is absent.
4. **Reproducibility:** Every experiment stores source dataset, exact split, configuration, seed, package versions, Git commit, GPU type, and timing.
5. **Honesty:** Areas outside measured views are `unverified`, not `safe`. Sensor-model mismatch, pose uncertainty, and synthetic-vs-real differences appear in every report.

---

## 2. User stories

**Builder**

1. I can import a scene and see whether poses, depth scale, timestamps, intrinsics, and image files are valid.
2. I can launch a reconstruction job and see logs, VRAM usage, status, and output artifact links.
3. I can navigate the splat scene, place/remove *newly inserted* proxy obstacles, and configure a virtual route.
4. I can compare a real test frame and rendered frame at an aligned pose, inspect error heatmaps, and save the result.
5. I can submit a scene, its declared operating region, and evaluation report for review.

**Reviewer / robotics engineer**

1. I can inspect reconstruction metrics, detection disagreements, depth discrepancies, and unobserved areas.
2. I can compare two scene versions or obstacle configurations.
3. I can approve/reject a scene **for a named, limited task**, write a justification, and review its history.
4. I can export its render asset, collision proxy, metadata, and report for further experiments.

**Researcher**

1. I can reproduce baseline reconstruction/evaluation from a manifest and one CLI entry point.
2. I can run matched-image comparison with classical metrics and task-aware metrics on the same frozen test split.
3. I can evaluate whether a risk score predicts true task failure and whether targeted recapture helps.

---

## 3. System architecture

```text
RGB-D capture / posed images / public dataset
                 |
        Import + validate + split
                 |
          Canonical dataset
       (intrinsics, poses, frames,
        masks, manifests, metadata)
                 |
       +---------+----------+
       |                    |
     3DGS                TSDF / coarse
  reconstruction         collision geometry
 (RGB, depth)               (mesh / proxies)
       |                    |
       +---------+----------+
                 |
         Scene package v1
  (splat, collider, camera frames,
   objects, coordinate transforms)
                 |
    +------------+----------------+
    |            |                |
 Scene editor  Render service   Offline evaluation
    |            |                |
 new objects    RGB/depth      held-out comparisons
 trajectories      |                |
    +------------+----------------+
                 |
          Scene QA + report
    (coverage, visual, geometry,
       detector consistency)
                 |
        Review and approval
                 |
   Lightweight navigation simulator
          (P1; optional external
           simulator adapter in P3)

  Research branch P2: predict risky poses → acquire
  extra *candidate* frames → reconstruct → frozen test eval
```

### Separation of concerns

- **Renderer:** photorealistic Gaussian splats, rendered RGB/depth.
- **Physics/collision:** separate coarse geometry; splats alone are never treated as solid objects.
- **Editor:** new rigid assets and scene metadata, non-destructive to the base reconstruction.
- **Validator:** offline metrics and confidence/coverage diagnostics.
- **Simulation:** low-cost deterministic navigation checks, not a substitute for physically accurate Isaac/CARLA.
- **Workflow:** report, approval, and audit logs.

### Component interfaces

Keep adapters behind stable Python interfaces:

```python
class SceneImporter:
    def ingest(self, source_path, output_path, config) -> "SceneManifest": ...

class ReconstructionBackend:
    def train(self, dataset_manifest, config, output_dir) -> "SceneArtifact": ...
    def render(self, scene_artifact, cameras, outputs=("rgb", "depth")) -> "RenderBatch": ...

class GeometryBackend:
    def build_collision_proxy(self, dataset_manifest, config, output_dir) -> "GeometryArtifact": ...

class PerceptionBackend:
    def predict(self, images, config) -> "PredictionBatch": ...

class Evaluator:
    def evaluate(self, scene, split_manifest, config, output_dir) -> "EvaluationReport": ...

class SimulationBackend:
    def run(self, scene, scenario, config) -> "SimulationReport": ...
```

These are *design targets*, not assumptions about third-party library classes. Keep training GPU dependencies separate from the API/UI environment.

---

## 4. Technical stack

| Layer | Preferred implementation | Notes |
|---|---|---|
| Language | Python 3.11 (or a version supported by pinned dependencies), TypeScript | Choose supported combination and lock it |
| Reconstruction | Nerfstudio Splatfacto + `gsplat`, wrapped in an adapter | Favor proven training pipeline; avoid rewriting 3DGS from scratch |
| Rendering | gsplat offline/server rendering | One reference renderer for scientific evaluation |
| RGB-D fusion | Open3D TSDF | Separate collision geometry; clearly mark proxy quality |
| Camera/data | OpenCV, NumPy, SciPy, Pillow | Validate depth units, pose conventions, calibration |
| Perception baseline | One small, fixed open-source detector or segmenter | Pin weights, class mapping, thresholds; use exactly the same backend on real and rendered frames |
| Metrics | PyTorch, scikit-image, LPIPS implementation (pin version) | Record image scaling, masks, and `data_range` |
| API/jobs | FastAPI, Pydantic, worker process / simple job queue | Prevent GPU training from blocking HTTP worker |
| Storage | Filesystem artifacts + SQLite for single-machine MVP | PostgreSQL only if needed later |
| Frontend | React + TypeScript + Three.js | 3DGS viewer library is a replaceable adapter |
| Browser splat rendering | Evaluate Three.js `GaussianSplat` (WebGPU) **or** a compatible viewer | Do not assume ordinary WebGLRenderer supports it; fallback to server-rendered camera views |
| Test/CI | pytest, Ruff, mypy (gradually), Vitest, Playwright smoke test, GitHub Actions | CPU CI; optional CUDA jobs locally |
| Experiments | JSON/YAML configs + CSV/Parquet outputs; MLflow optional | Reproducibility before dashboards |
| Deployment | Docker Compose for API, UI, worker | GPU-aware worker separate from CPU services |

**GPU budget:** Primary development environment is a GTX 1660 Ti with 6 GB VRAM. Start with one short indoor sequence, 480p or lower, limited frames, and conservative Gaussian counts. Use `gsplat` packed mode when applicable. Log actual peak VRAM. If training fails on 6 GB, reduce scene/image size or use a cloud GPU; do not promise every 3DGS run will fit.

**Simulator constraint:** Current Isaac Sim requirements are much higher than this laptop's GPU capacity. Do not make Isaac Sim a hard requirement for the MVP or local CI. An OpenUSD export is not equivalent to a validated Isaac Sim simulation; mark it experimental until tested in the target environment.

**Licensing:** Check the actual licenses of pretrained models, sample scenes, dataset redistribution, 3D viewer packages, and renderers before bundling artifacts or deploying a public demo. Keep public demo inputs privacy-safe, remove faces/identifiers when applicable, and never put copyrighted datasets in Git.

---

## 5. Data ingestion, representation, and coordinate conventions

### Supported data sources

**Priority order:**

1. Small built-in synthetic fixture with known poses, depth, and ground-truth mesh (for unit/CI tests).
2. One public posed RGB-D sequence from the TUM RGB-D benchmark, or small official Open3D RGB-D sample (for reproducible integration testing).
3. One personal RGB-D capture of a stationary room/corridor, including intrinsics and estimated/known poses.
4. Replica scene or another controlled synthetic scene with ground-truth geometry and annotations for stronger quantitative evaluation.
5. Later: COLMAP video, LiDAR, KITTI-360, dynamic scenes.

Do **not** require LiDAR in MVP. For RGB-only video, pose recovery is a separate pipeline; the first deliverable assumes known poses. RGB-D images without valid poses are **not** ready for reconstruction.

### Canonical scene dataset contract

```text
data/scenes/<scene_id>/
  manifest.json              # dataset metadata, units, cameras, privacy/license
  frames.jsonl               # frame id, timestamp, rgb/depth paths, camera id, c2w
  splits.json                # train/candidate/test immutable frame IDs
  rgb/                       # sampled or linked frames
  depth/                     # optional, documented scale and invalid pixels
  masks/                     # optional static/dynamic/privacy masks
  calib/                     # per-camera intrinsics, distortion, extrinsics
```

Minimum `manifest.json` fields: schema version, scene ID, source, license/attribution, image resolution, world units `meters`, coordinate convention, camera intrinsics model, depth scale and invalid value, pose provenance, split hash, capture conditions, and whether this is real or synthetic.

Minimum `frames.jsonl` fields: `frame_id`, `timestamp`, `camera_id`, `rgb_path`, optional `depth_path`, `T_world_camera` (4x4), frame group/sequence ID, and optional masks.

**Pose convention:** Use `T_world_camera` (`c2w`) internally. Treat all rigid transforms as 4x4 homogeneous matrices, world units in meters. Normalize to one canonical right-handed world frame, document the world-up axis, and implement conversion helpers for OpenCV view convention, gsplat viewmat (`world-to-camera`), Open3D, and Three.js. Include tests showing that world → camera → world and 3D → pixel → 3D round-trip within specified numerical tolerance. Never silently transpose/invert a pose.

### Split and leakage rules

- Train / candidate / test must be declared **before training**, versioned, and immutable during experiments.
- Prefer held-out camera positions or short trajectory blocks separated spatially from training views, instead of only random interleaved neighboring video frames.
- Avoid highly near-duplicate train/test images; report coverage and overlap in pose/view direction.
- Use a **development/validation set** for threshold tuning, a **candidate pool** for simulated recapture selection, and a distinct **frozen test set** for final conclusions. If data is too small, explicitly disclose a reduced protocol.
- A candidate's unseen RGB/depth is inaccessible to the selection algorithm until selected; candidate **pose metadata** may be used if the research protocol explicitly allows it.
- The test set may be used only for final reported evaluation, never for choosing model hyperparameters, selecting candidate views, or fitting colliders.
- If a detector is fine-tuned, train it only on appropriately partitioned data and lock the detector before scene comparisons.

### Ingestion checks

- [ ] Paths exist; unreadable frames fail with actionable error.
- [ ] Timestamps are ordered and RGB/depth association tolerance documented.
- [ ] Dimensions/intrinsics match the loaded image; resize scales `fx, fy, cx, cy` correctly.
- [ ] Depth scale and zero/NaN/invalid values are explicit and tested.
- [ ] Pose matrices are finite, invertible, proper rotations within tolerance.
- [ ] Scene units/scale and world-up convention are consistent.
- [ ] Dataset manifest and split hash are saved with the run.
- [ ] If dynamic people/objects appear, mask or flag them as reconstruction limitations.

---

## 6. Reconstruction and geometry modules

### 6.1 3DGS backend

- Prefer a stable training implementation (`nerfstudio` Splatfacto) via a Python/CLI adapter to get checkpoints and Gaussian `.ply` export quickly.
- Keep a dedicated scientific render adapter using the trained checkpoint and its exact camera calibration.
- Make training preset configurations: `smoke` (tiny), `local_6gb` (limited resolution/frames), and `quality_cloud` (higher compute).
- Record initialization strategy (COLMAP/SfM points, RGB-D points, or random), iterations, image resolution, sampling, densification settings, seed, VRAM peak, total time, and final number of Gaussians.
- Do not convert between incompatible Gaussian `.ply` dialects without tested validation (attributes, SH coefficients, scale/opacities, orientation).
- Produce sample renders for both train and held-out camera poses, and export a provenance manifest.

**Exit test:** Fresh checkout + documented GPU environment can train or load one real scene, render a held-out pose, and produce deterministic metadata and evaluation files. Training may not be numerically deterministic across all CUDA kernels; state tolerances.

### 6.2 Coarse collision geometry

- Use RGB-D + valid camera poses and Open3D TSDF to build an initial mesh (or a simpler occupancy grid).
- Label this geometry `coarse` / `proxy`, not physically exact. Simplify and validate floor/walls/obstacles. Permit user to edit colliders manually.
- If no RGB-D, do not infer trustworthy collision geometry from a Gaussian `.ply` alone. Allow manual primitive colliders and mark their origin.
- Enforce consistent world coordinates with the 3DGS rendering scene.
- Export `collision_mesh.ply` or `.obj`, a transform, validity notes, and quality metrics where ground truth permits.

**Exit test:** A known box placed at a measured pose intersects the collision map where expected and has correct metric dimensions.

### 6.3 Rendered assets versus editability

- Base splats stay immutable in MVP. Newly inserted mesh assets are editable.
- MVP supports add/move/rotate/scale/hide/delete new objects only; **do not claim arbitrary base-scene object removal**.
- For visual occlusion, depth-test/composite inserted meshes against rendered splat depth with the **same camera**. If depth compositing is not yet reliable, clearly label the insertion as an overlay-only preview and do not use it for photorealistic perception experiments.
- Store mesh and collision transforms once in canonical coordinates; renderer and simulator consume identical object transforms.
- Avoid photorealistic claims about unseen surfaces revealed after scene edits.

---

## 7. Scene package and API contracts

### Portable scene package

```text
artifacts/scenes/<scene_id>/<version>/
  scene.json
  reconstruction/
    checkpoint/...            # optional, large, external reference allowed
    gaussian.ply
    renderer_config.json
  geometry/
    collision_mesh.ply
    occupancy_grid.npz
    geometry_report.json
  edits/
    objects.json
    scenarios.json
  evaluation/
    report.json
    per_view.csv
    overlays/...
  provenance.json
```

Suggested `scene.json` example:

```json
{
  "schema_version": "1.0",
  "scene_id": "corridor_demo",
  "version": 1,
  "world_units": "m",
  "world_frame": "canonical_right_handed_y_up",
  "render_asset": "reconstruction/gaussian.ply",
  "collision_asset": "geometry/collision_mesh.ply",
  "objects": "edits/objects.json",
  "scenarios": "edits/scenarios.json",
  "status": "draft",
  "approved_use_case": null
}
```

Update metadata atomically; maintain immutable version history when approved scenes change. Generated checkpoints/datasets should not live in Git.

### Minimal HTTP endpoints (version under `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service health, optional GPU info |
| `GET` | `/scenes` | List scenes and states |
| `POST` | `/scenes/import` | Validate/import manifest and return job ID |
| `POST` | `/scenes/{id}/reconstruct` | Queue reconstruction, preset/config reference |
| `GET` | `/jobs/{id}` | Status, logs summary, output paths, errors |
| `GET` | `/scenes/{id}` | Scene info, versions and artifact URLs |
| `POST` | `/scenes/{id}/render` | Render at specified verified camera pose |
| `PUT` | `/scenes/{id}/objects` | Persist scene edits with version check |
| `POST` | `/scenes/{id}/evaluate` | Queue frozen-split evaluation |
| `GET` | `/scenes/{id}/reports/{run_id}` | Metrics, assets, uncertainty/limits |
| `POST` | `/scenes/{id}/scenarios/run` | Run deterministic lightweight simulator |
| `POST` | `/scenes/{id}/submit` | Submit scene for review |
| `POST` | `/scenes/{id}/review` | Approve/reject with reason + scope |

- Structured errors with request IDs; validate uploads and prevent path traversal.
- For MVP, a single-machine worker queue is acceptable; use processes for GPU work and a persistent job state table.
- Authentication: minimal local Builder/Reviewer accounts or test fixtures. Never allow self-approval via role spoofing or client-only checks. Log approval decisions server-side. Document that this is not production-grade IAM.
- All large assets should stream from controlled artifact locations, not arbitrary client-supplied filesystem paths.

---

## 8. Frontend UX

### Views

1. **Scene Library:** scene thumbnails, source type, reconstruction status, review status, latest evaluation.
2. **3D Scene Editor:** splat or server-render view, camera controls, reference camera path, add/manipulate rigid proxy assets, toggle collision geometry, choose scenario.
3. **Evaluation Explorer:** side-by-side **real / rendered / residual**, per-view scores, depth discrepancy, detector overlays, error distribution, sorted failure views.
4. **Readiness Report:** measured view coverage, limitations, metric tables, uncertain areas, attached scenarios, and approval scope.
5. **Review Queue:** reject/approve with text justification and immutable log.
6. **Research Dashboard (P2):** baseline-vs-risk capture comparisons and run provenance.

### Frontend design constraints

- Provide screenshot-friendly states but build real functionality first.
- A badge saying `approved` must link to a recorded review, version, scope, and timestamp.
- Clearly distinguish **observed/validated**, **interpolated but tested**, and **unobserved/unverified** regions.
- Allow download of reports and scene manifests.
- Guard against incompatible viewer camera conventions. Tests should compare a simple known 3D marker in backend and browser projections.
- Keep browser free-view render quality separate from offline scientific render metrics if the browser uses a different renderer.

---

## 9. Evaluation and experimental methodology

### 9.1 Benchmark levels

| Level | Dataset | Available truth | Valid claims |
|---|---|---|---|
| Integration | Toy synthetic scene / Open3D sample | Known calibration or simple geometry | Technical correctness and reproducibility |
| Real scene | TUM RGB-D or personal capture | RGB-D, camera poses (depending on sequence) | Held-out rendering and real/render detection discrepancy |
| Controlled geometry | Replica or other permitted synthetic ground-truth scene | Renderer/mesh/depth/semantic truth | Geometry and perception accuracy on this synthetic domain |
| Sim scenario | Local deterministic occupancy navigation | Known collision rules and planned route | Route feasibility and collision behavior in **our** simplified simulator |

### 9.2 Render metrics

Evaluate only camera-aligned held-out views, after matching resolution, intrinsics, distortion, exposure assumptions, and image color space:

- PSNR (dB): state color domain, RGB range, and valid-pixel mask.
- SSIM: specify implementation, channel convention, image scale.
- LPIPS: pin network/version, input normalization and image scale.
- Depth MAE / RMSE (meters) on observed valid ground-truth pixels when calibrated depth exists.
- Depth completeness/valid fraction and optional robust relative depth error.
- Geometry: Chamfer distance and F-score **only if coordinate-aligned ground-truth mesh/point cloud exists**, with sampling density and alignment method specified. No geometric GT means `N/A`, not an invented number.

### 9.3 Perception consistency (core differentiator)

Use **the same fixed model**, weights, input preprocessing, confidence threshold, classes, and NMS for real and rendered frames. Save raw predictions and compare object-level correspondence (e.g., Hungarian matching with class agreement and IoU gate). Report:

- Detection count / confidence discrepancies.
- Matched-box IoU and localization error (pixels normalized by image size).
- Unmatched detections (appeared/disappeared) and class disagreement.
- Optional segmentation agreement with IoU/soft-mask metrics.
- Per-class and per-view breakdown; small/distant/occluded object slices.

**Crucial distinction:** Agreement between model predictions on real and rendered images is **not object detection accuracy**. Compute true precision/recall/mAP only on a manually annotated or otherwise valid ground-truth subset. A detector can make the same mistake in both domains. Ground-truth quality and label provenance must be reported.

### 9.4 Failure localization / readiness

Define separate diagnostics rather than an unexplained single magic score:

- **Visual inconsistency:** residual and LPIPS-based per-view ranking.
- **Task discrepancy:** object-level detector disagreement, localized boxes/masks.
- **Geometric discrepancy:** depth/mesh validation where truth exists.
- **Coverage:** distance and angular novelty relative to training cameras, observed depth support, and opacity/hole cues where defensible.
- **Simulator compatibility:** colliders exist, scale is metric, no major intersections, active objects have valid collision proxies.

A report may display **task-specific thresholds configured by reviewer**, but initial threshold choices should be declared heuristics and calibrated on validation data, not falsely labeled certified pass/fail thresholds.

**Recommended outcome:** `usable_for_declared_test`, `needs_review`, or `insufficient_evidence`, each with score components and scope. Never classify broad real-world safety.

### 9.5 Main experiments

**E0 — Technical correctness**

- Camera transforms and depth scale unit tests.
- View synthesis sanity: a held-out render has correct pose and image dimensions.
- Inserted obstacle visible at expected pose; collider agrees with asset transform.

**E1 — Image similarity vs perception discrepancy**

- Train one scene using the fixed training set.
- Evaluate each held-out camera with PSNR, SSIM, LPIPS, depth error, and detection discrepancy.
- Rank views by image quality and by task discrepancy; compare Spearman correlation and show counterexamples.
- On a labeled subset, measure relation to *true* detection errors, not only agreement.
- Report paired per-view measurements, not just an aggregate mean.

**E2 — Viewpoint robustness**

- Bin held-out viewpoints by distance/orientation from training cameras.
- Compare performance across bins, controlling for scene/visibility differences as much as feasible.
- Mark extrapolated views without real references as unverified; only use them for diagnostics, not for accuracy claims.

**E3 — Scene edit and navigation task**

- Use one scene and at least two manually placed obstacle variants.
- Validate transform alignment between render object and collider.
- Run same deterministic route planner/controller in the simple simulator; log route success, collisions, travel distance, path length, runtime.
- Do not claim this validates real robot behavior. For any perception impact of edits, require proper occlusion/compositing and disclose synthetic-object domain mismatch.

**E4 — P2 targeted recapture**

- Freeze untouched test views beforehand.
- Predict risk in candidate *poses* from currently available reconstruction/coverage/renders and validation-trained scoring rules; do not inspect candidate RGB/depth before selection.
- Select K additional observations by highest risk; compare with K uniformly random candidate frames and optionally a farthest-pose baseline.
- Use equal training steps, resolution, selected-frame count, evaluation detector, and fixed test set. Control seeds; repeat where feasible.
- Show results by reconstruction quality **and** task-specific metrics, including confidence intervals / variability when sample size permits.
- Include a failure analysis even if targeted recapture does not win.

### 9.6 Statistical hygiene

- Avoid claims of statistical significance from 5 highly correlated video frames.
- Use scene-level or pose-block-level summaries if possible, not independent-frame assumptions.
- Report sample counts, selection method, seeds, CIs/variation, and compute cost.
- Compare methods on exactly the same test frames and report unpaired/missing cases.
- Log how thresholds and metric weights were chosen.

### 9.7 Benchmark output contract

```text
experiments/<run_id>/
  config.yaml
  environment.json
  git_commit.txt
  dataset_and_split_hash.json
  per_view.csv
  metrics_summary.json
  predictions_real.jsonl
  predictions_rendered.jsonl
  visuals/
  report.html
  report.md
```

Every metric in the UI and README must trace back to these output files. **Never put placeholder metrics on the CV or in a research report.**

---

## 10. Simulation and export plan

### P1: Lightweight navigation simulation

Implement a deterministic CPU-only 2D/2.5D occupancy-grid simulator using coarse scene geometry:

- Import floor/obstacle collision representations; allow review/edits.
- Robot modeled as a circle or footprint with given radius.
- Define start, goal, waypoints, timestep, occupancy resolution, and obstacle placements.
- Implement or reuse A* grid planning, collision checking, route replay; dynamic agents are optional after static scenarios work.
- Validate map metric scale; log path length, collisions, route success, elapsed simulated time, and reproducibility seed.
- Produce a route overlay in the 3D viewer. Visually distinguish *simulated* motion from *real* robot performance.

### P3: External simulator adapter

- Define a backend-neutral `SimulationScene` schema including world scale, reference poses, mesh colliders, named rigid assets, movable trajectories, and optional visual splat assets.
- Build an OpenUSD exporter only after schema and collision tests pass.
- External simulation is **complete only if tested in an actual simulator** with correct scale, frame transforms, visual assets, physics collisions, and camera output. A file that merely loads is not closed-loop integration.
- Prefer running Isaac Sim on a compatible cloud/workstation rather than the 6 GB laptop.
- If CARLA lacks a compatible direct splat rendering path in selected version, mark Gaussian playback as a separate renderer rather than inventing native support.

---

## 11. Repository layout

```text
simready/
  README.md
  PLAN.md                          # copy of this plan
  AGENTS.md                        # concise Codex working rules
  pyproject.toml
  uv.lock / requirements-lock.txt  # lock exact tested environment
  docker-compose.yml
  .github/workflows/ci.yml
  configs/
    scene_demo.yaml
    recon_smoke.yaml
    recon_local_6gb.yaml
    evaluation.yaml
    simulator.yaml
  src/simready/
    cli.py
    config.py
    data/                          # import, schema, splits, calibration
    geometry/                      # TSDF and collision proxies
    reconstruction/                # adapter(s) + render
    scene/                         # artifacts, edits, coordinates
    evaluation/                    # image, depth, perception, coverage
    simulation/                    # grid simulator + scenario replay
    workflow/                      # approval/state/audit
    api/                           # FastAPI routes and jobs
  frontend/
    src/
      pages/
      components/
      adapters/                    # splat viewer + render client
      api/
  tests/
    unit/
    integration/
    fixtures/                     # tiny synthetic fixtures only
  scripts/
    fetch_example_data.py
    prepare_dataset.py
    run_benchmark.py
    make_demo_assets.py
  docs/
    ARCHITECTURE.md
    DATASET_PROTOCOL.md
    EVALUATION_PROTOCOL.md
    DECISIONS.md
    PROGRESS.md
    LIMITATIONS.md
    CV_EVIDENCE.md
  experiments/                     # ignored outputs except small examples
  artifacts/                       # gitignored large assets
  data/                            # ignored raw datasets
```

Repo naming can adapt to actual tooling, but keep scientific logic separated from frontend/API and keep all inputs configurable.

---

## 12. Implementation milestones with exact definitions of done

### M0 — Repo bootstrap, data contracts, and mathematical sanity (P0)

**Tasks**

- [ ] Inspect CPU, GPU/VRAM, CUDA runtime, OS, available dependency versions, and disk space; record environment.
- [ ] Initialize package, `AGENTS.md`, CI, Ruff/pytest, frontend shell, README.
- [ ] Implement typed dataset/scene schemas and versioned manifest validation.
- [ ] Build tiny synthetic scene/camera fixture and documented transform conversions.
- [ ] Import one simple official RGB-D dataset/sample, save immutable splits.
- [ ] Add tests for intrinsics resizing, depth scale, transform round trip, projection, bad manifests, split overlaps.

**Definition of done**

`pytest` and lint pass on CPU; CLI can validate/import example scene; a known 3D point projects into an expected pixel; no train/test overlap. No GPU required.

### M1 — Reconstruction vertical slice (P0)

**Tasks**

- [ ] Integrate a stable 3DGS backend behind `ReconstructionBackend`.
- [ ] Add one `local_6gb` preset and one `smoke` preset.
- [ ] Train/load an actual small scene, export Gaussian artifact, and render supplied camera view(s).
- [ ] Store run config, versions, GPU memory, timing, sample images.
- [ ] Add CLI smoke path that loads a precomputed model or fixture when GPU training unavailable.

**Definition of done**

One scene is genuinely reconstructed, saved, reloaded, and rendered at held-out camera poses with logged provenance. If GPU constraints prevent training locally, use a separate available compatible GPU and document it; do not substitute a fake rendering.

### M2 — Geometry + editable scene (P0)

**Tasks**

- [ ] Create coarse TSDF geometry from RGB-D and known poses; align with Gaussian scene.
- [ ] Create `scene.json` and persistent versioned object transforms.
- [ ] Build 3D scene editor with add/move/rotate/scale/hide/delete new proxy assets.
- [ ] Implement asset persistence via API, reload, and version-conflict handling.
- [ ] Address occlusion, at minimum disclose overlay-only behavior until depth compositing is verified.
- [ ] Add screenshot/demo fixture with a visible placed box and corresponding collider.

**Definition of done**

A new object inserted at a known metric transform remains correctly placed after save/reload. Coordinate correctness is confirmed numerically and visually. UI is usable without retraining.

### M3 — Perception-aware validation (P0; key differentiator)

**Tasks**

- [ ] Implement PSNR/SSIM/LPIPS and depth metrics with explicit masks and units.
- [ ] Choose and pin one detector; save raw real/render predictions.
- [ ] Implement object matching and detection-disagreement metrics.
- [ ] Add failure heatmaps and per-view comparisons in a frontend page.
- [ ] Export reproducible per-view CSV + summary JSON + markdown/HTML report.
- [ ] Evaluate at least one real, held-out sequence and inspect 5–10 qualitative failure cases.

**Definition of done**

Run one command on a frozen test manifest; it produces real metrics, input/view provenance, plots, disagreement breakdowns, and a human-readable report. No test-frame leakage.

### M4 — Simulation-readiness and review workflow (P1)

**Tasks**

- [ ] Implement coverage/geometry/perception diagnostics and report uncertainty.
- [ ] Add draft/submit/approve/reject flow with separate Builder/Reviewer permissions and audit log.
- [ ] Create lightweight occupancy simulator, simple scenario editor, and route replay.
- [ ] Test a baseline layout and one inserted-obstacle layout; collect route and collision metrics.
- [ ] Export scene package with split render/collider assets and review scope.

**Definition of done**

The user can inspect/edit a reconstructed scene, run a navigation replay, view QA results, submit for review, and export the reviewed scene. Tests prohibit unauthorized self-approval.

### M5 — Research experiments and targeted recapture (P2)

**Tasks**

- [ ] Freeze baselines and test protocol before experimentation.
- [ ] Implement E1/E2 analyses and run across available scenes/view blocks.
- [ ] Define and validate a candidate viewpoint-risk function using only allowed information.
- [ ] Compare fixed-K risk recapture, random recapture, and optionally farthest-pose acquisition.
- [ ] Analyze gains/losses and failures with plots, reproducible scripts, and a research-style report.

**Definition of done**

A third party can reproduce the benchmark configuration and trace every result to a run and split. The report states failures, variance, scope, and relation to existing work. No claimed research novelty without a literature comparison.

### M6 — Polish, optimization, and shipping (P0/P1)

**Tasks**

- [ ] Run tests and inspect results end-to-end; fix UX and data integrity issues.
- [ ] Document all CLI commands, environment setup, dataset download steps, and licenses.
- [ ] Add a short demo video/script, architecture diagram, qualitative examples, failure cases, and quantitative results to README.
- [ ] Benchmark memory, reconstruction time, render FPS at specified resolution, evaluation throughput, p50/p95 API latency where meaningful.
- [ ] Verify fresh-install demo, fallback behavior, and disabled/unsupported feature labels.
- [ ] Produce `docs/CV_EVIDENCE.md`: only genuinely implemented features and measured results.

**Definition of done**

A reviewer can launch the demo in a clean setup, reproduce key figures, and understand both strengths and limitations without assistance.

### M7 — Optional advanced integration (P3)

Only after M6. Choose **one** high-value extension:

- **Option A:** Actual Isaac Sim/OpenUSD integration on compatible compute with collision and camera validation.
- **Option B:** Dynamic objects/agent trajectories and reproducible task scenarios.
- **Option C:** Occlusion-aware object removal/inpainting, with verified unknown regions and multi-view consistency evaluation.
- **Option D:** Controlled appearance/weather variations and a robustness benchmark; no claim of physical atmospheric accuracy without a validated sensor/lighting model.

Do not attempt all four unless earlier work is complete and supported by evidence.

---

## 13. Initial CLI and automation targets

These are *target interfaces* for Codex to implement and document, not currently executable commands:

```bash
# Dataset preparation and data integrity
simready data import --source data/raw/example --format tum_rgbd --out data/scenes/example
simready data validate --scene data/scenes/example
simready data split --scene data/scenes/example --config configs/scene_demo.yaml

# Reconstruction + export
simready recon train --scene data/scenes/example --preset local_6gb
simready recon render --artifact artifacts/scenes/example/1 --split test
simready geometry build --scene data/scenes/example --method tsdf

# Scientific evaluation and report
simready eval run --artifact artifacts/scenes/example/1 --config configs/evaluation.yaml
simready report build --run experiments/<run_id>

# Simulation and serving
simready sim run --scene artifacts/scenes/example/1 --scenario scenario_a
simready api serve

# Development/test
pytest -q
ruff check .
cd frontend && npm test
```

Create useful `Makefile` aliases such as `make setup`, `make test`, `make demo`, and `make benchmark`. For optional GPU tests, include a skip marker and documented reproducible GPU commands.

---

## 14. Quality assurance test matrix

| Layer | Must-test cases |
|---|---|
| Data schema | Missing file, wrong image size, non-finite pose, invalid depth scale, split overlap |
| Geometry | Pose inverse/round-trip, reprojection, known cube scale, world/frame conversions |
| Reconstruction | Checkpoint restore, unsupported render mode error, matching K/pose dimensions |
| Metrics | Identical image PSNR handling, mask correctness, LPIPS normalization, depth invalids |
| Detection matching | Class mismatch, empty detections, duplicate matches, confidence thresholds |
| Assets/editor | Transform persistence, version conflict, object deletes, collision alignment |
| Renderer/UI | Backend/frontend known-marker projection parity, error states, viewer fallback |
| Job system | Restart/resume state, failed worker, GPU OOM report, path safety |
| Review | Unauthorized submission/review, self-approval, version invalidation after edit |
| Simulation | Collision at known coordinates, obstacle reroute, deterministic replay |
| Evaluation protocol | Test-set leakage guard, immutable split hash, provenance completeness |
| CI | CPU-only install, unit/integration suite, frontend build, sample report generation |

Avoid trusting synthetic fixture tests alone; at least one full integration run must operate on real collected or public posed images.

---

## 15. Key risks and mitigations

| Risk | Mitigation |
|---|---|
| GPU OOM during 3DGS training | Small scenes, downsampling, conservative Gaussian limits, separate cloud training |
| Incorrect camera frames/scale | Single canonical convention, projection tests, render of known markers |
| False confidence from photorealism | Task-aware evaluation, observed coverage, explicit unknown/unverified zones |
| Train/test leakage | Immutable split manifests, image-access restrictions, pose-block splits |
| Detector agreement hides shared mistakes | Ground-truth subset, report agreement separately from accuracy |
| Geometry not suitable for physics | Independent coarse collision mesh/proxies, reviewer adjustments |
| Gaussian/mesh insertion visual artifacts | Depth-aware compositing or transparent overlay-only limitation |
| External simulator too resource-intensive | CPU navigation simulator first; tested adapter only on compatible hardware |
| Hard-to-repeat results | Version pins, configs, seeds, dataset hashes, artifact provenance |
| Feature creep | Strict P0 → P1 → P2 → P3 priority; milestone gates and non-goals |
| No scientific novelty | Benchmark carefully, compare to current literature, label extension as exploratory |
| Dataset/model licensing or privacy | License manifest, sanitized capture, no raw restricted data in repository |

---

## 16. Research references and engineering documentation

Read enough to make correct implementation choices; do not block M0 on exhaustive literature review.

### Work motivating this project

1. **YUBI-Real2Sim: 3DGS Scene Verification for Reliable Policy Evaluation** (arXiv, October 2026): specifically studies scene artifacts and the reliability of policy evaluation, including limits of quality-based prediction. https://arxiv.org/abs/2610.17521
2. **RE³SIM: Generating High-Fidelity Simulation Data via 3D-Photorealistic Real-to-Sim for Robotic Manipulation** (ICRA 2026). https://re3sim.github.io/
3. **Scalable Real2Sim: Physics-Aware Asset Generation Via Robotic Pick-and-Place Setups** (2025): distinction between visual geometry, colliders, and physical properties. https://arxiv.org/abs/2503.00370
4. **Replica Dataset:** dense indoor geometry and semantics. https://github.com/facebookresearch/Replica-Dataset
5. **NVIDIA Isaac Sim:** background on OpenUSD-based robotic simulation and real-world capture integration. https://developer.nvidia.com/isaac/sim

### Implementation sources

- gsplat docs and rasterization modes (RGB, RGB+depth, packed memory): https://docs.gsplat.studio/main/apis/rasterization.html
- Nerfstudio Splatfacto training and Gaussian export: https://docs.nerf.studio/nerfology/methods/splat.html
- Nerfstudio custom RGB/video datasets and camera poses: https://docs.nerf.studio/quickstart/custom_dataset.html
- Open3D RGB-D / TSDF fusion: https://www.open3d.org/docs/latest/tutorial/pipelines/rgbd_integration.html
- Open3D tensor-based integration: https://www.open3d.org/docs/latest/tutorial/t_reconstruction_system/integration.html
- Three.js GaussianSplat (note WebGPU requirements): https://threejs.org/docs/pages/GaussianSplat.html
- TUM RGB-D dataset and sample scenes: https://cvg.cit.tum.de/data/datasets/rgbd-dataset
- Isaac Sim hardware requirements: https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html

**Literature-integrity requirement:** Before describing a proposed technique as novel, survey closely related work published through the experiment date. Verify each claim against the actual paper; don't infer novelty from having built a dashboard.

---

## 17. Deliverables and public portfolio presentation

Final deliverables:

- Public repository with code, licenses, tests, configs, data-fetch instructions, and reproducible experiment entry points.
- Working scene reconstruction with at least one recorded indoor scene.
- Web demo: viewer + insertion/editing + QA explorer + scenario replay + review workflow.
- One dataset-backed evaluation report with per-view qualitative results and measured numbers.
- At least one failure case where visual similarity alone was insufficient to understand a reconstruction defect (if supported by actual observations).
- Documented limitations and unsupported cases, including unknown-camera regions and simulator differences.
- Short walkthrough video showing **input → reconstruction → edit → evaluation → simulator replay → review**.
- Optional P2 experiment report with baseline and ablation.

**README outline:** motivation, 30-second demo, architecture, exact setup, supported datasets, core results, qualitative failures, reproducibility, limitations, future work, citations. Show real graphs and link to artifacts; no invented rankings or speedups.

**Potential future CV bullet template — use only after implementation:**

> Built **SimReady**, an editable RGB-D-to-3DGS Real2Sim pipeline with scene-level collision proxies, obstacle insertion, and perception-aware reconstruction validation. Evaluated held-out viewpoint fidelity and detector consistency on [dataset/scene count], and benchmarked [measured result] against [baseline] under [hardware].

---

## 18. Codex execution protocol

1. **Start by reading this entire file** and inspecting the actual repo and available compute. List what exists versus what is proposed.
2. Create `docs/PROGRESS.md` as a milestone checklist and `docs/DECISIONS.md` for implementation tradeoffs; keep both updated.
3. Work on **M0 only** first. Provide a brief implementation plan and then implement it end-to-end without asking open-ended design questions unless absolutely blocked.
4. For every milestone: implement → run automated tests → manually smoke-test critical path → record commands/results → update docs → summarize what is done, incomplete, and next.
5. Prefer existing, maintained research libraries over unnecessary reimplementations. Abstract them behind adapters.
6. Use real inputs, saved predictions, and experimentally measured numbers. Do not hardcode success metrics or pretend toy fixtures are real reconstructions.
7. Maintain careful train/candidate/test separation and never use test observations to guide acquisition, fitting, or tuning.
8. If something cannot work on the available GPU, show the exact blocker and the viable fallback. Keep P0 runnable without Isaac/CARLA.
9. Do not silently weaken acceptance tests or delete failing tests to claim a milestone passed.
10. At each milestone, emit a concise status report with files changed, tests executed, evidence, unresolved risks, and a precise next task.

### First instruction to paste into Codex

```text
Read PLAN.md thoroughly. Treat it as the project specification. First inspect the current repository, OS, Python/Node environment, CUDA/GPU capabilities, and disk space. Create AGENTS.md, docs/DECISIONS.md, and docs/PROGRESS.md. Implement only Milestone M0 (repo scaffold, canonical RGB-D dataset contract, synthetic camera/geometry fixture, real sample import, immutable split manifest, camera/depth validation, CPU tests and CI). Make reasonable implementation decisions, document them, and keep the interface ready for subsequent milestones. Run the actual tests before reporting completion. Do not claim that reconstruction, perception evaluation, simulation, or frontend features exist until implemented.
```

---

**End-state definition:** SimReady is complete as a portfolio project when a real captured scene has been reconstructed, an engineer can meaningfully edit it, the system provides a reproducible task-aware validation report on held-out views, and a basic scenario can be run and reviewed. The recapture study and Isaac/CARLA adapters increase research/production depth but are not required to call the core product completed.
