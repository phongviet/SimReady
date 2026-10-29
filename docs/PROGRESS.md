# Progress

Actual execution: **2026-10-29 (Asia/Bangkok)**. User-requested Git dates across
June–October are documented in `DECISIONS.md`; they are not experiment timestamps.

**Correction found during M1:** Open3D's Redwood sample is synthetic ICL-NUIM,
not real capture. The earlier `real` importer label and corresponding M0 wording
below were incorrect. They are retained as historical execution records, with
classification explicitly superseded. New imports use `synthetic`; validators
reject the old mislabeled datasets/artifacts. Real-capture acceptance uses TUM.

## Initial inspection

Only `PLAN.md` and a Windows download metadata sidecar existed. There was no Git
repository, source, environment, tests, frontend or sample data. Environment and
exact tested package versions are recorded in `ENVIRONMENT.md` and the lockfiles.

## Milestones

- [x] **M0 complete locally:** repo bootstrap, typed versioned data/scene contracts,
  camera math, analytic fixture, official real RGB-D import, frozen splits, tests,
  frontend shell, CI configuration and documented acceptance.
- [x] **M1 complete locally:** actual real TUM reconstruction, checkpoint/PLY,
  held-out RGB/depth rendering, isolated GPU runtime and CPU demo. See M1_CHECKLIST.md.
- [x] **M2 complete locally:** independent TSDF, versioned proxy edits, controlled
  local API, working splat/orbit editor, conflict handling and browser evidence.
- [ ] M3: perception validation (implementation and acceptance checks in progress).
- [ ] M4: simulation and review (not started).
- [ ] M5: research experiments (not started).
- [ ] M6: shipping (not started).
- [ ] M7: optional integrations (not started).

Detailed acceptance criteria: [M0 checklist](M0_CHECKLIST.md).

## Verified commands and evidence

| Command/check | Actual outcome |
|---|---|
| `make setup` | Locked Python sync and clean `npm ci` passed |
| `make test` | 80 Python tests passed (including real input), 1 frontend test passed, TypeScript/Vite production build passed; Ruff lint and format checks passed |
| `make demo` | Eight-frame analytic fixture validates; 4/1/1/2 splits |
| `make test-real` | Official sample validated; real integration test passed, 79 deselected |
| Fresh `simready data import` into `data/scenes/redwood-m0-verified` | Five real RGB-D pairs imported, validated; supplied estimated poses and 2/1/1/1 frozen splits |
| CLI error and repeat-import checks | Automated tests confirm exit 2, actionable errors and no overwrite |
| Known point projection | Camera point (0.4,-0.2,2)m projects to pixel (419.5,199.5) for declared test calibration |
| Transform/pixel round trips | Float64 tests pass at 1e-12 absolute tolerance; proper rotation checks reject invalid poses |
| Live local Vite HTTP smoke | `/`, `/src/main.tsx`, `/src/App.tsx` returned HTTP 200 with expected content; server stopped afterward |
| `npm audit` after dependency updates | Zero vulnerabilities reported at verification time |
| `uv lock --check`, `git diff --check` | Passed |
| `make storage` | About 0.30 GB including .git/.venv/node_modules/caches/data; below 30 GB decimal |

The official ZIP is 3,772,513 bytes and matched the publisher MD5 plus pinned
SHA-256. Raw data and imported scenes remain local and gitignored. Small actual
validation outputs are saved in [evidence](evidence/m0-provenance.json), with
[real-sample validation](evidence/redwood-validation.json) and
[synthetic validation](evidence/synthetic-validation.json). These are integrity
counts/hashes, not reconstruction quality or experimental results.

Development proceeded through bootstrap, camera/contracts (54 passing tests),
real import/adversarial checks (79 passing tests), then a four-frame split boundary
regression (final 80 passing tests) and frontend/CI acceptance. The four-frame
allocation was fixed rather than weakening nonempty split checks. The final
source tree retains every test.

## Limits and next task

Hosted CI has not run: there is no configured remote and nothing was published.
The UI is only a scope shell; HTTP smoke is not a visual/browser interaction test.
Real sample timing uses indices, world-up is nominal, odometry is supplied/estimated,
data redistribution terms remain unverified, and adjacent tiny split blocks are
not statistically independent. See `DATASET_PROTOCOL.md` and `LIMITATIONS.md`.

No reconstruction, perception metrics, navigation, approval or recapture
experiments exist. No experimental results are reported.

## Full-project continuation

The user subsequently authorized completing the full project. M0 evidence above
is historical. M1 now has an isolated Python3.10 / torch2.4.1+cu124 /
gsplat1.5.3+pt24cu124 worker, with an actual CUDA render/backward witness and a
fresh-agent documentation pass. A 40-iteration synthetic Redwood RGB-D smoke run
produced 1,283 learned Gaussians from 935 training-only depth points, exported
PLY/NPZ, and reloaded to render a validation pose. This is an integration result,
not a reconstruction-quality finding. A separate 1,200-iteration synthetic run
produced 9,187 Gaussians and rendered a frozen test pose; its original metadata
was wrongly labeled real and is rejected by the corrected validator. It does
not satisfy real-capture acceptance. The CPU suite passed 93 tests before the
optional GPU integration test was added; later non-GPU checks passed 105 tests,
with real TUM integration explicitly skipped pending its live download. Full
M1's real-data gate subsequently passed on the actual TUM capture.

Scope/status descriptions elsewhere referring to M0 only are historical and are
being updated incrementally. M2+ remain unimplemented. No perception metrics,
navigation, approval or recapture experiments have run.

## M1 acceptance (2026-10-29)

