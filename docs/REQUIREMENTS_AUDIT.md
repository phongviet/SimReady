# PLAN.md completion audit — local gates verified, publication open

Audited2026-10-30 against the current source and local artifacts. This is a
requirements ledger, not a declaration that shipping is complete. PASS means the
listed evidence supports that limited requirement; OPEN remains work; FALLBACK
identifies an explicit tested alternative/unsupported boundary allowed by PLAN.md;
OPTIONAL does not block P0/P1. Current-source final regression and credential/Git review are now recorded in
FINAL_VERIFICATION.md. Publication remains unverified; do not mark the whole
project complete while it remains open.

## Priority requirements and user stories (PLAN1–2)

| Requirement | State | Evidence / exact scope |
|---|---|---|
|P0.1 posed real/synthetic import and validation|PASS|data/schema.py, tum.py, synthetic.py; real100-frame TUM validation; M0_REVERIFICATION.md|
|P0.2 actual reproducible3DGS/checkpoint/portable artifact|PASS|M1_CHECKLIST.md; real17,828-Gaussian baseline; artifact hashes in m6-training-views.json|
|P0.3 specified-camera RGB/depth|PASS|gsplat.py frozen and custom render paths; actual CUDA HTTP pipeline test; PIPELINE_API.md|
|P0.4 interactive scene/orbit|PASS|Viewer.tsx; actual pixels/orbit browser test; fresh checkout7-browser acceptance|
|P0.5 rigid proxy add/translate/rotate/scale/delete/persistence|PASS|SceneStore revisions; editor test and real walkthrough; original splats immutable|
|P0.6 frozen PSNR/SSIM/LPIPS/depth/detection agreement|PASS|M3 report/protocol, runner.py, metric tests; actual18 real test views|
|P0.7 per-view failures and JSON/CSV/HTML export|PASS|EvaluationExplorer, report assets, M3_FAILURE_CASES.md; actual downloads|
|P0.8 draft/submit/approve/reject/audit|PASS|review/workflow.py; unauthorized/self-review tests; browser review/export fixture|
|P0.9 documented CPU demo|PASS|FRESH_INSTALL.md; fresh wheel + independent CPU checkout; saved assets, no live CPU inference|
|P0.10 genuine reconstructed scene product demo|PASS|WALKTHROUGH.md;50.8s real TUM clip, verified playback and213 export payloads|
|P1.1 independent coarse collision geometry|PASS|training-only TSDF; geometry/tsdf.py; M2 acceptance; coarse/open surface explicitly labeled|
|P1.2 footprint/grid/waypoints/collision/replay|PASS|simulation modules/tests; SIMULATION_PROTOCOL.md; actual route/replay|
|P1.3 two obstacle variants and comparison|PASS|run_navigation_layouts.py; configs/navigation_layouts.json; M4 evidence baseline/box/barrier|
|P1.4 readiness components/unknown regions|PASS|evaluation/readiness.py; coverage/depth/geometry flags; unknown floor blocked|
|P1.5 named scoped review/camera region|PASS|REVIEW_PROTOCOL.md; immutable scope/reason/history; automated local roles, not human endorsement|
|P2.1–5 allowed risk inputs, equalK, equal compute, shared tests/seeds, failures|PASS|RECAPTURE_PROTOCOL.md; clean frozen run6947fb8; M5_RESULTS.md; negative outcome and fresh audit WARN|
|P3 dynamic agents, removal, weather, USD/external simulator|OPTIONAL|PLAN explicitly optional afterM6; none claimed; M7 not selected|
|Objective1 new reviewer launches, edits/reloads, evaluates/reads reports|PASS|fresh CPU browser path + saved reports; fresh GPU evaluation has separate actual acceptance; no GPU inference implied on CPU|
|Objective2 scientific masks/units/no leakage/raw predictions|PASS|frozen hashes/access gates, EVALUATION_PROTOCOL.md, raw M5 audits; temporal dependence disclosed|
|Objective3 tests in CI|PASS locally / hosted OPEN|workflow config plus local CPU/GPU/frontend/browser evidence; no remote/hosted run|
|Objective4 source/split/config/seed/version/Git/GPU/timing|PASS|artifact/evaluation/study manifests and pinned outputs; raw chronology limitations retained|
|Objective5 honest feature/result claims|PASS with ongoing audit|negative/undefined results retained, no fixtures mislabeled as real; M6 remains open|
|Builder1–5 import/reconstruct, inspect, edit, evaluate, simulation/export|PASS|CLI/API pipeline, editor, evaluation/review modules; explicit registration joins model/collider|
|Reviewer1–4 inspect, compare configurations, scoped decisions, export|PASS|failure explorer, revision/configuration histories and measured layout comparison; separate roles|
|Researcher1–3 reproduce, matched metrics, risk/true errors|PASS qualified|main real study + separate labeled bench companion; saturated true-error endpoint is undefined, not a successful predictor|

