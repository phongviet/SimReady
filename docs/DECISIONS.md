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
