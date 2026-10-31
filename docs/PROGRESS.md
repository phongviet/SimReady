# Progress

Actual execution: **2026-10-29–30 (Asia/Bangkok)**. User-requested Git dates across
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
  camera math, analytic fixture, official synthetic RGB-D sample import, frozen splits, tests,
  frontend shell, CI configuration and documented acceptance.
- [x] **M1 complete locally:** actual real TUM reconstruction, checkpoint/PLY,
  held-out RGB/depth rendering, isolated GPU runtime and CPU demo. See M1_CHECKLIST.md.
- [x] **M2 complete locally:** independent TSDF, versioned proxy edits, controlled
  local API, working splat/orbit editor, conflict handling and browser evidence.
- [x] M3: perception validation, real held-out report and nine inspected failures; see M3_CHECKLIST.md.
- [x] M4: readiness, local roles, scoped review/audit, navigation and reviewed exports; see M4_CHECKLIST.md.
- [x] M5: real recapture study and labeled synthetic companion verified, with explicit negative/undefined outcomes.
- [x] M6: local release gates, public repository and actual hosted CI verified; see PUBLICATION.md.
- [ ] M7: optional integrations (not started).

Detailed acceptance criteria: [M0 checklist](M0_CHECKLIST.md).

Latest M0-only verification: [M0_REVERIFICATION.md](M0_REVERIFICATION.md).
The foundation passed 101 targeted CPU tests, five frontend unit tests, build,
lint/format and live dataset validation. Preexisting later milestone work was
preserved. These checks do not establish M5 acceptance or hosted CI execution.

## Historical M0 commands and evidence (source classification superseded above)

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

## M5 protocol and access boundaries (in progress)

Resumed the full-project goal. The written experiment plan freezes equal K4,
three optimization seeds, fresh1200-step base/recapture training and validation
fit/check blocks. M3's inspected test views cannot be called blind; the curator
will reserve18additional raw TUM pairs and disclose their temporal proximity.
Observation-scoped training validation avoids decoding candidate/test pixels;
ordinary full validation remains strict. Typed selector features exclude RGB/depth,
and candidate/test releases require matching complete sealed acquisitions.
Experiments, final fairness audit, analysis and dashboard are still pending.

Access guards passed22targeted tests and the full CPU/geometry regression:
161passed,2opt-in GPU skips. The complete selection-matrix fixture verifies
withheld pixels, named release, metadata-only camera access, strict full validation,
tampered decision rejection and deterministic selection/calibration arithmetic.
Its generated values are test fixtures, not experimental results.

### M5 actual acquisition and evaluation completed

Clean6947fb8 curated18new late TUM test pairs, preserving50train/16validation/
16candidate and excluding all original100observations. All9K4selections were
sealed before any candidate release. Three base models plus9fresh54frame models
ran1200steps each; all12models were evaluated on identical18test references.
All45stages completed with zero recorded failures. Run directory:
`experiments/tum-recapture-1`. No measured result is inferred from success alone.

Post-run deterministic checks validate every stage/content hash, replay all
acquisition decisions and216test-view RGB/depth/detector measurements, and verify
identical test observations, cameras, raw real predictions and fixed configurations.
Recorded source pins match historical Git objects. Analysis math/adversarial
tests passed; the fresh same-family semantic audit resumed after a usage-limit
interruption and has no completed verdict yet. Never treat its partial remarks
as acceptance. Storage after the raw matrix:15,494,459,790bytes, below30GB.

### M5 primary study, analysis and dashboard verified

The fresh audit completed: WARN for limited scope/local chronology and future
recovery hardening, with raw experiment evidence pass; same-family semantic
acceptance remains provisional. All163indexed inputs,264validation/test paired
records,636training RGB-D tensor pairs and45stage records were verified. See
EXPERIMENT_AUDIT.md/JSON; the initial usage error and raw review are retained.

Analysis from clean772e055 exports full benchmark-contract outputs, correlations,
common original50camera novelty bins, three6view blocks, paired seed variation,
figures and actual failure comparisons. Primary result is negative: mean LPIPS
base0.408576, risk0.416258, random0.401532, farthest0.410811. Paired risk-minus-
random+0.0147255±0.0042631sampleSD; higher LPIPS is worse. All fits set distance/
rotation coefficients to zero. No acquisition superiority or true accuracy claim.