## Architecture, stack, data and reconstruction (PLAN3–6)

| Requirement / named target | State | Evidence / adaptation |
|---|---|---|
|Renderer/collision/editor/validator/simulation/workflow separation|PASS|ARCHITECTURE.md and corresponding source modules; no splat-as-solid assumption|
|SceneImporter.ingest design target|PASS adaptation|atomic import_tum/import_redwood/make_synthetic functions and versioned dataset contract; no third-party class assumption|
|ReconstructionBackend train/render|PASS|typed Protocol, GsplatBackend; supplied-camera method now declared too|
|GeometryBackend build_collision_proxy design target|PASS adaptation|build_tsdf function and versioned geometry artifact; independent training-only source|
|PerceptionBackend.predict design target|PASS adaptation|versioned JSON/NPZ worker boundary, pinned inference implementation; CPU environment does not import torch|
|Evaluator.evaluate / SimulationBackend.run design targets|PASS adaptation|evaluation.runner.evaluate / SimulationStore.run and artifact contracts|
|Supported locked Python/TS/FastAPI/SQLite/React/Three stack|PASS|uv.lock, package-lock, ENVIRONMENT.md; CPU3.12/GPU3.10 supported split|
|Maintained upstream Gaussian rasterizer/densification|PASS|gsplat DefaultStrategy adapter; no invented rasterizer or requirement for Nerfstudio itself|
|Mypy gradual / MLflow optional|OPTIONAL|runtime typed validation/Ruff/TS/tests implemented; these optional tools are not claimed|
|Docker Compose preferred deployment|FALLBACK|actual WSL command reports engine integration unavailable; tested native deployment in DEPLOYMENT.md; no container claim|
|GPU6GB budget/OOM/unsupported worker|PASS|conservative presets, actual witnesses, persisted worker failures; hardware scope in GPU_SETUP.md|
|Licenses/model/data/privacy|PASS locally|LICENSE, THIRD_PARTY.md, source manifests/weight digests; no raw Redwood/weights committed; public publication review still open|
|Data-source priority synthetic/public posed RGB-D|PASS|analytic, synthetic Redwood, real TUM; personal/Replica/video/LiDAR are optional later sources|
|Canonical manifest/frames/splits/calib/RGB/depth/masks|PASS|strict versioned schema; optional masks/distortion unsupported and disclosed, not fabricated|
|Metric RH Y-up / OpenCV c2w / conversions/roundtrips|PASS|data/camera.py and camera tests; browser known-marker parity test|
|Immutable pretraining train/validation/candidate/test|PASS|SHA-bound manifests/splits; new datasets for changes; data split only revalidates|
|Near-duplicate/spatial separation/pose overlap|PASS qualified|trajectory blocks and pose bins; no duplicate detector or independent-scene claim; limitations explicit|
|Candidate/test pixel access rules|PASS|research phase-scoped materialization and sealed selection; local owner is outside sandbox threat model|
|All ingestion checks: paths/time/association/dimensions/depth/pose/scale/hashes/dynamics|PASS|dataset/tum/archive/acquisition tests; source calibration/dynamic/exposure limits recorded|
|smoke/local_6gb presets|PASS|configs and actual CUDA runs|
|quality_cloud preset target|FALLBACK|no cloud compute configured; deliberately unsupported, documented in CLI.md; tested local/saved-demo alternatives|
|Initialization/densification/config/seed/memory/time/count provenance|PASS|artifact.json/train-job.json/training-log.jsonl/worker metadata; allocator limits explicit|
|Portable PLY dialect/attributes/reload|PASS|Graphdeco SH export validation and actual reload/render witness|
|Train AND held-out sample renders|PASS|new50 training cameras/150 channel files verified in m6-training-views.json; original18 frozen test cameras|
|TSDF scale/alignment/box intersection|PASS|independent geometry, SAT tests and real layout replay; no solid occupancy or GT geometry accuracy claim|
|Manual colliders / shared transform / immutable base edits|PASS|proxy object contract, SceneStore revisions, scene tests and actual UI|
|Depth-aware insertion OR explicit overlay-only fallback|FALLBACK|permitted PLAN alternative: visible overlay warning; excluded from photorealistic edited-scene metrics|

## Scene/API/UX (PLAN7–8)

