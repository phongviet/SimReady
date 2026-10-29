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
- [x] M3: perception validation, real held-out report and nine inspected failures; see M3_CHECKLIST.md.
- [x] M4: readiness, local roles, scoped review/audit, navigation and reviewed exports; see M4_CHECKLIST.md.
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

## M3 acceptance (2026-10-29)

Complete local frozen-view pipeline, pinned metric/detector definitions,
raw predictions and Hungarian discrepancy traces, HTML/Markdown/CSV/JSON exports,
heatmaps, an actual evaluation explorer, and persistent serialized process jobs.
The real run from clean source06114ba evaluated all18 immutable test views:
mean PSNR16.73498062647631dB, SSIM0.5177023670227732,
LPIPS Squeeze0.4032108618153466, supported-depth MAE0.030070565783854666m,
RMSE0.07341390428977546m and completeness0.9437883254681552.
At the fixed0.5 confidence threshold: 48 real predictions, 0 rendered, 0 matched,
48 disappeared, 0 appeared. These are summed predictions across correlated views,
not unique objects or object detection accuracy. No threshold was tuned on test.

Nine highest-LPIPS paired views were visually inspected and documented in
M3_FAILURE_CASES.md. They show blur/detail loss, object-edge residuals and
unmatched predictions; the baseline's perception failure is retained honestly.
Reports and UI distinguish base offline evaluation from browser proxy overlays.
The CPU demo now bundles an actually measured analytic report from the same clean
source (both filtered predictions empty; no positive task-quality inference).
An isolated installed wheel loaded this report without GPU or geometry packages.

Verification: 140 CPU/geometry tests passed, 2 opt-in GPU skips; the new actual
queued GPU evaluation separately passed. Four frontend unit and four Playwright
browser tests passed, including paired image loading, failure selection, overlay
toggle, CSV download and portable HTML images. TypeScript/Vite, Ruff, format,
lock and diff checks passed. An actual queue run demonstrated report binding to
the submitted revision after a later edit; injected backend failures persist in
SQLite with actionable logs. Hosted CI remains unrun (no remote).

M4 simulation/readiness/review, M5 recapture research and M6 shipping remain
unimplemented. M3 does not establish a ready scene or detection accuracy.

M3 final storage: **14,086,309,730 bytes / 30,000,000,000**, including installed
wheel-test caches, CUDA/core environments, raw data, reports and Git before the
evidence commit. The temporary verification API was stopped cleanly.

## M4 navigation vertical slice (milestone still in progress)

Implemented bounded metric occupancy, observed TSDF support versus explicitly
assumed virtual floor, unknown/exterior blocking, robot inflation, collidable
proxy volumes, deterministic four-neighbor A*, waypoints and swept replay.
Scenarios save as immutable scene revisions. Actual runs save geometry/source/
config hashes, map JSON/NPZ, trajectory/metrics and route images. The Navigation
UI edits scenarios, selects saved runs, and animates a robot/route overlay using
that run's saved scene objects. It distinguishes simulated motion from real
performance and declared virtual support from observed floor surfaces.

Verification so far: six simulator unit tests plus existing scene tests (20 total)
passed; simulator/API targeted checks passed (9 total); five frontend unit and
five actual Playwright tests passed. Browser checks verify pixel changes and the
actual 3D robot position at the route endpoint, save/reload, and a hidden collider
blocking the start. The initial UI test exposed a request wait issue and software
WebGL contention; no pixel/orbit correctness assertion was removed. Add activity
cadence and optimize the full storage scan while preserving conservative bytes.
The successful complete browser run took35.4s; this is a test duration, not a
render performance benchmark. Full current-worktree CPU/geometry regression after these changes passed150tests
with2opt-in GPU skips; lint/format and production build also passed.

A development geometry probe on real TUM TSDF found947floor-support cells and
125free robot-center cells; the largest connected component had100cells. The
selected nominal-floor example planned1.05m. These are development diagnostics,
not yet the clean committed multi-layout M4 acceptance runs. The endpoints were
chosen from the known supported map, not an independent real navigation task.

