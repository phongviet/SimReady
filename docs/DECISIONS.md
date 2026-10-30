# Implementation decisions

Actual execution date: **2026-10-29 (Asia/Bangkok)**.

1. **Scope:** implement M0 only. Later component names in PLAN.md are design
   targets, not implemented interfaces. No reconstruction or evaluation claims.
2. **Runtime:** use installed Python 3.12 rather than download 3.11. Keep NumPy,
   Pillow, Pydantic, pytest, and Ruff in a uv-locked CPU environment. No Open3D,
   PyTorch, CUDA toolkit, pretrained weights, or simulator installation in M0.
3. **Git history:** no repository existed. Initialize `main` and create focused
   commits with user-requested author AND committer dates beginning June 2026
   and ending October 2026. These are assigned historical metadata, not actual
   implementation dates. This file and PLAN.md retain their actual dates. Git
   identity is repo-local `SimReady Development <simready@localhost>` because no
   user identity is configured; no remote or publication is configured.
4. **Storage:** enforce a decimal 30 GB project budget, including hidden files,
   dependencies, raw/extracted data and Git. Bound download and extraction sizes,
   use only a small official sample, and avoid large training dependencies.
5. **Frontend:** React + TypeScript shell only. Explicitly display implemented
   scope; do not add fake dashboards, rendered views, or nonfunctional controls.

Further contract and data decisions will be recorded with implementation.

6. **Coordinates:** canonical world is right-handed Y-up, meters. Camera local
   axes are OpenCV X-right/Y-down/Z-forward. Transform records are always c2w.
   gsplat and Open3D receive w2c. Three.js camera local Y-up/-Z-forward is an
   explicit right multiplication by diag(1,-1,-1,1), without changing world axes.
7. **Image resize:** integer pixel centers and half-pixel resampling convention:
   `cx' = (cx + 0.5) * sx - 0.5` (and similarly for cy). Focal lengths scale
   independently in each axis. No distortion or image resizing importer in M0.
8. **Immutability:** SHA-256 binds raw serialized split bytes to the manifest,
   frames bytes to both manifest and splits, and image bytes to frame records.
   All split groups must be nonempty, disjoint and exhaustive. Frame records,
   manifest and splits are read-only on disk. Imports refuse overwrite and stage
   atomically with an exclusive import lock. Hashes detect modification, not a
   malicious user rewriting all hashes. Future experiments must pin these hashes.
9. **Synthetic fixture:** analytic textured plane at Z=-2m, eight known camera
   poses and metric OBJ, not Gaussian reconstruction. Known calibration and
   transform tests verify mathematical correctness only.

Incremental verification: 54 CPU tests passed after implementing contracts,
fixture generation and camera math. Final acceptance will be recorded separately.

10. **Official sample (initial real classification superseded by decision 18):**
    use `SampleRedwoodRGBDImages` from Open3D's official release.
    It is only 3,772,513 compressed bytes and includes five posed, registered
    RGB-D pairs. Verify publisher MD5 during inspection and pin SHA-256 in the
    downloader. Use the documented `odometry.log` c2w path rather than guess a
    direction from the other trajectory file. Source calibration and association
    files are preserved. Details and original implementation links are in
    `DATASET_PROTOCOL.md`. This import was tested locally, but is synthetic.
11. **Reduced protocol:** use contiguous 2/1/1/1 train/validation/candidate/test
    blocks for the sample. Indices stand in for unavailable capture timestamps.
    Explicitly disclose near-neighbor overlap, supplied estimated poses and
    nominal Y-up. This validates import only; no research findings are inferred.
12. **License status:** the original Redwood page could not be fetched (HTTP 502)
    during inspection, and the sample descriptor does not establish dataset
    redistribution terms. Record unverified data terms; fetch locally without
    committing/publishing sample files. No distribution license is chosen for
    project code; the generated analytic fixture is explicitly CC0.
13. **Frontend tools:** Node 20.20.2 supports Vite 8.3.5 and Vitest 4.1.12.
    An initial Vitest 3 install produced npm vulnerability findings; replace it
    with the patched version before acceptance. `npm audit` then reported zero.
    React, TypeScript and all transitive dependencies are pinned by the npm lock.
14. **CI:** independent CPU, official-sample network integration and frontend
    jobs. The real-data test fails for an explicitly missing configured sample;
    ordinary offline tests skip it visibly. CI configuration is provided, but no
    remote exists and hosted CI execution is not claimed.
15. **Storage controls:** conservative allocated/logical accounting includes Git,
    .venv, node_modules and local caches. Make targets keep new uv/npm caches in
    the project, and fetch checks both bounded acquisition and total budget.
    Existing system/shared caches outside the project are not counted. No large
    GPU packages or model artifacts have been acquired.

16. **Expanded authorization (2026-10-29):** user requested completion of the full
    project after M0. Continue milestone gates; the original M0 acceptance remains
    historical evidence. M1 begins with the local 6 GB GPU, not paid cloud compute.