The Research dashboard serves controlled immutable packages, downloads and raw
run provenance. CPU demo includes a2MBactual measured summary snapshot, explicitly
omitting raw predictions/checkpoints. The full package is registered locally as
tum-recapture-1. It is independent of the selected editor scene. Actual browser
capture has zero page errors; the verification server was stopped.

Current verification:170CPU/geometry tests passed,2opt-in GPU skips;5frontend
unit and7actual browser tests passed. Lint/format/build/lock/diff checks pass.
Concurrent browser cleanup exposed a disappearing-directory storage race; a
bounded full recount now preserves conservative accounting and fails closed on
repeated churn. Focused race/package tests passed after the fix. About15.55GB
total, below30GB. M5's labeled-object companion and two forward recovery fixes
remain explicit; M6 shipping and optional M7 remain open.

The first audit hardening item is now fixed: cached/missing-stage recovery compares
the saved full dataset/reference camera records, model digest and render-index
digest against the requested inputs. An internally hash-consistent report with a
different saved render digest is rejected.12targeted evaluation/resume tests
passed, and all15historical study evaluations passed the stronger read-only
binding check without rerunning inference. Timestamped atomic release completion
and partial-operation recovery remain pending, alongside the labeled E1 companion.

Release hardening now records timestamped started/resumed/failed/completed events
using serialized atomic ledger replacement. Completion follows verification;
candidate datasets left behind by interrupted completion are validated against
the sealed frames, partitions and calibration before reuse. Test release retries
verify existing linked bytes. Fault tests cover process death after candidate
materialization, failed partial test linking and failed ledger replacement;
9targeted research tests passed, with4gate/atomic tests repeated after stricter
metadata validation. Historical TUM outputs/ledger remain unchanged.

The remaining labeled-object E1 gap now has a pre-measurement companion protocol
in refine-logs/SUPPLEMENTAL_GT_PLAN.md. It uses authored procedural geometry for
truth, a genuine learned reconstruction and the unchanged detector; no synthetic
accuracy result is claimed yet. M6 shipping remains open.

The labeled companion now has authored bench geometry and independent analytic
ray-derived RGB-D/masks/boxes. Two numeric truth tests passed. Clean7112deb
trained a genuine model for1200steps on14training views and rendered/evaluated
all6frozen test views using the unchanged detector. Labels/geometry/manifest/plan
hashes were saved before training; detector metadata confirms bench category15.
See evidence/m5-bench-run.json. This is a synthetic-domain companion, not a
second real capture. Precision/recall/custom AP50 and true-error correlation
analysis remain pending; no accuracy result is claimed from pipeline success.

Companion analysis from clean81a8985 now verifies frozen truth hashes and replays
test masks/boxes from geometry. It computes class-only precision/recall/custom
101pointAP50 from raw predictions, with hand-calculated perfect/duplicate/false-
positive tests. All6synthetic bench observations are correctly detected in both
domains; precision/recall/AP50are1.0here. True-error changes are constant, so both
correlations are null, and no shared-miss counterexample is observed. This easy
one-object domain does not establish prediction of errors or real accuracy.
Evidence: m5-bench-summary.json and m5-bench-comparison.png. A fresh same-family
companion integrity reviewer is still running; M5 closure waits for that review.

M6 entry audit identifies missing queued import/reconstruction/render HTTP paths
despite existing CLI operations; these remain required implementation gaps.
A freshly installed wheel in .cache/m6-fresh-cpu passed saved421Gaussian/2view
CPU smoke, demo scene/report registration, measured12model snapshot loading and
API import with torch/Open3D absent. Isolation confirmed imports came from the
installed wheel. This does not verify the frontend in a fresh checkout or live
CPU neural rendering. Initial offline install used the wrong cache and failed;
using the project-local UV_CACHE_DIR succeeded. See m6-fresh-wheel.json.

