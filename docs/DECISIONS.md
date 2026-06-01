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
