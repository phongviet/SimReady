# M1 acceptance criteria

Actual work: 2026-10-29, after the user expanded scope to the full project.

- [x] Isolated worker spec, pinned packages, local GPU ledger and setup instructions.
- [x] Seeded CUDA matrix + Gaussian RGB/expected-depth forward/backward witness.
- [x] Fresh agent executed documented witness verbatim and confirmed it passes.
- [x] `ReconstructionBackend` interface with CPU preparation and isolated gsplat adapter.
- [x] `smoke` and `local_6gb` configurations, explicit seed and Gaussian budgets.
- [x] Initialization and losses consume only frozen training observations.
- [x] Portable Graphdeco SH PLY and safe NumPy checkpoint, content-hashed artifacts.
- [x] Actual short real RGB-D training run (40 iterations), validation-pose render.
- [ ] Actual `local_6gb` real run, checkpoint reload and frozen-test RGB/depth render.
- [ ] Saved provenance: dataset/split, source revision, configuration, timing,
      package/GPU versions, allocator peak memory, final Gaussian count.
- [ ] GPU integration test verifies checkpoint reload, PLY values and metric depth.
- [ ] Small genuinely trained analytic fixture for CPU-only artifact/render smoke.
- [ ] CPU suite, lint, frontend regression checks pass with GPU tests skipping by default.

Success means genuine learned Gaussians are saved/reloaded and rendered, not a
photorealism claim. The five-frame real sample remains an integration-only dataset.
GPU allocator memory is reported separately from driver/context overhead; the
reported PyTorch peaks are not total process or total device memory measurements.