17. **M1 backend:** wrap the stable gsplat 1.5.3 CUDA rasterizer and its upstream
    DefaultStrategy densification behind a worker protocol. Nerfstudio is the
    preferred high-level option in PLAN.md, but its broad dependency set (including
    additional reconstruction and notebook stacks) is unnecessary for a canonical
    posed RGB-D adapter. This adapter reuses gsplat's algorithms, initializes from
    training-only RGB-D, and preserves metric coordinates without pose optimization.
    The official precompiled CPython 3.10 / torch2.4 / cu124 wheel avoids installing
    a CUDA compiler and keeps CPU and GPU dependencies isolated. Sources:
    https://docs.gsplat.studio/whl/pt24cu124/gsplat/ and
    https://github.com/nerfstudio-project/gsplat/tree/v1.5.3/gsplat/strategy .
18. **Source classification correction:** during visual inspection of M1's
    learned render, the Open3D sample appeared synthetic. The original Redwood
    HTTP site confirms synthetic augmented ICL-NUIM indoor scenes. The initial
    M0 `real` label was wrong; correct the importer to `synthetic`, reject legacy
    mislabeled records, annotate prior evidence, and use the official real TUM
    Kinect desk capture for the actual real-scene gate. Do not rewrite frozen
    source manifests or treat successful synthetic training as real reconstruction.
19. **M2 geometry:** use optional `open3d-cpu==0.19.0` in the CPU environment,
    not the CUDA worker. The upstream smaller Linux wheel supports NumPy 2 and
    Python3.12. Fuse only frozen training observations; use the same c2w/world
    frame as reconstruction and explicit w2c integration extrinsics. No ICP or
    scene rescaling. Export a coarse TSDF mesh plus numeric mesh arrays and hashes.
20. **M2 editor:** use Three.js + Spark (MIT, maintained WebGL2 renderer) behind
    a replaceable frontend adapter, with OrbitControls and TransformControls.
    Browser output is an inspection/overlay preview, separate from gsplat metrics.
    Use the exact same inserted-box transform for the visible mesh and collider.
21. **M2 persistence/API:** local filesystem packages hold immutable base assets
    and scene revision JSON; SQLite transactions provide atomic revision/CAS
    updates. Local FastAPI serves only registered package assets through scene IDs.
    API is loopback-only in this milestone. Review authentication/permissions and
    persistent worker jobs are later milestones; no client-only approval is exposed.
22. **M2 browser verification:** an initial screenshot caught an empty canvas despite
    successful asset loading. OrbitControls initializes its own orientation, so
    preserve the calibrated look target before constructing it. Browser acceptance
    now reads rendered pixels and tests orbit movement, rather than trusting a load
    message. Overlays use a separate render pass with a cleared depth buffer and
    remain explicitly unsuitable for scientific edited-scene evaluation.
23. **Optional-dependency tests:** Open3D brings Dash as an upstream dependency;
    disable only its unrelated pytest plugin (`-p no:dash`) so it does not alter
    this project's test runner. Geometry fusion has its own optional integration
    marker. No project warning or failing test is suppressed.
24. **M3 protocol before test measurement:** pin torchvision0.19.1+cu124
    SSDLite320 COCO_V1 and LPIPS0.1.4 Squeeze/v0.1. Full content pins and all
    preprocessing are recorded; choose Squeeze for compact local weights.
    Confidence/IoU=.5 and depth alpha=.1 are declared heuristics, never certification.
    Whole-image sRGB metrics and valid-depth errors remain separate. Hungarian
    matching prioritizes valid cardinality then IoU. Agreement is not accuracy.
    See EVALUATION_PROTOCOL.md for formulas, empty semantics and primary sources.
25. **M3 report/queue:** immutable, content-hashed reports preserve raw backend
    outputs, input camera/dataset hashes, per-view diagnostics, and source state.
    The local SQLite/process queue serializes GPU evaluation through Linux flock;
    browser edits are excluded from offline base-model metrics. Reports attach to
    a submitted scene revision without changing the immutable reconstruction.
26. **M4 navigation contract:** deterministic four-neighbor A* over a bounded
    metric XZ occupancy grid. TSDF surfaces in the configured robot-height slab
    and collidable box volumes are obstacles. Floor support is derived from
    near-horizontal TSDF triangles; unknown cells/exterior are blocked. A
    declared virtual floor is an explicit alternative for the analytic demo,
    with a required assumption note. Conservative robot-radius/cell inflation,
    swept replay checks, and exact corner events prevent tunneling/shortcutting.
    This is a coarse local simulator, not real robot or physical safety validation.
27. **Viewer activity cadence:** the M4 browser regression exposed slow saves
    while software WebGL consumed roughly eight CPU threads at a continuous
    frame loop. Cap viewer rendering at 30fps during load/interaction/replay
    activity and 5fps when idle; preserve actual pixel and orbit checks.
    This is a display cadence limit, not a measured render-throughput claim.
    Performance reports must state this cap. Full-budget scans remain intact.