M6 now includes a Builder-authenticated queued import endpoint and persistent
job polling backed by a real subprocess and SQLite state. Sources are controlled
inbox keys with bounded size/count, no symlinks and before/after digest checks.
The actual HTTP analytic import passed with8validated frames; anonymous, duplicate,
traversal and missing-source requests were rejected. Importer/HTTP focused checks
passed; reconstruction/render HTTP paths remain incomplete. PIPELINE_API.md
documents this exact current scope rather than implying an editable scene exists
immediately after import.

M5 companion review is complete: same-family/provisional WARN, no invalidation.
Independent replay reproduced all28geometry labels, the14view training buffer,
6evaluation rows and custom AP50. The synthetic outcome is saturated and cannot
establish failure prediction. BENCH_COMPANION_RESULTS.md and the full audit
retain that limitation. Generic no-annotation boilerplate is corrected for future
reports; historical outputs stay unchanged. M5 is complete locally within these
explicit scientific limits; the full project is still incomplete.

M6 queued reconstruction now accepts authenticated preset requests against
completed imports or registered datasets, captures a source digest, runs under
the shared GPU lock and serves only verified artifact keys. Actual CUDA HTTP
acceptance passed with import→40steptraining→artifact download; changed-source
failure and anonymous access checks passed. Focused API/import checks passed4
tests, and the new failure test separately passed with the GPU test visibly
skipped in its CPU run. Rendering HTTP and remaining shipping gates stay open.


### M6 supplied-camera render increment

2026-10-30: Added bounded calibrated camera requests and durable render jobs,
sharing the existing local GPU lock. Parent reconstruction IDs must match the
scene; model and output hashes bind jobs/downloads. Custom views are marked
unverified and excluded from held-out evaluation. Actual GPU HTTP import/train/
render/download test passed (2 tests,20.02s); CPU failure/validation tests passed
(2 passed,1 GPU skip). Full M6 shipping acceptance remains open.

Current-source CPU regression:179 passed,3 opt-in skips in138.44s; Ruff
lint/format passed, frontend5 tests and production build passed. Real TUM
100-frame dataset validation and saved421-Gaussian CPU smoke passed. A new
tampering test initially modified its source fixture; restored the exact Git
content, isolated the corrupt model copy, and reran the full suite successfully.
Architecture/limitations/README status now include completed M3–M5 behavior.

Final CUDA pipeline regression:3 passed in19.71s, including same-scene model
binding and all custom-view channel downloads. Postflight storage:
15,844,983,255bytes of30,000,000,000. M6 benchmarks, fresh-checkout UI,
walkthrough recording, CV evidence and complete requirements audit remain open.

### M6 benchmark implementation

2026-10-30: Added `scripts/run_benchmark.py`, isolated `workers/render_benchmark.py`,
`make benchmark` and `docs/BENCHMARK_PROTOCOL.md`. CLI help and Ruff pass. Measurement
results remain pending until the source-pinned actual GPU/evaluation/API run.


### M6 measured shipping performance

2026-10-30: `make benchmark` completed from clean df422ba.180 synchronized warm
320×240 RGB+ED frames:656.770FPS; fresh18-pair real TUM evaluation12.768s;
100 samples/endpoint loopback TCP p95health2.198ms/list3.813ms/detail3.491ms.
Raw sample recomputation, source pins and full evaluation binding passed.
Exact scopes/historical reconstruction metadata are in BENCHMARK_RESULTS.md;
source summary copied byte-identically into docs/evidence/m6-benchmark.json.
Postflight storage15,863,636,439bytes (<30GB). Benchmark processes terminated.
Fresh-checkout UI, walkthrough recording, CV evidence and final audit remain open.


### M6 fresh checkout UI acceptance

2026-10-30: Detached clean a407ddd checkout with independent CPU .venv,
node_modules, production build and seeded registry passed5 frontend tests and
all7 real browser tests in19.1s. Torch/Open3D absent; actual GPU evaluation job
failed explicitly with missing-worker message while saved reports remained intact.
CPU checkpoint smoke passed421 Gaussians/two saved views. Editor screenshot
visually inspected and copied with structured evidence; see FRESH_INSTALL.md.
Offline cache-only install initially lacked archives; locked online install passed.
Post-install full-project storage16,453,960,691bytes, including this ignored checkout.
M6 recording, CV evidence and full requirements audit remain open.