Local opaque-token account foundations have two passing unit tests, but are not
yet wired into HTTP/UI permissions. Scoped submission/review, coverage/readiness
reports, audit and reviewed exports remain unimplemented. Do not treat M4 as
complete or the current local API as authenticated.

### M4 real navigation regression verified

From clean committed source1afbb60, `scripts/run_navigation_layouts.py` created
`artifacts/m4-navigation-1` and ran the pinned real-TUM coarse-floor scenario.
Baseline: route/travel1.05m, simulated7s, collisions0. Inserted0.15m box: detour
1.15m, simulated7.6667s, collisions0. Inserted0.8m barrier: no route, null planned
length, zero travel/time/collisions. All947support and5269unknown floor cells
remain explicit. Permitted robot-center cells125/83/68. Inputs and all run asset
hashes verified; manifests record clean source and immutable versions3/4/5.
See SIMULATION_PROTOCOL.md and evidence/m4-navigation-acceptance.json.
This satisfies the navigation comparison vertical slice, not full M4 acceptance.
Readiness, HTTP role enforcement, scoped decisions/audit and reviewed export are
still pending. Current full-project goal remains active.

## M4 readiness/review implementation, real acceptance pending

Measured camera novelty, mesh topology/surface diagnostics, actual perception
flags and exact-revision navigation feed separate readiness components. There is
no automatic safety/quality certificate. Authenticated server-assigned local roles
now gate all HTTP mutations. Scope restricts measured camera IDs and tested map
bounds/expected navigation result. Submission/decisions create immutable revisions
and transactional append-only audit; self-review after role changes is forbidden.
Later edits clear current approval, while old decisions remain inspectable.
Reviewed ZIPs preserve source/content/evidence hashes, separate splats/colliders,
and exclude tokens/DB/weights. QA retains its original pre-decision bytes.

Verification: full CPU/geometry suite157passed,2opt-in GPU skips;5frontend unit
and6real browser tests passed. Tests cover role/header spoofing, anonymous and
wrong-role mutations, self-review after role changes, concurrent decisions,
tampered evidence, contradictory declared outcomes, exported payload hashes,
immutable history and edit invalidation. Full real-TUM review/export acceptance
is the remaining M4 gate. The opt-in authenticated GPU queue regression
separately passed1test with actual rendering/detection/LPIPS.

## M4 acceptance (2026-10-29)

Full local acceptance passed:158CPU/geometry tests with2opt-in GPU skips,
1separate actual authenticated GPU evaluation test,5frontend unit tests,
6browser tests, build/lint/format/lock/diff checks. The real TUM workflow from
clean3d584ed captures source5, submits6 and records scoped approval7 using
explicitly automated distinct local-role fixtures. It approves only the declared
known-map obstruction regression (`no_route`), not perception accuracy or safety.
The original48-versus0detector predictions,6964mesh boundary edges and5269unknown
floor cells remain visible. Every payload of a27,017,824byte reviewed ZIP and its
SHA256 were verified. See REVIEW_PROTOCOL.md and the saved audit/QA/package manifest.

Further guardb20a246 rejects readiness/export if evidence is changed after
approval. A current-code real-package verification checks the existing recorded
approval without fabricating a new decision. Historical approved versions remain
readable/exportable after edits; self-review, client role spoof, wrong scope,
tampering and concurrent decisions are tested. Local account tokens stay in a
private0600file and never enter exported payloads. This is not production IAM.

M5 research/targeted recapture and M6 shipping remain unimplemented; the overall
full-project goal is active. M7 stays optional and conditional on M6.

M4 final current-code verification: cleanb20a246 reads the existing recorded
fixture approval and rebuilds/verifies all213ZIP payloads. It creates no new review
decision. Final storage: **14,239,961,486 / 30,000,000,000 bytes** including all
caches/environments/data/packages/Git before the acceptance commit. Temporary
HTTP verification server stopped cleanly. No hosted service or CI run is claimed.