28. **Budget-scan latency:** profiling found ~90,786 stat calls and substantial
    pathlib path-construction overhead in each full project scan. Use iterative
    `os.scandir`/DirEntry stat while preserving full conservative accounting,
    per-path hardlink counting and non-traversal of symlink targets. Count
    directory-symlink metadata as well (previous walk skipped those entries).
    A single local comparison against the corrected walk reference returned
    identical14,088,647,054bytes in0.496s versus2.451s. This is a diagnostic,
    not a universal speedup/API benchmark. See evidence/m4-storage-scan.json.
29. **M4 component bindings:** base-only evaluation may be reused when the model
    and frozen split are unchanged; object/scenario content and navigation must
    match the exact submitted source revision. Capture QA and content digests,
    rather than recomputing an approval from whichever report is newest.
30. **M4 local permissions:** opaque random bearer tokens with server-assigned
    Builder/Reviewer roles; separate identities and explicit self-review checks
    survive a role change. Private0600 credential bootstrap, no token HTTP endpoint.
    Reads remain local/read-only; mutation endpoints require roles. Not production IAM.
31. **M4 workflow/export:** submission and decisions create new immutable revisions
    with transactional append-only hash-chained audit. Edits invalidate current
    approval; historical scoped approvals remain inspectable/exportable. Export
    validates captured content/evidence and separates render/collision assets with
    complete payload digests and source attribution. No weights/accounts/DB exported.
32. **M0-only re-verification:** the latest request is checked against M0's exact
    definition of done. Preserve existing M1–M4 history and unfinished M5 changes;
    do not silently reset or commit unrelated work. Record current targeted checks
    separately from historical M0 evidence and correct misleading source labels.
    The June–October author/committer date range already satisfies the requested
    history range; use the actual October date for this documentation update.
33. **M5 resumption and protocol:** the active full-project goal resumes work
    after the M0 verification. Original M3 test images were already inspected;
    retain that exposure record and curate 18 additional late TUM pairs for E4.
    They remain temporally correlated with the same capture, not a new scene.
    Fix K4, three seeds, 1200 fresh steps, validation-only nonnegative ridge risk,
    random and farthest-pose controls before new test evaluation. Candidate/test
    pixels are physically omitted from learner datasets until sealed release.
34. **Observation-scoped validation:** keep default dataset validation complete;
    training explicitly checks training pixels and all metadata, pose-only render
    preparation checks metadata, and evaluation checks only its requested split.
    Reading test images merely to validate training input would violate the study
    boundary. Access scopes are recorded; partial validation is never called full.
35. **M5 negative outcome:** preserve the completed6947fb8study unchanged. Risk
    loses to random on LPIPS in all3paired seeds. Do not tune the rule or rerun
    successful arms after viewing test outputs. The rule's fitted distance and
    rotation coefficients are zero; validation association is not acquisition benefit.
36. **Research packages:** read-only HTTP serves only registered, content-verified
    study assets. The CPU demo carries an actual measured-summary snapshot with
    explicit raw-prediction/checkpoint omissions; full raw outputs remain in the
    reproducible GPU study. Research is separate from the selected editor scene.
37. **Concurrent budget scans:** retry a complete scan up to3times if files vanish
    during traversal, rather than ignoring entries or returning partial bytes.
    Repeated churn fails closed. This fixes the observed browser-cache cleanup
    race while retaining sparse/hardlink/symlink accounting and the30GB cap.


### Reference-free render requests

2026-10-30: Added bounded calibrated camera requests and durable render jobs,
sharing the existing local GPU lock. Parent reconstruction IDs must match the
scene; model and output hashes bind jobs/downloads. Custom views are marked
unverified and excluded from held-out evaluation. Actual GPU HTTP import/train/
render/download test passed (2 tests,20.02s); CPU failure/validation tests passed
(2 passed,1 GPU skip). Full M6 shipping acceptance remains open.

### M6 measurement boundaries

2026-10-30: Shipping performance uses a source-pinned harness rather than inferred
FPS from historical training time. Warm synchronized render timing excludes IO;
fresh evaluation throughput includes startup/reporting; loopback API p50/p95 uses
sequential real TCP reads. Raw samples and exact scopes accompany all summaries.
No performance target, baseline speedup or browser FPS is inferred from these runs.

### Actual real-scene walkthrough recording

2026-10-30: A fresh registry and Playwright recorder use the genuine saved TUM
model/report, metric proxy edits, observed-map replay and separate automated
local review roles. No live retraining or human endorsement is implied. Tokens
are switched in browser storage and never displayed in the recording. Source
and measured reports are preserved; new review history belongs only to this demo.

### M6 license and interface reconciliation

2026-10-30: Original project source uses MIT, matching the existing reviewed-export
notice. Authored fixtures remain CC0; TUM-derived imagery remains attributed
CC BY4.0; dependencies retain their own distribution notices. Redwood data is
not redistributed. The output manifest now preserves earlier indexed studies
when adding companion/benchmark runs. ReconstructionBackend now declares the
implemented supplied-camera method explicitly. Native local serving is the
verified deployment fallback; this WSL distro reports Docker unavailable.
