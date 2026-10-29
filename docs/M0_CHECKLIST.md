# M0 acceptance criteria

- [x] Inspect existing repository, OS, CPU, memory, GPU/VRAM, CUDA, runtimes, disk.
- [x] Package, CLI, README, AGENTS.md, CPU CI, pytest and Ruff initialized.
- [x] React/TypeScript frontend shell built at M0 acceptance (later milestones
      have subsequently extended it).
- [x] Typed v1 dataset and scene contracts reject unsupported versions and bad inputs.
- [x] Tiny analytic synthetic scene includes RGB, metric depth, poses, mesh.
- [x] Camera/depth tests: intrinsics resize, invalid depths, proper rigid transforms,
      world/camera round trip, projection/unprojection, backend conventions.
- [x] Files validated: missing/corrupt frames, dimensions, units, timestamps, poses.
- [x] Immutable exhaustive split IDs, no overlap, hashes detect edits.
- [x] Official public RGB-D sample downloaded with checksum and bounded size,
      imported with supplied pose/calibration provenance, validated on CPU.
- [x] CLI smoke tests include success and actionable failure; repeat import refuses overwrite.
- [x] CPU suite, Ruff, frontend checks pass; record actual commands and counts.
- [x] Entire project stays below 30,000,000,000 bytes, including local dependencies.
- [x] M0 delivery excluded M1+ implementation; limitations and next task documented.
      This is a historical scope statement, not the current repository status.

Acceptance date: 2026-10-29. Result: 80 CPU tests and 1 frontend test pass,
lint/format and frontend build pass; real import and manual CLI/HTTP smoke verified.
The official sample was later identified as synthetic Redwood/ICL-NUIM. Earlier
references to a real import were wrong; see the correction in `PROGRESS.md`.
Real Kinect integration is covered separately by M1's TUM path.
Commands and evidence are in `PROGRESS.md`. CI is configured but has not run on
a host. No GPU, reconstruction, scientific performance or browser visual
verification is implied by this checklist.

## Current M0 re-verification (2026-10-29)

The requested foundation already exists in Git. A fresh targeted run against the
current working tree passed **101 CPU tests** covering camera math, contracts,
splits, acquisition/storage safeguards, both import formats and CLI behavior.
The integration inputs were present: the official five-frame **synthetic**
Open3D sample and the 100-frame **real** TUM sequence both validated successfully.
All image hashes and frozen split hashes were checked with full validation.
The known-marker and 1e-12 transform round-trip assertions remain in the tests.

Ruff lint/format, `uv lock --check`, five frontend unit tests, TypeScript/Vite
production build and `git diff --check` passed. The build reports its existing
large-chunk warning. Hosted CI was not run. This targeted run is not acceptance
of the unfinished M5 changes already present in the working tree.

See [the reproducible commands and scope](M0_REVERIFICATION.md). Preexisting
M1–M4 commits and uncommitted M5 work were preserved; no later milestone was
implemented by this re-verification.