### M6 walkthrough tooling

2026-10-30: Added a fresh real-scene registry preparation script and an actual
browser video recorder with chapter timestamps. Syntax/lint checks pass; video
acceptance remains pending until the real UI workflow completes and is inspected.

### M6 replay overlay legibility fix

2026-10-30: Real-scene recording inspection exposed translucent occupancy-map
sorting over the route/robot. Diagnostic map, route and robot now have explicit
transparent-layer order and no depth writes; robot opacity is0.9. These remain
labeled overlays, not physical compositing.5 frontend tests, production build,
Prettier and all7 actual browser tests passed (31.8s). Final recording pending.


### M6 actual recording and CV evidence

2026-10-30: Final recording from clean3907377 completed the real TUM saved-model/
report workflow, metric box save, actual1.15m zero-collision route replay,
submission, distinct automated Reviewer approval and ZIP build. No page errors.
The50.8s1440×1000WebM played to completion; comparison/replay/review frames were
decoded and visually inspected. All213 exported payload hashes passed. Published
clip is10,120,465bytes, SHAee09273afc9afe8b36505e2d600d137f615e1eaa2d055b6c8f1302cb318897ce.
Source inputs, script hashes, chapters and limits are in evidence/m6-walkthrough.json
and WALKTHROUGH.md. Earlier registries/recordings remain ignored, never overwritten.
Recording server terminated. Added CV_EVIDENCE.md with explicit measured scopes,
negative recapture result and prohibited unsupported claims. M6 remains open for
current documentation/license/interface reconciliation and the final full audit.

### M6 specification reconciliation increment

2026-10-30: Added root source license and third-party/data notices, removed stale
README/scene/simulation statements, and repaired multi-study output indexing.
Actual reindex retained all previous rows and added companion/benchmark outputs
(5,455 files). Lint passes. Docker CLI reports no integration in this WSL distro;
no container runtime or hosted deployment is claimed. Native clean-install demo
is verified. Training-view sample renders and comprehensive interface audit follow.


### M6 concrete requirements audit and training samples

2026-10-30: Actual gsplat rendered50 original training cameras (150 RGB/depth/alpha
files) from the saved real baseline; cameras and content hashes verified exactly.
These are training samples, not held-out quality evidence. All25 installed CLI
help subprocesses passed; built wheel includes MIT/third-party notices and excludes
caches/dependencies. CLI.md/DEPLOYMENT.md map actual interfaces and native fallback.
REQUIREMENTS_AUDIT.md traces PLAN priorities/interfaces/milestones/deliverables and
keeps concrete gaps open: library thumbnails/latest QA, reference camera path,
final current-source regression/history/storage audit, and unconfigured public
publication. No M6/project completion is claimed from the documentation audit.


### M6 remaining UI requirements implemented

2026-10-30: SceneCard now displays a controlled saved-render thumbnail,
reconstruction/reference status and latest base QA with its source revision;
refreshes every10s and reports unavailable QA explicitly. Reference camera path
frames the scene/tested centers and draws diagnostic centers/polyline; connecting
segments do not imply coverage. Saved-view mode disables this control.
5frontend tests, TypeScript/Vite build, Prettier, Ruff and all8actual browser tests
passed (35.0s). New browser acceptance independently computes centers as-R^Tt,
verifies metadata/thumbnail and toggle/fallback. Screenshot visually inspected:
card metadata and cyan reference centers are visible, controls remain usable.
Final full CPU/GPU regression, history/credential/storage checks and publication
remain open; no whole-project completion is claimed.

### M6 current regression and containment follow-up

2026-10-30: Clean43ec61c CPU/geometry/research regression passed179tests with3CUDA
skips in152.91s, with real TUM and official synthetic sample explicitly enabled.
All536reachable Git blobs were scanned for declared credential patterns: zero
findings/forbidden tracked output paths/over20MBblobs.133local Markdown links
exist (47documents); raw audit links intentionally include local study outputs.
Found252MBof legacy pytest temporary output outside the project; moved future
test basetemp into ignored `.cache/pytest` for budget accounting and serialized
acceptance. Reverification follows this configuration change.


