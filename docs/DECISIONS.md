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

10. **Real sample:** use `SampleRedwoodRGBDImages` from Open3D's official release.
    It is only 3,772,513 compressed bytes and includes five posed, registered
    RGB-D pairs. Verify publisher MD5 during inspection and pin SHA-256 in the
    downloader. Use the documented `odometry.log` c2w path rather than guess a
    direction from the other trajectory file. Source calibration and association
    files are preserved. Details and original implementation links are in
    `DATASET_PROTOCOL.md`. Real data was imported and tested locally.
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