Portable package targets are adapted to the actual registry layout documented in
SCENE_PROTOCOL.md and reviewed ZIP: separate reconstruction, collision geometry,
objects/scenarios, evaluation, navigation, review/audit and hash manifest. SQLite
is authoritative; atomic snapshots and immutable historical revisions preserve
approved state. Tests cover stale writes, content tampering and version invalidation.

All thirteen minimal HTTP targets exist under `/api/v1`: health, scenes,
scenes/import, scenes/{id}/reconstruct, jobs/{id}, scenes/{id}, scenes/{id}/render,
scenes/{id}/objects, scenes/{id}/evaluate, scenes/{id}/reports/{run_id},
scenes/{id}/scenarios/run, scenes/{id}/submit, scenes/{id}/review. Inspect
api/app.py and PIPELINE_API.md. Import/reconstruction/custom render have actual
subprocess/CUDA HTTP acceptance; scientific evaluation has actual GPU acceptance;
other actions are exercised by integration/browser/real walkthrough evidence.
Structured errors/request IDs, path restrictions, streaming allowlisted assets,
server-bound roles, self-review prohibition and persistent failures are tested.

| UX requirement | State | Evidence / remaining action |
|---|---|---|
|Scene Library source/review state|PASS|scene cards and review filter|
|Scene Library thumbnail/reconstruction state/latest evaluation|PASS|SceneCard uses saved-render thumbnail, registered scene status and latest base QA with source revision;8-browser acceptance|
|3D editor camera controls/reference selection/collider/scenario|PASS|App/Viewer/SimulationPanel; numerical + visual acceptance|
|Reference camera PATH overlay|PASS|bounded tested-camera centers/polyline; independent -R^Tt check, toggle/fallback and inspected screenshot; segments do not establish coverage|
|Evaluation real/render/residual/depth/overlays/distribution/failure sort|PASS|EvaluationExplorer and browser/download tests|
|Readiness view components/camera region/limits/scenarios/scope|PASS|ReviewPanel, measured coverage diagnostics, actual real-scene recording|
|Review queue reject/approve/reason/log|PASS|separate roles, immutable audit tests and UI|
|P2 research dashboard/comparison/provenance|PASS|ResearchDashboard, measured snapshot/full package and browser checks|
|Approval badge links to version/scope/time|PASS|badge opens review; captured decision and audit include source/approved versions and timestamps|
|Observed/tested/unknown distinction and unsupported labels|PASS|saved tested cameras, unverified free-view/custom cameras, blocked unknown floor, visible overlay/coverage limitations|
|Report and scene manifest downloads|PASS|verified report routes and reviewed package manifest; no arbitrary filesystem URLs|
|Backend/frontend marker projection parity|PASS|Python/Three.js shared numerical witness tests; actual saved-camera wireframes|
|Browser rendering kept separate from scientific metrics|PASS|separate Spark/gsplat paths and visible scope labels|

## Experiments/statistics (PLAN9–10)

| Requirement | State | Evidence |
|---|---|---|
|E0 transforms/pose/dimensions/visible box/collider|PASS|camera/scene/geometry tests and actual editor/recording|
|E1 paired image/depth/detector metrics/ranking/counterexamples|PASS qualified|M3 failures + M5 E1 raw results; undefined correlation retained when disagreement is constant|
|E1 true detection errors on labeled subset|PASS qualified|separate authored bench companion with exact masks/boxes; six correlated views, saturated endpoint; no real GT accuracy|
|E2 distance/orientation bins and unverified extrapolation|PASS|common-base pose bins/blocks in M5; custom views explicitly ineligible for accuracy|
|E3 two edit variants/same planner/full logged metrics|PASS|real baseline/box/barrier layouts, source/config hashes, route/zero-collision results|
|E4 sealed risk/random/farthest equalK/steps/resolution/seeds/shared tests|PASS|three seeds,12 models,45 actual stages; negative outcome and original frozen evidence|
|Statistical hygiene: correlated frames/counts/seeds/variation/missing/thresholds|PASS|M5 report seed SD, pose blocks, null/empty bins; no independent-frame CI/significance|
|Benchmark output contract filenames|PASS adaptation|M5 analysis exports config.yaml, environment/Git/input pins, per_view.csv, prediction JSONL, summaries/figures/reports; nested immutable raw artifacts retain exact provenance|
|Navigation footprint/grid/start/goal/waypoints/timing/replay/unknown/seed|PASS|scenario schema, inflated A-star, swept checks, saved trajectory; tests and real run|
|Backend-neutral external simulator/USD adapter|OPTIONAL|P3 only; no external simulator package-load or closed-loop claim|