### M6 local release verification

2026-10-30: Tested source22afb45 passed179CPU tests/3CUDA skips in148.24s with
geometry/research extras and real/official data enabled; actual CUDA suite passed
3tests in39.58s. A second independent clean CPU checkout passed saved421-Gaussian/
two-view smoke,38-route API import,5frontend tests/build and8browser tests in20.7s.
Ruff/Prettier/whitespace and licensed wheel content checks passed. Current-source
artifact replay verified45stages/12models/216test rows, package/companion hashes,
real TSDF,213reviewed ZIP payloads and video hash, without rerunning neural
inference or inventing a new semantic verdict.547Git blobs including unreachable
objects had zero declared credential-pattern hits;52commit trees had no forbidden
outputs; fsck had no corrupt/missing object errors (dangling objects preserved).
Evidence capture combined root/legacy external pytest upper bound17,792,987,490bytes
(<30GB). FINAL_VERIFICATION.md and JSON retain scopes. Only public publication /
hosted CI remain open; destination requested asynchronously. Full goal remains active.

### Release handoff portability finding

2026-10-30: RC1 source/history/wheel archives were created and bundle-verified.
A further restore under Git core.autocrlf=true reproduced a train-job.json hash
mismatch from line-ending conversion. Root evidence stayed unchanged. Added Git
attributes protecting hashed demo/evidence bytes and LF source checkout; actual
restore recheck follows. Preserve RC1 rather than rewriting its tag.

### Byte-exact checkout reverified

2026-10-30: Fresh clone with core.autocrlf=true imported the cloned source and
passed saved421-Gaussian/two-view smoke plus geometry, evaluation and measured
research package hashes after f864106's checkout-policy fix. No application code
changed from tested22afb45. RC1 tag/archives stay preserved; RC2 and its checksums
are prepared next. Bundle restore explicitly selects main. Public publication
remains pending the destination/account already requested.

### RC2 handoff verified; publication prerequisite remains

2026-10-30: Annotated v0.0.1-rc.2 points to191105d. Its full-history bundle (HEAD,
main, tag),354-entry source archive and CPU wheel have verified checksums under
artifacts/releases/v0.0.1-rc.2. Restored the actual bundle on main with
core.autocrlf=true and validated the cloned421-Gaussian/two-view checkpoint and
research package. Runtime code-tree descriptor exactly matches tested22afb45;
checkout policy is separately pinned/verified. RC1 is preserved and superseded.
Tool stdout logs were moved into ignored project cache for accounting. Combined
project plus conservative legacy external pytest accounting is about18.0GB,
below30GB; exact postflight in evidence/m6-release-candidate.json.
Local source/archive/wheel are concrete and reviewable. No Git remote, credential
helper, GitHub tool/account or public destination is configured. Destination was
requested through the pending async question; no publication/hosted CI is claimed.
The full project goal remains active awaiting that required information.

### Public repository published; hosted CI findings

2026-10-30: User supplied git@github.com:phongviet/SimReady.git. SSH read access
worked; the destination was verified public/empty. Published main a0ff29f and
v0.0.1-rc.2 without overwriting history. Actual hosted run41002058943 passed
public synthetic sample and frontend/browser jobs; CPU/geometry tests failed.
Direct log-download API needs additional admin authentication; public check
annotations exposed exit codes but not test traces. Added bounded JUnit failure
annotations (escaped, preserving test failures) and pinned the runner to tested
Ubuntu24.04 rather than migrating ubuntu-latest. Exact failing assertions remain
unproven until the diagnostic run. No all-green/whole-project claim is made.

### Hosted cold-cache failure diagnosed

2026-10-30: Run41002399387 annotations reproduce FileNotFoundError creating
.cache/pytest because its parent does not exist on the fresh runner. Pinning
Ubuntu did not fix that independent configuration bug. Added a pytest configure
hook creating only basetemp's parent; pytest retains ownership/cleanup of its base.
No tests or assertions were skipped/weakened. Cold-checkout and hosted rechecks
follow; initial hosted failures remain recorded rather than called successful.

### M6 public acceptance passed