- Actual official TUM archive: 344,011,403 bytes; SHA-256 pinned in
  `configs/tum_fr1_desk.source.json`. Source and CC BY 4.0 attribution verified.
- 100 real RGB-D frames imported; unique <=20ms associations, motion-capture
  pose interpolation, publisher-recommended pinhole approximation, frozen
  **50 train / 16 validation / 16 candidate / 18 test** split.
- Real training: committed `local_6gb` preset, 1,200 iterations, 320x240,
  10,000 training-only initial points -> **17,828 learned Gaussians**.
- NPZ/PLY saved and reloaded in a separate GPU process; all **18 frozen test
  cameras** rendered to RGB, expected axial depth and alpha. Content hashes,
  dimensions, finite depth and nonempty support verified for every output.
- Run source `3fcc516` was clean. Package/GPU versions, full configuration,
  dataset/split/content hashes, timing and allocated/reserved PyTorch memory
  peaks are recorded in [the actual artifact metadata](evidence/m1-tum-artifact.json).
  [Render metadata](evidence/m1-tum-renders.json) and
  [real data validation](evidence/tum-validation.json) are also checked in.
- CPU smoke loads a genuinely trained 421-Gaussian analytic model and two saved
  views, including from an isolated built wheel. It does not render live on CPU.
- Prior non-GPU run: 111 passed and 1 real-data skip; after real import, the
  required real-data test passed. CUDA training/reload/PLY/depth integration also
  passed. Final `make test`: **112 passed, 1 optional GPU skip**, Ruff lint/format,
  1 frontend test and TypeScript/Vite production build passed. Final
  `make test-gpu`: **1 passed, 112 deselected** on the actual local GPU.

Held-out image/perception quality has not been measured, and inspected real
renders show visible blur/artifacts. Training success is not a sim-readiness or
transfer claim. Dataset pose/calibration uncertainty and temporal/spatial overlap
are disclosed. Total conservative storage accounting remains about 11.6 GB,
under the 30 GB limit. No paid compute or external publication was used.

## M2 acceptance (2026-10-29)

- Open3D CPU 0.19.0 fused the 50 frozen real TUM training frames into an
  independent coarse TSDF: **28,007 vertices / 48,828 triangles**, 3cm voxels,
  identity world transform, no ICP or scene rescaling. Hashes and limitations are
  in [geometry evidence](evidence/m2-tum-geometry.json). No geometric GT error is claimed.
- The analytic TSDF surface stays within one voxel of its known 2m plane;
  numeric tests confirm metric dimensions, rotated box/surface intersection and
  identical visible/collider transforms.
- SQLite authoritative immutable revisions and expected-version transactions
  preserve inserted boxes/barriers, pose, size, visibility, collision flags and
  deletion history. Concurrent writers produce exactly one winner and one conflict.
- FastAPI serves registered asset keys with path containment and hashes; malformed
  edits/status spoofing are rejected. Request IDs and HTTP 409 conflict handling
  are implemented. Server is local/loopback; review authentication remains M4.
- The React/Three.js/Spark editor loads actual learned PLY splats, supports orbit,
  transform gizmos and numeric transforms, reference-camera selection, independent
  TSDF/collider toggles and save/reload. Saved-camera overlays remain available
  without WebGL2. An OrbitControls initialization bug was found visually and fixed;
  a stale save message was also corrected.
- Final Python suite with geometry installed: **129 passed, 1 optional GPU skip**.
  One upstream Starlette/httpx deprecation warning remains visible. Ruff passes.
  Frontend: **3 tests**, TypeScript/Vite build and format checks pass. Actual
  Playwright browser suite: **3 passed**, including pixel content/orbit changes,
  edits, reload, hide/delete, stale versions and saved-camera mode.
- The actual real TUM scene was registered, opened in Chromium, and a visible
  30cm box was saved at revision 2. No browser page errors were observed.
  [Real-scene screenshot](evidence/m2-tum-editor.png) (derived TUM data, CC BY 4.0;
  Sturm et al., IROS 2012) and [analytic box + collider screenshot](evidence/m2-analytic-editor.png)
  are actual browser captures. Base reconstruction remains unchanged.
- CI now includes CPU, optional CPU TSDF, official sample and browser jobs;
  hosted execution remains unverified because no remote is configured.
- Conservative project storage is about **13.2 GB / 30 GB**, including dependencies,
  browser runtime/caches and local data/artifacts. Acquisition/install preflights
  reserve space for optional components.

Rendering limitation: inserted meshes are **overlay-only**, without validated
splat-depth occlusion. Browser output is not used for scientific perception
metrics. Coarse mesh holes, uncertain calibration/poses and unknown space remain
unverified. There is still no evaluation, simulation, approval or recapture result.

**Next:** M3, pin one detector/LPIPS implementation, evaluate camera-aligned real
and gsplat views on the frozen test split, save raw predictions/per-view metrics,
and build the evaluation explorer/report with actual failure cases. Continue
toward the full project; M3–M6 remain open.

## M3 implementation, acceptance pending

Pinned SSDLite320 COCO_V1 and LPIPS0.1.4 Squeeze/v0.1 before real test evaluation.
Both GPU witnesses and an independent fresh-agent follows-doc pass succeeded.
Spec3db6217d retains torch2.4.1/gsplat1.5.3. The initial actual two-view analytic
pipeline run produced RGB/depth metrics and saved raw predictions (both filtered
prediction sets empty, so no task-quality claim). Early tests caught integer IoU
output casting and Python symlink resolution escaping the GPU venv; both were
fixed before any real evaluation. Frozen provenance, exact split camera checks,
CSV/JSON/Markdown/HTML exports, persistent local evaluation queue and explorer
are implemented; full acceptance and real results remain pending.