## Repository, milestone gates and automation (PLAN11–18)

| Named requirement | State | Evidence / next action |
|---|---|---|
|README/PLAN/AGENTS/pyproject/locks/CI/configs/module separation|PASS|tracked files and actual installed/build evidence|
|scripts fetch/prepare/benchmark/demo targets|PASS adaptation|fetch scripts + CLI import/synthetic/scene demo; run_benchmark.py; walkthrough tooling|
|docs architecture/data/evaluation/decisions/progress/limitations/CV|PASS|all named documents exist; CLI.md/DEPLOYMENT.md clarify adaptations|
|Data/artifacts/experiments/dependencies/caches/builds ignored|PASS locally|.gitignore and current Git status; entire-history scan passed through tested source22afb45|
|M0 all tasks/DoD|PASS|M0_CHECKLIST.md, M0_REVERIFICATION.md; preserved later work|
|M1 all tasks/DoD|PASS|M1_CHECKLIST.md, actual real source, isolated worker and saved CPU demo|
|M2 all tasks/DoD|PASS|M2_CHECKLIST.md; actual metric edits/collider alignment/reload/occlusion disclosure|
|M3 all tasks/DoD|PASS|M3_CHECKLIST.md; actual18-view evaluation and nine inspected failures|
|M4 all tasks/DoD|PASS|M4_CHECKLIST.md; real layout/QA/review/export evidence|
|M5 all tasks/DoD|PASS qualified|M5_CHECKLIST.md, real negative result, companion, audits; no novelty claim|
|M6 tests/UX/data integrity|PASS|179CPU/3CUDA checks and fresh8-browser/5-unit acceptance passed; FINAL_VERIFICATION.md|
|M6 all CLI/setup/data/license docs and architecture|PASS incremental|CLI25 help entries, license wheel inclusion, current protocols; CLI25 entry points, wheel and local link review passed|
|M6 recording/examples/results/README|PASS|WALKTHROUGH.md; actual50.8s clip; failure cases, figures and benchmark links|
|M6 memory/train/render/evaluation/API measurements|PASS|BENCHMARK_RESULTS.md with raw samples, exclusions and historical training metadata|
|M6 fresh install/fallback/unsupported labels|PASS|fresh wheel/checkout, missing-worker persistence, saved views; DEPLOYMENT.md|
|M6 CV_EVIDENCE|PASS|only traceable local claims and measured scopes|
|M7 choose one extension only afterM6|OPTIONAL|explicitly not selected; does not block core release|
|Initial target CLI commands|PASS adaptation|CLI.md +25 actual help subprocesses; explicit output/reference paths; split validation and report location semantics disclosed|
|Make setup/test/demo/benchmark, GPU opt-in skip|PASS|Makefile, actual runs and test markers|
|QA matrix schema/geometry/reconstruction/metrics/matching/editor/UI/jobs/review/sim/protocol|PASS incremental|tests/unit + integration + browser; final CPU/CUDA/frontend/browser regression passed|
|QA CI CPU install/build/sample report|PASS locally / hosted OPEN|fresh installed environments, report/browser acceptance, workflow config; no hosted run|
|Research references/literature integrity|PASS qualified|related-work comparison in M5; no novelty claim; no false baseline reproduction|
|Public repository + code/licenses/tests/configs/fetch/reproduce|OPEN|local materials ready; no remote/account destination configured, no publication claimed|
|Working captured reconstruction/web demo/dataset report/failure/limits/video|PASS|real walkthrough, M3/M5 evidence, FRESH_INSTALL and limitations|
|Git date range June–October2026|PASS locally|first assigned June1, latest actual October30; assignment disclosed; final history scan passed|
|Total storage<30,000,000,000bytes|PASS incremental|combined project/legacy-temp accounting<18GB; final evidence/postflight recorded|
|Incremental execution, verified claims and milestones|PASS ongoing|focused commits, checklists, raw evidence; project remains active until remaining gates are resolved|

## Concrete remaining work

1. UI gaps above are now implemented and verified in8 browser tests. Preserve
   thumbnail/latest-base-QA scope and tested-center/unknown-coverage labels.
2. Current-source full CPU/GPU/frontend/browser regression passed; see
   FINAL_VERIFICATION.md and the retained warnings/scopes.
3. Git/content/export/link/package/storage audits passed through tested source
   22afb45. Source archives retain exact release/tested revisions and checksums.
4. Resolve public repository destination/account only after local release is
   concrete and reviewable. No hosted CI or public URL is asserted in advance.

This audit retains the full objective. Optional/unsupported boundaries are
explicit PLAN-authorized alternatives, not hidden claims of implementation.