2026-10-30: Public repository https://github.com/phongviet/SimReady verified.
Actual hosted run41002820745 on f007390 completed successfully for CPU, official
synthetic sample, geometry and frontend/browser jobs. Earlier two hosted failures
are retained; their cold-cache parent bug is fixed, not hidden. Current local
CUDA tests passed3in91.17s and real TUM test passed1in4.07s. PUBLICATION.md and
API observations separate public source/hosted CPU checks from local CUDA and
real-capture evidence. All named required PLAN gates are now supported, with
optional M7/unsupported targets explicitly unchanged. Final tag/remote recheck
follows this documentation-only completion commit.

### Final remote state verified

2026-10-30: Main and annotated v0.0.1 both resolve to4b5ffac. Actual hosted runs
41003523510 and41003523291 completed successfully for the final publication
commit. All4jobs passed on both runs. Later documentation-only corrections
remove stale hosted-CI/storage wording; no runtime/test code is changed. Public
repository visibility, branch/tag hashes and clean working tree were checked.
The supported full project scope M0–M6 is delivered; optional M7 remains unselected.

### GitHub attribution correction

2026-10-30: Verified GitHub account phongviet ID162717702. All60 original commits
were rebuilt with phongviet's noreply identity; every tree/date/message and graph
parent relationship was checked. Future repository-local commits use that identity.
Added immutable old-to-new source aliases for historical experiments, with tests
for lookup when original objects are absent and invalid alias rejection. Five
history/analysis unit tests passed; actual frozen45-stage/216-row inspection
passed unchanged. Fresh-clone source-pin verification and leased remote update
follow. Original backup bundle remains ignored locally.

### Reconstruction-quality study specification (new task)

2026-10-30: Reviewed worker, adapter/config contracts and reconstruction/evaluation
protocols. Existing baseline is1200steps, SH1,40kcap, RGB L1+0.05supported depthL1;
only final model saved. Wrote focused hypotheses/controls/compute/acceptance plan
and tracker under refine-logs/reconstruction-quality-1 before new training. All
runs remain unexecuted; no new quality claim. Current historical outputs stay
read-only, and previously inspected test results are excluded from selection.

### Reconstruction-quality implementation gate

2026-10-30: Added opt-in strict loss/depth/checkpoint/memory controls; differentiable
objectives; cumulative convergence/timing records; reloadable parameter snapshots;
source/config/data/history seals; immutable stage ledger; complete-validation
selection; automatic cost/quality/seed-delta/SD tables, Pareto/convergence figures
and deterministic actual-image failure montages. No historical output was edited.

Verification before TUM dispatch: Torch CPU analytic objectives/gradients passed;
four actual GPU tests passed (including each photometric mode and snapshot tensor
identity/reload/render); seeded gsplat CUDA witness passed on GTX1660Ti. Eight
focused study tests passed, including held-out pixel exclusion and protocol/source/
history mutation detection. Frontend5 tests/build and CLI smoke passed. Final full CPU
regression:189 passed/4 GPU-skipped; lint and formatting passed before sealing.
No new TUM metric or improvement claim is made here.

### Reconstruction-quality study closure (2026-10-31)

The frozen study executed on 2026-10-30 from clean source 15d783b:24 training runs,
79,200 updates,67 complete validation evaluations/1,072 pairs; all 91 stages
completed. No candidate/test observations selected settings. All143 frozen source
hashes and 5,458 historical file hashes remained unchanged. No simulation/frontend
features were added.

The rule selected L1+SSIM/3,600 for all three seeds: mean validation LPIPS 0.24201
versus matched control 0.28287. Gaussian count and optimization time also increased;
masked depth MAE was slightly worse. Cap20k, SH0 and depth-off LPIPS regressions,
relative-depth's mixed result, SSIM regressions and visible holes/blur remain in
[results](RECONSTRUCTION_QUALITY_RESULTS.md). These are exposed-sequence validation
observations, not fixed-density causal effects or independent-test quality claims.

