# M0 acceptance criteria

- [x] Inspect existing repository, OS, CPU, memory, GPU/VRAM, CUDA, runtimes, disk.
- [x] Package, CLI, README, AGENTS.md, CPU CI, pytest and Ruff initialized.
- [x] React/TypeScript frontend shell builds and clearly labels M0 scope.
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
- [x] M1+ remain unimplemented; limitations and next task documented.

Acceptance date: 2026-10-29. Result: 80 CPU tests and 1 frontend test pass,
lint/format and frontend build pass; real import and manual CLI/HTTP smoke verified.
The official sample was later identified as synthetic Redwood/ICL-NUIM. Earlier
references to a real import were wrong; see the correction in `PROGRESS.md`.
Real Kinect integration is covered separately by M1's TUM path.
Commands and evidence are in `PROGRESS.md`. CI is configured but has not run on
a host. No GPU, reconstruction, scientific performance or browser visual
verification is implied by this checklist.
