# M0 acceptance criteria

- [x] Inspect existing repository, OS, CPU, memory, GPU/VRAM, CUDA, runtimes, disk.
- [ ] Package, CLI, README, AGENTS.md, CPU CI, pytest and Ruff initialized.
- [ ] React/TypeScript frontend shell builds and clearly labels M0 scope.
- [ ] Typed v1 dataset and scene contracts reject unsupported versions and bad inputs.
- [ ] Tiny analytic synthetic scene includes RGB, metric depth, poses, mesh.
- [ ] Camera/depth tests: intrinsics resize, invalid depths, proper rigid transforms,
      world/camera round trip, projection/unprojection, backend conventions.
- [ ] Files validated: missing/corrupt frames, dimensions, units, timestamps, poses.
- [ ] Immutable exhaustive split IDs, no overlap, hashes detect edits.
- [ ] Official public RGB-D sample downloaded with checksum and bounded size,
      imported with supplied pose/calibration provenance, validated on CPU.
- [ ] CLI smoke tests include success and actionable failure; repeat import refuses overwrite.
- [ ] CPU suite, Ruff, frontend checks pass; record actual commands and counts.
- [ ] Entire project stays below 30,000,000,000 bytes, including local dependencies.
- [ ] M1+ remain unimplemented; limitations and next task documented.