Numerical replay reproduced all 1,072 RGB/depth/detector calculations and selection,
re-aggregated saved LPIPS, and checked 132 allowed observation files. Cached-stage
verification passed without retraining. A separate fresh same-family audit also
verified nested hashes/aggregates/checkpoints and ten CPU LPIPS forwards (maximum
saved-GPU difference 4.47e-8). Overall semantic verdict is WARN/provisional for
support conditioning, count/runtime mediation and limited validation scope.
The original report's seed42-only baseline flag is preserved; a new supplement
checks seeds43/44 as well, all within the predeclared tolerances.

Original pre-training test stdout is in the parent execution transcript; it was
not saved as raw repository logs. During closure, separately labeled durable
post-run JUnit/logs captured 189 CPU passes (four GPU skips), four actual CUDA
passes, lint/formatting, frontend 5 tests/build and CLI smoke. Hosted implementation
CI 41049601408 passed all four jobs. Curated evidence excludes dataset imagery and
learned scene parameters; full local reports/montages remain Git-ignored.

### Improvement workstream intake (2026-10-31)

Read the supplied research/UI/documentation brief, reviewed the existing plan,
frontend, experiment/configuration inventory and resource accounting. Created
IMPROVEMENT_PLAN.md before implementation, with independent-scene controls,
validation-only densification, annotation-access gate, workstation tokens/layout
and acceptance criteria. Read the mandatory design skill instructions and the
sidebar-07 reference. README now separates actual capabilities, validation and
recapture results, demo setup, GPU setup and limitations; personal resource and
commit-date narrative was removed from its public copy. Functional guards and
historical scientific records are preserved. Research execution and UI redesign
remain pending; no new results or screenshots are claimed.

First workstation-shell slice: implemented collapsible workflow/scene navigation,
shared controls, graphite tokens, local Inter, lazy workflow chunks and corrected
stale shell text. Stable-build browser regression:9 passed; targeted desktop/mobile
visual check:1 passed after adding framebuffer-readiness assertions. Inspected both
screenshots. Five frontend unit tests and build passed. See
WORKSTATION_DESIGN_REVIEW.md for remaining accessibility/view-specific work and the
invalid mixed-build baseline failure. Full improvement brief is not complete.
The previous optimized policy is frozen in evidence/improvement-intake/frozen-policy.json.
Independent-sequence and extended-densification runs have not been executed.
Trustworthy annotated-data access or actual human review remains unresolved.

### Research-extension input and implementation gate (2026-10-31)

Official ScanNet access requires an agreement/request; no authorized subset was
confirmed locally or in the official repository tree. Used the user-authorized TUM
fallback. Downloaded official fr1 room/fr2 desk archives with observed hashes.
Fr1 room imports successfully. Fr2 initially failed on two conflicting poses at
one timestamp; preserved the failure/protocol in improvement-data-1, documented
an input-integrity amendment, excluded both ambiguous records, retained original
GT/calibration provenance, and recovered under improvement-data-2. No poses were
arbitrarily chosen and no test-driven policy change was made.

Both datasets have256 frames and frozen112 train/32 validation/48 candidate/64 test
splits. Only16 designated candidate pilots per capture were inspected for
qualitative vocabulary coverage. The pilots contain plausible selected COCO
objects, but no human-verified boxes/counts or AP numbers are claimed.

Implemented offline COCO box editing/review with explicit per-frame checks,
draft import/export, local recovery and hash-bound human approval; production
packages remain pending_human_review. Added pycocotools2.0.11 as an isolated CPU
optional extra, official AP50 matching, per-class results, recall/misses and paired
render-minus-real evaluation. Missing/incomplete approval blocks accuracy. This
is a tested pipeline, not executed real-data ground-truth accuracy.

Acceptance before primary study freeze:205 CPU tests passed/four GPU skips;
four actual CUDA tests passed; fresh kernel witness passed. Separate engineering
40-step preflights trained/reloaded both real captures and evaluated32 validation
views each; these are excluded from the27-run primary matrix. Six frontend unit
tests/build and11 browser tests passed, including draft-review gating, URL state,
contextual inspector and deletion undo. One review test initially expected a
hidden edit control; it now navigates to Workspace and retains the same explicit
reviewer-permission assertion. No failing permission assertion was removed.

Primary independent-scene/densification measurements have not started at this gate.
Protocols, source/config/data seals and immutable failure handling precede them.
